# Helm Chart for Kafka


This [Helm](https://helm.sh/) chart installs [Kafka].

## Prerequisites

- Kubernetes cluster 1.23+
- Helm 3.0.0+
- [Persistent Volumes (PV)](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) provisioner support in the underlying infrastructure.


Configurable Parameters for Kafka Helm Chart

The following table lists the configurable parameters of the Kafka chart and their default values:


| Parameter                                                           | Description                            | Default                              |
| ------------------------------------------------------------------- | -------------------------------------- | ------------------------------------ |
| **Replica Count**                                                   |                                        |                                      |
| `brokers`                                                           | Number of Kafka broker pods            | `3`                                  |
| **Global / Image**                                                  |                                        |                                      |
| `global.imageRegistry`                                              | Global image registry for all images   | `artifactory.fnc.fujitsu.com/fcp/1.0`            |
| `image`                                                             | Kafka broker image                     | `kafka`                              |
| `imageTag`                                                          | Kafka broker image tag                 | `7.9.2`                              |
| `imagePullPolicy`                                                   | Kafka broker image pull policy         | `IfNotPresent`                       |
| `initBusyBoxContainer.image`                                        | Init container image                   | `busybox`                            |
| `initBusyBoxContainer.imageTag`                                     | Init container image tag               | `1.33.1`                             |
| `initBusyBoxContainer.imagePullPolicy`                              | Init container image pull policy       | `IfNotPresent`                       |
| `prometheus.image`                                                  | Prometheus JMX exporter image          | `prometheus-jmx-exporter-kubernetes` |
| `prometheus.imageTag`                                               | Prometheus JMX exporter image tag      | `0.3.1`                              |
| `prometheus.imagePullPolicy`                                        | Prometheus image pull policy           | `IfNotPresent`                       |
| **Pod Settings**                                                    |                                        |                                      |
| `podManagementPolicy`                                               | StatefulSet pod management policy      | `OrderedReady`                       |
| `updateStrategy`                                                    | Update strategy for StatefulSet        | `RollingUpdate`                      |
| **Security Context**                                                |                                        |                                      |
| `securityContext.runAsUser`                                         | Pod container user ID                  | `1000`                               |
| `securityContext.runAsGroup`                                        | Pod container group ID                 | `1000`                               |
| `securityGroup.fsGroup`                                             | Pod filesystem group ID                | `1000`                               |
| **Kafka Settings / Overrides**                                      |                                        |                                      |
| `configurationOverrides.default.replication.factor`                 | Default replication factor for topics  | `3`                                  |
| `configurationOverrides.num.partitions`                             | Default number of partitions per topic | `8`                                  |
| `configurationOverrides.offsets.topic.replication.factor`           | Replication factor for offset topic    | `3`                                  |
| `configurationOverrides.message.max.bytes`                          | Max message size in bytes              | `10000000`                           |
| `configurationOverrides.acks`                                       | Producer acks setting                  | `-1`                                 |
| `configurationOverrides.max.request.size`                           | Max request size                       | `10000000`                           |
| `configurationOverrides.max.block.ms`                               | Max block time                         | `5000`                               |
| `configurationOverrides.max.in.flight.requests.per.connection`      | Max in-flight requests per connection  | `1`                                  |
| `configurationOverrides.producer.purgatory.purge.interval.requests` | Purge interval for producer requests   | `10000`                              |
| `configurationOverrides.replica.lag.time.max.ms`                    | Max replica lag time                   | `10000`                              |
| `configurationOverrides.zookeeper.session.timeout.ms`               | Zookeeper session timeout              | `30000`                              |
| `configurationOverrides.delete.topic.enable`                        | Allow topic deletion                   | `false`                              |
| `configurationOverrides.log.roll.hours`                             | Log roll interval in hours             | `24`                                 |
| `configurationOverrides.log.retention.hours`                        | Log retention in hours                 | `24`                                 |
| `heapOptions`                                                       | JVM heap options for Kafka broker      | `-Xms1G -Xmx2G`                      |
| `insync.replicas`                                                   | Number of in-sync replicas             | `1`                                  |
| `retention.bytes`                                                   | Log retention size in bytes            | `536870912`                          |
| `retention.ms`                                                      | Log retention in ms                    | `259200000`                          |
| `roll.ms`                                                           | Log roll interval in ms                | `259200000`                          |
| `segment.bytes`                                                     | Log segment size                       | `1073741824`                         |
| **Zookeeper Connection**                                            |                                        |                                      |
| `zookeeper.serviceName`                                             | Zookeeper service name                 | `zookeeper`                          |
| `zookeeper.namespace`                                               | Namespace where Zookeeper runs         | `ndl`                                |
| `zookeeper.port`                                                    | Zookeeper client port                  | `2181`                               |
| `zookeeper.svc`                                                     | Zookeeper FQDN                         | `svc.cluster.local`                  |
| **Node / Network Settings**                                         |                                        |                                      |
| `nodeAffinity.enabled`                                              | Enable node affinity                   | `False`                              |
| `nodeport.enabled`                                                  | Enable NodePort service                | `False`                              |
| `nodeport.servicePort`                                              | NodePort service port                  | `9092`                               |
| `nodeport.firstListenerPort`                                        | First listener port                    | `31090`                              |
| **Prometheus / JMX**                                                |                                        |                                      |
| `prometheus.enabled`                                                | Enable Prometheus exporter             | `False`                              |
| `jmx.port`                                                          | Broker JMX port                        | `5555`                               |
| `prometheus.port`                                                   | Prometheus port                        | `5556`                               |




## Installation & Uninstallation Steps of Kafka application

### Kafka  Installation
Note:
1. Make sure to edit the parameters as per requirement; the current values are defaults from the `values.yaml`.
2. Update `<namespace_name>` in the Helm command; if the namespace does not exist, create it (ex: `kubectl create ns <namespace_name>`).

```bash

helm upgrade --install kafka --namespace <namespace_name> --create-namespace \
  -f values.yaml ./ \
  --set global.imageRegistry=artifactory.fnc.fujitsu.com/fcp/1.0 \
  --set global.ns=ndl \
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
  --set zookeeper.namespace=ndl \
  --set zookeeper.port=2181 \
  --set zookeeper.svc=svc.cluster.local






Uninstallation of Kafka using Helm command

helm uninstall zookeeper -n <namespace_name>

# Example:
helm uninstall Kafka -n Kafka


