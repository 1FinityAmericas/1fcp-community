#!/bin/bash

# Configuration
NAMESPACE="ndl"
TOPIC="perf-test-par"
TOTAL_RECORDS=1000000
PODS=("kafka-0" "kafka-1" "kafka-2")
PARTITIONS=8 
REPLICATION_FACTOR=3
RECORD_SIZE=1000 
RECORDS_PER_POD=$((TOTAL_RECORDS / ${#PODS[@]}))
BOOTSTRAP_SERVER="kafka:9092"

log() {
  echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1"
}

# Step 1: Check if topic exists, create if not
log "Checking if topic '$TOPIC' exists..."
kubectl exec -n "$NAMESPACE" "${PODS[0]}" -- kafka-topics --bootstrap-server "$BOOTSTRAP_SERVER" --describe --topic "$TOPIC" > /dev/null 2>&1
if [ $? -ne 0 ]; then
  log "Topic does not exist. Creating topic '$TOPIC'..."
  kubectl exec -n "$NAMESPACE" "${PODS[0]}" -- kafka-topics --create --topic "$TOPIC" \
    --bootstrap-server "$BOOTSTRAP_SERVER" --partitions "$PARTITIONS" --replication-factor "$REPLICATION_FACTOR"
else
  log "Topic '$TOPIC' already exists."
fi

# Create temp dirs
TMPDIR=$(mktemp -d)
PRODUCE_TMP="$TMPDIR/produce"
CONSUME_TMP="$TMPDIR/consume"
mkdir -p "$PRODUCE_TMP" "$CONSUME_TMP"

# Step 2: Produce in parallel
log "Starting parallel producers..."
for POD in "${PODS[@]}"; do
  {
    start=$(date +%s)
    log "Producing $RECORDS_PER_POD records from $POD..."
    kubectl exec -n "$NAMESPACE" "$POD" -- /bin/sh -c "kafka-producer-perf-test --topic $TOPIC \
      --num-records $RECORDS_PER_POD --throughput -1 \
      --producer-props bootstrap.servers=$BOOTSTRAP_SERVER \
      batch.size=65536 acks=1 linger.ms=5 buffer.memory=4294967296 \
      compression.type=none request.timeout.ms=30000 \
      --record-size $RECORD_SIZE" > /dev/null 2>&1
    end=$(date +%s)
    echo $((end - start)) > "$PRODUCE_TMP/$POD"
    log "Producer $POD finished in $((end - start)) seconds (Records: $RECORDS_PER_POD)"
  } &
done
wait

# Calculate produce stats
total_produce_time=0
total_records_produced=0
for POD in "${PODS[@]}"; do
  TIME=$(cat "$PRODUCE_TMP/$POD")
  total_produce_time=$((total_produce_time + TIME))
  total_records_produced=$((total_records_produced + RECORDS_PER_POD))
done
avg_produce_time=$((total_produce_time / ${#PODS[@]}))

log "All producers finished. Total time: $total_produce_time seconds, Average per pod: $avg_produce_time seconds"
log "Total records produced: $total_records_produced"

# Step 3: Wait before consuming
log "Waiting for 10 seconds before consuming..."
sleep 10

# Step 4: Consume in parallel
log "Starting parallel consumers..."
for POD in "${PODS[@]}"; do
  {
    start=$(date +%s)
    log "Consuming $RECORDS_PER_POD records from $POD..."
    kubectl exec -n "$NAMESPACE" "$POD" -- /bin/bash -c "kafka-consumer-perf-test \
      --topic $TOPIC --bootstrap-server $BOOTSTRAP_SERVER --messages $RECORDS_PER_POD" > /dev/null 2>&1
    end=$(date +%s)
    echo $((end - start)) > "$CONSUME_TMP/$POD"
    log "Consumer $POD finished in $((end - start)) seconds (Records: $RECORDS_PER_POD)"
  } &
done
wait

# Calculate consume stats
total_consume_time=0
total_records_consumed=0
for POD in "${PODS[@]}"; do
  TIME=$(cat "$CONSUME_TMP/$POD")
  total_consume_time=$((total_consume_time + TIME))
  total_records_consumed=$((total_records_consumed + RECORDS_PER_POD))
done
avg_consume_time=$((total_consume_time / ${#PODS[@]}))

log "All consumers finished. Total time: $total_consume_time seconds, Average per pod: $avg_consume_time seconds"
log "Total records consumed: $total_records_consumed"

# Clean up
rm -rf "$TMPDIR"
