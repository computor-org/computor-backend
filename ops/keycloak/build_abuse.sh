#!/usr/bin/env bash
# Build and test the optional Keycloak provider, then atomically stage its JAR.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
destination="${1:?Usage: build_abuse.sh PROVIDERS_DIRECTORY}"
module="$here/abuse-provider"
cache="${XDG_CACHE_HOME:-$HOME/.cache}/computor-keycloak-maven"
mkdir -p "$destination" "$cache"
# Pinned Java21/Maven toolchain; all direct dependencies/plugins are pinned in pom.xml.
docker run --rm --user "$(id -u):$(id -g)" \
    -e MAVEN_CONFIG=/tmp/maven \
    -v "$module:/build" -v "$cache:/cache" -w /build \
    maven:3.9.9-eclipse-temurin-21@sha256:3a4ab3276a087bf276f79cae96b1af04f53731bec53fb2e651aca79e4b10211e \
    mvn -q -Dmaven.repo.local=/cache/repository package
stage=$(mktemp "$destination/.computor-keycloak-abuse.XXXXXXXX")
trap 'rm -f "$stage"' EXIT
install -m 0644 "$module/target/computor-keycloak-abuse.jar" "$stage"
mv -f "$stage" "$destination/computor-keycloak-abuse.jar"
sha256sum "$destination/computor-keycloak-abuse.jar"
