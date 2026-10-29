# MongoDB Replica Set Deployment

This README provides standalone installation and uninstallation instructions for the Percona Server for MongoDB replica set Helm chart.

# 1. Pre-requisite

## 1.1 System Requirements

- Kubernetes 1.32+
- Helm v3
- A configured StorageClass in your cluster
- kubectl configured with cluster access
- MongoDB Operator must be deployed and running (see mongodb-rs-operator chart)

## 1.2 Default Configuration

The chart can be customized using the following configurable parameters. These are the default values from `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `nameOverride` | Override name portion | `mongodb-rs` |
| `namespaceOverride` | Override namespace | `""` |
| `fullnameOverride` | Override full name | `mongodb-rs` |
| `crVersion` | CR Cluster Manifest version | `1.22.0` |
| `pause` | Stop PSMDB Database safely | `false` |
| `unmanaged` | Start cluster and don't manage it | `false` |
| `unsafeFlags.tls` | Allow configuring cluster without TLS | `false` |
| `unsafeFlags.replsetSize` | Allow unsafe replica set parameters | `false` |
| `unsafeFlags.mongosSize` | Allow unsafe sharded cluster parameters | `false` |
| `unsafeFlags.terminationGracePeriod` | Allow unsafe termination grace period | `false` |
| `unsafeFlags.backupIfUnhealthy` | Allow backup on unhealthy cluster | `false` |
| `enableVolumeExpansion` | Allow PVC resizing | `false` |
| `annotations` | PSMDB custom resource annotations | `{}` |
| `multiCluster.enabled` | Enable Multi Cluster Services | `false` |
| `updateStrategy` | PSMDB Cluster Pods update strategy | `SmartUpdate` |
| `upgradeOptions.versionServiceEndpoint` | PSMDB Versions provider endpoint | `https://check.percona.com` |
| `upgradeOptions.apply` | PSMDB image to apply from version service | `disabled` |
| `upgradeOptions.schedule` | Cron time for update execution | `"0 2 * * *"` |
| `upgradeOptions.setFCV` | Set feature compatibility version | `false` |
| `imageRegistry` | Container registry for images | `docker.io/percona` |
| `imagePullPolicy` | Container image pull policy | `IfNotPresent` |
| `image.repository` | PSMDB Container image repository | `percona-server-mongodb` |
| `image.tag` | PSMDB Container image tag | `7.0.31` |
| `initImage.repository` | Repository for custom init image | `percona-server-mongodb-operator` |
| `initImage.tag` | Tag for custom init image | `1.22.0` |
| `tls.mode` | Control usage of TLS | `preferTLS` |
| `tls.certValidityDuration` | External certificate validity duration | `2160h` |
| `tls.allowInvalidCertificates` | Allow invalid server certificates | `true` |
| `secrets.users` | MongoDB users secret name | `mongodb-rs-secrets` |
| `secrets.ssl` | TLS certificate secret for external comms | `mongodb-rs-ssl` |
| `secrets.sslInternal` | TLS certificate secret for internal comms | `mongodb-rs-ssl-internal` |
| `pmm.enabled` | Enable PMM integration | `false` |
| `pmm.image.repository` | PMM Container image repository | `pmm-client` |
| `pmm.image.tag` | PMM Container image tag | `3.6.0` |
| `pmm.serverHost` | PMM server service hostname | `monitoring-service` |
| `replsets.rs0.name` | ReplicaSet name | `rs0` |
| `replsets.rs0.size` | ReplicaSet size (pod quantity) | `3` |
| `replsets.rs0.affinity.antiAffinityTopologyKey` | ReplicaSet Pod affinity | `kubernetes.io/hostname` |
| `replsets.rs0.labels` | ReplicaSet Pod labels | `{app: mongodb-rs}` |
| `replsets.rs0.podSecurityContext.fsGroup` | Pod filesystem group ID | `1001` |
| `replsets.rs0.containerSecurityContext.runAsNonRoot` | Run as non-root user | `true` |
| `replsets.rs0.containerSecurityContext.runAsUser` | Run as user ID | `1001` |
| `replsets.rs0.containerSecurityContext.runAsGroup` | Run as group ID | `1001` |
| `replsets.rs0.livenessProbe.failureThreshold` | Liveness probe failure threshold | `4` |
| `replsets.rs0.livenessProbe.initialDelaySeconds` | Liveness probe initial delay | `120` |
| `replsets.rs0.livenessProbe.periodSeconds` | Liveness probe period | `30` |
| `replsets.rs0.livenessProbe.timeoutSeconds` | Liveness probe timeout | `15` |
| `replsets.rs0.livenessProbe.startupDelaySeconds` | Liveness probe startup delay | `7200` |
| `replsets.rs0.readinessProbe.failureThreshold` | Readiness probe failure threshold | `8` |
| `replsets.rs0.readinessProbe.initialDelaySeconds` | Readiness probe initial delay | `30` |
| `replsets.rs0.readinessProbe.periodSeconds` | Readiness probe period | `3` |
| `replsets.rs0.readinessProbe.successThreshold` | Readiness probe success threshold | `1` |
| `replsets.rs0.readinessProbe.timeoutSeconds` | Readiness probe timeout | `15` |
| `replsets.rs0.expose.enabled` | Allow external access to replicaSet | `false` |
| `replsets.rs0.expose.type` | Network service access point type | `ClusterIP` |
| `replsets.rs0.podDisruptionBudget.maxUnavailable` | Maximum failed ReplicaSet Pods | `1` |
| `replsets.rs0.resources.limits.cpu` | ReplicaSet Pods CPU limit | `2000m` |
| `replsets.rs0.resources.limits.memory` | ReplicaSet Pods memory limit | `1Gi` |
| `replsets.rs0.resources.requests.cpu` | ReplicaSet Pods CPU request | `1000m` |
| `replsets.rs0.resources.requests.memory` | ReplicaSet Pods memory request | `500Mi` |
| `replsets.rs0.volumeSpec.pvc.storageClassName` | PVC target storageClass | `rancher-dynamic-local-path` |
| `replsets.rs0.volumeSpec.pvc.resources.requests.storage` | PVC storage size | `3Gi` |
| `replsets.rs0.hidden.enabled` | Add MongoDB hidden Pods | `false` |
| `replsets.rs0.hidden.size` | Number of hidden Pods | `2` |
| `replsets.rs0.hidden.podDisruptionBudget.maxUnavailable` | Hidden Pods max unavailable | `1` |
| `replsets.rs0.hidden.resources.limits.cpu` | Hidden Pods CPU limit | `600m` |
| `replsets.rs0.hidden.resources.limits.memory` | Hidden Pods memory limit | `1Gi` |
| `replsets.rs0.hidden.resources.requests.cpu` | Hidden Pods CPU request | `300m` |
| `replsets.rs0.hidden.resources.requests.memory` | Hidden Pods memory request | `500Mi` |
| `replsets.rs0.hidden.volumeSpec.pvc.storageClassName` | Hidden PVC storageClass | `rancher-dynamic-local-path` |
| `replsets.rs0.hidden.volumeSpec.pvc.resources.requests.storage` | Hidden PVC storage size | `3Gi` |
| `replsets.rs0.nonvoting.enabled` | Add MongoDB nonvoting Pods | `false` |
| `replsets.rs0.nonvoting.size` | Number of nonvoting Pods | `3` |
| `replsets.rs0.nonvoting.podDisruptionBudget.maxUnavailable` | Nonvoting Pods max unavailable | `1` |
| `replsets.rs0.nonvoting.resources.limits.cpu` | Nonvoting Pods CPU limit | `600m` |
| `replsets.rs0.nonvoting.resources.limits.memory` | Nonvoting Pods memory limit | `1Gi` |
| `replsets.rs0.nonvoting.resources.requests.cpu` | Nonvoting Pods CPU request | `300m` |
| `replsets.rs0.nonvoting.resources.requests.memory` | Nonvoting Pods memory request | `500Mi` |
| `replsets.rs0.nonvoting.volumeSpec.pvc.storageClassName` | Nonvoting PVC storageClass | `rancher-dynamic-local-path` |
| `replsets.rs0.nonvoting.volumeSpec.pvc.resources.requests.storage` | Nonvoting PVC storage size | `3Gi` |
| `replsets.rs0.arbiter.enabled` | Add MongoDB arbiter | `false` |
| `replsets.rs0.arbiter.size` | Number of arbiter Pods | `1` |
| `replsets.rs0.arbiter.resources.limits.cpu` | Arbiter Pods CPU limit | `600m` |
| `replsets.rs0.arbiter.resources.limits.memory` | Arbiter Pods memory limit | `1Gi` |
| `replsets.rs0.arbiter.resources.requests.cpu` | Arbiter Pods CPU request | `300m` |
| `replsets.rs0.arbiter.resources.requests.memory` | Arbiter Pods memory request | `1Gi` |
| `sharding.enabled` | Enable sharded cluster | `false` |
| `sharding.balancer.enabled` | Enable balancer | `false` |
| `backup.enabled` | Enable backup functionality | `false` |
| `backup.image.repository` | Backup container image repository | `percona-backup-mongodb` |
| `backup.image.tag` | Backup container image tag | `2.12.0` |
| `backup.pitr.enabled` | Enable point-in-time recovery | `false` |
| `backup.pitr.oplogOnly` | Oplog only backup | `false` |
| `backup.pitr.oplogSpanMin` | Oplog span minimum | `10` |
| `backup.pitr.compressionType` | Compression type | `gzip` |
| `backup.pitr.compressionLevel` | Compression level | `6` |
| `systemUsers.MONGODB_BACKUP_USER` | Backup username | `backup` |
| `systemUsers.MONGODB_BACKUP_PASSWORD` | Backup password | `backup123456` |
| `systemUsers.MONGODB_DATABASE_ADMIN_USER` | Database admin username | `databaseAdmin` |
| `systemUsers.MONGODB_DATABASE_ADMIN_PASSWORD` | Database admin password | `databaseAdmin123456` |
| `systemUsers.MONGODB_CLUSTER_ADMIN_USER` | Cluster admin username | `clusterAdmin` |
| `systemUsers.MONGODB_CLUSTER_ADMIN_PASSWORD` | Cluster admin password | `clusterAdmin123456` |
| `systemUsers.MONGODB_CLUSTER_MONITOR_USER` | Cluster monitor username | `clusterMonitor` |
| `systemUsers.MONGODB_CLUSTER_MONITOR_PASSWORD` | Cluster monitor password | `clusterMonitor123456` |
| `systemUsers.MONGODB_USER_ADMIN_USER` | User admin username | `userAdmin` |
| `systemUsers.MONGODB_USER_ADMIN_PASSWORD` | User admin password | `userAdmin123456` |
| `logcollector.enabled` | Enable log collection | `false` |
| `logcollector.image.repository` | Log collector image repository | `fluentbit` |
| `logcollector.image.tag` | Log collector image tag | `4.0.1-2` |
| `logcollector.resources.requests.memory` | Log collector memory request | `100M` |
| `logcollector.resources.requests.cpu` | Log collector CPU request | `200m` |

