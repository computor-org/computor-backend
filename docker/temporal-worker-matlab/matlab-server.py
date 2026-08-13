
import os
import sys
import time
import json
import matlab
import matlab.engine
import signal
import subprocess
from threading import RLock, Thread
from concurrent.futures import TimeoutError as FuturesTimeoutError
from Pyro5.api import expose, Daemon
from computor_types.repositories import Repository
from matlab.engine import RejectedExecutionError as MatlabTerminated

# MATLAB engine may raise different timeout exceptions depending on version
try:
    from matlab.engine import MatlabExecutionError
except ImportError:
    MatlabExecutionError = Exception

@expose
class MatlabServer(object):

    @staticmethod
    def ENGINE_NAME():
      return "engine_1"

    @staticmethod
    def PYRO_OBJECT_ID():
      return "matlab_server"

    @staticmethod
    def commit(value: dict):
      return json.dumps(value)

    @staticmethod
    def raise_exception(e: Exception, msg: str = "Internal Server Error"):
      return MatlabServer.commit({'details': {"exception": {"message": msg,"trace": str(e)}}})

    engine: matlab.engine = None
    server_thread: Thread
    testing_environment_path: str
    _engine_stuck: bool = False  # Flag to track if engine needs restart
    _engine_initialized: bool = False  # initTest has run on the *current* engine

    # Statements that isolate one submission from the next. Deliberately NOT
    # `clear all`: the workspace has to be clean between students, the code
    # cache does not. `clear all` empties both, so every framework class and the
    # whole +yaml package gets re-parsed and re-JITted for each submission --
    # measured at +1.8s on R2025b, against ~0.4s of actual test work for
    # itpcp.pgph.mat.simple_plot. `builtin` is used because the test engine puts
    # its own clear.m on the path, shadowing the built-in.
    RESET_STATEMENTS = (
        "cd ~",
        "builtin('clear','variables')",
        "builtin('clear','global')",
        # A test that errors out before its teardown leaves its figures open,
        # and the cost of creating a figure grows with how many already are.
        "close all force",
        # Only touches the path when a submission actually changed it.
        "if ~isempty(getappdata(groot,'codeAbilityEnginePath')) &&"
        " ~strcmp(path,getappdata(groot,'codeAbilityEnginePath')),"
        " path(getappdata(groot,'codeAbilityEnginePath')); end",
    )

    def __init__(self,  worker_path: str):
      self.testing_environment_path = worker_path
      self._engine_stuck = False
      self._engine_initialized = False
      # There is one MATLAB session behind this object and MATLAB executes one
      # command at a time, so submissions are serialised no matter what. Making
      # that explicit buys two things the implicit version does not: a timeout
      # measures how long a test *ran* rather than how long it queued, and
      # _force_restart_engine() can no longer pkill MATLAB out from under a
      # submission that is still executing in it.
      self._engine_lock = RLock()
      self.connect()

    def _force_restart_engine(self):
      """Force restart the MATLAB engine after a timeout/stuck state."""
      print("FORCE RESTART: Killing stuck MATLAB engine...", flush=True)

      # First, try graceful quit (probably won't work if stuck)
      if self.engine is not None:
        try:
          self.engine.quit()
          print("Engine quit successfully", flush=True)
        except Exception as e:
          print(f"Engine quit failed (expected if stuck): {e}", flush=True)
        finally:
          self.engine = None

      # Kill any MATLAB processes forcefully - use killall as backup.
      #
      # MathWorksServiceHost is deliberately NOT killed here. It is a
      # container-wide daemon shared by every MATLAB session (it also fronts
      # the license checkout), not part of the stuck session, and taking it
      # down just means the replacement engine has to cold-start it again:
      # measured at 4.3s -> 6.9s per restart in the R2025b worker. The startup
      # path below still clears it, where a clean slate is actually wanted.
      print("Killing MATLAB processes...", flush=True)
      os.system("pkill -9 -f MATLAB 2>/dev/null || true")
      os.system("killall -9 MATLAB 2>/dev/null || true")

      # R2025b starts a private Xvfb (3840x2160x24) plus a fluxbox for it, as
      # children of the MATLAB session. Neither matches `pkill -f MATLAB`, so
      # without this they survive every restart and pile up for the lifetime of
      # the container -- one framebuffer's worth of memory each. Safe to do
      # here because the session that owned them is already gone and the
      # replacement engine starts its own.
      #
      # The bracket around the first letter is the usual self-exclusion trick:
      # the shell os.system() spawns carries the pattern in its own command
      # line, and would otherwise match it.
      os.system("pkill -9 -f 'sys/[X]vfb/glnxa64/bin/Xvfb' 2>/dev/null || true")
      os.system("pkill -9 -f 'sys/[f]luxbox/glnxa64/bin/fluxbox' 2>/dev/null || true")

      # Clean up stale session files
      import glob
      import shutil
      session_patterns = [
          '/tmp/matlab_engine_*',
          '/tmp/MathWorks_*',
          '/tmp/.matlab_*'
      ]
      for pattern in session_patterns:
        for f in glob.glob(pattern):
          try:
            if os.path.isfile(f):
              os.remove(f)
            elif os.path.isdir(f):
              shutil.rmtree(f, ignore_errors=True)
          except Exception:
            pass

      # Wait for MATLAB to actually die - check that no engines are found
      max_wait = 10
      waited = 0
      while waited < max_wait:
        time.sleep(1)
        waited += 1
        try:
          engines = matlab.engine.find_matlab()
          if len(engines) == 0:
            print(f"FORCE RESTART: MATLAB processes terminated after {waited}s", flush=True)
            break
          else:
            print(f"FORCE RESTART: Still found engines {engines}, waiting... ({waited}/{max_wait}s)", flush=True)
            # Try killing again
            os.system("pkill -9 -f MATLAB 2>/dev/null || true")
        except Exception as e:
          print(f"FORCE RESTART: find_matlab() error (good, means no engines): {e}", flush=True)
          break

      if waited >= max_wait:
        print(f"WARNING: Could not confirm MATLAB termination after {max_wait}s, proceeding anyway", flush=True)

      print("FORCE RESTART: Cleanup complete, starting fresh engine...", flush=True)
      self._engine_stuck = False
      self._engine_initialized = False

    def _initialize_engine(self):
      """Bring a freshly started engine up to a runnable state.

      This is where `clear all` belongs: it is the one place a clean class and
      function cache is actually wanted, and the cost is paid once per engine
      rather than once per submission (see RESET_STATEMENTS).
      """
      init_file = f"{self.testing_environment_path}/initTest.m"
      print(f"Initializing test environment at {init_file}", flush=True)
      initErg = self.engine.evalc(f"clear all;cd ~;run {init_file}")
      # Remember the search path initTest built, so a submission that mangles it
      # (addpath/rmpath/restoredefaultpath in student code) cannot break every
      # later submission that shares this engine.
      self.engine.eval("setappdata(groot,'codeAbilityEnginePath',path);", nargout=0)
      self._engine_initialized = True
      print(f'Initialization complete: {initErg}', flush=True)

    def _reset_workspace(self):
      """Clean the workspace between submissions, keeping the code cache warm."""
      self.engine.eval(";".join(MatlabServer.RESET_STATEMENTS) + ";", nargout=0)

    def connect(self):
      # Check if we need to force restart due to previous timeout
      if self._engine_stuck:
        print("Engine marked as stuck from previous timeout, forcing restart...", flush=True)
        self._force_restart_engine()

      retries = 5
      attempts = 0
      engine_name = MatlabServer.ENGINE_NAME()
      while attempts < retries:
        try:
          if self.engine is None:
            # Whatever engine we end up on below is not one we have run
            # initTest against yet -- including an already-shared engine we
            # merely reconnect to.
            self._engine_initialized = False
            engines = matlab.engine.find_matlab()
            print(f"Found existing MATLAB engines: {engines}", flush=True)
            if engine_name in engines:
              print(f"-- setup: connecting to existing engine '{engine_name}'", flush=True)
              self.engine = matlab.engine.connect_matlab(engine_name)
              print(f"-- setup: connected to '{engine_name}'", flush=True)
            elif len(engines) > 0:
              # engines is a tuple, not a list, so convert to list or use indexing
              name = engines[0]
              print(f"-- setup: connecting to existing engine '{name}'", flush=True)
              self.engine = matlab.engine.connect_matlab(name)
              print(f"-- setup: connected to '{name}'", flush=True)
            else:
              print(f"-- setup: starting new MATLAB engine", flush=True)
              start_time = time.time()
              self.engine = matlab.engine.start_matlab(background=False)
              elapsed = time.time() - start_time
              print(f"-- setup: MATLAB engine started in {elapsed:.1f}s", flush=True)
              # Try to share with preferred name, but don't fail if name is taken
              # MATLAB remembers shared engine names even after process death
              try:
                self.engine.eval(f"matlab.engine.shareEngine('{engine_name}')", nargout=0)
                print(f"-- setup: engine shared as '{engine_name}'", flush=True)
              except Exception as share_err:
                # Name conflict - just use the default auto-assigned name
                print(f"-- setup: could not share as '{engine_name}' ({share_err}), using default name", flush=True)
          else:
            print('Engine is already available!', flush=True)

          if self._engine_initialized:
            self._reset_workspace()
          else:
            self._initialize_engine()
          return

        except Exception as e:
          attempts += 1
          self._engine_initialized = False
          print(f'Failed connection attempt #{attempts}/{retries}: {type(e).__name__}: {str(e)}', flush=True)

          # Clean up failed engine to ensure fresh start on retry
          if self.engine is not None:
            try:
              print("Cleaning up failed engine...", flush=True)
              self.engine.quit()
            except Exception as cleanup_error:
              print(f"Warning: Engine cleanup failed: {cleanup_error}", flush=True)
            finally:
              self.engine = None

          if attempts < retries:
            wait_time = 2 * attempts  # Exponential backoff
            print(f"Waiting {wait_time}s before retry...", flush=True)
            time.sleep(wait_time)

      # All retry attempts failed
      print("FATAL: All MATLAB connection attempts failed", flush=True)
      sys.exit(2)

    def evalc(self, arg):
        with self._engine_lock:
            self.connect()

            print(f"Evaluating command: {arg}", flush=True)
            result = self.engine.evalc(arg)
            print(f"Result: {result}", flush=True)
            return result

    def test_student_example(self, test_file, spec_file, timeout_seconds=300):
        """
        Execute student test with timeout protection.

        Args:
            test_file: Path to test YAML file
            spec_file: Path to specification YAML file
            submit: Submission identifier
            timeout_seconds: Maximum execution time in seconds (default: 300 = 5 minutes)
        """
        # Held across connect() and the test itself, so a restart triggered by
        # one submission's timeout cannot land while another is mid-test.
        with self._engine_lock:
            return self._run_student_example(test_file, spec_file, timeout_seconds)

    def _run_student_example(self, test_file, spec_file, timeout_seconds):
        """Body of test_student_example; callers must hold ``_engine_lock``."""
        try:
           self.connect()
        except Exception as e:
          return MatlabServer.raise_exception(e, "MatlabInitException")

        try:
          command = f"CodeAbilityTestSuite('{test_file}','{spec_file}')"
          print(f"Executing test with {timeout_seconds}s timeout: {command}", flush=True)

          try:
            # Execute asynchronously with background=True to enable timeout
            future = self.engine.evalc(command, background=True)

            # Wait for result with timeout
            try:
                lscmd = future.result(timeout=timeout_seconds)
                return MatlabServer.commit({"details": lscmd})

            except (FuturesTimeoutError, MatlabExecutionError) as timeout_err:
                # Timeout occurred - cancel the execution
                print(f"TIMEOUT: Test execution exceeded {timeout_seconds}s limit (exception: {type(timeout_err).__name__})", flush=True)
                try:
                    future.cancel()
                    print("Cancelled pending MATLAB operation", flush=True)
                except Exception as cancel_err:
                    print(f"Warning: Could not cancel operation: {cancel_err}", flush=True)

                # Mark engine as stuck - it will be force-restarted on next connect()
                # MATLAB is single-threaded, so if it's stuck in an infinite loop,
                # we can't send any commands to it. The only way to recover is to
                # kill the process and start fresh.
                print("Marking engine as stuck for force restart on next test", flush=True)
                self._engine_stuck = True
                self.engine = None  # Don't try to use this engine anymore

                return MatlabServer.commit({
                    "details": {
                        "exception": {
                            "message": f"Execution timeout: Test exceeded {timeout_seconds} seconds. "
                                       "This usually indicates an infinite loop in the code.",
                            "type": "TimeoutError"
                        }
                    },
                    "timeout": True,
                    "timeout_seconds": timeout_seconds
                })

          except Exception as ei:
            error_str = str(ei).lower()
            print(f"Failed! Command error: {ei}", flush=True)

            # Check if this is a timeout-related error (MATLAB may raise different exception types)
            if 'timeout' in error_str or 'timed out' in error_str:
                print("Detected timeout in exception message, treating as timeout", flush=True)
                self._engine_stuck = True
                self.engine = None
                return MatlabServer.commit({
                    "details": {
                        "exception": {
                            "message": f"Execution timeout: Test exceeded {timeout_seconds} seconds. "
                                       "This usually indicates an infinite loop in the code.",
                            "type": "TimeoutError"
                        }
                    },
                    "timeout": True,
                    "timeout_seconds": timeout_seconds
                })

            return MatlabServer.raise_exception(ei, f"command failed: {command}")

        except MatlabTerminated as e:
          return MatlabServer.raise_exception(e, "MatlabTerminated")

        except Exception as e:
          return MatlabServer.raise_exception(e)

    def rpc_server(self):
        with Daemon(host="0.0.0.0", port=7777) as daemon:
            uri = daemon.register(self, objectId=MatlabServer.PYRO_OBJECT_ID())
            print(f"MATLAB RPC server started, URI: {uri}", flush=True)
            daemon.requestLoop()

    def start_thread(self):
        server_thread = Thread(target=self.rpc_server)
        server_thread.daemon = True
        server_thread.start()


