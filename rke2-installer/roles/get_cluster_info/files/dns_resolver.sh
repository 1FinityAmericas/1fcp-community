#!/bin/bash

# Use the logs_dir environment variable passed from the playbook
LOGS_DIR="${OUTPUT_DIR}/logs"


# Function to check DNS resolution for the target pod's DNS name
check_target_dns_resolution() {
  local pod_name="$1"
  local target_pod="$2"

  # Construct the full DNS name for the target pod
  full_target_pod_name="$target_pod.headless-svc-stateful.default.svc.cluster.local"

  # Attempt to resolve the target pod's DNS name using nslookup inside the pod
  result=$(kubectl exec "$pod_name" -n default -- bash -c "nslookup $full_target_pod_name" 2>/dev/null)

  # Check if the exec command was successful
  if [[ $? -ne 0 ]]; then
    echo "Target Pod DNS Not Found ($full_target_pod_name)"
  else
    # Extract the IP addresses from the nslookup command output
    ip_addresses=$(echo "$result" | awk '/Address: / {print $2}')

    # Check if there are any IPs found
    if [[ -z "$ip_addresses" ]]; then
      echo "Target Pod DNS Not Found (No IP resolved)"
    else
      echo "Target Pod DNS Resolved: $ip_addresses"
    fi
  fi
}

# Function to curl a target pod from the current pod
check_curl_result() {
  local pod_name="$1"
  local target_pod="$2"

  # Attempt to curl the target pod from the current pod
  curl_result=$(kubectl exec "$pod_name" -n default -- curl -s -o /dev/null -w "%{http_code}" "$target_pod.headless-svc-stateful.default.svc.cluster.local")

  # Check if the curl was successful (e.g., HTTP 200)
  if [[ "$curl_result" -eq 200 ]]; then
    echo "Curl successful, HTTP Status: $curl_result"
  else
    echo "Curl failed, HTTP Status: $curl_result"
  fi
}

# Get the list of pods related to the headless-statefulset (assuming the label `app=headless-stateful` is used)
pods=$(kubectl get pods -n default -l app=headless-stateful -o jsonpath='{.items[*].metadata.name}')

# Create a file to store the results inside the logs_dir
output_file="$LOGS_DIR/dns_results.csv"
echo "Pod Name,Target Pod,Target Pod DNS Resolution,Curl Result" > "$output_file"
echo "===========================================================" >> "$output_file"

# Iterate through each pod and check DNS resolution and curl result to all other headless-statefulset pods
for pod in $pods; do
  # Check if the pod exists before attempting to exec
  if kubectl get pod "$pod" -n default > /dev/null 2>&1; then
    # Get the IP of the source pod
    source_pod_ip=$(kubectl get pod "$pod" -n default -o jsonpath='{.status.podIP}')

    # Write the header for the current pod to the output file
    echo "======= Resolving Pod DNS and curl status for $pod to target pods ======" >> "$output_file"
    
    # Now check curl from the current pod to all other headless-statefulset pods
    for target_pod in $pods; do
      # Skip curl check to itself
      if [[ "$pod" != "$target_pod" ]]; then
        # Check the DNS resolution for the target pod
        target_dns_result=$(check_target_dns_resolution "$pod" "$target_pod")

        # Perform the curl check
        curl_result=$(check_curl_result "$pod" "$target_pod")

        # Output the result to the CSV file with the source pod's IP
        echo "$pod,$target_pod,$target_dns_result,$curl_result" >> "$output_file"
      fi
    done
    echo "" >> "$output_file"
  else
    echo "$pod,Not Found (Pod does not exist)" >> "$output_file"
  fi
done