# 2. Installation

**Note:** The configuration values shown in the installation steps are the defaults from `values.yaml`. These can be customized to your specific requirements by using `--set` parameters or by providing a custom values file.

## 2.1 Create Namespaces

```bash
kubectl create ns database
```

## 2.2 Verify StorageClass

```bash
kubectl get storageclass
```

Ensure at least one StorageClass is available and marked as default.

## 2.3 Verify MongoDB Operator is Running

**Pre-deployment Check:** Verify that the MongoDB Operator is deployed and running before proceeding:

```bash
# Check operator pod status
kubectl get pods -n mongodb-operator -l app=mongodb-rs

# Verify CRDs are established
kubectl get crd perconaservermongodbs.psmdb.percona.com
kubectl get crd perconaservermongodbbackups.psmdb.percona.com
kubectl get crd perconaservermongodbrestores.psmdb.percona.com

# Check operator logs for any errors
kubectl logs -n mongodb-operator -l app=mongodb-rs --tail=20
```

Expected output should show:
- 1 operator pod in `Running` state
- All 3 CRDs in `Established` status
- No error messages in operator logs

⚠️ **If the operator is not running, deploy it first using the mongodb-rs-operator chart before proceeding.**

## 2.4 Deploy MongoDB Replica Set

```bash
helm upgrade --install mongodb-rs -f values.yaml . -n database \
  --set crVersion=1.22.0 \
  --set imageRegistry=docker.io/percona \
  --set multiCluster.enabled=false \
  --set image.repository=percona-server-mongodb \
  --set image.tag=7.0.31 \
  --set initImage.repository=percona-server-mongodb-operator \
  --set initImage.tag=1.22.0 \
  --set tls.mode=preferTLS \
  --set tls.certValidityDuration=2160h \
  --set tls.allowInvalidCertificates=true \
  --set replsets.rs0.name=rs0 \
  --set replsets.rs0.size=3 \
  --set replsets.rs0.resources.limits.cpu=2000m \
  --set replsets.rs0.resources.limits.memory=1Gi \
  --set replsets.rs0.resources.requests.cpu=1000m \
  --set replsets.rs0.resources.requests.memory=500Mi \
  --set replsets.rs0.volumeSpec.pvc.storageClassName=rancher-dynamic-local-path \
  --set replsets.rs0.volumeSpec.pvc.resources.requests.storage=3Gi \
  --set replsets.rs0.hidden.enabled=false \
  --set replsets.rs0.nonvoting.enabled=false \
  --set replsets.rs0.arbiter.enabled=false \
  --set systemUsers.MONGODB_DATABASE_ADMIN_USER=databaseAdmin \
  --set systemUsers.MONGODB_DATABASE_ADMIN_PASSWORD=databaseAdmin123456 \
  --set systemUsers.MONGODB_CLUSTER_ADMIN_USER=clusterAdmin \
  --set systemUsers.MONGODB_CLUSTER_ADMIN_PASSWORD=clusterAdmin123456 \
  --set systemUsers.MONGODB_CLUSTER_MONITOR_USER=clusterMonitor \
  --set systemUsers.MONGODB_CLUSTER_MONITOR_PASSWORD=clusterMonitor123456 \
  --set systemUsers.MONGODB_USER_ADMIN_USER=userAdmin \
  --set systemUsers.MONGODB_USER_ADMIN_PASSWORD=userAdmin123456
```

