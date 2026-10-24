"""Seed code-server's native language-pack registry into isolated editor state.

The image adapter follows VS Code 1.139.1 LanguagePacksCache exactly: installed
identifier, version, localization paths and sequential MD5 identity/version hash.
The shipped CLI leaves that cache service lazy, so installation alone omits it.
"""

import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile



def build_german_registry(extensions_dir: Path, output_dir: Path) -> None:
    """Adapt installed native metadata, without network access or locale changes."""
    installed = json.loads((extensions_dir / "extensions.json").read_text(encoding="utf-8"))
    matches = [item for item in installed
               if item["identifier"]["id"].lower() == "ms-ceintl.vscode-language-pack-de"]
    if len(matches) != 1:
        raise ValueError("Expected exactly one installed German language pack")
    extension = matches[0]
    location = Path(extension["location"]["path"])
    if not location.is_absolute() or not location.is_relative_to(extensions_dir):
        raise ValueError("German language pack is outside the installed extensions directory")
    manifest = json.loads((location / "package.json").read_text(encoding="utf-8"))
    if extension["version"] != manifest["version"]:
        raise ValueError("Installed German language-pack version does not match its manifest")
    localizations = [item for item in manifest["contributes"]["localizations"]
                     if item["languageId"] == "de"]
    if len(localizations) != 1:
        raise ValueError("Expected exactly one German localization")
    localization = localizations[0]
    translations = {}
    for translation in localization["translations"]:
        path = location / translation["path"]
        if not path.is_file() or not path.resolve().is_relative_to(location.resolve()):
            raise ValueError("German translation path is missing or outside its extension")
        translations[translation["id"]] = str(path)
    if "vscode" not in translations:
        raise ValueError("German language pack has no core VS Code translations")
    identifier = extension["identifier"]
    digest = hashlib.md5(usedforsecurity=False)
    digest.update((identifier.get("uuid") or identifier["id"]).encode())
    digest.update(manifest["version"].encode())
    registry = {"de": {"hash": digest.hexdigest(),
                       "extensions": [{"extensionIdentifier": identifier, "version": manifest["version"]}],
                       "translations": translations,
                       "label": localization.get("localizedLanguageName", localization.get("languageName"))}}
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "languagepacks.json").write_text(json.dumps(registry), encoding="utf-8")


def seed_language_packs(source: Path, user_data_dir: Path) -> None:
    shipped = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(shipped, dict) or not shipped.get("de"):
        raise ValueError("The image has no native German language-pack registration")
    target = user_data_dir / "languagepacks.json"
    existing = json.loads(target.read_text(encoding="utf-8")) if target.exists() else {}
    if not isinstance(existing, dict):
        raise ValueError("The existing language-pack registry is not an object")
    merged = {**existing, **shipped}
    if merged == existing:
        return
    user_data_dir.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=user_data_dir, delete=False) as output:
        json.dump(merged, output, ensure_ascii=False)
        output.write("\n")
        temporary = output.name
    os.replace(temporary, target)


if __name__ == "__main__":
    if sys.argv[1] == "--build":
        build_german_registry(Path(sys.argv[2]), Path(sys.argv[3]))
    else:
        seed_language_packs(Path(sys.argv[1]), Path(sys.argv[2]))
