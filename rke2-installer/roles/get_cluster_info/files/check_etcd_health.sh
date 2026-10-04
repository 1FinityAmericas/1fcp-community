#!/bin/bash

# Check ETCD health and save results to a file
LOGS_DIR="$OUTPUT_DIR/logs"

# Function to log messages to OUTPUT_FILE
log() {
    echo -e "$1" | tee -a "$LOGS_DIR/etcd_health_results.log"
}

# Print the value of LOGS_DIR for debugging
echo "LOGS_DIR is set to: $LOGS_DIR"

# Ensure the script runs with sudo
if [[ $EUID -ne 0 ]]; then
    echo "This script must be run as root or with sudo." >&2
    exit 1
fi

# Export the CRI config file
export CRI_CONFIG_FILE="/var/lib/rancher/rke2/agent/etc/crictl.yaml"

# Get the etcd container ID
etcdcontainer=$(/var/lib/rancher/rke2/bin/crictl ps --label io.kubernetes.container.name=etcd --quiet)

# Check if etcd container was found
if [ -z "$etcdcontainer" ]; then
    echo "ETCD container not found or not running." >&2
    exit 1
fi

# Run etcdctl command and check health
output=$(/var/lib/rancher/rke2/bin/crictl exec "$etcdcontainer" etcdctl \
    --cert /var/lib/rancher/rke2/server/tls/etcd/server-client.crt \
    --key /var/lib/rancher/rke2/server/tls/etcd/server-client.key \
    --cacert /var/lib/rancher/rke2/server/tls/etcd/server-ca.crt \
    endpoint health --cluster --write-out=table 2>&1)

# Check if the command succeeded
if [ $? -ne 0 ]; then
    echo "Error executing etcdctl command. Output: $output" >&2
    exit 1
fi

# Check if output is empty
if [ -z "$output" ]; then
    echo "No output from etcdctl command." >&2
    exit 1
fi

# Save the output to the file
echo "$output" > "$LOGS_DIR/etcd_health_results.log"
echo "ETCD health check results saved to $LOGS_DIR/etcd_health_results.log"

# Optionally, you can also log the output to the console
#log "$output"
#log "$LOGS_DIR/etcd_health_results.log"

