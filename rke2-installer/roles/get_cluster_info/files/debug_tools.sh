#!/bin/bash

# Output file for logging results
LOGS_DIR="$OUTPUT_DIR/logs"

# Function to log messages to OUTPUT_FILE
log() {
    echo -e "$1" | tee -a "$LOGS_DIR/cluster_results.log"
}

# Function to run all tests sequentially
run_all() {
    echo "Running all tests sequentially..."

    echo "1. Running Cluster Status Check (Node and Pod)..."
    check_node_status
    check_pod_status

    echo "2. Running Iperf3 Test..."
    run_iperf3_test

    echo "3. Running Network Overlay Test..."
    run_network_overlay_test

    echo "4. Running FIO Test..."
    run_fio_test

    echo "All tests completed."
}

# Function to get cluster node status
check_node_status() {
    echo "Starting Node status Check..."
    log "=================== Node Status  ======================"
    kubectl get nodes >> "$LOGS_DIR/cluster_results.log" 2>&1
    log "===================================================================="
    echo "Node Status check completed."
}

# Function to check pod statuses (cluster health status)
check_pod_status() {
    echo "Starting pod status check..."
    log "==================== Pod Status ===================="
    kubectl get pods --all-namespaces >> "$LOGS_DIR/cluster_results.log" 2>&1
    log "====================================================================="
    echo "Pod status check completed."
}

