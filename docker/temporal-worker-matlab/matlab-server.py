
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

    def evalc(self, arg):
        self.connect()

        print(f"evaluate command: {arg}")
        result = self.engine.evalc(arg)
        print(result)
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
            print("Failed! Commit error message...")
            return MatlabServer.raise_exception(ei, f"command failed: {command}")

        except MatlabTerminated as e:
          return MatlabServer.raise_exception(e, "MatlabTerminated")

        except Exception as e:
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
