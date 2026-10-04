#!/bin/bash

# Configuration variables
KUBECTL="/var/lib/rancher/rke2/bin/kubectl"
KUBECONFIG="$HOME/.kube/config"
LOCK_FILE="$HOME/vip/kubevip_wrapper.lock"
SCRIPT_PATH="$HOME/vip/kube_vip.sh"
LOG_PATH="$HOME/vip/kube_vip.log"

log_message() {
    local LOG_LEVEL=$1
    local MESSAGE=$2
    local TIMESTAMP=$(date +"%Y-%m-%d %H:%M:%S")
    echo "$TIMESTAMP [$LOG_LEVEL] $MESSAGE" >&2
}

# Function to login azure using user identity
login() {
  log_message "INFO" "Attempting Azure login with client-id: ${AZURE_CLIENT_ID}"
  az login --identity --client-id ${AZURE_CLIENT_ID}
  local exit_code=$?
  if [ $exit_code -eq 0 ]; then
    log_message "INFO" "Azure login successful"
  else
    log_message "ERROR" "Azure login failed with exit code: $exit_code"
  fi
  return $exit_code
}

# Function to check kubectl working
check_kubectl_working() {
  log_message "DEBUG" "Checking if kubectl is working..."
  $KUBECTL get pods --kubeconfig $KUBECONFIG >/dev/null 2>&1;
  if [ $? -eq 0 ]; then
    log_message "INFO" "kubectl command working"
    return 0
  else
    log_message "ERROR" "kubectl command not working, Looks system restarted or some issue with node"
    return 1
  fi
}

# Function to get the kube-vip pod node name
get_node_ip() {
  log_message "DEBUG" "Fetching kube-vip pod IPs from cluster..."
  local result=$($KUBECTL get pods -n kube-system -l app.kubernetes.io/name=kube-vip --kubeconfig $KUBECONFIG -o jsonpath='{range .items[*]}{.status.podIP}{"\n"}{end}' 2>&1)
  local exit_code=$?

  if [ $exit_code -ne 0 ]; then
    log_message "ERROR" "Failed to fetch kube-vip pod IPs. Exit code: $exit_code"
    log_message "ERROR" "kubectl error output: $result"
    return 1
  fi

  if [ -z "$result" ]; then
    log_message "WARN" "No kube-vip pod IPs found in kube-system namespace"
    return 1
  fi

  local pod_count=$(echo "$result" | wc -l)
  log_message "INFO" "Found $pod_count kube-vip pod IP(s)"
  log_message "DEBUG" "Kube-vip pod IPs: $result"
  echo "$result"
  return 0
}

# Function to get the kube-vip address
get_kube_vip() {
  local vip_address
  if [ -z "$vip_address" ]; then
    vip_address=$($KUBECTL get daemonset -n kube-system kube-vip \
      --kubeconfig $KUBECONFIG \
      -o jsonpath='{.spec.template.spec.containers[0].env[?(@.name=="vip_address")].value}' 2>/dev/null | tr -d '[:space:]')
  fi

  if [ -n "$vip_address" ]; then
    log_message "DEBUG" "Discovered VIP address: $vip_address"
    echo "$vip_address"
    return 0
  else
    log_message "DEBUG" "Unable to discover VIP address from any source"
    return 1
  fi
}

# Function to check the network interfaces on the node
check_network_interfaces() {
  local node_name=$1
  local kube_vip=$2

  log_message "INFO" "Checking network interfaces on node: $node_name for VIP: $kube_vip"

  if [ -z "$node_name" ]; then
    log_message "ERROR" "Node name is empty, cannot check network interfaces"
    return 1
  fi

  if [ -z "$kube_vip" ]; then
    log_message "ERROR" "VIP address is empty, cannot check network interfaces"
    return 1
  fi

  log_message "DEBUG" "Executing SSH command to node $node_name to check for VIP $kube_vip"
  local result
  result=$(ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 $node_name "ip add show | grep $kube_vip" 2>/dev/null)
  local exit_code=$?

  if [ $exit_code -eq 255 ]; then
    log_message "ERROR" "SSH connection failed to node $node_name (exit code: $exit_code)"
    return 1
  elif [ $exit_code -eq 1 ]; then
    log_message "DEBUG" "VIP $kube_vip not found on node $node_name network interfaces"
    return 1
  elif [ $exit_code -ne 0 ]; then
    log_message "ERROR" "Command execution failed on node $node_name (exit code: $exit_code)"
    log_message "ERROR" "Error output: $result"
    return 1
  fi

  if [ -n "$result" ]; then
    log_message "INFO" "VIP $kube_vip found on node $node_name"
    log_message "DEBUG" "Network interface details: $result"
  else
    log_message "DEBUG" "No matching network interface found for VIP $kube_vip on node $node_name"
  fi

  echo "$result"
  return 0
}