if __name__ == '__main__':
    import glob

    print("Starting matlab server", flush=True)

    # Clean up any zombie MATLAB sessions and stale files
    print("Cleaning up any zombie MATLAB sessions...", flush=True)
    try:
        # Remove any stale MATLAB engine session files from /tmp
        session_patterns = [
            '/tmp/matlab_engine_*',
            '/tmp/MathWorks_*',
            '/tmp/.matlab_*'
        ]
        cleaned_files = 0
        for pattern in session_patterns:
            for f in glob.glob(pattern):
                try:
                    if os.path.isfile(f):
                        os.remove(f)
                        cleaned_files += 1
                    elif os.path.isdir(f):
                        import shutil
                        shutil.rmtree(f, ignore_errors=True)
                        cleaned_files += 1
                except Exception as e:
                    print(f"Warning: Could not remove {f}: {e}", flush=True)

        if cleaned_files > 0:
            print(f"Removed {cleaned_files} stale MATLAB session files/directories", flush=True)

        # Kill any zombie MATLAB processes (from previous crashed sessions)
        # This is safe because we're starting fresh
        os.system("pkill -9 MATLAB 2>/dev/null || true")
        os.system("pkill -9 MathWorksServiceHost 2>/dev/null || true")
        time.sleep(2)  # Give processes time to clean up
        print("Cleanup complete", flush=True)
    except Exception as e:
        print(f"Cleanup warning (non-fatal): {e}", flush=True)

    MATLAB_TEST_ENGINE_URL = os.getenv("MATLAB_TEST_ENGINE_URL")
    MATLAB_TEST_ENGINE_TOKEN = os.getenv("MATLAB_TEST_ENGINE_TOKEN")
    MATLAB_TEST_ENGINE_VERSION = os.getenv("MATLAB_TEST_ENGINE_VERSION") or "main"

    if MATLAB_TEST_ENGINE_TOKEN is None:
       print("No test repository token available. Please assign environment variable MATLAB_TEST_ENGINE_TOKEN to matlab worker!", flush=True)
       sys.exit(2)

    worker_path = os.path.join(os.path.expanduser("~"), "test-engine")

    print(f"Cloning/fetching test engine from {MATLAB_TEST_ENGINE_URL}...", flush=True)
    try:
      result = Repository(url=MATLAB_TEST_ENGINE_URL,token=MATLAB_TEST_ENGINE_TOKEN,branch=MATLAB_TEST_ENGINE_VERSION).clone_or_fetch(worker_path)
      print(f"Test engine ready: {result}", flush=True)
    except Exception as e:
      print(f"FAILED: git clone {MATLAB_TEST_ENGINE_URL} failed [{str(e)}]", flush=True)
      quit(2)

    print("Initializing MATLAB server...", flush=True)
    MATLAB = MatlabServer(worker_path=worker_path)
    print("MATLAB server initialized successfully", flush=True)

    print("Starting MATLAB RPC server thread...", flush=True)
    MATLAB.start_thread()
    print("MATLAB RPC server thread started", flush=True)

    # Pass command line arguments to the temporal worker
    # This allows docker-compose to specify --queues=testing-matlab
    argv = ["python3.10", "-m", "computor_backend.tasks.temporal_worker", *sys.argv[1:]]
    print(f"Starting temporal worker with command: {' '.join(argv)}", flush=True)

    # Popen (not run()) so worker startup and activity logs flow through, and no
    # shell=True: `sh -c` used to sit between this process and the worker, so a
    # forwarded signal would have reached the shell instead of the worker.
    worker = subprocess.Popen(
        argv,
        cwd=os.path.abspath(os.path.expanduser("~")),
        stdout=sys.stdout,  # Forward stdout to container logs
        stderr=sys.stderr,  # Forward stderr to container logs
    )

    # Unlike the other worker images this script cannot exec the worker away —
    # it owns the in-process MATLAB engine the worker talks to over Pyro — so it
    # has to forward the stop signal by hand. Without this the worker never saw
    # SIGTERM: tini killed this process on the spot and the worker died with the
    # container mid-test. Test activities are deliberately never retried, so
    # that destroyed the run instead of draining it.
    def forward_shutdown(signum, _frame):
        print(f"Received signal {signum}, forwarding to temporal worker", flush=True)
        worker.send_signal(signum)

    for stop_signal in (signal.SIGTERM, signal.SIGINT):
        signal.signal(stop_signal, forward_shutdown)

    worker.wait()  # Wait for the worker to drain and exit
