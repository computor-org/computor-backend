
import os
import sys
import time
import json
import matlab
import matlab.engine
import subprocess
from threading import Thread
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

    def __init__(self,  worker_path: str):
      self.testing_environment_path = worker_path
      self._engine_stuck = False
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

      # Kill any MATLAB processes forcefully - use killall as backup
      print("Killing MATLAB processes...", flush=True)
      os.system("pkill -9 -f MATLAB 2>/dev/null || true")
      os.system("pkill -9 -f MathWorksServiceHost 2>/dev/null || true")
      os.system("killall -9 MATLAB 2>/dev/null || true")

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

          print(f"Initializing test environment at {self.testing_environment_path}/initTest.m", flush=True)
          initErg = self.engine.evalc(f"clear all;cd ~;run {self.testing_environment_path}/initTest.m")
          print(f'Initialization complete: {initErg}', flush=True)
          return

        except Exception as e:
          attempts += 1
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
        self.connect()

        print(f"Evaluating command: {arg}", flush=True)
        result = self.engine.evalc(arg)
        print(f"Result: {result}", flush=True)
        return result

    def test_student_example(self, test_file, spec_file, submit, test_number, submission_number, timeout_seconds=300):
        """
        Execute student test with timeout protection.

        Args:
            test_file: Path to test YAML file
            spec_file: Path to specification YAML file
            submit: Submission identifier
            test_number: Test number
            submission_number: Submission number
            timeout_seconds: Maximum execution time in seconds (default: 300 = 5 minutes)
        """
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
            print(f"Failed! Command error: {ei}", flush=True)
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
    args = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    cmd = f"python3.10 -m computor_backend.tasks.temporal_worker {args}"
    print(f"Starting temporal worker with command: {cmd}", flush=True)

    # Use Popen instead of run() to allow logs to flow through
    # This way we can see worker startup and activity logs
    import sys as pysys
    subprocess.Popen(
        cmd,
        cwd=os.path.abspath(os.path.expanduser("~")),
        shell=True,
        stdout=pysys.stdout,  # Forward stdout to container logs
        stderr=pysys.stderr,  # Forward stderr to container logs
    ).wait()  # Wait for worker to finish (blocks forever)