# Function to run iperf3 tests
run_iperf3_test() {
    echo "Starting iperf3 tests..."
    log "==================== iperf3 Test Results ============================"
    echo "Server,Client,Test Result"

    # Get the list of iperf pods, their IPs, and the nodes they are scheduled on
    pod_list=$(kubectl get po -n default -o wide | grep iperf | awk '{print $1}' | xargs)
    pod_ip_list=$(kubectl get po -n default -o wide | grep iperf | awk '{print $6}' | xargs)
    pod_schd_node_list=$(kubectl get po -n default -o wide | grep iperf | awk '{print $7}' | xargs)

    # Create the directory for iperf3 logs if not exists (using pwd instead of HOME)
    iperf_log_dir="$LOGS_DIR/iperf3_logs"
    if [ -d "$iperf_log_dir" ]; then
        log "Removing existing $iperf_log_dir"
        rm -rf "$iperf_log_dir"
    fi
    mkdir -p "$iperf_log_dir"

    # Convert the space-separated pod names into arrays
    IFS=' ' read -ra pods <<< "$pod_list"
    IFS=' ' read -ra pods_ip <<< "$pod_ip_list"
    IFS=' ' read -ra node_schd <<< "$pod_schd_node_list"

    # Iterate over the array with nested loops to run tests
    for ((i = 0; i < ${#pods[@]}; i++)); do
        echo "[INFO] Outer loop: $((i+1))"

        # Ensure that any existing iperf3 server process is terminated
        existing_server_pid=$(kubectl exec ${pods[i]} -n default -- ps aux | grep 'iperf3 -s' | grep -v grep | awk '{print $2}')
        if [ -n "$existing_server_pid" ]; then
            log "[INFO] Killing existing iperf3 server process (PID: $existing_server_pid)"
            kubectl exec ${pods[i]} -n default -- kill -9 $existing_server_pid
            sleep 3
        fi

        # Start iperf3 server on the pod
        kubectl exec -i ${pods[i]} -n default -- iperf3 -s -p 12345 >& $iperf_log_dir/server_${node_schd[i]} & 
        sleep 5 # Wait for the server to start

        for ((j = 0; j < ${#pods[@]}; j++)); do
            if [ $i -ne $j ]; then
                # Run the iperf3 client test and log the result
                kubectl exec -i ${pods[j]} -n default -- iperf3 -c ${pods_ip[i]} -p 12345 >> $iperf_log_dir/server_${node_schd[i]}_client_${node_schd[j]}
                sleep 5
            fi
        done

        # Kill the iperf3 server process after the inner loop
        kubectl exec ${pods[i]} -n default -- pkill iperf3
        sleep 5 # Allow time for cleanup
    done

    # Check for errors in the log files
    grep -Pz '\[\s+[4-5]\].*0\.00-10\.\d+\s+sec.*?GBytes.*?[0-7][0-9][0-9] Mbits/sec' $iperf_log_dir/* > /dev/null 2>&1
    if [[ $? -eq 0 ]]; then
        log "[ERROR] iperf3 test failed, Please check logs $iperf_log_dir for more info"
        error_occurred=true
    else
        log "iperf3 test run successfully, Please check $iperf_log_dir logs for more info"
    fi

    echo "Iperf3 tests completed."
    log "==================== iperf3 Test End ================================"
}

# Function to run network overlay tests
run_network_overlay_test() {
    echo "Starting network overlay test..."
    log "==================== Network Overlay Test ===================="

    # Start network overlay test message
    echo "=> Start network overlay test" >> "$LOGS_DIR/cluster_results.log"

    # Get all pods and their corresponding host nodes
    kubectl get pods -l name=overlaytest -o jsonpath='{range .items[*]}{@.metadata.name}{" "}{@.spec.nodeName}{"\n"}{end}' |
    while read spod shost; do
        echo "========= Starting test from $shost ===========" | tee -a "$LOGS_DIR/cluster_results.log"

        kubectl get pods -l name=overlaytest -o jsonpath='{range .items[*]}{@.status.podIP}{" "}{@.spec.nodeName}{"\n"}{end}' |
        while read tip thost; do
            kubectl --request-timeout='10s' exec "$spod" -c overlaytest -- /bin/sh -c "ping -c2 $tip > /dev/null 2>&1"
            RC=$?
            if [ $RC -ne 0 ]; then
                log "FAIL: $spod on $shost cannot reach pod IP $tip on $thost"
            else
                log "$shost can reach $thost"
            fi
        done
    done

    # End network overlay test message
    echo "=============== End network overlay test ===================" >> "$LOGS_DIR/cluster_results.log"

    # Final log message after all tests
    echo "Network overlay test completed."
    log "============================================================"
}

# Function to convert latency to milliseconds
convert_to_msec() {
    local timestamp=$1
    local unit=$2
    case "$unit" in
        nsec) echo "scale=3; $timestamp / 1000000" | bc ;;
        usec) echo "scale=3; $timestamp / 1000" | bc ;;
        msec) echo "$timestamp" ;;
        *) echo "Unknown time unit: $unit"; exit 1 ;;
    esac
}

# Function to run FIO tests
run_fio_test() {
    echo "Starting FIO tests..."
    log "==================== FIO Test Results ===================="
    log "ip_address,timestamp,write_iops,write_99th Latency (msec)"

    ip_address=$(hostname -I | awk '{print $1}')
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')

    # Loop to run the FIO test 5 times
    for i in {1..5}; do
        echo "Running FIO test iteration $i..."

        # Run the FIO test
        fio_output=$(fio --name=write-test --rw=write --ioengine=sync --fdatasync=1 \
            --size=100m --bs=4k --runtime=60s --group_reporting --directory=/tmp 2>&1)

        if [[ $? -ne 0 ]]; then
            log "Failed to run FIO on this node. Error: $fio_output"
            return
        fi

        write_iops=$(echo "$fio_output" | grep -oP "write: IOPS=\K[0-9]+")
        lat_unit=$(echo "$fio_output" | grep -oP "sync percentiles \(\K[^\)]+")
        write_99th=""

        if [[ -n "$lat_unit" ]]; then
            latency=$(echo "$fio_output" | grep -oP "99\.00th=\[\s*\K[0-9]+")
            write_99th=$(convert_to_msec "$latency" "$lat_unit")
        fi

        if [[ -n "$write_iops" && -n "$write_99th" ]]; then
            ip_address=$(echo "$ip_address" | tr -d '\n')
            timestamp=$(echo "$timestamp" | tr -d '\n')
            write_iops=$(echo "$write_iops" | tr -d '\n')
            write_99th=$(echo "$write_99th" | tr -d '\n')

            # Log the results for each iteration
            printf "%s,%s,%s,%s\n" "$ip_address" "$timestamp" "$write_iops" "$write_99th" >> "$LOGS_DIR/cluster_results.log"
        else
            log "Failed to parse FIO output on iteration $i"
        fi
    done

    echo "FIO tests completed."
    log "========== FIO Test Completed  =========="
}

# Main script execution starts here
run_all

