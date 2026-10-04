# Cassandra Helm Chart

Helm chart for deploying [Apache Cassandra](https://cassandra.apache.org/) `4.1.5` on Kubernetes as part of the **1Finity Cloud Platform (1FCP)**. Cassandra is a distributed, wide-column NoSQL database designed for high availability with no single point of failure.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Parameters](#parameters)
- [Installation](#installation)
- [Multi-DC (Geo) Deployment](#multi-dc-geo-deployment)
- [Uninstallation](#uninstallation)
- [Configuration Details](#configuration-details)
- [Troubleshooting](#troubleshooting)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Kubernetes | 1.24+ |
| Helm | 3.2.0+ |
| PV Provisioner | Required if persistence is enabled |

---

## Quick Start

```bash
helm install cassandra -n <namespace> . -f values.yaml
```

---

## Parameters

### Global

| Name | Description | Default |
|---|---|---|
| `imageRegistry` | Docker image registry | `artifactory.fnc.fujitsu.com/fcp/1.0` |
| `storageClass` | Global StorageClass for Persistent Volumes | `rancher-dynamic-local-path` |
| `imagePullSecrets` | Registry pull secret names | `[{"name": "vnc-docker-registry-key"}]` |

### Common

| Name | Description | Default |
|---|---|---|
| `nameOverride` | Partial name override | `""` |
| `fullnameOverride` | Full name override | `""` |

### Image

| Name | Description | Default |
|---|---|---|
| `image.repository` | Cassandra image repository | `cassandra` |
| `image.tag` | Image tag | `4.1.5-debian-12-r0-patched` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| `image.debug` | Enable debug mode | `false` |

### Cluster

| Name | Description | Default |
|---|---|---|
| `cluster.name` | Cluster name | `cassandra` |
| `cluster.replicaCount` | Number of Cassandra replicas | `1` |
| `cluster.seedCount` | Number of seed nodes | `1` |
| `cluster.seeds` | Comma-separated seed node IPs (empty = auto-discovery) | `""` |
| `cluster.numTokens` | Number of tokens per node | `256` |
| `cluster.datacenter` | Datacenter name | `dc1` |
| `cluster.rack` | Rack name | `rack1` |
| `cluster.endpointSnitch` | Endpoint snitch class | `GossipingPropertyFileSnitch` |
| `cluster.readTimeout` | Read timeout | `10000ms` |
| `cluster.writeTimeout` | Write timeout | `5000ms` |
| `cluster.pdbEnabled` | Enable Pod Disruption Budget | `false` |
| `cluster.minAvailable` | Minimum available pods | `1` |
| `cluster.maxUnavailable` | Maximum unavailable pods | `""` |
| `cluster.internodeEncryption` | Internode encryption (`none`, `all`, `dc`, `rack`) | `none` |
| `cluster.clientEncryption` | Enable client-to-node TLS | `false` |
| `cluster.domain` | Kubernetes cluster domain | `cluster.local` |

### JVM

| Name | Description | Default |
|---|---|---|
| `jvm.extraOpts` | Extra JVM options | `""` |
| `jvm.maxHeapSize` | Max heap size | `2G` |
| `jvm.newHeapSize` | New generation heap size | `600M` |

### Database Credentials

| Name | Description | Default |
|---|---|---|
| `dbUser.user` | Cassandra admin username | `cassandra` |
| `dbUser.password` | Cassandra admin password | `cassandra` |
| `dbUser.existingSecret` | Existing secret name | `""` |

### Service

| Name | Description | Default |
|---|---|---|
| `service.type` | Service type | `ClusterIP` |
| `service.port` | CQL port | `9042` |
| `service.loadBalancerIP` | Load balancer IP | `""` |
| `service.annotations` | Service annotations | `{}` |

### Persistence

| Name | Description | Default |
|---|---|---|
| `persistence.enabled` | Enable PVC | `true` |
| `persistence.storageClass` | Storage class | `""` |
| `persistence.annotations` | PVC annotations | `{}` |
| `persistence.accessModes` | Access modes | `["ReadWriteOnce"]` |
| `persistence.size` | PVC size | `8Gi` |

### Resources

| Name | Description | Default |
|---|---|---|
| `resources.requests.cpu` | CPU request | `2` |
| `resources.requests.memory` | Memory request | `2Gi` |
| `resources.limits.cpu` | CPU limit | `4` |
| `resources.limits.memory` | Memory limit | `4Gi` |

### Health Probes

| Name | Description | Default |
|---|---|---|
| `startupProbe.enabled` | Enable startup probe | `false` |
| `startupProbe.initialDelaySeconds` | Initial delay | `70` |
| `startupProbe.periodSeconds` | Period | `60` |
| `startupProbe.timeoutSeconds` | Timeout | `50` |
| `startupProbe.failureThreshold` | Failure threshold | `5` |
| `livenessProbe.enabled` | Enable liveness probe | `true` |
| `livenessProbe.initialDelaySeconds` | Initial delay | `300` |
| `livenessProbe.periodSeconds` | Period | `60` |
| `livenessProbe.timeoutSeconds` | Timeout | `30` |
| `livenessProbe.failureThreshold` | Failure threshold | `5` |
| `readinessProbe.enabled` | Enable readiness probe | `true` |
| `readinessProbe.initialDelaySeconds` | Initial delay | `60` |
| `readinessProbe.periodSeconds` | Period | `10` |
| `readinessProbe.timeoutSeconds` | Timeout | `30` |
| `readinessProbe.failureThreshold` | Failure threshold | `5` |

### Security Context

| Name | Description | Default |
|---|---|---|
| `securityContext.enabled` | Enable security context | `true` |
| `securityContext.fsGroup` | Filesystem group ID | `1001` |
| `securityContext.runAsUser` | Container user ID | `1001` |

### StatefulSet

| Name | Description | Default |
|---|---|---|
| `statefulset.updateStrategy` | Update strategy | `OnDelete` |
| `statefulset.rollingUpdatePartition` | Rolling update partition | `""` |

### Network Policy

| Name | Description | Default |
|---|---|---|
| `networkPolicy.enabled` | Enable network policy | `false` |
| `networkPolicy.allowExternal` | Allow external connections | `true` |

### Metrics (Prometheus)

| Name | Description | Default |
|---|---|---|
| `metrics.enabled` | Enable Prometheus exporter | `false` |
| `metrics.image.repository` | Exporter image repository | `cassandra-exporter` |
| `metrics.image.tag` | Exporter image tag | `2.3.4-debian-10-r84` |
| `metrics.image.pullPolicy` | Pull policy | `IfNotPresent` |
| `metrics.resources.limits.cpu` | CPU limit | `200m` |
| `metrics.resources.limits.memory` | Memory limit | `128Mi` |
| `metrics.resources.requests.cpu` | CPU request | `200m` |
| `metrics.resources.requests.memory` | Memory request | `128Mi` |
| `metrics.podAnnotations` | Pod annotations | `{"prometheus.io/scrape": "true", "prometheus.io/port": "8080"}` |

### TLS / Encryption

| Name | Description | Default |
|---|---|---|
| `tlsEncryptionSecretName` | Secret with keystore, truststore, and passwords | `""` |
| `cluster.internodeEncryption` | Internode encryption type | `none` |
| `cluster.clientEncryption` | Enable client-to-node TLS | `false` |

### Configuration & Init

| Name | Description | Default |
|---|---|---|
| `existingConfiguration` | ConfigMap with custom Cassandra configuration | `cassandra-config` |
| `initDBConfigMap` | ConfigMap with CQL init scripts | `""` |

### Pod Scheduling

| Name | Description | Default |
|---|---|---|
| `podAnnotations` | Pod annotations | `{}` |
| `podLabels` | Extra pod labels | `{}` |
| `affinity` | Affinity rules | `{}` |
| `nodeSelector` | Node selector | `{}` |
| `tolerations` | Tolerations | `[]` |

---

## Installation

```bash
helm install cassandra -n <namespace> . -f values.yaml
```

> **Tip:** List all releases with `helm list`

---

## Multi-DC (Geo) Deployment

### Deploy DC1

Edit `values.yaml`:

```yaml
cluster:
  datacenter: dc1
  seeds: ""
```

```bash
helm install cassandra -n <namespace> . -f values.yaml
```

Get DC1 seed node IP:

```bash
kubectl get pods -o wide -n <namespace>
```

### Deploy DC2 (connected to DC1)

Edit `values.yaml`:

```yaml
cluster:
  datacenter: dc2
  seeds: "<DC1_SEED_IP>"    # Use "IP1,IP2" for multiple seeds
```

```bash
helm install cassandra -n <namespace> . -f values.yaml
```

**Requirements:** DC names must differ (`dc1`, `dc2`); recommended 1–2 seed nodes per DC.

Verify both DCs appear:

```bash
kubectl exec -it cassandra-0 -n <namespace> -- nodetool status
```

---

## Uninstallation

> Helm delete does **not** remove PVCs — they must be deleted manually.

```bash
helm delete cassandra -n <namespace>
kubectl delete pvc -n <namespace> -l app=cassandra
```

---

## Configuration Details

### Custom Cassandra configuration

Provide a ConfigMap name in `existingConfiguration`. The ConfigMap should contain the Cassandra configuration files.

### Enabling TLS

1. Create a Kubernetes secret containing the keystore, truststore, and their passwords.
2. Set `tlsEncryptionSecretName` to the secret name.
3. Set `cluster.internodeEncryption` (`none`, `all`, `dc`, `rack`).
4. Set `cluster.clientEncryption: true` for client-to-node TLS.

### Enabling Prometheus metrics

```yaml
metrics:
  enabled: true
```

The exporter will be available on port `8080` and auto-annotated for Prometheus scraping.

### Persistence

The chart mounts a Persistent Volume at `/bitnami/cassandra`. Dynamic provisioning is used by default.

---

## Troubleshooting

### Pod stuck in Pending state

```bash
kubectl get pv
kubectl describe pvc <pvc-name> -n <namespace>
```

Check for available PersistentVolumes and StorageClass availability.

### Cassandra not starting

```bash
kubectl logs <pod-name> -n <namespace>
```

Common causes:
- Insufficient CPU or memory resources
- StorageClass not available
- Image pull errors
