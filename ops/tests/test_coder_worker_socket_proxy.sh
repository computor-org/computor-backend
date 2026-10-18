#!/bin/bash
# The coder worker's Docker proxy refuses what makes a Docker client root.
#
# Starts coder-worker-socket-proxy (pinned image + this repo's allowlist) on a
# private internal network against the local daemon and probes it from a
# client container: the calls the worker makes must pass, container
# create/exec, volume create, the risky build parameters and image names
# outside the registry must get 403. Nothing it refuses is ever created; the
# one image it builds (FROM scratch, a label) is removed again. Requires a
# local Docker daemon; nothing is pushed anywhere.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
template="$here/../docker/coder-worker-socket-proxy/haproxy.cfg.template"
proxy_image="tecnativa/docker-socket-proxy:0.3.0@sha256:9e4b9e7517a6b660f2cc903a19b257b1852d5b3344794e3ea334ff00ae677ac2"
curl_image="${CURL_IMAGE:-curlimages/curl:8.10.1}"
cli_image="${CLI_IMAGE:-docker:28.5.1-cli}"
tag="cwsp-test-$$"
reg="localhost:5000"  # CODER_REGISTRY_HOST of the proxy; no registry needed

cleanup() {
    docker image rm -f "$reg/$tag:probe" "$reg/$tag:probe2" >/dev/null 2>&1 || true
    docker rm -f "$tag-proxy" >/dev/null 2>&1 || true
    docker network rm "$tag-net" >/dev/null 2>&1 || true
}
trap cleanup EXIT

docker network create --internal "$tag-net" >/dev/null
docker run -d --name "$tag-proxy" --network "$tag-net" --cap-drop ALL \
    --security-opt no-new-privileges:true -e "CODER_REGISTRY_HOST=$reg" \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v "$template:/usr/local/etc/haproxy/haproxy.cfg.template:ro" \
    "$proxy_image" >/dev/null

# Each probe prints "<expected> <got> <description>"; the client loop runs
# inside one container so the probes share a network namespace with nothing
# but the proxy.
probes=$(cat <<'PROBES'
200 GET /_ping
200 GET /version
200 GET /images/json
200 GET /system/df
200 GET /volumes
403 GET /containers/json
403 GET /info
403 POST /containers/create {"Image":"alpine","HostConfig":{"Privileged":true,"Binds":["/:/host"]}}
403 POST /v1.41/containers/create {"Image":"alpine","HostConfig":{"Privileged":true}}
403 POST //containers/create {"Image":"alpine"}
403 POST /images/..%2fcontainers/create {"Image":"alpine"}
403 POST /images/%2e%2e/containers/create {"Image":"alpine"}
403 POST /images/x/..%2F..%2Fcontainers/create {"Image":"alpine"}
403 POST /containers/x/exec {"Cmd":["id"]}
403 POST /exec/x/start {}
403 POST /volumes/create {"Name":"cwsp-bind","DriverOpts":{"type":"none","o":"bind","device":"/"}}
403 POST /volumes/prune {}
403 DELETE /volumes/computor_postgres-data
403 POST /images/create?fromImage=alpine {}
403 POST /images/load {}
403 POST /networks/create {"Name":"x"}
403 POST /session {}
403 POST /grpc {}
403 POST /swarm/init {}
403 POST /plugins/pull {}
PROBES
)

build_probes=$(cat <<'PROBES'
403 networkmode=host
403 network%6dode=host
403 NetworkMode=host
403 cgroupparent=foo.slice
403 remote=http://127.0.0.1:2375/
403 version=2
403 version=1&version=2
403 outputs=type=local
PROBES
)

