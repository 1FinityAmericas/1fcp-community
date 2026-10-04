#!/bin/bash

# Configuration
NAMESPACE="ndl"
CLIENT_POD_NAME="kafka-test-client"
TOPIC="temp"
TOTAL_RECORDS=1000000
PARTITIONS=8
REPLICATION_FACTOR=3
RECORD_SIZE=1000
BOOTSTRAP_SERVER="kafka.ndl.svc.cluster.local:9092"
GROUP_ID="temp-final"
IMAGE="fnc.fujitsu.reg/mvp/2.0/kafka:7.6.1"
ZK_NAMESPACE="ndl"
ZK_PODS=("zookeeper-0" "zookeeper-1" "zookeeper-2")
KAFKA_PODS=("kafka-0" "kafka-1" "kafka-2")

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Utility to check pod running
check_pod_status() {
  local pod_name=$1
  local namespace=$2
  kubectl get pod "$pod_name" -n "$namespace" --no-headers | awk '{print $3}'
}

# Log the status of Zookeeper and Kafka pods
log_pod_status() {
  log "=== Checking Pod Statuses ==="

  # Check and log status of Zookeeper pods
  for zk in "${ZK_PODS[@]}"; do
    status=$(check_pod_status "$zk" "$ZK_NAMESPACE")
    log "Zookeeper Pod $zk status: $status"
  done

  # Check and log status of Kafka pods
  for kafka in "${KAFKA_PODS[@]}"; do
    status=$(check_pod_status "$kafka" "$NAMESPACE")
    log "Kafka Pod $kafka status: $status"
  done

  log "=== Pod Status Check Complete ==="
}


# Find Current Zookeeper Leader
find_current_zk_leader() {
  for zk in "${ZK_PODS[@]}"; do
    status=$(check_pod_status "$zk" "$ZK_NAMESPACE")
    if [[ "$status" == "Running" ]]; then
      mode=$(kubectl exec -n "$ZK_NAMESPACE" "$zk" -c zookeeper-server -- sh -c "echo srvr | nc localhost 2181 | grep Mode")
      if [[ "$mode" == *"leader"* ]]; then
        echo "$zk"
        return
      fi
    fi
  done
  echo ""
}

# Wait until leader is elected
wait_for_zk_leader_election() {
  log "Waiting for Zookeeper leader election..."
  retries=5
  delay=5
  for ((i=1; i<=retries; i++)); do
    leader=$(find_current_zk_leader)
    if [[ -n "$leader" ]]; then
      log "New Zookeeper leader elected: $leader"
      return 0
    fi
    log "No leader yet. Retry $i/$retries"
    sleep $delay
  done
  log "Leader election failed after retries!"
  exit 1
}

# Describe Kafka Topic
describe_kafka_topic() {
  log "Describing topic $TOPIC..."
  kubectl exec -n "$NAMESPACE" "$CLIENT_POD_NAME" -- bash -c "
    kafka-topics --bootstrap-server $BOOTSTRAP_SERVER \
    --describe --topic $TOPIC
  "
}

# Simulate Pod Failure
simulate_failure() {
  local pod=$1
  log "Deleting pod $pod..."
  kubectl delete pod "$pod" -n "$NAMESPACE" --grace-period=0 --force
}

# Create Kafka client if not exists
setup_client_pod() {
  if ! kubectl get pod "$CLIENT_POD_NAME" -n "$NAMESPACE" >/dev/null 2>&1; then
    log "Creating Kafka test client pod..."
    cat <<EOF | kubectl apply -n "$NAMESPACE" -f - 
apiVersion: v1
kind: Pod
metadata:
  name: $CLIENT_POD_NAME
spec:
  containers:
  - name: client
    image: $IMAGE
    command: ["sleep", "3600"]
  restartPolicy: Never
EOF
    kubectl wait --for=condition=Ready pod/$CLIENT_POD_NAME -n "$NAMESPACE" --timeout=120s
  else
    log "Kafka test client pod already exists."
  fi
}

# Main Test Flow

log "=== Starting Kafka High Availability Test ==="

setup_client_pod

log_pod_status

# Step 1: Find initial Zookeeper leader
initial_leader=$(find_current_zk_leader)
log "Current Zookeeper leader: $initial_leader"

