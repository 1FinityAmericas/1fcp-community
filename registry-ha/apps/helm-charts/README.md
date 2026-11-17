# Registry HA Helm Chart

Helm chart for deploying a High Availability Docker Registry on Kubernetes as part of the **1Finity Cloud Platform (1FCP)**. The registry (`3.0.0`) uses [MinIO](https://min.io/) (`RELEASE.2025-09-07T16-13-09Z`) as a distributed object storage backend and is pinned to master/control-plane nodes via node affinity.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Architecture](#architecture)
- [Parameters](#parameters)
- [Installation](#installation)
- [Uninstallation](#uninstallation)

---

## Prerequisites

| Requirement | Version / Note |
|---|---|
| Kubernetes | 1.23+ |
| Helm | 3.0.0+ |
| NGINX Ingress Controller | Deployed |
| Master nodes | Minimum 3 (registry is pinned to control-plane nodes) |
| Host path on each master | `/var/lib/minio-vol/` (100Gi per node) |

---

## Architecture

```
┌─────────────────────────────────────┐
│         NGINX Ingress                │
│   host: docker.reg             │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│         Docker Registry 3.0.0        │
│   (configured to use MinIO backend) │
└──────────────┬──────────────────────┘
               │ S3 API
┌──────────────▼──────────────────────┐
│           MinIO StatefulSet          │
│   3 replicas on master nodes         │
│   backend: /var/lib/minio-vol/       │
└─────────────────────────────────────┘
```

---

## Parameters

### Node Affinity

| Parameter | Description | Default |
|---|---|---|
| `masterNodes` | Number of master/control-plane nodes | `3` |
| `nodeAffinity.enabled` | Pin pods to control-plane nodes | `true` |
| `nodeAffinity.key` | Node label key for affinity | `node-role.kubernetes.io/control-plane` |
| `nodeAffinity.operator` | Affinity operator | `Exists` |

### Security Context

| Parameter | Description | Default |
|---|---|---|
| `securityContextEnabled` | Enable security context | `true` |
| `securityGroup.fsGroup` | Filesystem group ID | `1000` |
| `securityGroup.seccompProfile.type` | Seccomp profile | `RuntimeDefault` |
| `securityContext.runAsNonRoot` | Run as non-root | `true` |
| `securityContext.runAsUser` | Container user ID | `1000` |
| `securityContext.runAsGroup` | Container group ID | `1000` |
| `securityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `securityContext.capabilities.drop` | Drop capabilities | `["ALL"]` |

### MinIO

NOTE : The upstream MinIO image quay.io/minio/minio:RELEASE.2025-09-07T16-13-09Z is no longer open source. As a workaround, use the alternative image as below 

| `minio.image.repository` | MinIO image | `docker.io/1finitycom/minio` |


| Parameter | Description | Default |
|---|---|---|
| `minio.replicaCount` | Number of MinIO replicas | `3` |
| `minio.image.repository` | MinIO image | `quay.io/minio/minio` |
| `minio.image.tag` | MinIO image tag | `RELEASE.2025-09-07T16-13-09Z` |
| `minio.storageClass` | Storage class for MinIO PVs | `local-store` |
| `minio.storageSize` | Storage size per PV | `100Gi` |
| `minio.basePath` | Host base path for MinIO data | `/var/lib/minio-vol` |
| `minio.volumePaths[].pvName` | PV name for each replica | `minio-pv-0/1/2` |
| `minio.volumePaths[].path` | Host path on the node | `/var/lib/minio-vol/` |
| `minio.volumePaths[].node` | Node name for this PV | `master1/2/3` |

### Registry

| Parameter | Description | Default |
|---|---|---|
| `registry.image.repository` | Docker Registry image | `docker.io/library/registry` |
| `registry.image.tag` | Image tag | `3.0.0` |
| `registry.bucket` | MinIO bucket for registry blobs | `docker-registry` |
| `registry.region` | S3 region | `us-east-1` |
| `registry.logLevel` | Registry log level | `info` |

### Credentials

| Parameter | Description | Default |
|---|---|---|
| `credentials.create` | Create MinIO credentials secret | `true` |
| `credentials.name` | Secret name | `minio-creds` |
| `credentials.accessKey` | MinIO access key | `minioadmin` |
| `credentials.secretKey` | MinIO secret key | `minioadmin123` |
| `credentials.httpSecret` | Registry HTTP secret (random hash) | *(auto-generated)* |

### Storage Class & PVs

| Parameter | Description | Default |
|---|---|---|
| `createStorageClass` | Create the `local-store` StorageClass | `true` |
| `createPVs` | Create PersistentVolumes from `minio.volumePaths` | `true` |

### Bucket Init Job

| Parameter | Description | Default |
|---|---|---|
| `bucketInit.enabled` | Run a job to create the MinIO bucket on first deploy | `true` |
| `bucketInit.backoffLimit` | Job retry limit | `3` |

### TLS

| Parameter | Description | Default |
|---|---|---|
| `tls.enabled` | Enable registry-side TLS handling | `false` |
| `tls.source` | TLS source (`secret` or `minio`) | `secret` |
| `tls.secretName` | TLS secret name | `registry-tls` |
| `tls.ca.distributeToNodes` | Distribute CA cert to cluster nodes | `false` |
| `tls.ca.source` | CA source (`minio` or `secret`) | `minio` |
| `tls.ca.secretName` | CA secret name | `registry-ca` |

### Proxy Registry

| Parameter | Description | Default |
|---|---|---|
| `proxy_reg.enabled` | Enable proxy to upstream registry (e.g. Artifactory) | `false` |

### Ingress

| Parameter | Description | Default |
|---|---|---|
| `ingress.enabled` | Enable NGINX ingress for the registry | `true` |
| `ingress.host` | Registry hostname | `docker.reg` |
| `ingress.annotations` | Ingress annotations | `nginx.ingress.kubernetes.io/proxy-body-size: "0"` |
| `minioConsoleIngress.enabled` | Enable MinIO console ingress | `false` |
| `minioConsoleIngress.host` | MinIO console hostname | `minio.<IP>.nip.io` |

---

## Installation

### 1 — Prepare host paths on each master node

On each master node, create the MinIO data directory:

```bash
sudo mkdir -p /var/lib/minio-vol
```

### 2 — Update `values.yaml`

Set the correct master node names under `minio.volumePaths`:

```yaml
minio:
  volumePaths:
    - pvName: minio-pv-0
      path: /var/lib/minio-vol/
      node: <master1-hostname>
    - pvName: minio-pv-1
      path: /var/lib/minio-vol/
      node: <master2-hostname>
    - pvName: minio-pv-2
      path: /var/lib/minio-vol/
      node: <master3-hostname>
```

### 3 — Deploy

```bash
helm upgrade --install registry \
  -f ./apps/helm-charts/values.yaml \
  ./apps/helm-charts \
  -n registry --create-namespace
```

### 4 — Verify deployment

```bash
kubectl get pods -n registry
kubectl get pvc  -n registry
kubectl get svc  -n registry
kubectl get ingress -n registry
```

Expected: all pods `Running`, PVCs `Bound`.

### 5 — Test the registry

```bash
# Pull and tag an image
docker pull hello-world
docker tag hello-world docker.reg/hello-world

# Push to the registry
docker push docker.reg/hello-world
```

---

## Uninstallation

```bash
helm delete registry -n registry

# Delete PVCs (not removed by helm delete)
kubectl delete pvc -n registry --all

# Delete PVs
kubectl delete pv minio-pv-0 minio-pv-1 minio-pv-2

# Delete StorageClass (if created by chart)
kubectl delete storageclass local-store

# Optional: clean host paths on each master node
sudo rm -rf /var/lib/minio-vol
```
