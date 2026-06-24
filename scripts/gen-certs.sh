#!/usr/bin/env bash
# Generate the internal CA and the IP-SAN server certificate for nginx.
#
# Run once on the deployment host (or anywhere with openssl):
#   ./scripts/gen-certs.sh
#
# Outputs into ./certs (gitignored):
#   ca.key      - CA private key  (KEEP SECRET, keep offline after issuing)
#   ca.crt      - CA certificate  (distribute to users to import as trusted)
#   server.key  - server private key (mounted into nginx)
#   server.crt  - server certificate signed by the CA (mounted into nginx)
#   dhparam.pem - Diffie-Hellman parameters for DHE ciphers
#
# After generating, each user imports ca.crt into their OS/browser trust store
# ONCE to avoid certificate warnings. Reissuing server.crt later (e.g. on
# expiry) does not require redistributing ca.crt.

set -euo pipefail

# No-op on Linux; stops Git Bash (MSYS) on Windows from rewriting the
# OpenSSL "/C=.../CN=..." subject strings into filesystem paths.
export MSYS_NO_PATHCONV=1

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CERT_DIR="${ROOT_DIR}/certs"
CNF="${ROOT_DIR}/nginx/openssl.cnf"

CA_DAYS=3650      # 10 years for the CA
SERVER_DAYS=825   # max accepted by most browsers for leaf certs

mkdir -p "${CERT_DIR}"
cd "${CERT_DIR}"

echo "==> Generating internal CA"
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days "${CA_DAYS}" \
    -subj "/C=ES/O=ActEU Narrative Tracker/CN=ActEU Internal CA" \
    -out ca.crt

echo "==> Generating server key and CSR (IP SAN from nginx/openssl.cnf)"
openssl genrsa -out server.key 2048
openssl req -new -key server.key -out server.csr -config "${CNF}"

echo "==> Signing server certificate with the CA"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
    -out server.crt -days "${SERVER_DAYS}" -sha256 \
    -extfile "${CNF}" -extensions v3_req

echo "==> Generating Diffie-Hellman parameters (this can take minutes)"
openssl dhparam -out dhparam.pem 2048

rm -f server.csr ca.srl
chmod 600 ca.key server.key

echo
echo "Done. Files written to ${CERT_DIR}:"
ls -1 "${CERT_DIR}"
echo
echo "Next: distribute ca.crt to users so they can trust the server certificate."
