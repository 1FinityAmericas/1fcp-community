# BEGIN_FNC_Windsurf_Watermark (DO NOT REMOVE)

# Cassandra Helm Chart

[Apache Cassandra](https://cassandra.apache.org/) is a free and open-source, distributed, wide column store, NoSQL database management system designed to handle large amounts of data across many commodity servers, providing high availability with no single point of failure.

## TL;DR

```bash
helm install -n <namespace> cassandra . -f values.yaml 
```

## Introduction

This chart bootstraps a [Cassandra](https://cassandra.apache.org/) deployment on a [Kubernetes](https://kubernetes.io) cluster using the [Helm](https://helm.sh) package manager.

## Prerequisites

- Kubernetes 1.24+
- Helm 3.2.0+
- PV provisioner support in the underlying infrastructure (if persistence is enabled)

## Installing the Chart

To install the chart with the release name `cassandra`:

```bash
helm install -n <namespace> cassandra . -f values.yaml
```


---

## Deploy Cassandra with Geo (Multi-DC)

### Deploy DC1

Edit `values.yaml`:

```yaml
cluster:
  datacenter: dc1
  seeds: ""
```

Install:

```bash
helm install cassandra -n <namespace> . -f values.yaml
```

Get DC1 seed node IP:

```bash
kubectl get pods -o wide -n <namespace>
```

---

### Deploy DC2 (connect to DC1)

Edit `values.yaml`:

```yaml
cluster:
  datacenter: dc2
  seeds: DC1_SEED_IP
```

Multiple seeds:

```yaml
seeds: IP1,IP2
```

Install:

```bash
helm install cassandra -n <namespace> . -f values.yaml
```

---

### Requirements

DC names must be different (`dc1`, `dc2`)
Recommended: 1–2 seed nodes per DC

---

### Verify Cluster

```bash
kubectl exec -it cassandra-0 -n <namespace> -- nodetool status
```

Both datacenters should appear.

---

The command deploys Cassandra on the Kubernetes cluster in the default configuration. The [Parameters](#parameters) section lists the parameters that can be configured during installation.

> **Tip**: List all releases using `helm list`

## Uninstalling the Chart

To uninstall/delete the `cassandra` deployment:
(Helm delete does not delete pvc created, manual delete is required)
```bash
helm delete -n <namespace> cassandra

kubectl -n <namespace> delete pvc -l app=cassandra
```

The command removes all the Kubernetes components associated with the chart and deletes the release.

## Parameters

### Global parameters

| Name | Description | Value |
|------|-------------|-------|
| `imageRegistry` | Global Docker image registry | `artifactory.fnc.fujitsu.com/fcp/1.0` |
| `storageClass` | Global StorageClass for Persistent Volume(s) | `rancher-dynamic-local-path` |
| `imagePullSecrets` | Global Docker registry secret names as an array | `[{"name": "vnc-docker-registry-key"}]` |

### Common parameters

| Name | Description | Value |
|------|-------------|-------|
| `nameOverride` | String to partially override cassandra.fullname | `""` |
| `fullnameOverride` | String to fully override cassandra.fullname | `""` |

### Cassandra image parameters

| Name | Description | Value |
|------|-------------|-------|
| `image.repository` | Cassandra image repository | `cassandra` |
| `image.tag` | Cassandra image tag (immutable tags are recommended) | `4.1.5-debian-12-r0-patched` |
| `image.pullPolicy` | Cassandra image pull policy | `IfNotPresent` |
| `image.debug` | Enable image debug mode | `false` |

### Cassandra cluster parameters

| Name | Description | Value |
|------|-------------|-------|
| `cluster.name` | Cassandra cluster name | `cassandra` |
| `cluster.replicaCount` | Number of Cassandra replicas | `1` |
| `cluster.seedCount` | Number of seed nodes | `1` |
| `cluster.seeds` | Comma-separated list of seed nodes (leave empty for auto-discovery) | `""` |
| `cluster.numTokens` | Number of tokens for each node | `256` |
| `cluster.datacenter` | Datacenter name | `dc1` |
| `cluster.rack` | Rack name | `rack1` |
| `cluster.endpointSnitch` | Endpoint snitch class name | `GossipingPropertyFileSnitch` |
| `cluster.readTimeout` | Read timeout | `10000ms` |
| `cluster.writeTimeout` | Write timeout | `5000ms` |
| `cluster.pdbEnabled` | Enable Pod Disruption Budget | `false` |
| `cluster.minAvailable` | Minimum number of available pods | `1` |
| `cluster.maxUnavailable` | Maximum number of unavailable pods | `""` |
| `cluster.internodeEncryption` | Internode encryption type (none, all, dc, rack) | `none` |
| `cluster.clientEncryption` | Enable client-to-node encryption | `false` |
| `cluster.domain` | Kubernetes cluster domain | `cluster.local` |

### JVM parameters

| Name | Description | Value |
|------|-------------|-------|
| `jvm.extraOpts` | Extra JVM options | `""` |
| `jvm.maxHeapSize` | Max heap size for JVM | `2G` |
| `jvm.newHeapSize` | New generation heap size for JVM | `600M` |

### Database credentials

| Name | Description | Value |
|------|-------------|-------|
| `dbUser.user` | Cassandra admin username | `cassandra` |
| `dbUser.password` | Cassandra admin password | `cassandra` |
| `dbUser.existingSecret` | Name of existing secret containing Cassandra credentials | `""` |

### Service parameters

| Name | Description | Value |
|------|-------------|-------|
| `service.type` | Kubernetes Service type | `ClusterIP` |
| `service.port` | CQL port | `9042` |
| `service.loadBalancerIP` | Load balancer IP if service type is LoadBalancer | `""` |
| `service.annotations` | Additional custom annotations for Cassandra service | `{}` |

### Persistence parameters

| Name | Description | Value |
|------|-------------|-------|
| `persistence.enabled` | Enable Cassandra data persistence using PVC | `true` |
| `persistence.storageClass` | PVC Storage Class for Cassandra data volume | `""` |
| `persistence.annotations` | Persistent Volume Claim annotations | `{}` |
| `persistence.accessModes` | Persistent Volume Access Modes | `["ReadWriteOnce"]` |
| `persistence.size` | PVC Storage Request for Cassandra data volume | `8Gi` |

### Volume Permissions parameters

| Name | Description | Value |
|------|-------------|-------|
| `volumePermissions.enabled` | Enable init container that changes volume permissions | `false` |
| `volumePermissions.image.registry` | Init container volume-permissions image registry | `docker.io` |
| `volumePermissions.image.repository` | Init container volume-permissions image repository | `bitnami/minideb` |
| `volumePermissions.image.tag` | Init container volume-permissions image tag | `buster` |
| `volumePermissions.image.pullPolicy` | Init container volume-permissions image pull policy | `Always` |
| `volumePermissions.resources` | Init container resources | `{}` |

### Resource parameters

| Name | Description | Value |
|------|-------------|-------|
| `resources.limits.cpu` | CPU limit | `4` |
| `resources.limits.memory` | Memory limit | `4Gi` |
| `resources.requests.cpu` | CPU request | `2` |
| `resources.requests.memory` | Memory request | `2Gi` |

### Probe parameters

| Name | Description | Value |
|------|-------------|-------|
| `startupProbe.enabled` | Enable startup probe | `false` |
| `startupProbe.initialDelaySeconds` | Initial delay seconds for startup probe | `70` |
| `startupProbe.periodSeconds` | Period seconds for startup probe | `60` |
| `startupProbe.timeoutSeconds` | Timeout seconds for startup probe | `50` |
| `startupProbe.successThreshold` | Success threshold for startup probe | `1` |
| `startupProbe.failureThreshold` | Failure threshold for startup probe | `5` |
| `livenessProbe.enabled` | Enable liveness probe | `true` |
| `livenessProbe.initialDelaySeconds` | Initial delay seconds for liveness probe | `300` |
| `livenessProbe.periodSeconds` | Period seconds for liveness probe | `60` |
| `livenessProbe.timeoutSeconds` | Timeout seconds for liveness probe | `30` |
| `livenessProbe.successThreshold` | Success threshold for liveness probe | `1` |
| `livenessProbe.failureThreshold` | Failure threshold for liveness probe | `5` |
| `readinessProbe.enabled` | Enable readiness probe | `true` |
| `readinessProbe.initialDelaySeconds` | Initial delay seconds for readiness probe | `60` |
| `readinessProbe.periodSeconds` | Period seconds for readiness probe | `10` |
| `readinessProbe.timeoutSeconds` | Timeout seconds for readiness probe | `30` |
| `readinessProbe.successThreshold` | Success threshold for readiness probe | `1` |
| `readinessProbe.failureThreshold` | Failure threshold for readiness probe | `5` |

### Pod parameters

| Name | Description | Value |
|------|-------------|-------|
| `podAnnotations` | Annotations for Cassandra pods | `{}` |
| `podLabels` | Extra labels for Cassandra pods | `{}` |
| `affinity` | Affinity for Cassandra pods assignment | `{}` |
| `nodeSelector` | Node labels for Cassandra pods assignment | `{}` |
| `tolerations` | Tolerations for Cassandra pods assignment | `[]` |

### StatefulSet parameters

| Name | Description | Value |
|------|-------------|-------|
| `statefulset.updateStrategy` | StatefulSet update strategy | `OnDelete` |
| `statefulset.rollingUpdatePartition` | Partition for rolling update | `""` |

### Security Context parameters

| Name | Description | Value |
|------|-------------|-------|
| `securityContext.enabled` | Enable security context | `true` |
| `securityContext.fsGroup` | Group ID for the filesystem | `1001` |
| `securityContext.runAsUser` | User ID for the container | `1001` |

### Container parameters

| Name | Description | Value |
|------|-------------|-------|
| `entrypoint` | Container entrypoint | `/entrypoint.sh` |
| `cmd` | Container command | `/run.sh` |

### Network Policy parameters

| Name | Description | Value |
|------|-------------|-------|
| `networkPolicy.enabled` | Enable network policy | `false` |
| `networkPolicy.allowExternal` | Allow external connections | `true` |

### TLS/Encryption parameters

| Name | Description | Value |
|------|-------------|-------|
| `tlsEncryptionSecretName` | Secret containing keystore, truststore and passwords | `""` |

### Configuration parameters

| Name | Description | Value |
|------|-------------|-------|
| `existingConfiguration` | ConfigMap with custom Cassandra configuration | `cassandra-config` |
| `initDBConfigMap` | ConfigMap with CQL scripts for initialization | `""` |

### Metrics parameters

| Name | Description | Value |
|------|-------------|-------|
| `metrics.enabled` | Enable Cassandra Prometheus exporter | `false` |
| `metrics.image.repository` | Cassandra exporter image repository | `cassandra-exporter` |
| `metrics.image.tag` | Cassandra exporter image tag | `2.3.4-debian-10-r84` |
| `metrics.image.pullPolicy` | Cassandra exporter image pull policy | `IfNotPresent` |
| `metrics.resources.limits.cpu` | CPU limit for metrics container | `200m` |
| `metrics.resources.limits.memory` | Memory limit for metrics container | `128Mi` |
| `metrics.resources.requests.cpu` | CPU request for metrics container | `200m` |
| `metrics.resources.requests.memory` | Memory request for metrics container | `128Mi` |
| `metrics.podAnnotations` | Annotations for metrics pods | `{"prometheus.io/scrape": "true", "prometheus.io/port": "8080"}` |

## Configuration and Installation Details

### Configuring Cassandra

You can specify custom Cassandra configuration by providing a ConfigMap name in `existingConfiguration`. This ConfigMap should contain the Cassandra configuration files.

### Persistence

The chart mounts a [Persistent Volume](https://kubernetes.io/docs/concepts/storage/persistent-volumes/) at `/bitnami/cassandra`. The volume is created using dynamic volume provisioning by default. An existing PersistentVolumeClaim can also be defined.

### Setting Pod's affinity

This chart allows you to set custom Pod affinity using the `affinity` parameter. Find more information about Pod's affinity in the [Kubernetes documentation](https://kubernetes.io/docs/concepts/configuration/assign-pod-node/#affinity-and-anti-affinity).

### Enabling TLS

To enable TLS encryption between nodes and clients:

1. Create a secret containing the keystore, truststore, and their passwords
2. Set `tlsEncryptionSecretName` to the name of the secret
3. Configure `cluster.internodeEncryption` (options: `none`, `all`, `dc`, `rack`)
4. Set `cluster.clientEncryption` to `true` for client-to-node encryption

### Enabling Metrics

To enable Prometheus metrics:

```yaml
metrics:
  enabled: true
```

The exporter will be available on port 8080 and automatically annotated for Prometheus scraping.

## Troubleshooting

### Pod stuck in Pending state

If pods are stuck in Pending state, check if there are available PersistentVolumes:

```bash
kubectl get pv
kubectl describe -n <namespace>pvc <pvc-name>
```

### Cassandra not starting

Check the logs for more information:

```bash
kubectl -n <namespace> logs <pod-name>
```

Common issues:
- Insufficient resources (CPU/Memory)
- Storage class not available
- Image pull errors

# END_FNC_Windsurf_Watermark (DO NOT REMOVE)