# Image names: only under $reg (@R@), checked on build t=, tag repo=, push and
# delete. @T@ is this run's image; it is built by the 200 build probe below.
# The push of an absent image passes the proxy ("pass": anything but 403);
# dockerd answers 200 or 400 depending on its version, and pushes nothing.
name_probes=$(cat <<'PROBES'
403 POST /build?t=alpine:3
403 POST /build?t=evil.example/@T@:x
403 POST /build?t=@R@1/@T@:x
403 POST /build?t=@R@/@T@:x&t=alpine:3
403 POST /build?foo=x;t=@R@/@T@:x&t=alpine:3
403 POST /images/@R@/@T@:probe/tag?x=1;repo=@R@/x&repo=alpine&tag=3
403 POST /build?%74=alpine:3
403 POST /build?
200 POST /build?t=@R@/@T@:probe
403 POST /images/@R@/@T@:probe/tag?repo=alpine&tag=3
403 POST /images/@R@/@T@:probe/tag?repo=docker.io/library/alpine&tag=3
403 POST /images/@R@/@T@:probe/tag?repo=evil.example/x&tag=1
403 POST /images/@R@/@T@:probe/tag?repo=@R@/x&repo=alpine&tag=3
403 POST /v1.41/images/@R@/@T@:probe/tag?repo=%61lpine&tag=3
201 POST /v1.41/images/@R@/@T@:probe/tag?repo=@R@/@T@&tag=probe2
403 POST /images/alpine:3/push?tag=3
403 POST /v1.41/images/docker.io/library/alpine/push?tag=3
pass POST /v1.41/images/@R@/cwsp-absent-@T@/push?tag=x
403 DELETE /images/alpine:3
403 DELETE /v1.41/images/@R@1/x:1
200 DELETE /v1.41/images/@R@/@T@:probe2
PROBES
)
name_probes=${name_probes//@R@/$reg}
name_probes=${name_probes//@T@/$tag}

out=$(docker run --rm --network "$tag-net" -e "P=$probes" -e "B=$build_probes" \
    -e "N=$name_probes" -e "T=$reg/$tag:deny" \
    -e "H=http://$tag-proxy:2375" --entrypoint sh "$curl_image" -c '
set -u
for _ in $(seq 1 30); do wget -q -O /dev/null "$H/_ping" && break; sleep 0.5; done
echo "$P" | while read -r want method path body; do
    got=$(curl -s -o /dev/null -w "%{http_code}" --path-as-is -X "$method" \
        -H "Content-Type: application/json" ${body:+--data "$body"} "$H$path")
    echo "$want $got $method $path"
done
tar_ctx=$(mktemp); printf "FROM scratch\nLABEL cwsp=probe\n" > /tmp/Dockerfile
tar -C /tmp -cf "$tar_ctx" Dockerfile
# A registry tag first, so the parameter itself is what is refused.
echo "$B" | while read -r want query; do
    got=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/x-tar" --data-binary "@$tar_ctx" "$H/build?t=$T&$query")
    echo "$want $got POST /build?t=$T&$query"
done
echo "$N" | while read -r want method path; do
    case $path in
        */build*) set -- -H "Content-Type: application/x-tar" --data-binary "@$tar_ctx" ;;
        *) set -- ;;
    esac
    got=$(curl -s -o /dev/null -w "%{http_code}" -X "$method" "$@" "$H$path")
    echo "$want $got $method $path"
done
# Tag and push read no form body: a urlencoded repo= would beat the query.
got=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" --data "repo=alpine&tag=3" \
    "$H/images/$T/tag?repo=${T%%:*}&tag=x")
echo "403 $got POST /images/{n}/tag (urlencoded body)"
# Form parameters in a urlencoded body take precedence over the query.
got=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" \
    --data "networkmode=host&remote=http://127.0.0.1/" "$H/build")
echo "403 $got POST /build (urlencoded body)"
got=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
    -H "Content-Type: application/x-www-form-urlencoded" -H "Content-Type: application/x-tar" \
    --data "networkmode=host" "$H/build")
echo "403 $got POST /build (two content types)"
')

# The docker CLI itself: the privileged, host-root-mounting container the
# prefix-only proxy let through (alpine:3 must be local so no pull is tried).
docker image inspect alpine:3 >/dev/null 2>&1 || docker pull -q alpine:3 >/dev/null
if cli=$(docker run --rm --network "$tag-net" -e "DOCKER_HOST=tcp://$tag-proxy:2375" "$cli_image" \
        docker run --rm --privileged -v /:/host alpine:3 cat /host/etc/hostname 2>&1); then
    out+=$'\n'"403 200 docker run --privileged -v /:/host"
elif grep -qi "forbidden" <<<"$cli"; then
    out+=$'\n'"403 403 docker run --privileged -v /:/host"
else
    out+=$'\n'"403 ??? docker run --privileged -v /:/host: ${cli:0:200}"
fi

echo "$out"
failed=$(echo "$out" | awk '$1 == "pass" ? $2 == "403" : $1 != $2' | wc -l)
if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed probe(s) did not get the expected status" >&2
    exit 1
fi
echo "OK: $(echo "$out" | wc -l) probes"
