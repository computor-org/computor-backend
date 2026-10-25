#!/usr/bin/env bash
# Generate the Temporal mTLS material for one deployment (see
# ops/docker/docker-compose.temporal-tls.yaml).
#
#   generate-certs.sh OUT_DIR [CLIENT_NAME...]
#
# OUT_DIR/ca.pem, ca-key.pem      deployment CA (keep ca-key.pem off the hosts)
# OUT_DIR/server/                 ca.pem server.pem server-key.pem -> TEMPORAL_TLS_DIR
# OUT_DIR/<client>.env            TEMPORAL_TLS_CERT/KEY/CA as single-line base64,
#                                 to append to the client host's .env
#
# CLIENT_NAME defaults to "control execution": one certificate for the
# control-plane host (API and control workers) and one for the execution host.
# TEMPORAL_TLS_SERVER_SANS adds names/addresses clients dial (default covers
# the compose service name and the prod WireGuard address 10.88.0.1).
# TEMPORAL_TLS_DAYS sets the validity (default 825). Refuses to overwrite.
set -euo pipefail
out=${1:?usage: generate-certs.sh OUT_DIR [CLIENT_NAME...]}
shift
if [ $# -gt 0 ]; then clients=("$@"); else clients=(control execution); fi
days=${TEMPORAL_TLS_DAYS:-825}
sans=${TEMPORAL_TLS_SERVER_SANS:-DNS:temporal,DNS:localhost,IP:127.0.0.1,IP:10.88.0.1}

if [ -e "$out" ] && [ -n "$(ls -A "$out" 2>/dev/null)" ]; then
    echo "refusing to overwrite non-empty $out" >&2
    exit 1
fi
umask 077
mkdir -p "$out/server"
cd "$out"

key() { openssl genpkey -algorithm EC -pkeyopt ec_paramgen_curve:P-256 -out "$1" 2>/dev/null; }

key ca-key.pem
openssl req -x509 -new -key ca-key.pem -sha256 -days "$days" -subj "/CN=computor-temporal-ca" \
    -addext "basicConstraints=critical,CA:TRUE,pathlen:0" \
    -addext "keyUsage=critical,keyCertSign,cRLSign" -out ca.pem

issue() { # name cn eku [sans]
    local name=$1 cn=$2 eku=$3 san=${4:-}
    key "$name-key.pem"
    openssl req -new -key "$name-key.pem" -subj "/CN=$cn" -out "$name.csr"
    {
        echo "basicConstraints=critical,CA:FALSE"
        echo "keyUsage=critical,digitalSignature"
        echo "extendedKeyUsage=$eku"
        [ -z "$san" ] || echo "subjectAltName=$san"
    } > "$name.ext"
    openssl x509 -req -in "$name.csr" -CA ca.pem -CAkey ca-key.pem -CAcreateserial \
        -days "$days" -sha256 -extfile "$name.ext" -out "$name.pem" 2>/dev/null
    rm -f "$name.csr" "$name.ext"
}

# The server certificate is also the internode and in-container CLI client
# certificate, hence both usages.
issue server temporal serverAuth,clientAuth "$sans"
mv server.pem server-key.pem server/
cp ca.pem server/ca.pem

for c in "${clients[@]}"; do
    issue "$c" "computor-temporal-$c" clientAuth
    {
        echo "TEMPORAL_TLS_CERT=$(base64 -w0 "$c.pem")"
        echo "TEMPORAL_TLS_KEY=$(base64 -w0 "$c-key.pem")"
        echo "TEMPORAL_TLS_CA=$(base64 -w0 ca.pem)"
        echo "TEMPORAL_TLS_SERVER_NAME=temporal"
    } > "$c.env"
done
rm -f ca.srl
echo "wrote $out (server SANs: $sans; clients: ${clients[*]}; valid $days days)"
