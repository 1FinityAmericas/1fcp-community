#!/bin/bash

# Configuration
NAMESPACE="ndl"
TOPIC="test-ha-topic3"
TOTAL_RECORDS=1000000
PODS=("kafka-0" "kafka-1" "kafka-2")
PARTITIONS=8
REPLICATION_FACTOR=3
RECORD_SIZE=1000
BOOTSTRAP_SERVER="kafka:9092"
GROUP_ID="perf-consumer-group"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

log "=== Starting Kafka HA Performance Test ==="

# Step 1: Check if topic exists
log "Checking if topic '$TOPIC' exists..."
kubectl exec -n "$NAMESPACE" "${PODS[0]}" -- kafka-topics --bootstrap-server "$BOOTSTRAP_SERVER" --describe --topic "$TOPIC" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  log "Topic does not exist. Creating topic '$TOPIC'..."
  kubectl exec -n "$NAMESPACE" "${PODS[0]}" -- kafka-topics --create --topic "$TOPIC" \
    --bootstrap-server "$BOOTSTRAP_SERVER" --partitions "$PARTITIONS" --replication-factor "$REPLICATION_FACTOR"
else
  log "Topic '$TOPIC' already exists."
fi

# Step 2: Detect running pods
RUNNING_PODS=()
for POD in "${PODS[@]}"; do
  STATUS=$(kubectl get pod "$POD" -n "$NAMESPACE" --no-headers 2>/dev/null | awk '{print $3}')
  if [[ "$STATUS" == "Running" ]]; then
    RUNNING_PODS+=("$POD")
  fi
done

if [ ${#RUNNING_PODS[@]} -eq 0 ]; then
  log "No running Kafka pods found. Exiting."
  exit 1
fi

RECORDS_PER_POD=$((TOTAL_RECORDS / ${#RUNNING_PODS[@]}))
log "Distributing $TOTAL_RECORDS records across ${#RUNNING_PODS[@]} running pods (Each: $RECORDS_PER_POD records)"

# Step 3: Prepare temp dirs
TMPDIR=$(mktemp -d)
PRODUCE_TMP="$TMPDIR/produce"
CONSUME_TMP="$TMPDIR/consume"
mkdir -p "$PRODUCE_TMP" "$CONSUME_TMP"

# Step 4: Start producer test in parallel
log "Starting parallel producers..."
for POD in "${RUNNING_PODS[@]}"; do
  {
    start=$(date +%s)
    log "Producing from $POD..."
    kubectl exec -n "$NAMESPACE" "$POD" -- /bin/sh -c "
      kafka-producer-perf-test --topic $TOPIC \
      --num-records $RECORDS_PER_POD --throughput -1 \
      --producer-props bootstrap.servers=$BOOTSTRAP_SERVER \
      batch.size=65536 acks=1 linger.ms=5 buffer.memory=4294967296 \
      compression.type=none request.timeout.ms=30000 \
      --record-size $RECORD_SIZE" > /dev/null 2>&1
    end=$(date +%s)
    echo $((end - start)) > "$PRODUCE_TMP/$POD"
    log "Producer $POD finished in $((end - start)) seconds"
  } &
done
wait

# Step 5: Producer timing summary
total_produce_time=0
for POD in "${RUNNING_PODS[@]}"; do
  TIME=$(cat "$PRODUCE_TMP/$POD")
  total_produce_time=$((total_produce_time + TIME))
done
avg_produce_time=$((total_produce_time / ${#RUNNING_PODS[@]}))

log "All producers finished. Total time: $total_produce_time seconds, Average per pod: $avg_produce_time seconds"
log "Total records produced: $((RECORDS_PER_POD * ${#RUNNING_PODS[@]}))"

# Step 6: Wait before consumers
log "Waiting 10 seconds before consuming..."
sleep 10

# Step 7: Detect running pods again
UPDATED_RUNNING_PODS=()
for POD in "${PODS[@]}"; do
  STATUS=$(kubectl get pod "$POD" -n "$NAMESPACE" --no-headers 2>/dev/null | awk '{print $3}')
  if [[ "$STATUS" == "Running" ]]; then
    UPDATED_RUNNING_PODS+=("$POD")
  fi
done

if [ ${#UPDATED_RUNNING_PODS[@]} -eq 0 ]; then
  log "No running Kafka pods available for consumption. Exiting."
  exit 1
fi

RECORDS_PER_POD=$((TOTAL_RECORDS / ${#UPDATED_RUNNING_PODS[@]}))
log "Distributing $TOTAL_RECORDS records across ${#UPDATED_RUNNING_PODS[@]} running pods for consumption (Each: $RECORDS_PER_POD records)"

# Step 8: Start consumer test in parallel
log "Starting parallel consumers..."
for POD in "${UPDATED_RUNNING_PODS[@]}"; do
  {
    start=$(date +%s)
    log "Consuming from $POD..."
    kubectl exec -n "$NAMESPACE" "$POD" -- /bin/bash -c "
      kafka-consumer-perf-test --topic $TOPIC \
      --bootstrap-server $BOOTSTRAP_SERVER --messages $RECORDS_PER_POD" > /dev/null 2>&1
    end=$(date +%s)
    echo "$((end - start))" > "$CONSUME_TMP/$POD"
    log "Consumer $POD finished in $((end - start)) seconds"
  } &
done
wait

# Step 9: Consumer timing summary
total_consume_time=0
for POD in "${UPDATED_RUNNING_PODS[@]}"; do
  TIME=$(cat "$CONSUME_TMP/$POD")
  total_consume_time=$((total_consume_time + TIME))
done
avg_consume_time=$((total_consume_time / ${#UPDATED_RUNNING_PODS[@]}))

log "All consumers finished. Total time: $total_consume_time seconds, Average per pod: $avg_consume_time seconds"
log "Total records consumed: $((RECORDS_PER_POD * ${#UPDATED_RUNNING_PODS[@]}))"

# Cleanup
rm -rf "$TMPDIR"

log "=== Kafka HA Performance Test Completed ==="