# Get kube vip node
get_kube_vip_node() {
  log_message "DEBUG" "Starting get_kube_vip_node function"
  check_kubectl_working
  local node_name=$(get_node_ip)
  local kube_vip=$(get_kube_vip)
  log_message "DEBUG" "Node IPs to check: $node_name, VIP to find: $kube_vip"

  for node in $node_name; do
    log_message "INFO" "Connecting to $node to verify ip $kube_vip"
    local out=$(check_network_interfaces $node $kube_vip)
    if [ -n "$out" ]; then
      log_message "INFO" "Kube VIP associated with node $node"
      kube_vip_node=$node
      break
    fi
  done
  log_message "DEBUG" "get_kube_vip_node completed. kube_vip_node=$kube_vip_node"
}


# Function to find the resource of a given IP address
find_resource_by_vip() {
  local ip_address=$1
  ip_address_exists="true"

  log_message "INFO" "Finding Azure resource for IP: $ip_address"

  if [ -z "$ip_address" ]; then
    log_message "ERROR" "IP address is empty, cannot find Azure resource"
    echo "false"
    return 1
  fi

  # Get the network interface associated with the IP address
  log_message "DEBUG" "Querying Azure for NIC with IP: $ip_address"
  local nic_id=$(az network nic list --query "[?ipConfigurations[?privateIPAddress=='$ip_address']].id" -o tsv 2>&1)
  local exit_code=$?

  if [ $exit_code -ne 0 ]; then
    log_message "ERROR" "Failed to query Azure NIC list (exit code: $exit_code)"
    log_message "ERROR" "Azure CLI error: $nic_id"
    echo "false"
    return 1
  fi

  log_message "DEBUG" "NIC ID query result: $nic_id"

  if [ -z "$nic_id" ]; then
    ip_address_exists="false"
    log_message "WARN" "No NIC found for IP: $ip_address in Azure"
    echo "$ip_address_exists"
    return 1
  fi

  log_message "INFO" "Found NIC ID: $nic_id"

  # Get the resource group of the network interface
  log_message "DEBUG" "Retrieving resource group for NIC: $nic_id"
  local resource_group=$(az network nic show --ids "$nic_id" --query "resourceGroup" -o tsv 2>&1)
  exit_code=$?

  if [ $exit_code -ne 0 ]; then
    log_message "ERROR" "Failed to retrieve resource group (exit code: $exit_code)"
    log_message "ERROR" "Azure CLI error: $resource_group"
    return 1
  fi

  log_message "DEBUG" "Resource Group: $resource_group"

  # Get network interface name
  log_message "DEBUG" "Retrieving NIC name for NIC ID: $nic_id"
  local nic_name=$(az network nic show --ids "$nic_id" --query "name" -o tsv 2>&1)
  exit_code=$?

  if [ $exit_code -ne 0 ]; then
    log_message "ERROR" "Failed to retrieve NIC name (exit code: $exit_code)"
    log_message "ERROR" "Azure CLI error: $nic_name"
    return 1
  fi

  log_message "DEBUG" "NIC Name: $nic_name"

  # Get VM primary IP
  log_message "DEBUG" "Retrieving primary IP configuration for NIC: $nic_name"
  local vm_ip=$(az network nic show --ids "$nic_id" --query "ipConfigurations[0].privateIPAddress" --output tsv 2>&1)
  exit_code=$?

  if [ $exit_code -ne 0 ]; then
    log_message "ERROR" "Failed to retrieve primary IP (exit code: $exit_code)"
    log_message "ERROR" "Azure CLI error: $vm_ip"
    return 1
  fi

  log_message "DEBUG" "Primary VM IP: $vm_ip"

  # Get Secondary IP configuration name
  log_message "DEBUG" "Retrieving secondary IP configuration name for NIC: $nic_name"
  local sec_ip_conf_name=$(az network nic show --ids "$nic_id" --query "ipConfigurations[1].name" --output tsv 2>&1)
  exit_code=$?

  if [ $exit_code -ne 0 ]; then
    log_message "WARN" "Failed to retrieve secondary IP config name (exit code: $exit_code), may not exist"
    sec_ip_conf_name=""
  else
    log_message "DEBUG" "Secondary IP configuration name: $sec_ip_conf_name"
  fi

  # Check if sec_ip_conf_name is empty or null and set to default if needed
  if [ -z "$sec_ip_conf_name" ] || [ "$sec_ip_conf_name" == "null" ]; then
    log_message "DEBUG" "Secondary IP config name is empty or null, setting to default: KUBEVIP"
    sec_ip_conf_name="KUBEVIP"
  fi

  log_message "INFO" "Successfully retrieved Azure resource details for IP: $ip_address"
  log_message "DEBUG" "Resource details - RG: $resource_group, NIC: $nic_name, SecIPConfig: $sec_ip_conf_name, VM_IP: $vm_ip"
  echo "$resource_group $nic_name $sec_ip_conf_name $vm_ip"
  return 0
}

