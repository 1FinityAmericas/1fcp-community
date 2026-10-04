# Kafka Helm Chart

Helm chart for deploying [Apache Kafka](https://kafka.apache.org/) `7.9.2` on Kubernetes as part of the **1Finity Cloud Platform (1FCP)**. Kafka is deployed as a StatefulSet and connects to a pre-existing ZooKeeper cluster.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Parameters](#parameters)
- [Installation](#installation)
- [Uninstallation](#uninstallation)

---

## Prerequisites

| Requirement | Version / Note |
|---|---|
| Kubernetes | 1.23+ |
| Helm | 3.0.0+ |
| ZooKeeper | Running and accessible — see the [zookeeper](../../zookeeper) chart |
| PV Provisioner | Required |

---

## Parameters

### Replica Count

| Parameter | Description | Default |
|---|---|---|
| `brokers` | Number of Kafka broker pods | `3` |

### Image

| Parameter | Description | Default |
|---|---|---|
| `global.imageRegistry` | Global image registry | `artifactory.fnc.fujitsu.com/fcp/1.0` |
| `image` | Kafka broker image name | `kafka` |
| `imageTag` | Kafka broker image tag | `7.9.2` |
| `imagePullPolicy` | Image pull policy | `IfNotPresent` |
| `initBusyBoxContainer.image` | Init container image | `busybox` |
| `initBusyBoxContainer.imageTag` | Init container image tag | `1.33.1` |
| `initBusyBoxContainer.imagePullPolicy` | Init container pull policy | `IfNotPresent` |
| `prometheus.image` | Prometheus JMX exporter image | `prometheus-jmx-exporter-kubernetes` |
| `prometheus.imageTag` | Prometheus JMX exporter tag | `0.3.1` |
| `prometheus.imagePullPolicy` | Prometheus pull policy | `IfNotPresent` |

### Pod Settings

| Parameter | Description | Default |
|---|---|---|
| `podManagementPolicy` | StatefulSet pod management policy | `OrderedReady` |
| `updateStrategy` | StatefulSet update strategy | `RollingUpdate` |

### Security Context

| Parameter | Description | Default |
|---|---|---|
| `securityContext.runAsUser` | Container user ID | `1000` |
| `securityContext.runAsGroup` | Container group ID | `1000` |
| `securityGroup.fsGroup` | Filesystem group ID | `1000` |

### Resources

| Parameter | Description | Default |
|---|---|---|
| `resources.requests.cpu` | CPU request | `300m` |
| `resources.requests.memory` | Memory request | `1.5Gi` |
| `resources.limits.cpu` | CPU limit | `500m` |
| `resources.limits.memory` | Memory limit | `2Gi` |

### Kafka Configuration Overrides

| Parameter | Description | Default |
|---|---|---|
| `configurationOverrides.default.replication.factor` | Default topic replication factor | `3` |
| `configurationOverrides.num.partitions` | Default partitions per topic | `8` |
| `configurationOverrides.offsets.topic.replication.factor` | Offset topic replication factor | `3` |
| `configurationOverrides.message.max.bytes` | Max message size (bytes) | `10000000` |
| `configurationOverrides.acks` | Producer acks setting | `-1` |
| `configurationOverrides.max.request.size` | Max request size (bytes) | `10000000` |
| `configurationOverrides.max.block.ms` | Max block time (ms) | `5000` |
| `configurationOverrides.max.in.flight.requests.per.connection` | Max in-flight requests | `1` |
| `configurationOverrides.producer.purgatory.purge.interval.requests` | Purge interval | `10000` |
| `configurationOverrides.replica.lag.time.max.ms` | Max replica lag time (ms) | `10000` |
| `configurationOverrides.zookeeper.session.timeout.ms` | ZooKeeper session timeout (ms) | `30000` |
| `configurationOverrides.delete.topic.enable` | Allow topic deletion | `false` |
| `configurationOverrides.log.roll.hours` | Log roll interval (hours) | `24` |
| `configurationOverrides.log.retention.hours` | Log retention (hours) | `24` |
| `heapOptions` | JVM heap options | `-Xms1G -Xmx2G` |
| `insync.replicas` | Number of in-sync replicas | `1` |
| `retention.bytes` | Log retention size (bytes) | `536870912` |
| `retention.ms` | Log retention (ms) | `259200000` |
| `roll.ms` | Log roll interval (ms) | `259200000` |
| `segment.bytes` | Log segment size (bytes) | `1073741824` |

### ZooKeeper Connection

| Parameter | Description | Default |
|---|---|---|
| `zookeeper.serviceName` | ZooKeeper service name | `zookeeper` |
| `zookeeper.namespace` | Namespace where ZooKeeper runs | `ndl` |
| `zookeeper.port` | ZooKeeper client port | `2181` |
| `zookeeper.svc` | ZooKeeper cluster domain suffix | `svc.cluster.local` |

### Persistence

| Parameter | Description | Default |
|---|---|---|
| `persistence.enabled` | Enable PVC | `true` |
| `persistence.size` | PVC size | `5Gi` |
| `persistence.storageClass` | Storage class | `rancher-dynamic-local-path` |

### Network / Node

| Parameter | Description | Default |
|---|---|---|
| `nodeAffinity.enabled` | Enable node affinity | `false` |
| `nodeport.enabled` | Enable NodePort service | `false` |
| `nodeport.servicePort` | NodePort service port | `9092` |
| `nodeport.firstListenerPort` | First listener port | `31090` |

### Prometheus / JMX

| Parameter | Description | Default |
|---|---|---|
| `prometheus.enabled` | Enable Prometheus exporter | `false` |
| `jmx.port` | Broker JMX port | `5555` |
| `prometheus.port` | Prometheus scrape port | `5556` |

---

## Installation

> Update `<namespace_name>` below. Create the namespace first if it does not exist:
> ```bash
> kubectl create ns <namespace_name>
> ```

```bash
helm upgrade --install kafka \
  --namespace <namespace_name> --create-namespace \
  -f values.yaml ./ \
  --set global.imageRegistry=artifactory.fnc.fujitsu.com/fcp/1.0 \
  --set global.ns=<namespace_name> \
  --set brokers=3 \
  --set image=kafka \
  --set imageTag=7.9.2 \
  --set imagePullPolicy=IfNotPresent \
  --set prometheus.image=prometheus-jmx-exporter-kubernetes \
  --set prometheus.imageTag=0.3.1 \
  --set prometheus.imagePullPolicy=IfNotPresent \
  --set initBusyBoxContainer.image=busybox \
  --set initBusyBoxContainer.imageTag=1.33.1 \
  --set initBusyBoxContainer.imagePullPolicy=IfNotPresent \
  --set resources.requests.cpu=300m \
  --set resources.requests.memory=1.5Gi \
  --set resources.limits.cpu=500m \
  --set resources.limits.memory=2Gi \
  --set podManagementPolicy=OrderedReady \
  --set updateStrategy=RollingUpdate \
  --set-string configurationOverrides.default.replication.factor=3 \
  --set-string configurationOverrides.num.partitions=8 \
  --set-string configurationOverrides.offsets.topic.replication.factor=3 \
  --set-string configurationOverrides.message.max.bytes=10000000 \
  --set-string configurationOverrides.acks=-1 \
  --set-string configurationOverrides.max.request.size=10000000 \
  --set-string configurationOverrides.max.block.ms=5000 \
  --set-string configurationOverrides.max.in.flight.requests.per.connection=1 \
  --set-string configurationOverrides.producer.purgatory.purge.interval.requests=10000 \
  --set-string configurationOverrides.replica.lag.time.max.ms=10000 \
  --set-string configurationOverrides.zookeeper.session.timeout.ms=30000 \
  --set-string configurationOverrides.delete.topic.enable=false \
  --set-string configurationOverrides.log.roll.hours=24 \
  --set-string configurationOverrides.log.retention.hours=24 \
  --set heapOptions="-Xms1G -Xmx2G" \
  --set insync.replicas=1 \
  --set retention.bytes=536870912 \
  --set retention.ms=259200000 \
  --set roll.ms=259200000 \
  --set segment.bytes=1073741824 \
  --set nodeAffinity.enabled=false \
  --set nodeport.enabled=false \
  --set nodeport.servicePort=9092 \
  --set nodeport.firstListenerPort=31090 \
  --set persistence.enabled=true \
  --set persistence.size=5Gi \
  --set persistence.storageClass=rancher-dynamic-local-path \
  --set securityContext.runAsGroup=1000 \
  --set securityContext.runAsUser=1000 \
  --set securityGroup.fsGroup=1000 \
  --set prometheus.enabled=false \
  --set jmx.port=5555 \
  --set prometheus.port=5556 \
  --set zookeeper.serviceName=zookeeper \
  --set zookeeper.namespace=<namespace_name> \
  --set zookeeper.port=2181 \
  --set zookeeper.svc=svc.cluster.local
```

---

## Uninstallation

```bash
helm uninstall kafka -n <namespace_name>
```

> **Example:**
> ```bash
> helm uninstall kafka -n kafka
> ```
