# Helm Chart for Zookeeper


This [Helm](https://helm.sh/) chart installs [Zookeeper].

## Prerequisites

- Kubernetes cluster 1.23+
- Helm 3.0.0+
- [Persistent Volumes (PV)](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) provisioner support in the underlying infrastructure.

## Configuration

The following table lists the configurable parameters of the Zookeeper chart and the default values.

| Parameter                         | Description                                | Default                                      |
| --------------------------------- | ------------------------------------------ | --------------------------------------------|
| **ReplicaCount**                   |                                            |                                              |
| `replicaCount`                     | Number of Zookeeper nodes                  | `3`                                         |
| **Image**                          |                                            |                                              |
| `image.registry`                   | Image registry                             | `artifactory.fnc.fujitsu.com/fcp/1.0`                  |
| `image.repository`                 | Zookeeper image repository                 | `zookeeper`                                 |
| `image.tag`                        | Zookeeper image tag                         | `7.9.2`                                     |
| `image.pullPolicy`                 | Image pull policy                           | `IfNotPresent`                              |
| **Pod Settings**                   |                                            |                                              |
| `podManagementPolicy`              | StatefulSet pod management policy           | `OrderedReady`                              |
| `updateStrategy`                   | Update strategy for StatefulSet             | `RollingUpdate`                             |
| **SecurityContext**                |                                            |                                              |
| `securityContext.runAsUser`        | Pod container user ID                       | `1000`                                      |
| `securityContext.runAsGroup`       | Pod container group ID                       | `1000`                                      |
| `securityContext.fsGroup`          | Pod filesystem group ID                      | `1000`                                      |
| **Zookeeper Settings**             |                                            |                                              |
| `tickTime`                          | Zookeeper tickTime (ms)                     | `2000`                                      |
| `syncLimit`                          | Zookeeper sync limit                        | `5`                                         |
| `initLimit`                          | Zookeeper init limit                        | `10`                                        |
| `maxClientCnxns`                     | Maximum client connections                   | `60`                                        |
| `autoPurgeSnapRetainCount`           | Snap retain count for auto purge             | `3`                                         |
| `autoPurgePurgeInterval`             | Interval for purge (hours)                  | `24`                                        |
| `heapOptions`                        | Java heap options                            | `-Xms2G -Xmx2G`                             |
| `serverPort`                         | Zookeeper server port                        | `2888`                                      |
| `leaderElectionPort`                 | Leader election port                          | `3888`                                      |
| `clientPort`                         | Client port                                  | `2181`                                      |
| **Persistence**                     |                                            |                                              |
| `persistence.enabled`                | Enable persistent storage                    | `True`                                      |
| `persistence.storageClass`           | Storage class for PVC                         | `rancher-dynamic-local-path`               |
| `persistence.dataDirSize`            | Data directory size                           | `5Gi`                                       |
| `persistence.dataLogDirSize`         | Data log directory size                        | `5Gi`                                       |
| **Resources**                        |                                            |                                              |
| `resources.requests.cpu`             | CPU request                                  | `2`                                         |
| `resources.requests.memory`          | Memory request                               | `2Gi`                                       |
| `resources.limits.cpu`               | CPU limit                                    | `3`                                         |
| `resources.limits.memory`            | Memory limit                                 | `5Gi`                                       |
| **Prometheus JMX**                    |                                            |                                              |
| `prometheus.jmx.enabled`             | Enable JMX Prometheus exporter               | `False`                                      |
| `prometheus.jmx.image.repository`    | Prometheus exporter image repository         | `kafka-prometheus-jmx-exporter`            |
| `prometheus.jmx.image.tag`           | Prometheus exporter image tag                | `v2`                                        |
| `prometheus.jmx.image.pullPolicy`    | Image pull policy                             | `IfNotPresent`                              |
| `prometheus.jmx.port`                | Prometheus exporter port                      | `5556`                                      |


## Installation & Uninstallation Steps of Zookeeper application

### Zookeeper Installation
Note:
1. Make sure to edit the parameters as per requirement; the current values are defaults from the `values.yaml`.
2. Update `<namespace_name>` in the Helm command; if the namespace does not exist, create it (ex: `kubectl create ns <namespace_name>`).

```bash
helm upgrade --install zookeeper --namespace <namespace_name> --create-namespace \
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
  --set persistence.enabled=True \
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




Uninstallation of Zookeeper using Helm command

helm uninstall zookeeper -n <namespace_name>

# Example:
helm uninstall zookeeper -n zookeeper

