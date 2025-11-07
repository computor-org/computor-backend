
import os
import sys
import time
import json
import matlab
import matlab.engine
import subprocess
from threading import Thread
from Pyro5.api import expose, Daemon
from computor_types.repositories import Repository
from matlab.engine import RejectedExecutionError as MatlabTerminated

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

    def __init__(self,  worker_path: str):
      self.testing_environment_path = worker_path
      self.connect()

    def connect(self):
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
              name = engines.pop(0)
              print(f"-- setup: connecting to existing engine '{name}'", flush=True)
              self.engine = matlab.engine.connect_matlab(name)
              print(f"-- setup: connected to '{name}'", flush=True)
            else:
              print(f"-- setup: starting new MATLAB engine '{engine_name}'", flush=True)
              start_time = time.time()
              self.engine = matlab.engine.start_matlab(background=False)
              elapsed = time.time() - start_time
              print(f"-- setup: MATLAB engine started in {elapsed:.1f}s", flush=True)
              self.engine.eval(f"matlab.engine.shareEngine('{engine_name}')", nargout=0)
              print(f"-- setup: engine '{engine_name}' shared and ready", flush=True)
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

    def test_student_example(self, test_file, spec_file, submit, test_number, submission_number):

        try:
           self.connect()
        except Exception as e:
          return MatlabServer.raise_exception(e, "MatlabInitException")

        try:
          command = f"CodeAbilityTestSuite('{test_file}','{spec_file}')"

          try:
            lscmd = self.engine.evalc(command)
            return MatlabServer.commit({ "details": lscmd})

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
    cmd = f"python -m computor_backend.tasks.temporal_worker {args}"
    print(f"Starting temporal worker with command: {cmd}", flush=True)
    subprocess.run(cmd, cwd=os.path.abspath(os.path.expanduser("~")), shell=True)
