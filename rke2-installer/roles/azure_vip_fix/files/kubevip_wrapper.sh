#!/bin/bash

set -o pipefail

# Source configuration file for Azure credentials
if [ -f "$HOME/vip/vip_config.sh" ]; then
  source "$HOME/vip/vip_config.sh"
  export AZURE_CLIENT_ID
fi

KUBECTL="/var/lib/rancher/rke2/bin/kubectl"
KUBECONFIG="$HOME/.kube/config"
LOCK_FILE="$HOME/vip/kubevip_wrapper.lock"
SCRIPT_PATH="$HOME/vip/kube_vip.sh"
LOG_PATH="$HOME/vip/kube_vip.log"

log_message() {
    local LOG_LEVEL=$1
    local MESSAGE=$2
    local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "$TIMESTAMP [$LOG_LEVEL] $MESSAGE"
}

get_master_nodes() {
  $KUBECTL get nodes --kubeconfig "$KUBECONFIG" \
    -l node-role.kubernetes.io/control-plane=true \
    -o jsonpath='{range .items[*]}{.status.addresses[?(@.type=="InternalIP")].address}{"\n"}{end}' 2>/dev/null
}

check_cluster_health() {
  local master_ips
  local ready_count=0
  local total_count=0

  master_ips=$(get_master_nodes)

  if [ -z "$master_ips" ]; then
    log_message "ERROR" "Unable to get master nodes from cluster"
    return 1
  fi

  for ip in $master_ips; do
    total_count=$((total_count + 1))
    if ping -c 1 -W 2 "$ip" &> /dev/null; then
      log_message "INFO" "Master node $ip is reachable"
      ready_count=$((ready_count + 1))
    else
      log_message "WARNING" "Master node $ip is not reachable"
    fi
  done

  log_message "INFO" "Cluster health: $ready_count/$total_count master nodes reachable"

  if [ $ready_count -lt 2 ] && [ $total_count -ge 3 ]; then
    log_message "ERROR" "Insufficient master nodes available ($ready_count/$total_count)"
    return 1
  fi

  return 0
}

is_script_running() {
  if pgrep -f "$SCRIPT_PATH" > /dev/null 2>&1; then
    return 0
  fi
  return 1
}

run_vip_fix_script() {
  if is_script_running; then
    log_message "INFO" "VIP fix script is already running, skipping execution"
    return 0
  fi

  if [ ! -f "$SCRIPT_PATH" ]; then
    log_message "ERROR" "Script not found: $SCRIPT_PATH"
    return 1
  fi

  log_message "INFO" "Starting VIP fix script"
  bash "$SCRIPT_PATH" >> "$LOG_PATH" 2>&1 &
  local script_pid=$!

  sleep 2

  if ps -p $script_pid > /dev/null 2>&1; then
    log_message "INFO" "VIP fix script started successfully (PID: $script_pid)"
    return 0
  else
    log_message "ERROR" "VIP fix script failed to start"
    return 1
  fi
}

main() {
  exec 200>"$LOCK_FILE"

  if ! flock -n 200; then
    log_message "INFO" "Another instance is already running, exiting"
    return 0
  fi

  log_message "INFO" "Starting kubevip wrapper"

  if ! check_cluster_health; then
    log_message "ERROR" "Cluster health check failed, skipping VIP fix"
    flock -u 200
    return 1
  fi

  run_vip_fix_script
  local exit_code=$?

  flock -u 200

  log_message "INFO" "Kubevip wrapper completed with exit code: $exit_code"
  return $exit_code
}

main
exit $?
