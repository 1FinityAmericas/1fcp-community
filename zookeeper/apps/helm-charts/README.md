# ZooKeeper Helm Chart

Helm chart for deploying [Apache ZooKeeper](https://zookeeper.apache.org/) `7.9.2` on Kubernetes as part of the **1Finity Cloud Platform (1FCP)**. ZooKeeper is deployed as a StatefulSet and is a required dependency for Kafka.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Parameters](#parameters)
- [Installation](#installation)
- [Uninstallation](#uninstallation)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Kubernetes | 1.23+ |
| Helm | 3.0.0+ |
| PV Provisioner | Required |

---

## Parameters

### Replica Count

| Parameter | Description | Default |
|---|---|---|
| `replicaCount` | Number of ZooKeeper nodes (use odd numbers: 3, 5) | `3` |

### Image

| Parameter | Description | Default |
|---|---|---|
| `image.registry` | Image registry | `artifactory.fnc.fujitsu.com/fcp/1.0` |
| `image.repository` | ZooKeeper image repository | `zookeeper` |
| `image.tag` | Image tag | `7.9.2` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |

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
| `securityContext.fsGroup` | Filesystem group ID | `1000` |

### ZooKeeper Settings

| Parameter | Description | Default |
|---|---|---|
| `tickTime` | ZooKeeper tick time (ms) | `2000` |
| `syncLimit` | Sync limit (in ticks) | `5` |
| `initLimit` | Init limit (in ticks) | `10` |
| `maxClientCnxns` | Maximum client connections | `60` |
| `autoPurgeSnapRetainCount` | Snapshot retain count for auto-purge | `3` |
| `autoPurgePurgeInterval` | Auto-purge interval (hours) | `24` |
| `heapOptions` | JVM heap options | `-Xms2G -Xmx2G` |
| `serverPort` | ZooKeeper server (peer) port | `2888` |
| `leaderElectionPort` | Leader election port | `3888` |
| `clientPort` | Client port | `2181` |

### Persistence

| Parameter | Description | Default |
|---|---|---|
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.storageClass` | Storage class for PVCs | `rancher-dynamic-local-path` |
| `persistence.dataDirSize` | Data directory PVC size | `5Gi` |
| `persistence.dataLogDirSize` | Data log directory PVC size | `5Gi` |

### Resources

| Parameter | Description | Default |
|---|---|---|
| `resources.requests.cpu` | CPU request | `2` |
| `resources.requests.memory` | Memory request | `2Gi` |
| `resources.limits.cpu` | CPU limit | `3` |
| `resources.limits.memory` | Memory limit | `5Gi` |

### Prometheus JMX Exporter

| Parameter | Description | Default |
|---|---|---|
| `prometheus.jmx.enabled` | Enable JMX Prometheus exporter | `false` |
| `prometheus.jmx.image.repository` | Exporter image repository | `kafka-prometheus-jmx-exporter` |
| `prometheus.jmx.image.tag` | Exporter image tag | `v2` |
| `prometheus.jmx.image.pullPolicy` | Pull policy | `IfNotPresent` |
| `prometheus.jmx.port` | Prometheus exporter port | `5556` |

---

## Installation

> Update `<namespace_name>` below. Create the namespace first if it does not exist:
> ```bash
> kubectl create ns <namespace_name>
> ```

```bash
helm upgrade --install zookeeper \
  --namespace <namespace_name> --create-namespace \
  -f values.yaml ./ \
  --set servers=3 \
  --set minAvailable=2 \
  --set image.registry=artifactory.fnc.fujitsu.com/fcp/1.0 \
  --set image.repository=zookeeper \
  --set image.tag=7.9.2 \
  --set image.pullPolicy=IfNotPresent \
  --set podManagementPolicy=OrderedReady \
  --set updateStrategy=RollingUpdate \
  --set securityContext.runAsUser=1000 \
  --set securityContext.runAsGroup=1000 \
  --set securityContext.fsGroup=1000 \
  --set tickTime=2000 \
  --set syncLimit=5 \
  --set initLimit=10 \
  --set maxClientCnxns=60 \
  --set autoPurgeSnapRetainCount=3 \
  --set autoPurgePurgeInterval=24 \
  --set heapOptions="-Xms2G -Xmx2G" \
  --set serverPort=2888 \
  --set leaderElectionPort=3888 \
  --set clientPort=2181 \
  --set persistence.enabled=true \
  --set persistence.storageClass=rancher-dynamic-local-path \
  --set persistence.dataDirSize=5Gi \
  --set persistence.dataLogDirSize=5Gi \
  --set resources.limits.cpu=3 \
  --set resources.limits.memory=5Gi \
  --set resources.requests.cpu=2 \
  --set resources.requests.memory=2Gi \
  --set jmx.port=5555 \
  --set prometheus.jmx.enabled=false \
  --set prometheus.jmx.image.repository=kafka-prometheus-jmx-exporter \
  --set prometheus.jmx.image.tag=v2 \
  --set prometheus.jmx.image.pullPolicy=IfNotPresent \
  --set prometheus.jmx.port=5556
```

### Verify deployment

```bash
kubectl get pods -n <namespace_name> -l app=zookeeper
kubectl get pvc  -n <namespace_name>
kubectl get svc  -n <namespace_name>
```

Expected: all pods `Running`, `1/1` Ready, PVCs `Bound`.

---

## Uninstallation

```bash
helm uninstall zookeeper -n <namespace_name>

# Delete PVCs (not removed by helm uninstall)
kubectl delete pvc -n <namespace_name> -l app=zookeeper
```

> **Example:**
> ```bash
> helm uninstall zookeeper -n zookeeper
> kubectl delete pvc -n zookeeper -l app=zookeeper
> ```
