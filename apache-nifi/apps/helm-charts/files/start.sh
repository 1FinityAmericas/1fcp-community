#!/bin/sh -e

scripts_dir='/opt/nifi/scripts'
bootstrap_file="${NIFI_HOME}/conf/bootstrap.conf"

[ -f "${scripts_dir}/common.sh" ] && . "${scripts_dir}/common.sh"

# --- NEW: Function to replace properties specifically in bootstrap.conf ---
# Assumes 'sed' is available
bootstrap_prop_replace() {
    local prop_name=$1
    local prop_value=$2

    if [ -n "$prop_value" ]; then
        echo "File [${bootstrap_file}] replacing [${prop_name}]"
        # The 'sed' command looks for the property and replaces the entire line
        sed -i -e "s|^${prop_name}=.*|${prop_name}=${prop_value}|" "${bootstrap_file}"
    fi
}

# --- NEW: Apply JVM memory settings from Environment Variables ---
if [ -n "${NIFI_JVM_HEAP_INIT}" ] && [ -n "${NIFI_JVM_HEAP_MAX}" ]; then
    echo "Applying JVM heap settings from environment variables..."
    # The bootstrap file uses 'java.arg.2' and 'java.arg.3' for -Xms and -Xmx
    # These override the defaults of -Xms1g and -Xmx1g
    bootstrap_prop_replace 'java.arg.2' "-Xms${NIFI_JVM_HEAP_INIT}"
    bootstrap_prop_replace 'java.arg.3' "-Xmx${NIFI_JVM_HEAP_MAX}"
else
    echo "NIFI_JVM_HEAP_INIT or NIFI_JVM_HEAP_MAX not set, using existing bootstrap.conf defaults."
fi
# --- END NEW ADDITIONS ---


# Convert PEM to PKCS12
CERT_DIR="/opt/nifi/certs"
KEYSTORE_PASS="changeit"
if [ -f "${CERT_DIR}/tls.crt" ] && [ -f "${CERT_DIR}/tls.key" ]; then
    echo "Converting PEM to PKCS12..."

    # Remove existing keystores (they persist on PVC)
    rm -f "${NIFI_HOME}/conf/keystore.p12"
    rm -f "${NIFI_HOME}/conf/truststore.p12"

    # Create keystore
    openssl pkcs12 -export \
        -in "${CERT_DIR}/tls.crt" \
        -inkey "${CERT_DIR}/tls.key" \
        -out "${NIFI_HOME}/conf/keystore.p12" \
        -name nifi \
        -passout pass:${KEYSTORE_PASS}

    # Create PKCS12 truststore
    keytool -import -trustcacerts -noprompt \
        -alias nifi-ca \
        -file "${CERT_DIR}/tls.crt" \
        -keystore "${NIFI_HOME}/conf/truststore.p12" \
        -storetype PKCS12 \
        -storepass ${KEYSTORE_PASS}

    echo "PKCS12 keystore and truststore created"
fi


# Setup NiFi to use Python
uncomment "nifi.python.command" ${nifi_props_file}
prop_replace 'nifi.python.extensions.source.directory.default'  "${NIFI_HOME}/python_extensions"
#prop_replace 'nifi.nar.library.autoload.directory'  "${NIFI_HOME}/nar_extensions"
prop_replace 'nifi.nar.library.autoload.directory'  "${NIFI_HOME}/extensions"

# Repository directories
prop_replace 'nifi.content.repository.directory.default' "${NIFI_HOME}/content_repository"
prop_replace 'nifi.flowfile.repository.directory.default' "${NIFI_HOME}/flowfile_repository"
prop_replace 'nifi.provenance.repository.directory.default' "${NIFI_HOME}/provenance_repository"
prop_replace 'nifi.database.repository.directory' "${NIFI_HOME}/database_repository"

# --- ENABLE TLS / HTTPS ---
prop_replace 'nifi.web.https.port'              "${NIFI_WEB_HTTPS_PORT:-8443}"
prop_replace 'nifi.web.https.host'              "${HOSTNAME}.${NIFI_HEADLESS_SERVICE}.${NAMESPACE}.svc.cluster.local"

# Disable HTTP
prop_replace 'nifi.web.http.port'               ''
prop_replace 'nifi.web.http.host'               ''

# Configure PEM keystore/truststore
prop_replace 'nifi.security.keystore'           "${NIFI_HOME}/conf/keystore.p12"
prop_replace 'nifi.security.keystoreType'       'PKCS12'
prop_replace 'nifi.security.keystorePasswd'     'changeit'
prop_replace 'nifi.security.keyPasswd'          'changeit'
prop_replace 'nifi.security.truststore'         "${NIFI_HOME}/conf/truststore.p12"
prop_replace 'nifi.security.truststoreType'     'PKCS12'
prop_replace 'nifi.security.truststorePasswd'   'changeit'

# Remote input
prop_replace 'nifi.remote.input.host'           "${HOSTNAME}.${NIFI_HEADLESS_SERVICE}.${NAMESPACE}.svc.cluster.local"
prop_replace 'nifi.remote.input.socket.port'    "${NIFI_REMOTE_INPUT_SOCKET_PORT:-10000}"
prop_replace 'nifi.remote.input.secure'         'true'

