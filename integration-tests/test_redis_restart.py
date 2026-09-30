"""Run the production Redis entrypoint through a real Docker restart.

No database or public ports are needed. Authenticate after both starts and
check that the password is absent from process arguments and the config is private.
"""
import json
import os
from pathlib import Path
import secrets
import subprocess
import time
import unittest

import yaml


class RedisRestartTest(unittest.TestCase):
    def test_private_config_survives_restart(self):
        svc = yaml.safe_load((Path(__file__).resolve().parents[1] /
                              "ops/docker/docker-compose.base.yaml").read_text())["services"]["redis"]
        entrypoint = [s.replace("$$", "$") for s in svc["entrypoint"]]
        name = "computor-redis-restart-test-" + secrets.token_hex(4)
        password = secrets.token_hex(24)
        env = dict(os.environ, REDIS_PASSWORD=password)

        def docker(*args, check=True):
            return subprocess.run(["docker", *args], env=env, text=True,
                                  capture_output=True, check=check)

        try:
            docker("run", "-d", "--name", name, "--network", "none", "-e", "REDIS_PASSWORD",
                   "--entrypoint", entrypoint[0], svc["image"], *entrypoint[1:])
            for boot in range(2):
                deadline = time.monotonic() + 20
                while time.monotonic() < deadline:
                    ping = docker("exec", name, "sh", "-c",
                                  'REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli PING', check=False)
                    if ping.returncode == 0 and ping.stdout.strip() == "PONG":
                        break
                    time.sleep(.2)
                else:
                    self.fail(f"Redis did not accept authenticated PING on boot {boot + 1}")
                argv = docker("exec", name, "sh", "-c", "tr '\\0' ' ' < /proc/1/cmdline").stdout
                self.assertNotIn(password, argv)
                self.assertNotIn(password, json.loads(docker("inspect", name).stdout)[0]["Config"]["Cmd"] or [])
                self.assertEqual(docker("exec", name, "stat", "-c", "%a:%U", "/tmp/redis-auth.conf").stdout.strip(),
                                 "600:redis")
                if boot == 0:
                    docker("restart", "-t", "2", name)
        finally:
            docker("rm", "-f", name, check=False)


if __name__ == "__main__":
    unittest.main()
