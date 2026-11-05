"""The Traefik route that full maintenance mode writes (ops/lib/common.sh).

Every URL a browser requests during the window is answered by this route, and
whatever the browser caches from it outlives the window (issues#602).
"""
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[4]


def _maintenance_config(tmp_path):
    script = (
        f'source "{ROOT}/ops/lib/common.sh"\n'
        f'SYSTEM_DEPLOYMENT_PATH="{tmp_path}"\n'
        "activate_traefik_maintenance\n"
    )
    subprocess.run(["bash", "-c", script], check=True, capture_output=True, text=True)
    return yaml.safe_load((tmp_path / "traefik/dynamic/maintenance.yaml").read_text())["http"]


def _router_middlewares(http):
    names = http["routers"]["maintenance-catchall"]["middlewares"]
    return [http["middlewares"][name] for name in names]


def test_maintenance_route_rewrites_to_the_directory_not_index_html(tmp_path):
    # The static server answers ".../index.html" with "301 Location: ./".
    # Browsers resolve that against the request they sent and cache it
    # permanently, so /api/coder/workspaces -> /api/coder/ -> itself kept
    # looping from the cache after maintenance ended.
    rewrites = [m["replacePath"]["path"] for m in _router_middlewares(_maintenance_config(tmp_path))
                if "replacePath" in m]
    assert rewrites == ["/_maintenance/"]


def test_maintenance_responses_are_never_stored(tmp_path):
    # The page has an old Last-Modified and no Cache-Control of its own, which
    # lets a browser heuristically reuse it for /api/... for days.
    headers = [m["headers"]["customResponseHeaders"] for m in _router_middlewares(_maintenance_config(tmp_path))
               if "headers" in m]
    assert {"Cache-Control": "no-store"} in headers
