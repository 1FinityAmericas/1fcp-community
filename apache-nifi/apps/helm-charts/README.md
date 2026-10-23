# Apache NiFi Helm Chart

Helm chart for deploying an Apache NiFi `2.9.0` multi-node cluster on Kubernetes as part of the **1Finity Cloud Platform (1FCP)**.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Parameters](#parameters)
- [Installation](#installation)
- [Uninstallation](#uninstallation)
- [Custom Volumes (hostPath)](#custom-volumes-hostpath)

---

## Prerequisites

| Requirement | Version |
|---|---|
| Kubernetes | 1.23+ |
| Helm | 3.0.0+ |
| Ingress Controller | NGINX |
| StorageClass | `rancher-dynamic-local-path` (default) |

---

## Parameters

### Release

| Parameter | Description | Default |
|---|---|---|
| `fullnameOverride` | Release name override | `nifi` |

### Image

| Parameter | Description | Default | `docker.io` |
| `image.repository` | Image repository | `apache/nifi` |
| `image.tag` | Image tag | `2.9.0` |
| `image.pullPolicy` | Pull policy | `IfNotPresent` |

### Security Context

| Parameter | Description | Default |
|---|---|---|
| `securityContext.runAsUser` | Pod user ID | `1000` |
| `securityContext.runAsGroup` | Pod group ID | `1000` |
| `securityContext.fsGroup` | Filesystem group ID | `1000` |
| `securityContext.seccompProfile.type` | Seccomp profile type | `RuntimeDefault` |
| `containerSecurityContext.runAsUser` | Container user ID | `1000` |
| `containerSecurityContext.runAsGroup` | Container group ID | `1000` |
| `containerSecurityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `containerSecurityContext.seccompProfile.type` | Container seccomp profile | `RuntimeDefault` |

### Service

| Parameter | Description | Default |
|---|---|---|
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `8443` |

### Ingress

| Parameter | Description | Default |
|---|---|---|
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `""` |
| `ingress.ip` | Ingress IP/domain | `apache-nifi.<IP>.nip.io` |
| `ingress.tls[0].secretName` | TLS secret name | `apache-nifi-secret` |
| `ingress.hosts[0].host` | Ingress host | `apache-nifi.<IP>.nip.io` |
| `ingress.hosts[0].paths[0].path` | Ingress path | `/nifi(.*)` |

### Resources & Replicas

| Parameter | Description | Default |
|---|---|---|
| `replicaCount` | Number of NiFi pods | `3` |
| `resources.requests.cpu` | CPU request | `2` |
| `resources.requests.memory` | Memory request | `2Gi` |
| `resources.limits.cpu` | CPU limit | `4` |
| `resources.limits.memory` | Memory limit | `4Gi` |

### Persistence

| Parameter | Description | Default |
|---|---|---|
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.accessModes` | PVC access modes | `[ReadWriteOnce]` |
| `persistence.size` | PV size | `10Gi` |
| `persistence.storageClassName` | Storage class | `rancher-dynamic-local-path` |

> **Note:** Actual PVC sizes are hardcoded in the chart: `conf-pvc` = 100Mi, `data` = 5Gi.

### RBAC

| Parameter | Description | Default |
|---|---|---|
| `rbac.create` | Create RBAC resources | `true` |

### JVM

| Parameter | Description | Default |
|---|---|---|
| `jvm.xms` | Initial heap size | `1g` |
| `jvm.xmx` | Maximum heap size | `2g` |
| `jvm.extra` | Extra JVM arguments | `""` |

### Authentication

| Parameter | Description | Default |
|---|---|---|
| `auth.mode` | Auth mode | `singleUser` |
| `auth.providerIdentifier` | Provider identifier | `single-user-provider` |
| `auth.username` | Admin username | `admin` |
| `auth.password` | Admin password (min 12 chars) | `0NifiAdmin@123` |
| `auth.hashedPassword` | Optional pre-hashed password | `""` |

### NiFi Properties

| Parameter | Description | Default |
|---|---|---|
| `properties.web.protocol` | Web protocol | `https` |
| `properties.web.host` | Web host | `0.0.0.0` |
| `properties.web.port` | Web port | `8443` |
| `properties.cluster.isNode` | Enable cluster node mode | `true` |
| `properties.cluster.nodeReadTimeout` | Node read timeout | `5 min` |
| `properties.cluster.nodeConnectionTimeout` | Node connection timeout | `30 sec` |
| `properties.cluster.requestReplicationClaimTimeout` | Replication claim timeout | `5 min` |
| `properties.s2s.enabled` | Enable Site-to-Site | `false` |
| `properties.s2s.port` | Site-to-Site port | `10000` |
| `nifiWebProxyHost` | NiFi web proxy host | `apache-nifi.<IP>.nip.io` |

### Health Probes

| Parameter | Description | Default |
|---|---|---|
| `probes.liveness.initialDelaySeconds` | Liveness probe initial delay | `120` |
| `probes.liveness.periodSeconds` | Liveness probe period | `15` |
| `probes.liveness.timeoutSeconds` | Liveness probe timeout | `5` |
| `probes.liveness.failureThreshold` | Liveness probe failure threshold | `8` |
| `probes.readiness.initialDelaySeconds` | Readiness probe initial delay | `90` |
| `probes.readiness.periodSeconds` | Readiness probe period | `10` |
| `probes.readiness.timeoutSeconds` | Readiness probe timeout | `5` |
| `probes.readiness.failureThreshold` | Readiness probe failure threshold | `12` |

### Custom Volume Mounts (hostPath)

| Parameter | Description | Default |
|---|---|---|
| `customConf.enabled` | Enable custom config mount | `false` |
| `customConf.storageSize` | Storage size | `100Mi` |
| `customConf.hostPath` | Host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/conf` |
| `customLib.enabled` | Enable custom library mount | `false` |
| `customLib.storageSize` | Storage size | `5Gi` |
| `customLib.hostPath` | Host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/lib` |
| `customExtensions.enabled` | Enable custom extensions mount | `false` |
| `customExtensions.storageSize` | Storage size | `5Gi` |
| `customExtensions.hostPath` | Host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/extensions` |
| `dpmScripts.enabled` | Enable DPM scripts mount | `false` |
| `dpmScripts.storageSize` | Storage size | `1Gi` |
| `dpmScripts.hostPath` | Host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/dpm-scripts` |

### Scheduling

| Parameter | Description | Default |
|---|---|---|
| `podAnnotations` | Pod annotations | `{}` |
| `nodeSelector` | Node selector | `{}` |
| `tolerations` | Tolerations | `[]` |
| `affinity` | Affinity rules | `{}` |

---

## Installation

### 1. Create namespace

```bash
kubectl create namespace <nifi-namespace>
```

### 2. Verify StorageClass

```bash
kubectl get storageclass
```

Ensure `rancher-dynamic-local-path` or your configured StorageClass is available.

### 3. Deploy Apache NiFi

```bash
helm upgrade --install nifi \
  -f ./apps/helm-charts/values.yaml \
  ./apps/helm-charts \
  -n <nifi-namespace>
```

### 4. Verify deployment

```bash
kubectl get pods -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl get pvc  -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl get svc  -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
```

Expected: all pods `Running`, `1/1` Ready.

### 5. Retrieve credentials

```bash
kubectl -n <nifi-namespace> get secret apache-nifi-secret \
  -o jsonpath="{.data.username}" | base64 --decode
kubectl -n <nifi-namespace> get secret apache-nifi-secret \
  -o jsonpath="{.data.password}" | base64 --decode
```

Default credentials: `admin` / `0NifiAdmin@123`

### 6. Access the NiFi UI

```
https://apache-nifi.<IP>.nip.io/nifi
```

---

## Uninstallation

### 1. Uninstall the Helm release

```bash
helm delete nifi -n <nifi-namespace>
```

### 2. Delete remaining resources

```bash
kubectl delete pvc          -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete secret       -n <nifi-namespace> apache-nifi-secret
kubectl delete svc          -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete configmap    -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete ingress      -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete role         -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete rolebinding  -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete serviceaccount -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
```

### 3. Remove custom hostPath directories (if enabled)

Run on all worker nodes:

```bash
sudo rm -rf /var/lib/docker/dynamic-local-path-mounts/nifi
```

### 4. Verify clean state

```bash
helm list -n <nifi-namespace>
kubectl get all,pvc,secret,configmap,ingress -n <nifi-namespace>
```

---

## Custom Volumes (hostPath)

To use custom configs, libraries, extensions, or DPM scripts:

1. Create host directories on **all worker nodes**:

   ```bash
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/conf
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/lib
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/extensions
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/dpm-scripts
   ```

2. Copy your files to the corresponding directories on all worker nodes.

3. Enable the volumes in `values.yaml`:

   ```yaml
   customConf:
     enabled: true
   customLib:
     enabled: true
   customExtensions:
     enabled: true
   dpmScripts:
     enabled: true
   ```

> Ensure identical data exists at the same paths on all worker nodes.
