"""The Traefik route that full maintenance mode writes (ops/lib/common.sh)."""
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_maintenance_route_rewrites_to_the_directory_not_index_html(tmp_path):
    # The static server answers ".../index.html" with "301 Location: ./".
    # Browsers resolve that against the request they sent and cache it
    # permanently, so every URL polled during the window (e.g.
    # /api/coder/workspaces -> /api/coder/ -> itself) kept looping from the
    # cache after maintenance ended (issues#602).
    script = (
        f'source "{ROOT}/ops/lib/common.sh"\n'
        f'SYSTEM_DEPLOYMENT_PATH="{tmp_path}"\n'
        "activate_traefik_maintenance\n"
    )
    subprocess.run(["bash", "-c", script], check=True, capture_output=True, text=True)

    config = (tmp_path / "traefik/dynamic/maintenance.yaml").read_text()
    assert 'path: "/_maintenance/"' in config
    assert "index.html" not in config
