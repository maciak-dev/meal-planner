import os
import socket
import subprocess
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


class NoRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def wait_for_port(host: str, port: int, timeout: float = 5.0) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.2)
            if sock.connect_ex((host, port)) == 0:
                return
        time.sleep(0.1)
    raise TimeoutError(f"Server on {host}:{port} did not start")


class AppSmokeTests(unittest.TestCase):
    def test_login_and_root_routes_respond(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "smoke.db"
            env = os.environ.copy()
            env.update(
                {
                    "ENV": "dev",
                    "APP_INSTANCE": "dev",
                    "SECRET_KEY": "dev-secret",
                    "DATABASE_URL": f"sqlite:///{db_path}",
                    "PYTHONPATH": str(ROOT),
                }
            )

            port = 8765
            proc = subprocess.Popen(
                [
                    "/var/www/meal-planner/venv/bin/python",
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(port),
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            try:
                wait_for_port("127.0.0.1", port)

                opener = urllib.request.build_opener(NoRedirectHandler())

                root_req = urllib.request.Request(f"http://127.0.0.1:{port}/", method="GET")
                login_req = urllib.request.Request(f"http://127.0.0.1:{port}/login", method="GET")
                static_req = urllib.request.Request(f"http://127.0.0.1:{port}/static/main.css", method="GET")

                with self.assertRaises(urllib.error.HTTPError) as root_err:
                    opener.open(root_req)
                self.assertEqual(root_err.exception.code, 307)
                self.assertEqual(root_err.exception.headers["Location"], "/login")

                with urllib.request.urlopen(login_req) as login_res:
                    self.assertEqual(login_res.status, 200)

                with urllib.request.urlopen(static_req) as static_res:
                    self.assertEqual(static_res.status, 200)
            finally:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