## 2.5 Verify MongoDB Replica Set Deployment

```bash
# Check MongoDB cluster pods
kubectl get pods -n database -l app=mongodb-rs

# Check MongoDB services
kubectl get svc -n database -l app=mongodb-rs

# Check PVCs
kubectl get pvc -n database

# Check MongoDB custom resource
kubectl get perconaservermongodbs.psmdb.percona.com -n database

# Check cluster status
kubectl get perconaservermongodbs.psmdb.percona.com mongodb-rs -n database -o jsonpath='{.status.state}'
```

Expected output should show:
- 3 MongoDB replica set pods in `Running` state
- MongoDB services created
- PVCs bound and ready
- Cluster state showing `ready`

## 2.6 Access Credentials

Retrieve MongoDB credentials from the secrets:

```bash
# Get database admin credentials
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_DATABASE_ADMIN_USER}" | base64 --decode
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_DATABASE_ADMIN_PASSWORD}" | base64 --decode

# Get cluster admin credentials
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_CLUSTER_ADMIN_USER}" | base64 --decode
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_CLUSTER_ADMIN_PASSWORD}" | base64 --decode

# Get cluster monitor credentials
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_CLUSTER_MONITOR_USER}" | base64 --decode
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_CLUSTER_MONITOR_PASSWORD}" | base64 --decode

# Get user admin credentials
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_USER_ADMIN_USER}" | base64 --decode
kubectl -n database get secrets mongodb-rs-secrets -o jsonpath="{.data.MONGODB_USER_ADMIN_PASSWORD}" | base64 --decode
```


