# MongoDB Replica Set Helm Charts

Helm charts for deploying a MongoDB Replica Set on Kubernetes using the **Percona Server for MongoDB Operator** as part of the **1Finity Cloud Platform (1FCP)**. The deployment follows a two-step flow: Operator → Database Cluster.

## Table of Contents

- [Available Charts](#available-charts)
- [Prerequisites](#prerequisites)
- [Deployment Flow](#deployment-flow)
- [Parameters](#parameters)
- [Installation](#installation)
- [Uninstallation](#uninstallation)

---

## Available Charts

| Chart | Description |
|---|---|
| `mongodb-rs-operator/` | Deploys the Percona MongoDB Operator |
| `mongodb-rs/` | Deploys the MongoDB replica set cluster (requires operator) |

---

## Prerequisites

| Requirement | Version / Note |
|---|---|
| Kubernetes | 1.32+ |
| Helm | v3+ |
| StorageClass | At least one configured in the cluster |
| Container registry access | Required |
| kubectl | Configured with cluster access |

---

## Deployment Flow

```
Step 1: Deploy mongodb-rs-operator
          ↓
Step 2: Deploy mongodb-rs (replica set cluster)
```

---

## Parameters

### Cluster (mongodb-rs)

#### Core

| Parameter | Description | Default |
|---|---|---|
| `crVersion` | Percona CR manifest version | `1.22.0` |
| `pause` | Safely stop the PSMDB cluster | `false` |
| `unmanaged` | Start cluster without operator management (cross-cluster replication) | `false` |
| `updateStrategy` | Pod update strategy (`SmartUpdate`, `RollingUpdate`, `OnDelete`) | `SmartUpdate` |
| `image.repository` | PSMDB container image repository | `percona-server-mongodb` |
| `image.tag` | PSMDB image tag | `7.0.31` |
| `imagePullPolicy` | Image pull policy | `IfNotPresent` |
| `initImage.repository` | Init image repository | `percona-server-mongodb-operator` |
| `initImage.tag` | Init image tag | `1.22.0` |

#### Storage Scaling

| Parameter | Description | Default |
|---|---|---|
| `storageScaling.enableVolumeScaling` | Allow PVC resize | `false` |
| `storageScaling.enableExternalAutoscaling` | Suppress storage discrepancy error if external autoscaling enabled | `false` |
| `storageScaling.autoscaling.enabled` | Enable automatic storage expansion | `false` |
| `storageScaling.autoscaling.triggerThresholdPercent` | Disk usage % that triggers expansion (50–95) | `80` |
| `storageScaling.autoscaling.growthStep` | Storage to add when threshold exceeded | `"2Gi"` |
| `storageScaling.autoscaling.maxSize` | Maximum PVC size limit | `""` |

#### Unsafe Flags

| Parameter | Description | Default |
|---|---|---|
| `unsafeFlags.tls` | Allow cluster without TLS | `false` |
| `unsafeFlags.replsetSize` | Allow unsafe replica set sizes | `false` |
| `unsafeFlags.mongosSize` | Allow < 3 config servers or < 2 mongos | `false` |
| `unsafeFlags.terminationGracePeriod` | Allow no termination grace period | `false` |
| `unsafeFlags.backupIfUnhealthy` | Allow backup on unhealthy cluster | `false` |

#### TLS

| Parameter | Description | Default |
|---|---|---|
| `tls.mode` | TLS mode (`allowTLS`, `preferTLS`, `requireTLS`, `disabled`) | `preferTLS` |
| `tls.certValidityDuration` | External certificate validity duration | `2160h` |
| `tls.allowInvalidCertificates` | Skip server certificate validation | `true` |
| `tls.issuerConf.name` | cert-manager issuer name | `""` |
| `tls.issuerConf.kind` | cert-manager issuer kind | `""` |
| `tls.issuerConf.group` | cert-manager issuer group | `""` |

#### Secrets

| Parameter | Description | Default |
|---|---|---|
| `secrets.users` | Secret name for MongoDB system users | `mongodb-rs-secrets` |
| `secrets.ssl` | Secret name for external TLS certificate | `mongodb-rs-ssl` |
| `secrets.sslInternal` | Secret name for internal TLS certificate | `mongodb-rs-ssl-internal` |
| `secrets.encryptionKey` | Secret for data-at-rest encryption key | `""` |
| `secrets.vault` | Secret for HashiCorp Vault integration | `""` |

#### Replica Set (rs0)

| Parameter | Description | Default |
|---|---|---|
| `replsets.rs0.name` | Replica set name | `rs0` |
| `replsets.rs0.size` | Number of replica set pods | `3` |
| `replsets.rs0.resources` | Pod resource requests/limits | `{}` |
| `replsets.rs0.volumeSpec.pvc.storageClassName` | PVC storage class | `rancher-dynamic-local-path` |
| `replsets.rs0.volumeSpec.pvc.resources.requests.storage` | PVC storage size | `3Gi` |
| `replsets.rs0.affinity.antiAffinityTopologyKey` | Pod anti-affinity key | `kubernetes.io/hostname` |
| `replsets.rs0.podDisruptionBudget.maxUnavailable` | Max unavailable pods | `1` |
| `replsets.rs0.expose.enabled` | Expose replica set outside cluster | `false` |
| `replsets.rs0.expose.type` | Service type when exposed | `ClusterIP` |
| `replsets.rs0.nonvoting.enabled` | Add non-voting pods | `false` |
| `replsets.rs0.nonvoting.size` | Number of non-voting pods | `1` |

#### Upgrade Options

| Parameter | Description | Default |
|---|---|---|
| `upgradeOptions.versionServiceEndpoint` | Endpoint for PSMDB version service | `https://check.percona.com` |
| `upgradeOptions.apply` | Image to apply (`disabled`, `recommended`, `latest`, or version) | `disabled` |
| `upgradeOptions.schedule` | Cron schedule for updates | `"0 2 * * *"` |
| `upgradeOptions.setFCV` | Set feature compatibility version on major upgrade | `false` |

#### Multi-cluster

| Parameter | Description | Default |
|---|---|---|
| `multiCluster.enabled` | Enable Multi Cluster Services (MCS) | `false` |
| `multiCluster.DNSSuffix` | DNS suffix for multi-cluster services | `""` |

#### PMM Monitoring

| Parameter | Description | Default |
|---|---|---|
| `pmm.enabled` | Enable Percona Monitoring and Management | `false` |
| `pmm.image.repository` | PMM client image repository | `pmm-client` |
| `pmm.image.tag` | PMM client image tag | `3.6.0` |
| `pmm.serverHost` | PMM server hostname | `monitoring-service` |

#### Backup

| Parameter | Description | Default |
|---|---|---|
| `backup.enabled` | Enable backups | `false` |
| `backup.image.repository` | Backup image repository | `percona-backup-mongodb` |
| `backup.image.tag` | Backup image tag | `2.12.0` |

#### Log Collector

| Parameter | Description | Default |
|---|---|---|
| `logcollector.enabled` | Enable Fluent Bit log collector sidecar | `false` |
| `logcollector.image.repository` | Log collector image | `fluentbit` |
| `logcollector.image.tag` | Log collector tag | `4.0.1-2` |

---

## Installation

### Step 1 — Create namespaces

```bash
kubectl create ns mongodb-operator
kubectl create ns database
```

### Step 2 — Verify StorageClass

```bash
kubectl get storageclass
```

Ensure at least one StorageClass is available.

### Step 3 — Deploy the PSMDB Operator

CRDs are bundled in the chart's `crds/` folder and applied automatically:

```bash
helm upgrade --install mongodb-rs-operator ./mongodb-rs-operator \
  -n mongodb-operator \
  --set replicaCount=1 \
  --set imageRegistry=docker.io/percona \
  --set image.repository=percona-server-mongodb-operator \
  --set image.tag=1.22.0 \
  --set watchNamespace=database
```

### Step 4 — Verify the Operator

```bash
kubectl get pods -n mongodb-operator -l app=mongodb-rs
```

Expected: all pods `1/1 Running`.

### Step 5 — Deploy the MongoDB Cluster

```bash
helm upgrade --install mongodb-rs \
  -f ./mongodb-rs/values.yaml ./mongodb-rs \
  -n database \
  --set imageRegistry=docker.io/percona \
  --set image.repository=percona-server-mongodb \
  --set image.tag=7.0.31
```

### Step 6 — Verify the Cluster

```bash
kubectl get pods -n database -l app=mongodb-rs
```

Expected: replica set pods `3/3 Running`.

### Step 7 — Access credentials

```bash
# User admin
kubectl -n database get secrets mongodb-rs-secrets \
  -o jsonpath="{.data.MONGODB_USER_ADMIN_USER}" | base64 --decode
kubectl -n database get secrets mongodb-rs-secrets \
  -o jsonpath="{.data.MONGODB_USER_ADMIN_PASSWORD}" | base64 --decode

# Cluster admin
kubectl -n database get secrets mongodb-rs-secrets \
  -o jsonpath="{.data.MONGODB_CLUSTER_ADMIN_USER}" | base64 --decode
kubectl -n database get secrets mongodb-rs-secrets \
  -o jsonpath="{.data.MONGODB_CLUSTER_ADMIN_PASSWORD}" | base64 --decode
```

### Step 8 — Connect to MongoDB

```bash
kubectl run -i --rm --tty percona-client \
  --image=percona/percona-server-mongodb:8.0 --restart=Never \
  -- mongosh "mongodb://${ADMIN_USER}:${ADMIN_PASSWORD}@mongodb-rs-rs0.database.svc.cluster.local/admin?replicaSet=rs0&ssl=false"
```

Or connect directly to a pod:

```bash
kubectl exec -it mongodb-rs-rs0-0 -n database -c mongod \
  -- mongosh -u clusterAdmin -p clusterAdmin123456
```

**Service naming convention:** `<cluster-name>-rs0` → `mongodb-rs-rs0.database.svc.cluster.local:27017`

---

## Uninstallation

> Uninstall cluster **first**, then the operator. CRDs are **not** deleted by `helm delete` and must be removed manually if a full cleanup is required.

### 1 — Uninstall the cluster

```bash
helm delete mongodb-rs -n database
```

If the CR gets stuck in `stopping`, remove the finalizer:

```bash
kubectl patch perconaservermongodb mongodb-rs -n database \
  -p '{"metadata":{"finalizers":[]}}' --type=merge
kubectl delete perconaservermongodb mongodb-rs -n database --force --grace-period=0
```

### 2 — Delete PVCs and secrets

```bash
kubectl delete pvc -l app=mongodb-rs -n database
kubectl delete secrets -n database --ignore-not-found \
  $(kubectl get secrets -n database -o name | grep mongodb-rs | cut -d/ -f2)
```

### 3 — Uninstall the Operator

```bash
helm delete mongodb-rs-operator -n mongodb-operator
```

### 4 — Delete CRDs (full cleanup only)

```bash
kubectl delete crd \
  perconaservermongodbs.psmdb.percona.com \
  perconaservermongodbbackups.psmdb.percona.com \
  perconaservermongodbrestores.psmdb.percona.com
```

### 5 — Verify clean state

```bash
helm list -A | grep mongodb-rs
kubectl get pods -n database
kubectl get pods -n mongodb-operator
kubectl get crd | grep psmdb
kubectl get pvc -n database
```

Expected: no output for all commands.
