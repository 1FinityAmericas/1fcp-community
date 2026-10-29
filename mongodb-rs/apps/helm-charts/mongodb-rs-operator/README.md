# MongoDB Operator Deployment

This README provides standalone installation and uninstallation instructions for the Percona Operator for MongoDB Helm chart.

# 1. Pre-requisite

## 1.1 System Requirements

- Kubernetes 1.32+
- Helm v3
- A configured StorageClass in your cluster
- kubectl configured with cluster access

## 1.2 Default Configuration

The chart can be customized using the following configurable parameters. These are the default values from `values.yaml`:

| Parameter | Description | Default |
|-----------|-------------|---------|
| `replicaCount` | Number of operator pods to deploy | `1` |
| `imageRegistry` | Container registry for images | `docker.io/percona` |
| `image.repository` | Operator container image name | `percona-server-mongodb-operator` |
| `image.tag` | Operator container image tag | `1.22.0` |
| `image.pullPolicy` | Container image pull policy | `IfNotPresent` |
| `disableTelemetry` | Disable telemetry collection | `true` |
| `watchNamespace` | Namespace to watch for MongoDB resources | `database` |
| `rbac.create` | Create RBAC resources | `true` |
| `serviceAccount.create` | Create service account | `true` |
| `serviceAccount.annotations` | Service account annotations | `{}` |
| `annotations` | Operator deployment annotations | `{}` |
| `labels` | Operator deployment labels | `{}` |
| `podAnnotations` | Operator pod annotations | `{}` |
| `podLabels` | Operator pod labels | `{app: mongodb-rs}` |
| `podSecurityContext.runAsNonRoot` | Run as non-root user | `true` |
| `podSecurityContext.runAsUser` | Run as user ID | `1001` |
| `podSecurityContext.runAsGroup` | Run as group ID | `1001` |
| `podSecurityContext.fsGroup` | Filesystem group ID | `1001` |
| `podSecurityContext.fsGroupChangePolicy` | Filesystem group change policy | `OnRootMismatch` |
| `securityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `securityContext.capabilities.drop` | Capabilities to drop | `[ALL]` |
| `securityContext.seccompProfile.type` | Seccomp profile type | `RuntimeDefault` |
| `imagePullSecrets` | Image pull secrets | `[]` |
| `nameOverride` | Override name portion | `mongodb-rs` |
| `namespaceOverride` | Override namespace | `""` |
| `fullnameOverride` | Override full name | `mongodb-rs-operator` |
| `env.resyncPeriod` | Operator resync period | `5s` |
| `resources` | Resource requests and limits | `{}` |
| `nodeSelector` | Node selector for pods | `{}` |
| `tolerations` | Tolerations for pods | `[]` |
| `affinity` | Affinity rules for pods | `{}` |
| `logStructured` | Enable structured logging | `false` |
| `logLevel` | Operator logging level | `INFO` |
| `maxConcurrentReconciles` | Maximum concurrent reconciles | `1` |

# 2. Installation

**Note:** The configuration values shown in the installation steps are the defaults from `values.yaml`. These can be customized to your specific requirements by using `--set` parameters or by providing a custom values file.

## 2.1 Create Namespaces

```bash
kubectl create ns mongodb-operator
kubectl create ns database
```

## 2.2 Verify StorageClass

```bash
kubectl get storageclass
```

Ensure at least one StorageClass is available and marked as default.

## 2.3 Deploy MongoDB Operator

Install the CRDs first, then deploy the operator:

```bash
# Install CRDs
kubectl create -f ./crds/perconaservermongodbs.yaml
kubectl create -f ./crds/perconaservermongodbbackups.yaml
kubectl create -f ./crds/perconaservermongodbrestores.yaml

# Deploy operator
helm upgrade --install mongodb-rs-operator . -n mongodb-operator \
  --set replicaCount=1 \
  --set imageRegistry=docker.io/percona \
  --set image.repository=percona-server-mongodb-operator \
  --set image.tag=1.22.0 \
  --set watchNamespace=database \
  --set env.resyncPeriod=5s
```

## 2.4 Verify MongoDB Operator Deployment

```bash
# Check operator pod status
kubectl get pods -n mongodb-operator -l app=mongodb-rs

# Verify CRDs are established
kubectl get crd perconaservermongodbs.psmdb.percona.com
kubectl get crd perconaservermongodbbackups.psmdb.percona.com
kubectl get crd perconaservermongodbrestores.psmdb.percona.com

# Check operator logs
kubectl logs -n mongodb-operator -l app=mongodb-rs
```

Expected output should show:
- 1 operator pod in `Running` state
- All 3 CRDs in `Established` status
- No error messages in operator logs

## 2.5 Operator Deployment Complete

The MongoDB Operator is now deployed and ready to manage MongoDB clusters. You can now deploy MongoDB replica sets using the separate mongodb-rs chart.

**Next Steps:**
- Deploy MongoDB replica sets using the mongodb-rs chart
- Refer to `../mongodb-rs/README.md` for MongoDB cluster deployment instructions

# 3. Uninstallation

## 3.1 Uninstall MongoDB Operator

```bash
helm delete mongodb-rs-operator -n mongodb-operator
```

## 3.2 Delete CRDs

```bash
kubectl delete crd perconaservermongodbs.psmdb.percona.com
kubectl delete crd perconaservermongodbbackups.psmdb.percona.com
kubectl delete crd perconaservermongodbrestores.psmdb.percona.com
```

## 3.3 Verify Clean State

```bash
# Check no helm releases remain
helm list -A | grep mongodb

# Check no pods remain
kubectl get pods -n mongodb-operator

# Check no CRDs remain
kubectl get crd | grep percona

# Check operator namespace is clean
kubectl get all -n mongodb-operator
```

Expected: No MongoDB operator-related resources should remain in the cluster.

#Related Documentation

- For MongoDB replica set deployment, see: `../../../README.md`
- For common Helm charts documentation, see: `../README.md`
- [Percona Operator Documentation](https://docs.percona.com/percona-operator-for-mongodb/)
- [Operator GitHub Repository](https://github.com/percona/percona-server-mongodb-operator)
