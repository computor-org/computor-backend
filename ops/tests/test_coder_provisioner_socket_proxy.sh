#!/bin/bash
# The Coder server's Docker proxy admits the workspace lifecycle and refuses
# what makes a Docker client root.
#
# Starts coder-provisioner-socket-proxy (pinned image + this repo's allowlist)
# on a private internal network against the local daemon and probes it from a
# client container. Positive half: the calls the kreuzwerker/docker provider
# makes for a workspace (volume create, container create with the templates'
# HostConfig, network connect/disconnect, start, stop, wait, delete) run end to
# end through the proxy. Negative half: privileged and host-namespace
# containers, host binds and mounts, foreign volumes and images, extra
# capabilities and security options, devices, body-encoding tricks, exec,
# build, pull from outside the registry and the rest get 403. Requires a local
# Docker daemon; it pulls alpine:3 and nothing is pushed anywhere.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
template="$here/../docker/coder-provisioner-socket-proxy/haproxy.cfg.template"
proxy_image="tecnativa/docker-socket-proxy:0.3.0@sha256:9e4b9e7517a6b660f2cc903a19b257b1852d5b3344794e3ea334ff00ae677ac2"
curl_image="${CURL_IMAGE:-curlimages/curl:8.10.1}"
cli_image="${CLI_IMAGE:-docker:28.5.1-cli}"
tag="cpsp-test-$$"
reg="localhost:5000"  # CODER_REGISTRY_HOST of the proxy; no registry needed
img="$reg/$tag:probe"
vol="coder-scratch-$tag"
work=$(mktemp -d)

cleanup() {
    docker ps -aq --filter "name=^coder-$tag" | xargs -r docker rm -f >/dev/null 2>&1 || true
    docker rm -f "$tag-proxy" >/dev/null 2>&1 || true
    docker volume rm -f "$vol" "coder-home-$tag" >/dev/null 2>&1 || true
    docker image rm -f "$img" >/dev/null 2>&1 || true
    docker network rm "$tag-net" "$tag-ws" >/dev/null 2>&1 || true
    rm -rf "$work"
}
trap cleanup EXIT

docker pull -q alpine:3 >/dev/null  # a stale local alpine:3 would fail the start probe
docker tag alpine:3 "$img"
docker network create --internal "$tag-net" >/dev/null
docker network create --internal "$tag-ws" >/dev/null
docker run -d --name "$tag-proxy" --network "$tag-net" --cap-drop ALL \
    --security-opt no-new-privileges:true -e "CODER_REGISTRY_HOST=$reg" \
    -e "CODER_WORKSPACE_NETWORK=$tag-ws" -e "CODER_WORKSPACE_NETWORK_OFFLINE=$tag-ws-offline" \
    -v /var/run/docker.sock:/var/run/docker.sock:ro \
    -v "$template:/usr/local/etc/haproxy/haproxy.cfg.template:ro" \
    "$proxy_image" >/dev/null