# Function to delete a secondary network interface
delete_secondary_nic() {
  local resource_group=$1
  local nic_name=$2
  local sec_ip_conf_name=$3
  deleted_kube_vip_ip_config="false"

  log_message "INFO" "Deleting secondary IP configuration: $sec_ip_conf_name from NIC: $nic_name"
  log_message "DEBUG" "Parameters - RG: $resource_group, NIC: $nic_name, SecIPConfig: $sec_ip_conf_name"

  # Validate input parameters
  if [ -z "$resource_group" ]; then
      log_message "ERROR" "Resource group is empty, cannot delete secondary IP config"
      return 1
  fi

  if [ -z "$nic_name" ]; then
      log_message "ERROR" "NIC name is empty, cannot delete secondary IP config"
      return 1
  fi

  if [ -z "$sec_ip_conf_name" ]; then
      log_message "ERROR" "Secondary IP config name is empty, cannot delete secondary IP config"
      return 1
  fi

  # Delete the secondary IP configuration
  log_message "DEBUG" "Executing Azure CLI command to delete secondary IP config: $sec_ip_conf_name"
  local result=$(az network nic ip-config delete --resource-group $resource_group --nic-name $nic_name --name $sec_ip_conf_name 2>&1)
  local exit_code=$?

  if [ $exit_code -eq 0 ]; then
      log_message "INFO" "Successfully deleted secondary IP config $sec_ip_conf_name from NIC $nic_name in resource group $resource_group"
      log_message "DEBUG" "Azure CLI output: $result"
      deleted_kube_vip_ip_config="true"
      return 0
  else
      log_message "ERROR" "Failed to delete secondary IP config $sec_ip_conf_name from NIC $nic_name in resource group $resource_group (exit code: $exit_code)"
      log_message "ERROR" "Azure CLI error output: $result"
      return 1
  fi
}


# Function to create a secondary IP configuration for a NIC
create_secondary_ipconfig() {
    local resource_group=$1
    local nic_name=$2
    local sec_ip_conf_name=$3
    local private_ip_address=$4

    log_message "INFO" "Creating secondary IP configuration for NIC: $nic_name"
    log_message "DEBUG" "Parameters - RG: $resource_group, NIC: $nic_name, IPConfig: $sec_ip_conf_name, IP: $private_ip_address"

    # Validate input parameters
    if [ -z "$resource_group" ]; then
        log_message "ERROR" "Resource group is empty, cannot create secondary IP config"
        return 1
    fi

    if [ -z "$nic_name" ]; then
        log_message "ERROR" "NIC name is empty, cannot create secondary IP config"
        return 1
    fi

    if [ -z "$sec_ip_conf_name" ]; then
        log_message "ERROR" "Secondary IP config name is empty, cannot create secondary IP config"
        return 1
    fi

    if [ -z "$private_ip_address" ]; then
        log_message "ERROR" "Private IP address is empty, cannot create secondary IP config"
        return 1
    fi

    # Create the secondary IP configuration
    log_message "DEBUG" "Executing Azure CLI command to create secondary IP config"
    local result=$(az network nic ip-config create \
        --resource-group $resource_group \
        --nic-name $nic_name \
        --name $sec_ip_conf_name \
        --private-ip-address $private_ip_address 2>&1)
    local exit_code=$?

    if [ $exit_code -eq 0 ]; then
        log_message "INFO" "Successfully created secondary IP configuration $sec_ip_conf_name for NIC $nic_name in resource group $resource_group"
        log_message "DEBUG" "Azure CLI output: $result"
        return 0
    else
        log_message "ERROR" "Failed to create secondary IP configuration $sec_ip_conf_name for NIC $nic_name in resource group $resource_group (exit code: $exit_code)"
        log_message "ERROR" "Azure CLI error output: $result"
        return 1
    fi
}


