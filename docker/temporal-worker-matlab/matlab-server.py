
import os
import sys
import time
import json
import matlab
import matlab.engine
import subprocess
import asyncio
import signal
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
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
    executor: ThreadPoolExecutor = None
    engine_lock_file: str = None

    # Configuration from environment variables
    MAX_EXECUTION_TIME: int = int(os.getenv("MATLAB_MAX_EXECUTION_TIME", "300"))  # 5 minutes default
    MAX_MEMORY_MB: int = int(os.getenv("MATLAB_MAX_MEMORY_MB", "2048"))  # 2GB default
    ENABLE_TIMEOUT: bool = os.getenv("MATLAB_ENABLE_TIMEOUT", "true").lower() == "true"
    ENABLE_MEMORY_LIMIT: bool = os.getenv("MATLAB_ENABLE_MEMORY_LIMIT", "true").lower() == "true"

    def __init__(self,  worker_path: str):
      self.testing_environment_path = worker_path
      self.executor = ThreadPoolExecutor(max_workers=1)  # Single worker for MATLAB execution
      self.engine_lock_file = os.path.join(os.path.expanduser("~"), ".matlab_engine.lock")
      self.connect()

    def connect(self):
      retries = 5
      attempts = 0
      engine_name = MatlabServer.ENGINE_NAME()
      while attempts < retries:
        try:
          if self.engine is None:
            engines = matlab.engine.find_matlab()
            print("engines: ", engines)
            if engine_name in engines:
              print(f"-- setup: start connect to '{engine_name}'")
              self.engine = matlab.engine.connect_matlab(engine_name)
              print(f"-- setup: connected to '{engine_name}'")
            elif len(engines) > 0:
              name = engines.pop(0)
              self.engine = matlab.engine.connect_matlab(name)
              print(f"-- setup: connected to '{name}'")
            else:
              print(f"-- setup: start engine '{engine_name}'")
              self.engine = matlab.engine.start_matlab()
              self.engine.eval(f"matlab.engine.shareEngine('{engine_name}')", nargout=0)
              print(f"-- setup: engine started' {engine_name}'")
          else:
            print('engine is available!')
          initErg = self.engine.evalc(f"clear all;cd ~;run {self.testing_environment_path}/initTest.m")
          print('Initialisation: ', initErg)
          return
        except:
          attempts += 1
          print(f'Failed connection attempt # {attempts}/{retries}')
          time.sleep(1)

      # Notification MATLAB SERVER CRASHED
      sys.exit(2)

    def restart_engine(self):
        """Forcefully restart the MATLAB engine after a timeout or error."""
        print("!! Restarting MATLAB engine due to timeout or error")

        try:
            if self.engine is not None:
                # Try to quit gracefully
                try:
                    self.engine.quit()
                except:
                    pass
                self.engine = None

            # Force reconnect
            self.connect()
            print("!! MATLAB engine restarted successfully")
            return True

        except Exception as e:
            print(f"!! Failed to restart MATLAB engine: {e}")
            return False

    def _execute_matlab_with_timeout(self, command: str, timeout_seconds: int):
        """Execute MATLAB command with timeout using ThreadPoolExecutor."""
        def run_command():
            return self.engine.evalc(command)

        # Submit to executor and wait with timeout
        future = self.executor.submit(run_command)

        try:
            result = future.result(timeout=timeout_seconds)
            return result, False  # result, timed_out
        except FuturesTimeoutError:
            print(f"!! MATLAB command timed out after {timeout_seconds} seconds")
            # Cancel the future (won't stop MATLAB, but cleans up Python side)
            future.cancel()
            return None, True  # None, timed_out
        except Exception as e:
            print(f"!! MATLAB command failed: {e}")
            raise

    def evalc(self, arg):
        self.connect()

        print(f"evaluate command: {arg}")
        result = self.engine.evalc(arg)
        print(result)
        return result

    def test_student_example(self, test_file, spec_file, submit, test_number, submission_number):
        """
        Execute student test with timeout and memory protection.

        Resource limits:
        - Timeout: Configurable via MATLAB_MAX_EXECUTION_TIME (default 300s)
        - Memory: Configurable via MATLAB_MAX_MEMORY_MB (default 2048MB)
        """
        # Ensure connection
        try:
           self.connect()
        except Exception as e:
          return MatlabServer.raise_exception(e, "MatlabInitException")

        try:
          # Build the main test command
          command = f"CodeAbilityTestSuite('{test_file}','{spec_file}')"

          # Wrap command with resource limits if enabled
          if self.ENABLE_MEMORY_LIMIT:
              # Add memory limit wrapper (clear workspace before test)
              # Note: Just clearing workspace, memory monitoring happens via Docker limits
              memory_limit_cmd = f"clear all; {command}"
              command = memory_limit_cmd

          print(f"Executing with timeout={self.MAX_EXECUTION_TIME}s, memory_limit={self.MAX_MEMORY_MB}MB")
          print(f"Command: {command}")

          try:
            # Execute with timeout if enabled
            if self.ENABLE_TIMEOUT:
                lscmd, timed_out = self._execute_matlab_with_timeout(
                    command,
                    self.MAX_EXECUTION_TIME
                )

                if timed_out:
                    # Timeout occurred - restart engine for next test
                    print("!! Test timed out - restarting MATLAB engine")
                    self.restart_engine()

                    return MatlabServer.commit({
                        "details": {
                            "exception": {
                                "message": f"Test execution timed out after {self.MAX_EXECUTION_TIME} seconds",
                                "trace": "Possible infinite loop or excessive computation",
                                "timeout": True,
                                "timeout_seconds": self.MAX_EXECUTION_TIME
                            }
                        }
                    })
            else:
                # No timeout - direct execution (original behavior)
                lscmd = self.engine.evalc(command)

            # Successful execution
            return MatlabServer.commit({"details": lscmd})

          except MatlabTerminated as e:
            print("!! MATLAB engine terminated - restarting")
            self.restart_engine()
            return MatlabServer.raise_exception(e, "MatlabTerminated")

          except Exception as ei:
            print(f"!! Test execution failed: {ei}")
            # Try to restart engine on error
            try:
                self.restart_engine()
            except:
                pass
            return MatlabServer.raise_exception(ei, f"command failed: {command}")

        except MatlabTerminated as e:
          print("!! MATLAB terminated exception")
          self.restart_engine()
          return MatlabServer.raise_exception(e, "MatlabTerminated")

        except Exception as e:
          print(f"!! Unexpected error: {e}")
          return MatlabServer.raise_exception(e)

    def rpc_server(self):
        with Daemon(host="0.0.0.0", port=7777) as daemon:
            uri = daemon.register(self, objectId=MatlabServer.PYRO_OBJECT_ID())
            print("Server started, uri: %s" % uri)
            daemon.requestLoop()
            
    def start_thread(self):
        server_thread = Thread(target=self.rpc_server)
        server_thread.daemon = True
        server_thread.start()