# Container create body as the provider sends it for the vscode template
# (Coder v2.37.3, kreuzwerker/docker 4.6.0), trimmed of labels it repeats.
# Go's encoder writes & and > as \u0026 and \u003e, so those stay allowed.
# @HC@ is spliced into HostConfig and @TOP@ at the top level; a duplicate key
# there is what Go decodes (the last one wins).
cat > "$work/base.json" <<'JSON'
{"Hostname":"t","Domainname":"","User":"","AttachStdin":false,"AttachStdout":false,"AttachStderr":false,"Tty":false,"OpenStdin":false,"StdinOnce":false,"Env":["CODER_AGENT_TOKEN=x"],"Cmd":null,"Image":"@IMG@","Volumes":{"/home/coder":{}},"WorkingDir":"","Entrypoint":["sh","-c","sleep 60 \u0026\u0026 echo done \u003e/dev/null"],"OnBuild":null,"Labels":{"computor.ingress":"workspace","traefik.http.routers.t.rule":"PathPrefix(`/coder/a/t`)","traefik.http.middlewares.strip-t.stripprefix.prefixes":"/coder/a/t"},"HostConfig":{"Binds":["@VOL@:/home/coder:rw"],"ContainerIDFile":"","LogConfig":{"Type":"","Config":null},"NetworkMode":"bridge","PortBindings":null,"RestartPolicy":{"Name":"unless-stopped","MaximumRetryCount":0},"AutoRemove":false,"VolumeDriver":"","VolumesFrom":null,"ConsoleSize":[0,0],"CapAdd":["CAP_AUDIT_WRITE","CAP_CHOWN","CAP_DAC_OVERRIDE","CAP_FOWNER","CAP_KILL","CAP_SETGID","CAP_SETUID"],"CapDrop":["ALL"],"CgroupnsMode":"","Dns":null,"DnsOptions":null,"DnsSearch":null,"ExtraHosts":["host.docker.internal:host-gateway"],"GroupAdd":null,"IpcMode":"","Cgroup":"","Links":null,"OomScoreAdj":0,"PidMode":"","Privileged":false,"PublishAllPorts":false,"ReadonlyRootfs":false,"SecurityOpt":["no-new-privileges:true"],"UTSMode":"","UsernsMode":"","ShmSize":0,"Isolation":"","CpuShares":0,"Memory":268435456,"NanoCpus":1000000000,"CgroupParent":"","BlkioWeight":0,"BlkioWeightDevice":null,"BlkioDeviceReadBps":null,"BlkioDeviceWriteBps":null,"BlkioDeviceReadIOps":null,"BlkioDeviceWriteIOps":null,"CpuPeriod":0,"CpuQuota":0,"CpuRealtimePeriod":0,"CpuRealtimeRuntime":0,"CpusetCpus":"","CpusetMems":"","Devices":null,"DeviceCgroupRules":null,"DeviceRequests":null,"MemoryReservation":0,"MemorySwap":268435456,"MemorySwappiness":null,"OomKillDisable":null,"PidsLimit":null,"Ulimits":null,"CpuCount":0,"CpuPercent":0,"IOMaximumIOps":0,"IOMaximumBandwidth":0,"MaskedPaths":null,"ReadonlyPaths":null,"Init":false@HC@},"NetworkingConfig":{"EndpointsConfig":null}@TOP@}
JSON
sed -i "s#@IMG@#$img#; s#@VOL@#$vol#" "$work/base.json"
base=$(cat "$work/base.json")
rest=${base#*@HC@}
printf %s "${base%%@HC@*}" > "$work/pre"
printf %s "${rest%%@TOP@*}" > "$work/mid"
printf %s "${rest#*@TOP@}" > "$work/end"

# Container create probes: "<expected>|<splice into HostConfig>|<splice at top>".
# The workspace-shaped body itself (empty splices) is the positive probe in the
# lifecycle below.
cat > "$work/create.txt" <<'PROBES'
403|,"Privileged":true|
403|,"privileged" : true|
403|,"PRIVILEGED":true|
403||,"Privileged":true
403|,"Privil\u0065ged":true|
403|,"PublishAllPorts":true|
403|,"Binds":["/:/host"]|
403|,"Binds":["\/:/host"]|
403|,"Binds":["/var/run/docker.sock:/var/run/docker.sock"]|
403|,"Binds":["@VOL@:/home/coder:rw","/:/host"]|
403|,"Binds":["@VOL@:/x]y","/:/host"]|
403|,"Binds":["@VOL@:/x\\y","/:/host"]|
403|,"Binds":[null,"/:/host"]|
403|,"Binds":"/:/host"|
403|,"Binds":["computor_postgres-data:/data"]|
403|,"bindſ":["/:/host"]|
403||,"Binds":["/:/host"]
403|,"Mounts":[{"Type":"bind","Source":"/","Target":"/host"}]|
403|,"Mounts":[{"Type":"volume","Source":"v","Target":"/v","VolumeOptions":{"DriverConfig":{"Name":"local","Options":{"type":"none","o":"bind","device":"/"}}}}]|
403|,"VolumesFrom":["computor-coder"]|
403|,"VolumeDriver":"evil"|
403|,"PidMode":"host"|
403|,"IpcMode":"host"|
403|,"UTSMode":"host"|
403|,"UsernsMode":"host"|
403|,"CgroupnsMode":"host"|
403|,"Cgroup":"container:computor-coder"|
403|,"NetworkMode":"host"|
403|,"NetworkMode":"container:computor-coder"|
403|,"NetworkMode":"computor-network"|
403|,"CapAdd":["SYS_ADMIN"]|
403|,"CapAdd":["CAP_CHOWN","cap_sys_module"]|
403|,"CapAdd":["ALL"]|
403|,"CapAdd":"SYS_ADMIN"|
403|,"SecurityOpt":["seccomp=unconfined"]|
403|,"SecurityOpt":["apparmor=unconfined"]|
403|,"SecurityOpt":["no-new-privileges:true","systempaths=unconfined"]|
403|,"SecurityOpt":["label=disable"]|
403|,"MaskedPaths":[]|
403|,"ReadonlyPaths":[]|
403|,"Devices":[{"PathOnHost":"/dev/mem","PathInContainer":"/dev/mem","CgroupPermissions":"rwm"}]|
403|,"DeviceCgroupRules":["a *:* rwm"]|
403|,"DeviceRequests":[{"Count":-1,"Capabilities":[["gpu"]]}]|
403|,"Sysctls":{"kernel.shm_rmid_forced":"1"}|
403|,"PortBindings":{"22/tcp":[{"HostIp":"0.0.0.0","HostPort":"2222"}]}|
403|,"Runtime":"io.containerd.runc.v2"|
403|,"LogConfig":{"Type":"syslog","Config":{"syslog-address":"udp://1.2.3.4:514"}}|
403|,"Links":["computor-coder:c"]|
403||,"NetworkingConfig":{"EndpointsConfig":{"computor-network":{}}}
403||,"Image":"alpine:3"
403||,"image":"localhost:5000.evil/x"
PROBES

# Everything else: "<expected> <method> <path> [json body]". "pass" = not 403.
cat > "$work/plain.txt" <<'PROBES'
200 HEAD /_ping
200 GET /_ping
200 GET /v1.51/version
200 GET /v1.51/info
200 GET /v1.51/images/json
200 GET /v1.51/containers/json?all=1
pass GET /v1.51/images/@IMG@/json
pass POST /v1.51/images/create?fromImage=localhost%3A5000%2F@TAG@-absent&tag=latest
403 POST /v1.51/images/create?fromImage=alpine&tag=3
403 POST /v1.51/images/create?fromImage=docker.io%2Flibrary%2Falpine&tag=3
403 POST /v1.51/images/create?fromImage=localhost%3A50001%2Fx&tag=1
403 POST /v1.51/images/create?fromImage=localhost%3A5000%2Fx&fromImage=alpine
403 POST /v1.51/images/create?fromImage=localhost%3A5000%2Fx&fromSrc=http%3A%2F%2Fexample.invalid%2Fr.tar
403 POST /v1.51/images/create?%66romImage=alpine&fromImage=localhost%3A5000%2Fx
403 POST /v1.51/images/load
403 POST /v1.51/build?t=localhost:5000/x
403 POST /v1.51/images/@IMG@/push
403 POST /v1.51/images/@IMG@/tag?repo=alpine&tag=3
403 DELETE /v1.51/images/@IMG@
403 POST /v1.51/volumes/create {"Name":"computor_postgres-data"}
403 POST /v1.51/volumes/create {"Name":"coder-home-@TAG@","DriverOpts":{"type":"none","o":"bind","device":"/"}}
403 POST /v1.51/volumes/create {"Name":"coder-home-@TAG@","Driver":"evil"}
403 POST /v1.51/volumes/create {"Name":"coder-home-@TAG@","name":"x"}
403 POST /v1.51/volumes/prune {}
403 DELETE /v1.51/volumes/coder-home-@TAG@
403 DELETE /v1.51/volumes/computor_postgres-data
403 POST /v1.51/containers/create?name=evil {"Image":"@IMG@"}
403 POST /v1.51/containers/create?name=coder-@TAG@-x&name=evil {"Image":"@IMG@"}
403 POST /v1.51/containers/create?name=coder-@TAG@-x&foo=1 {"Image":"@IMG@"}
403 POST //containers/create?name=coder-@TAG@-x {"Image":"@IMG@"}
403 POST /images/..%2fcontainers/create?name=coder-@TAG@-x {"Image":"@IMG@"}
403 POST /images/%2e%2e/containers/create?name=coder-@TAG@-x {"Image":"@IMG@"}
403 POST /v1.51/containers/x/exec {"Cmd":["id"]}
403 POST /v1.51/exec/x/start {}
403 POST /v1.51/containers/x/attach
403 PUT /v1.51/containers/x/archive?path=/
403 GET /v1.51/containers/x/archive?path=/
403 POST /v1.51/containers/x/update {"Memory":0}
403 POST /v1.51/containers/x/start {}
403 POST /v1.51/containers/x/start?checkpoint=c
403 POST /v1.51/containers/x/kill
403 POST /v1.51/containers/prune
403 POST /v1.51/networks/create {"Name":"x"}
403 POST /v1.51/networks/computor-network/connect {"Container":"x"}
403 POST /v1.51/networks/@TAG@-ws/connect {"Container":"x","EndpointConfig":{"Aliases":["computor-api"]}}
403 POST /v1.51/networks/@TAG@-ws/disconnect {"Container":"x"}
403 POST /v1.51/session
403 POST /v1.51/swarm/init {}
403 POST /v1.51/plugins/pull?remote=x
403 GET /v1.51/secrets
PROBES
sed -i "s#@IMG@#$img#g; s#@TAG@#$tag#g; s#@VOL@#$vol#g" "$work/plain.txt" "$work/create.txt"

cat > "$work/client.sh" <<'CLIENT'
set -u
for _ in $(seq 1 30); do wget -q -O /dev/null "$H/_ping" && break; sleep 0.5; done
code() { curl -s -o /dev/null -w "%{http_code}" --path-as-is "$@"; }
json() { code -X POST -H "Content-Type: application/json" --data-binary "$@"; }
create() { json "@$1" "$H/v1.51/containers/create?name=coder-$TAG-$2"; }
body() { cat /w/pre; printf %s "$1"; cat /w/mid; printf %s "$2"; cat /w/end; }

# Lifecycle of one workspace, end to end through the proxy.
id=coder-$TAG-ws
body "" "" > /tmp/ok.json
echo "201 $(json "{\"Name\":\"$VOL\"}" "$H/v1.51/volumes/create") volume create"
echo "200 $(code "$H/v1.51/volumes/$VOL") volume inspect"
echo "201 $(create /tmp/ok.json ws) container create (workspace body)"
echo "200 $(json "{\"Container\":\"$id\",\"Force\":false}" "$H/v1.51/networks/bridge/disconnect") network bridge disconnect"
echo "200 $(json "{\"Container\":\"$id\",\"EndpointConfig\":{\"IPAMConfig\":{},\"Links\":null,\"Aliases\":[],\"DriverOpts\":{},\"DNSNames\":null}}" "$H/v1.51/networks/$TAG-ws/connect") network connect"
echo "204 $(code -X POST "$H/v1.51/containers/$id/start") container start"
echo "200 $(code "$H/v1.51/containers/$id/json") container inspect"
echo "204 $(code -X POST "$H/v1.51/containers/$id/stop?t=0") container stop"
echo "200 $(code -X POST "$H/v1.51/containers/$id/wait?condition=not-running") container wait"
echo "204 $(code -X DELETE "$H/v1.51/containers/$id?force=1&v=1") container delete"
echo "204 $(code -X DELETE "$H/v1.51/volumes/$VOL?force=1") volume delete"

# Dangerous create bodies: the workspace body plus one splice.
n=0
while IFS="|" read -r exp hc top; do
    n=$((n + 1))
    body "$hc" "$top" > /tmp/b.json
    echo "$exp $(create /tmp/b.json d$n) create +HostConfig[$hc] +top[$top]"
done < /w/create.txt

# Body framing: oversized, padded past a 16 KiB buffer with escapes, chunked,
# compressed, wrong or no content type, a raw non-ASCII key (Go folds U+017F
# to s), a second JSON value after the first.
big=$(head -c 40000 /dev/zero | tr '\0' a)
body "" ",\"Pad\":\"$big\",\"HostConfig\":{\"Privileged\":true}" > /tmp/big.json
echo "403 $(create /tmp/big.json big) create > 32 KiB"
pad=$(head -c 12000 /dev/zero | tr '\0' n | sed 's/n/\\n/g')
body "" ",\"Pad\":\"$pad\",\"Privileged\":true" > /tmp/pad.json
echo "403 $(create /tmp/pad.json pad) create, 24 KiB of escapes then Privileged"
body "" ",\"Pad\":\"$pad\",\"Binds\":[\"/:/host\"]" > /tmp/pad2.json
echo "403 $(create /tmp/pad2.json pad2) create, 24 KiB of escapes then a host bind"
body ",\"Binds\":[\"$VOL:/x$pad\",\"/:/host\"]" "" > /tmp/pad3.json
echo "403 $(create /tmp/pad3.json pad3) create, long escaped bind then a host bind"
echo "403 $(code -X POST -H "Content-Type: application/json" -H "Transfer-Encoding: chunked" --data-binary @/tmp/ok.json "$H/v1.51/containers/create?name=coder-$TAG-chunked") create, chunked"
echo "403 $(code -X POST -H "Content-Type: application/json" -H "Content-Encoding: gzip" --data-binary @/tmp/ok.json "$H/v1.51/containers/create?name=coder-$TAG-gz") create, content-encoding"
echo "403 $(code -X POST -H "Content-Type: text/plain" --data-binary @/tmp/ok.json "$H/v1.51/containers/create?name=coder-$TAG-ct") create, text/plain"
echo "403 $(code -X POST -H "Content-Type:" --data-binary @/tmp/ok.json "$H/v1.51/containers/create?name=coder-$TAG-noct") create, no content type"
body "" ",\"HostConfig\":{\"$(printf 'Bind\305\277')\":[\"/:/host\"]}" > /tmp/utf.json
echo "403 $(create /tmp/utf.json utf) create, raw U+017F in a key"
{ cat /tmp/ok.json; printf '{"HostConfig":{"Privileged":true}}'; } > /tmp/two.json
echo "403 $(create /tmp/two.json two) create, trailing second value"

while read -r exp method path data; do
    if [ -n "$data" ]; then
        got=$(code -X "$method" -H "Content-Type: application/json" --data-binary "$data" "$H$path")
    else
        got=$(code -X "$method" "$H$path")
    fi
    echo "$exp $got $method $path"
done < /w/plain.txt
CLIENT

chmod -R a+rX "$work"
out=$(docker run --rm --network "$tag-net" -v "$work:/w:ro" -e "H=http://$tag-proxy:2375" \
    -e "TAG=$tag" -e "VOL=$vol" --entrypoint sh "$curl_image" /w/client.sh)

# The docker CLI itself: the containers a prefix-only proxy let through.
for args in "--privileged alpine:3" "-v /:/host $img" "--pid host $img"; do
    # shellcheck disable=SC2086
    if cli=$(docker run --rm --network "$tag-net" -e "DOCKER_HOST=tcp://$tag-proxy:2375" "$cli_image" \
            docker run --rm --name "coder-$tag-cli" $args true 2>&1); then
        out+=$'\n'"403 200 docker run $args"
    elif grep -qi "forbidden" <<<"$cli"; then
        out+=$'\n'"403 403 docker run $args"
    else
        out+=$'\n'"403 ??? docker run $args: ${cli:0:200}"
    fi
done

echo "$out"
# Nothing a refused probe asked for may exist.
if docker ps -aq --filter "name=^coder-$tag-" | grep -q .; then
    echo "FAIL: a refused container create left a container behind" >&2
    exit 1
fi
failed=$(echo "$out" | awk '$1 == "pass" ? $2 == "403" : $1 != $2' | wc -l)
if [ "$failed" -ne 0 ]; then
    echo "FAIL: $failed probe(s) did not get the expected status" >&2
    exit 1
fi
echo "OK: $(echo "$out" | wc -l) probes"
