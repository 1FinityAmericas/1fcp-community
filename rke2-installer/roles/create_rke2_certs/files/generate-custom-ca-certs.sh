#!/usr/bin/env bash

#Script to genrate rke2 custom ca certs
set -e
umask 027

TIMESTAMP=$(date +%s)
#PRODUCT="${PRODUCT:-rke2-server}"
PRODUCT="${PRODUCT:-rke2}"
DATA_DIR="${DATA_DIR:-/var/lib/rancher/${PRODUCT}}"

if type -t openssl-3 &>/dev/null; then
  OPENSSL=openssl-3
else
  OPENSSL=openssl
fi

echo "Using $(type -p ${OPENSSL}): $(${OPENSSL} version)"

if ! ${OPENSSL} ecparam -name prime256v1 -genkey -noout -out /dev/null &>/dev/null; then
  echo "openssl not found or missing Elliptic Curve (ecparam) support."
  exit 1
fi

${OPENSSL} version | grep -qF 'OpenSSL 3' && OPENSSL_GENRSA_FLAGS=-traditional

mkdir -p "${DATA_DIR}/server/tls/etcd"
cd "${DATA_DIR}/server/tls"

# Set up temporary openssl configuration
mkdir -p ".ca/certs"
trap "rm -rf .ca" EXIT
touch .ca/index
openssl rand -hex 8 > .ca/serial
cat >.ca/config <<'EOF'
[ca]
default_ca = ca_default
[ca_default]
dir = ./.ca
database = $dir/index
serial = $dir/serial
new_certs_dir = $dir/certs
default_md = sha256
policy = policy_anything
[policy_anything]
commonName = supplied
[req]
distinguished_name = req_distinguished_name
[req_distinguished_name]
[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always
basicConstraints = critical, CA:true
keyUsage = critical, digitalSignature, keyEncipherment, keyCertSign
EOF

# Don't overwrite the service account issuer key; we pass the key into both the controller-manager
# and the apiserver instead of passing a cert list into the apiserver, so there's no facility for
# rotation and things will get very angry if all the SA keys are invalidated.
if [[ -e service.key ]]; then
  echo "Generating additional Kubernetes service account issuer RSA key"
  OLD_SERVICE_KEY="$(cat service.key)"
else
  echo "Generating Kubernetes service account issuer RSA key"
fi
${OPENSSL} genrsa ${OPENSSL_GENRSA_FLAGS:-} -out service.key 2048
echo "${OLD_SERVICE_KEY}" >> service.key


# Generate new leaf CAs for all the control-plane and etcd components
for TYPE in client server request-header etcd/peer etcd/server; do
  CERT_NAME="${PRODUCT}-$(echo ${TYPE} | tr / -)-ca"
  echo "Generating ${CERT_NAME} leaf certificate authority EC key and certificate"
  ${OPENSSL} ecparam -name prime256v1 -genkey -noout -out ${TYPE}-ca.key
  ${OPENSSL} req -new -nodes \
                 -subj "/CN=${CERT_NAME}.fujitsu.com" \
                 -key ${TYPE}-ca.key |
  ${OPENSSL} ca  -batch -notext -days 365 \
                 -in /dev/stdin \
                 -out ${TYPE}-ca.pem \
                 -keyfile root-ca.key \
                 -cert root-ca.crt \
                 -config .ca/config \
                 -extensions v3_ca
  cat ${TYPE}-ca.pem \
      root-ca.crt > ${TYPE}-ca.crt
done

echo
echo "CA certificate generation complete. Required files are now present in: ${DATA_DIR}/server/tls"
echo "For security purposes, you should make a secure copy of the following files and remove them from cluster members:"
ls ${DATA_DIR}/server/tls/root-ca.* | xargs -n1 echo -e "\t"

if [ "${DATA_DIR}" != "/var/lib/rancher/${PRODUCT}" ]; then
  echo
  echo "To update certificates on an existing cluster, you may now run:"
  echo "    rke2-server certificate rotate-ca --path=${DATA_DIR}/server"
fi