# --- SINGLE USER AUTH ---
case ${AUTH} in
    singleUser)
        echo "Configuring single-user authentication..."
        prop_replace 'nifi.security.user.login.identity.provider' 'single-user-provider'
        prop_replace 'nifi.security.user.authorizer' 'single-user-authorizer'
        ;;
    *)
        echo "Auth mode: ${AUTH:-none}"
        ;;
esac
# Set single-user credentials (overwrites any auto-generated ones in conf-pvc)
if [ -n "${SINGLE_USER_CREDENTIALS_USERNAME}" ] && [ -n "${SINGLE_USER_CREDENTIALS_PASSWORD}" ]; then
    echo "Setting NiFi single-user credentials..."
    "${NIFI_HOME}/bin/nifi.sh" set-single-user-credentials \
        "${SINGLE_USER_CREDENTIALS_USERNAME}" \
        "${SINGLE_USER_CREDENTIALS_PASSWORD}"
fi


# Enable clustering
prop_replace 'nifi.cluster.is.node'                    "${NIFI_CLUSTER_IS_NODE:-true}"
prop_replace 'nifi.cluster.node.address'               "${HOSTNAME}.${NIFI_HEADLESS_SERVICE}.${NAMESPACE}.svc.cluster.local"
prop_replace 'nifi.cluster.node.protocol.port'         "${NIFI_CLUSTER_NODE_PROTOCOL_PORT:-11443}"
prop_replace 'nifi.cluster.protocol.is.secure'         'true'
prop_replace 'nifi.cluster.load.balance.port'          '6342'
prop_replace 'nifi.cluster.flow.election.max.wait.time' '1 min'
prop_replace 'nifi.cluster.flow.election.max.candidates' ''

# State management (Kubernetes, no ZooKeeper)
prop_replace 'nifi.state.management.configuration.file' './conf/state-management.xml'
prop_replace 'nifi.sensitive.props.key' 'thisIsADevKeyChangeIt'
prop_replace 'nifi.cluster.leader.election.implementation' 'org.apache.nifi.kubernetes.leader.election.KubernetesLeaderElectionManager'
prop_replace 'nifi.state.management.provider.cluster' 'kubernetes-provider'
prop_replace 'nifi.state.management.embedded.zookeeper.start' 'false'
prop_replace 'nifi.zookeeper.connect.string'           ''

# Cluster timeout overrides
if [ -n "${NIFI_CLUSTER_NODE_READ_TIMEOUT}" ]; then
    prop_replace 'nifi.cluster.node.read.timeout' "${NIFI_CLUSTER_NODE_READ_TIMEOUT}"
fi
if [ -n "${NIFI_CLUSTER_NODE_CONNECTION_TIMEOUT}" ]; then
    prop_replace 'nifi.cluster.node.connection.timeout' "${NIFI_CLUSTER_NODE_CONNECTION_TIMEOUT}"
fi
# nifi.cluster.request.replication.claim.timeout is a new property not present in default
# nifi.properties, so append it if missing rather than relying on prop_replace (sed replace)
if [ -n "${NIFI_CLUSTER_REQUEST_REPLICATION_CLAIM_TIMEOUT}" ]; then
    if grep -q "^nifi.cluster.request.replication.claim.timeout=" "${nifi_props_file}"; then
        prop_replace 'nifi.cluster.request.replication.claim.timeout' "${NIFI_CLUSTER_REQUEST_REPLICATION_CLAIM_TIMEOUT}"
    else
        echo "nifi.cluster.request.replication.claim.timeout=${NIFI_CLUSTER_REQUEST_REPLICATION_CLAIM_TIMEOUT}" >> "${nifi_props_file}"
    fi
fi

# Proxy context path
if [ -n "${NIFI_WEB_PROXY_CONTEXT_PATH}" ]; then
    prop_replace 'nifi.web.proxy.context.path' "${NIFI_WEB_PROXY_CONTEXT_PATH}"
fi
# Proxy host
# Build proxy host list dynamically
PROXY_HOSTS="${NIFI_WEB_PROXY_HOST}"
#for i in 0 1 2; do
replicaCount=2
for i in $(seq 0 2 ); do
    PROXY_HOSTS="${PROXY_HOSTS},nifi-${i}.${NIFI_HEADLESS_SERVICE}.${NAMESPACE}.svc.cluster.local:8443"
done
prop_replace 'nifi.web.proxy.host' "${PROXY_HOSTS}"

echo "Starting NiFi..."
# The 'exec' command launches the process with the *modified* bootstrap.conf
exec "${NIFI_HOME}/bin/nifi.sh" run
#echo "Starting NiFi (background) ..."
#"${NIFI_HOME}/bin/nifi.sh" start
#echo "NiFi start command exited with: $?"
#echo "Listing log dir:"
#ls -la "${NIFI_HOME}/logs" || true
#echo "Tailing NiFi logs to stdout..."
#touch "${NIFI_HOME}/logs/nifi-app.log" "${NIFI_HOME}/logs/nifi-bootstrap.log" || true
#tail -n 200 -F "${NIFI_HOME}/logs/nifi-bootstrap.log" "${NIFI_HOME}/logs/nifi-app.log"

