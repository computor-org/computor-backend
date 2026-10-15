"""Every Forgejo container runs the same digest-pinned image.

forgejo-bootstrap and forgejo-keycloak-setup run the forgejo CLI against the
data and database of the main forgejo service. After an upgrade migrates the
database, an older CLI refuses to open it, so a version bump that misses one of
these services breaks the one-shot setup containers on the next `up`.
"""
import re
from pathlib import Path

import yaml

DOCKER = Path(__file__).resolve().parents[4] / "ops" / "docker"
FILES = ("docker-compose.forgejo.yaml", "docker-compose.forgejo-keycloak.yaml")
PINNED = re.compile(r"codeberg\.org/forgejo/forgejo:[0-9][^@]*@sha256:[0-9a-f]{64}")


def _forgejo_images():
    images = {}
    for name in FILES:
        services = yaml.safe_load((DOCKER / name).read_text())["services"]
        for svc, spec in services.items():
            image = spec.get("image", "")
            if "forgejo/forgejo" in image:
                images[f"{name}:{svc}"] = image
    return images


def test_all_forgejo_services_share_one_pinned_image():
    images = _forgejo_images()
    assert set(images) >= {
        "docker-compose.forgejo.yaml:forgejo",
        "docker-compose.forgejo.yaml:forgejo-bootstrap",
        "docker-compose.forgejo-keycloak.yaml:forgejo-keycloak-setup",
    }
    assert len(set(images.values())) == 1, images
    assert all(PINNED.fullmatch(i) for i in images.values()), images