# Step 2: Create topic if not exists
kubectl exec -n "$NAMESPACE" "$CLIENT_POD_NAME" -- bash -c "
kafka-topics --bootstrap-server $BOOTSTRAP_SERVER \
  --describe --topic $TOPIC > /dev/null 2>&1 || \
kafka-topics --bootstrap-server $BOOTSTRAP_SERVER \
  --create --topic $TOPIC --partitions $PARTITIONS --replication-factor $REPLICATION_FACTOR
"

describe_kafka_topic

# Step 3: Fail Kafka pod and Zookeeper pod
FAILED_KAFKA="${KAFKA_PODS[$RANDOM % ${#KAFKA_PODS[@]}]}"
FAILED_ZK="${ZK_PODS[$RANDOM % ${#ZK_PODS[@]}]}"

simulate_failure "$FAILED_KAFKA"
simulate_failure "$FAILED_ZK"

# Step 4: If failed Zookeeper is leader, wait for election
if [[ "$FAILED_ZK" == "$initial_leader" ]]; then
  log "Zookeeper leader $FAILED_ZK failed! Waiting for new leader election..."
  wait_for_zk_leader_election
else
  log "Failed Zookeeper pod was not leader. Continuing..."
fi

# Check if Kafka leadership and rebalancing occurred
log "Waiting 5sec for Kafka rebalancing after pod failure..."
sleep 5

# Step 5: Start Producer
log "Starting producer perf test..."
start_produce=$(date +%s)
producer_output=$(kubectl exec -n "$NAMESPACE" "$CLIENT_POD_NAME" -- bash -c "
kafka-producer-perf-test --topic $TOPIC \
  --num-records $TOTAL_RECORDS --throughput -1 --record-size $RECORD_SIZE \
  --producer-props bootstrap.servers=$BOOTSTRAP_SERVER \
  batch.size=65536 acks=1 linger.ms=5 buffer.memory=4294967296 compression.type=none request.timeout.ms=60000
")
end_produce=$(date +%s)
produce_time=$((end_produce - start_produce))
log "Producer completed in $produce_time seconds."

# Extract actual produced data count
echo "Produce Records :"
echo "$producer_output"
produced_records=$(echo "$producer_output" | awk -F', ' '{print $1}' | tail -n 1)


describe_kafka_topic

# Step 6: Fail another Zookeeper pod after producing
sleep 5
SECOND_FAILED_ZK="${ZK_PODS[$RANDOM % ${#ZK_PODS[@]}]}"
log "Simulating second Zookeeper failure: $SECOND_FAILED_ZK"
simulate_failure "$SECOND_FAILED_ZK"

# Step 7: Check if second failure was leader
current_leader=$(find_current_zk_leader)

if [[ "$SECOND_FAILED_ZK" == "$current_leader" ]]; then
  log "Second Zookeeper leader $SECOND_FAILED_ZK failed! Waiting for new leader election..."
  wait_for_zk_leader_election
else
  log "Second Zookeeper pod was not leader. Continuing..."
fi

# Step 8: Start Consumer
log "Starting consumer perf test..."
start_consume=$(date +%s)
consumer_output=$(kubectl exec -n "$NAMESPACE" "$CLIENT_POD_NAME" -- bash -c "
kafka-consumer-perf-test --topic $TOPIC --messages $TOTAL_RECORDS \
  --bootstrap-server $BOOTSTRAP_SERVER \
  --timeout 200000 --group $GROUP_ID
")
end_consume=$(date +%s)
consume_time=$((end_consume - start_consume))
log "Consumer completed in $consume_time seconds."

# Extract actual consumed data count
echo "Consume Records $consumer_output"
consumed_records=$(echo "$consumer_output" | awk -F', ' '{print $5}' | tail -n 1)



log "=== Kafka High Availability Test Completed Successfully ==="

# Print Summary Report
echo " "
echo "===================================="
echo "Summary Report:"
echo "Record Produced: $produced_records"
echo "Records Consumed: $consumed_records consumed"
echo "Average Produce Time (secs): $produce_time"
echo "Average Consume Time (secs): $consume_time"
echo "===================================="