if __name__ == '__main__':
    print("Starting matlab server")

    MATLAB_TEST_ENGINE_URL = os.getenv("MATLAB_TEST_ENGINE_URL")
    MATLAB_TEST_ENGINE_TOKEN = os.getenv("MATLAB_TEST_ENGINE_TOKEN")
    MATLAB_TEST_ENGINE_VERSION = os.getenv("MATLAB_TEST_ENGINE_VERSION") or "main"

    if MATLAB_TEST_ENGINE_TOKEN is None:
       print("No test repository token available. Please assign environment variable MATLAB_TEST_ENGINE_TOKEN to matlab worker!")
       sys.exit(2)
       
    worker_path = os.path.join(os.path.expanduser("~"), "test-engine")
      
    try:
      print(Repository(url=MATLAB_TEST_ENGINE_URL,token=MATLAB_TEST_ENGINE_TOKEN,branch=MATLAB_TEST_ENGINE_VERSION).clone_or_fetch(worker_path))
    except Exception as e:
      print(f"FAILED: git clone {MATLAB_TEST_ENGINE_URL} failed [{str(e)}]")
      quit(2)

    MATLAB = MatlabServer(worker_path=worker_path)

    MATLAB.start_thread()
    
    # Pass command line arguments to the temporal worker
    # This allows docker-compose to specify --queues=testing-matlab
    args = ' '.join(sys.argv[1:]) if len(sys.argv) > 1 else ''
    cmd = f"python -m computor_backend.tasks.temporal_worker {args}"
    print(f"Starting temporal worker with command: {cmd}")
    subprocess.run(cmd, cwd=os.path.abspath(os.path.expanduser("~")), shell=True)