# Main function
main() {
  log_message "INFO" "=== Starting Azure VIP fix process ==="
  local main_exit_code=0

  # Login to azure using user identity
  log_message "INFO" "Step 1: Azure authentication"
  if ! login; then
    log_message "ERROR" "Azure login failed, cannot proceed with VIP fix"
    log_message "INFO" "=== Azure VIP fix process failed ==="
    return 1
  fi
  log_message "INFO" "Azure authentication successful"

  # Get kube vip address
  log_message "INFO" "Step 2: Retrieving kube-vip address from cluster"
  local kube_ip_address=$(get_kube_vip)
  if [ $? -ne 0 ] || [ -z "$kube_ip_address" ]; then
    log_message "ERROR" "Failed to retrieve kube-vip address, cannot proceed"
    log_message "INFO" "=== Azure VIP fix process failed ==="
    return 1
  fi
  log_message "INFO" "Kube-vip address: $kube_ip_address"

  # Get kube vip associated node
  log_message "INFO" "Step 3: Determining kube-vip associated node"
  get_kube_vip_node
  if [ -n "$kube_vip_node" ]; then
    log_message "INFO" "Kube-vip is associated with node: $kube_vip_node"
  else
    log_message "WARN" "Kube-vip node not determined yet"
  fi
  log_message "DEBUG" "kube_vip_node value: $kube_vip_node"

  # Create default name for secondary_ipconfig
  SECONDARY_IPCONFIG_NAME="KUBEVIP"
  log_message "DEBUG" "Default secondary IP config name: $SECONDARY_IPCONFIG_NAME"

  # Get resource using kube vip address
  log_message "INFO" "Step 4: Finding Azure resource for kube-vip address: $kube_ip_address"
  resources=($(find_resource_by_vip $kube_ip_address))
  local find_result=$?
  log_message "DEBUG" "find_resource_by_vip exit code: $find_result"
  log_message "DEBUG" "Resources array: RG=${resources[0]}, NIC=${resources[1]}, SecIPConfig=${resources[2]}, VM_IP=${resources[3]}"

   # Initialize ipconfig_name from resources or use default
  local ipconfig_name="${resources[2]}"
  if [ -z "$ipconfig_name" ] || [ "$ipconfig_name" == "null" ] || [ "$ipconfig_name" == "KUBEVIP" ]; then
    log_message "DEBUG" "ipconfig_name is empty, null, or default value, using: $SECONDARY_IPCONFIG_NAME"
    ipconfig_name="$SECONDARY_IPCONFIG_NAME"
  fi
  log_message "DEBUG" "Initial ipconfig_name to use: '$ipconfig_name'"

  # Scenario 1: Kube VIP node exists but VIP not found in Azure
  if [ -n "$kube_vip_node" ] && [ "${resources[0]}" == "false" ]; then
    log_message "INFO" "Scenario: Kube-vip $kube_ip_address not found in Azure, but found on node $kube_vip_node"
    log_message "INFO" "Action: Adding secondary IP config $ipconfig_name to node $kube_vip_node"

    log_message "DEBUG" "Finding Azure resource for node IP: $kube_vip_node"
    local new_resources=($(find_resource_by_vip $kube_vip_node))
    if [ $? -ne 0 ]; then
      log_message "ERROR" "Failed to find Azure resource for node $kube_vip_node"
      log_message "INFO" "=== Azure VIP fix process failed ==="
      return 1
    fi

    log_message "DEBUG" "New resources: RG=${new_resources[0]}, NIC=${new_resources[1]}, SecIPConfig=${new_resources[2]}, VM_IP=${new_resources[3]}"
    if create_secondary_ipconfig ${new_resources[0]} ${new_resources[1]} $ipconfig_name $kube_ip_address; then
      log_message "INFO" "Successfully created secondary IP config on node $kube_vip_node"
      log_message "INFO" "=== Azure VIP fix process completed successfully ==="
      return 0
    else
      log_message "ERROR" "Failed to create secondary IP config on node $kube_vip_node"
      log_message "INFO" "=== Azure VIP fix process failed ==="
      return 1
    fi

  # Scenario 2: Kube VIP not found in Azure and no node association
  elif [ "${resources[0]}" == "false" ]; then
    log_message "ERROR" "Scenario: Kube-vip $kube_ip_address not found in Azure and no node association detected"
    log_message "ERROR" "Action: Cannot proceed without valid VIP or node information"
    log_message "INFO" "=== Azure VIP fix process failed ==="
    return 1
  fi

  # Scenario 3: Check if kube VIP associated node matches Azure VM
  log_message "INFO" "Step 5: Validating VIP location consistency"
  if [ "${resources[3]}" == "$kube_vip_node" ]; then
    log_message "INFO" "Scenario: Kube-vip node $kube_vip_node matches Azure VM ${resources[3]}"
    log_message "INFO" "Action: No changes needed, VIP is correctly configured"
    log_message "INFO" "=== Azure VIP fix process completed successfully ==="
    return 0

  # Scenario 4: Kube VIP node exists but doesn't match Azure VM
  elif [ -n "$kube_vip_node" ]; then
    log_message "INFO" "Scenario: Kube-vip node $kube_vip_node does NOT match Azure VM ${resources[3]}"
    log_message "INFO" "Action: Moving VIP from ${resources[3]} to $kube_vip_node"

    log_message "INFO" "Step 5a: Deleting secondary IP config from current Azure VM"
    if delete_secondary_nic "${resources[0]}" "${resources[1]}" "${resources[2]}"; then
      log_message "INFO" "Successfully deleted secondary IP config from old location"
      log_message "DEBUG" "Waiting 5 seconds for Azure to process deletion..."
      sleep 5

      local ipconfig_name="${resources[2]}"
      log_message "DEBUG" "Original ipconfig_name from resources: '$ipconfig_name'"
      if [ -z "$ipconfig_name" ] || [ "$ipconfig_name" == "null" ]; then
        log_message "DEBUG" "ipconfig_name is empty or null, using default: $SECONDARY_IPCONFIG_NAME"
        ipconfig_name="$SECONDARY_IPCONFIG_NAME"
      fi
      log_message "DEBUG" "Final ipconfig_name to use: '$ipconfig_name'"

      log_message "INFO" "Step 5b: Creating secondary IP config on new node"
      log_message "DEBUG" "Finding Azure resource for new node IP: $kube_vip_node"
      local new_resources=($(find_resource_by_vip $kube_vip_node))
      if [ $? -ne 0 ]; then
        log_message "ERROR" "Failed to find Azure resource for node $kube_vip_node"
        log_message "INFO" "=== Azure VIP fix process failed ==="
        return 1
      fi

      log_message "DEBUG" "New resources: RG=${new_resources[0]}, NIC=${new_resources[1]}, SecIPConfig=${new_resources[2]}, VM_IP=${new_resources[3]}"
      if create_secondary_ipconfig ${new_resources[0]} ${new_resources[1]} $ipconfig_name $kube_ip_address; then
        log_message "INFO" "Successfully moved VIP to node $kube_vip_node"
        log_message "INFO" "=== Azure VIP fix process completed successfully ==="
        return 0
      else
        log_message "ERROR" "Failed to create secondary IP config on new node $kube_vip_node"
        log_message "INFO" "=== Azure VIP fix process failed ==="
        return 1
      fi
    else
      log_message "ERROR" "Failed to delete secondary IP config from old location"
      log_message "ERROR" "Cannot proceed with VIP migration"
      log_message "INFO" "=== Azure VIP fix process failed ==="
      return 1
    fi

  # Scenario 5: Kube VIP not associated with any VM
  else
    log_message "WARN" "Scenario: Kube-vip $kube_ip_address not associated with any VM in cluster"
    log_message "INFO" "Action: Waiting 30 seconds for VIP to stabilize"
    log_message "DEBUG" "Sleeping for 30 seconds..."
    sleep 30
    log_message "INFO" "Wait completed, VIP may stabilize in next iteration"
    log_message "INFO" "=== Azure VIP fix process completed with no action ==="
    return 0
  fi
}

# Execute the main function
main