# 3. Uninstallation

## 3.1 Uninstall MongoDB Replica Set

```bash
helm delete mongodb-rs -n database
```

## 3.2 Delete Remaining Resources

```bash
# Delete any remaining PVCs
kubectl delete pvc -l app=mongodb-rs -n database

# Delete any remaining secrets
kubectl delete secrets -n database --ignore-not-found $(kubectl get secrets -n database -o name | grep mongodb-rs | cut -d/ -f2)

# Delete any remaining services
kubectl delete svc -n database mongodb-rs-rs0 mongodb-rs-rs0-0 mongodb-rs-rs0-1 mongodb-rs-rs0-2

# Delete any remaining custom resources
kubectl delete perconaservermongodbs.psmdb.percona.com mongodb-rs -n database --ignore-not-found
```

## 3.3 Verify Clean State

```bash
# Check no helm releases remain
helm list -A | grep mongodb

# Check no pods remain
kubectl get pods -n database

# Check no PVCs remain
kubectl get pvc -n database

# Check no custom resources remain
kubectl get perconaservermongodbs.psmdb.percona.com -n database

# Check database namespace is clean
kubectl get all -n database
```

Expected: No MongoDB replica set-related resources should remain in the cluster.

**Note:** The MongoDB Operator and CRDs will remain in the cluster unless you separately uninstall the operator using the mongodb-rs-operator chart.



## Related Documentation

- For MongoDB Operator deployment, see: `../mongodb-rs-operator/README.md`
- For common Helm charts documentation, see: `../README.md`
- [Percona Server for MongoDB Documentation](https://docs.percona.com/percona-server-for-mongodb/)
- [Operator GitHub Repository](https://github.com/percona/percona-server-mongodb-operator)
