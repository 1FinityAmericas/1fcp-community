# Apache NiFi Helm Chart

Apache NiFi 2.9.0-debian13 multinode cluster deployment on Kubernetes.

## 1. Pre-requisite

### 1.1 System Requirements
- Kubernetes 1.23+
- Helm 3.0.0+
- Persistent Volume provisioner support
- Ingress Controller (NGINX or Traefik) deployed
- StorageClass configured (default: `rancher-dynamic-local-path`)

### 1.2 Default Configuration

| Parameter | Description | Default |
|----------|-------------|---------|
| **Release Configuration** |||
| `fullnameOverride` | Release name override | `nifi` |
| **Image Configuration** |||
| `image.registry` | Container image registry | `artifactory.fnc.fujitsu.com` |
| `image.repository` | Container image repository | `fcp/1.1/nifi` |
| `image.tag` | Container image tag | `2.9.0-debian13` |
| `image.pullPolicy` | Image pull policy | `IfNotPresent` |
| **Security Context** |||
| `securityContext.runAsUser` | Pod user ID | `1000` |
| `securityContext.runAsGroup` | Pod group ID | `1000` |
| `securityContext.fsGroup` | Filesystem group ID | `1000` |
| `securityContext.seccompProfile.type` | Seccomp profile type | `RuntimeDefault` |
| `containerSecurityContext.runAsUser` | Container user ID | `1000` |
| `containerSecurityContext.runAsGroup` | Container group ID | `1000` |
| `containerSecurityContext.allowPrivilegeEscalation` | Allow privilege escalation | `false` |
| `containerSecurityContext.seccompProfile.type` | Container seccomp profile | `RuntimeDefault` |
| **Service Configuration** |||
| `service.type` | Kubernetes service type | `ClusterIP` |
| `service.port` | Service port | `8443` |
| **Ingress Configuration** |||
| `ingress.enabled` | Enable ingress | `true` |
| `ingress.className` | Ingress class name | `` |
| `ingress.ip` | Ingress IP/domain | `apache-nifi.10.156.198.7.nip.io` |
| `ingress.tls[0].secretName` | TLS secret name | `apache-nifi-secret` |
| `ingress.hosts[0].host` | Ingress host | `apache-nifi.10.156.198.7.nip.io` |
| `ingress.hosts[0].paths[0].path` | Ingress path | `/nifi(.*)` |
| **Ingress Controller** |||
| `ingressController.name` | Ingress controller type (nginx/traefik) | `nginx` |
| `ingressController.localCert` | Use dedicated TLS cert for Traefik | `true` |
| **Traefik Gateway API** |||
| `shared_gateway.name` | Shared gateway name | `traefik-gateway` |
| `shared_gateway.namespace` | Gateway namespace | `kube-system` |
| `shared_gateway.hostname` | Gateway hostname | `` |
| `shared_gateway.pathMatch.type` | Path match type | `RegularExpression` |
| `shared_gateway.pathMatch.value` | Path match value | `^/nifi.*` |
| `shared_gateway.serversTransport.insecureSkipVerify` | Skip backend TLS verification | `true` |
| `shared_gateway.middleware.buffering.maxRequestBodyBytes` | Max request body size | `524288000` |
| `shared_gateway.middleware.buffering.memRequestBodyBytes` | Memory request body size | `2097152` |
| `shared_gateway.middleware.buffering.retryExpression` | Retry expression | `IsNetworkError() && Attempts() < 2` |
| `shared_gateway.sticky.cookieName` | Sticky session cookie name | `NIFI_SESSION` |
| `shared_gateway.sticky.secure` | Secure cookie flag | `true` |
| `shared_gateway.sticky.httpOnly` | HTTP-only cookie flag | `true` |
| `shared_gateway.sticky.sameSite` | Same-site cookie attribute | `none` |
| `shared_gateway.timeouts.request` | Request timeout | `3600s` |
| `shared_gateway.timeouts.backendRequest` | Backend request timeout | `3600s` |
| **Persistence** |||
| `persistence.enabled` | Enable persistent storage | `true` |
| `persistence.accessModes` | PVC access modes | `[ReadWriteOnce]` |
| `persistence.size` | Persistent volume size | `10Gi` |
| `persistence.storageClassName` | Storage class name | `rancher-dynamic-local-path` |
| **Note**: Actual PVC sizes are hardcoded: conf-pvc (100Mi), data (5Gi) | | |
| **Resources** |||
| `replicaCount` | Number of NiFi replicas | `3` |
| `resources.requests.cpu` | CPU request | `2` |
| `resources.requests.memory` | Memory request | `2Gi` |
| `resources.limits.cpu` | CPU limit | `4` |
| `resources.limits.memory` | Memory limit | `4Gi` |
| **RBAC** |||
| `rbac.create` | Create RBAC resources | `true` |
| **JVM Configuration** |||
| `jvm.xms` | Initial JVM heap size | `1g` |
| `jvm.xmx` | Maximum JVM heap size | `2g` |
| `jvm.extra` | Extra JVM arguments | `` |
| **Authentication** |||
| `auth.mode` | Authentication mode | `singleUser` |
| `auth.providerIdentifier` | Provider identifier | `single-user-provider` |
| `auth.username` | Admin username | `admin` |
| `auth.password` | Admin password (min 12 chars) | `0NifiAdmin@123` |
| `auth.hashedPassword` | Optional hashed password | `` |
| **NiFi Properties** |||
| `properties.web.protocol` | Web protocol (http/https) | `https` |
| `properties.web.host` | Web host | `0.0.0.0` |
| `properties.web.port` | Web port | `8443` |
| `properties.cluster.isNode` | Enable cluster node mode | `true` |
| `properties.cluster.nodeReadTimeout` | Node read timeout | `5 min` |
| `properties.cluster.nodeConnectionTimeout` | Node connection timeout | `30 sec` |
| `properties.cluster.requestReplicationClaimTimeout` | Replication claim timeout | `5 min` |
| `properties.s2s.enabled` | Enable Site-to-Site protocol | `false` |
| `properties.s2s.port` | Site-to-Site port | `10000` |
| **Probes** |||
| `probes.liveness.initialDelaySeconds` | Liveness probe initial delay | `120` |
| `probes.liveness.periodSeconds` | Liveness probe period | `15` |
| `probes.liveness.timeoutSeconds` | Liveness probe timeout | `5` |
| `probes.liveness.failureThreshold` | Liveness probe failure threshold | `8` |
| `probes.readiness.initialDelaySeconds` | Readiness probe initial delay | `90` |
| `probes.readiness.periodSeconds` | Readiness probe period | `10` |
| `probes.readiness.timeoutSeconds` | Readiness probe timeout | `5` |
| `probes.readiness.failureThreshold` | Readiness probe failure threshold | `12` |
| **Web Proxy** |||
| `nifiWebProxyHost` | NiFi web proxy host | `apache-nifi.10.156.198.7.nip.io` |
| **Custom Configuration Mount** |||
| `customConf.enabled` | Enable custom config mount | `false` |
| `customConf.storageSize` | Custom config storage size | `100Mi` |
| `customConf.hostPath` | Custom config host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/conf` |
| **Custom Library Mount** |||
| `customLib.enabled` | Enable custom library mount | `false` |
| `customLib.storageSize` | Custom library storage size | `5Gi` |
| `customLib.hostPath` | Custom library host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/lib` |
| **Custom Extensions Mount** |||
| `customExtensions.enabled` | Enable custom extensions mount | `false` |
| `customExtensions.storageSize` | Custom extensions storage size | `5Gi` |
| `customExtensions.hostPath` | Custom extensions host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/extensions` |
| **DPM Scripts Mount** |||
| `dpmScripts.enabled` | Enable DPM scripts mount | `false` |
| `dpmScripts.storageSize` | DPM scripts storage size | `1Gi` |
| `dpmScripts.hostPath` | DPM scripts host path | `/var/lib/docker/dynamic-local-path-mounts/nifi/dpm-scripts` |
| **Scheduling** |||
| `podAnnotations` | Pod annotations | `{}` |
| `nodeSelector` | Node selector | `{}` |
| `tolerations` | Tolerations | `[]` |
| `affinity` | Affinity rules | `{}` |

## 2. Installation

### 2.1 Create Namespaces
```bash
kubectl create namespace <nifi-namespace>
```

### 2.2 Verify StorageClass
```bash
kubectl get storageclass
```
Ensure `rancher-dynamic-local-path` or your configured StorageClass exists.

### 2.3 Deploy Apache NiFi
```bash
helm upgrade --install nifi -f ./apps/helm-charts/values.yaml ./apps/helm-charts -n <nifi-namespace>
```

### 2.4 Verify Apache NiFi Deployment
```bash
kubectl get pods -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl get pvc -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl get svc -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
```

Expected state: All pods in `Running` status with `1/1` Ready.

### 2.5 Access Credentials
```bash
kubectl -n <nifi-namespace> get secret apache-nifi-secret -o jsonpath="{.data.username}" | base64 --decode
kubectl -n <nifi-namespace> get secret apache-nifi-secret -o jsonpath="{.data.password}" | base64 --decode
```

Default credentials (if secret not customized):
- Username: `admin`
- Password: `0NifiAdmin@123`

### 2.6 Connect to Apache NiFi
Access the NiFi UI via the ingress URL:
- **NGINX**: `https://apache-nifi.<IP>.nip.io/nifi`
- **Traefik**: `https://apache-nifi.<IP>.nip.io/nifi`

Login with the credentials retrieved in step 2.5.

## 3. Uninstallation

### 3.1 Uninstall Apache NiFi
```bash
helm delete nifi -n <nifi-namespace>
```

### 3.2 Delete Remaining Resources
```bash
# Delete PVCs
kubectl delete pvc -n <nifi-namespace> -l app.kubernetes.io/instance=nifi

# Delete Secrets
kubectl delete secret -n <nifi-namespace> apache-nifi-secret

# Delete Services
kubectl delete svc -n <nifi-namespace> -l app.kubernetes.io/instance=nifi

# Delete ConfigMaps
kubectl delete configmap -n <nifi-namespace> -l app.kubernetes.io/instance=nifi

# Delete Ingress
kubectl delete ingress -n <nifi-namespace> -l app.kubernetes.io/instance=nifi

# Delete RBAC resources
kubectl delete role -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete rolebinding -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
kubectl delete serviceaccount -n <nifi-namespace> -l app.kubernetes.io/instance=nifi
```

### 3.3 Delete Traefik resources (if using Traefik ingress controller)
```bash
kubectl delete serverstransport -n <nifi-namespace> nifi-transport
kubectl delete middleware -n <nifi-namespace> nifi-buffering
kubectl delete traefikservice -n <nifi-namespace> nifi-sticky
kubectl delete httproute -n <nifi-namespace> nifi-https
# Delete Gateway only if using dedicated gateway (localCert: true)
kubectl delete gateway -n <nifi-namespace> nifi-gateway
```

### 3.4 Cleanup Custom hostPath Directories (if enabled)
If custom volumes (customConf, customLib, customExtensions, dpmScripts) were enabled:
```bash
sudo rm -rf /var/lib/docker/dynamic-local-path-mounts/nifi
```
Run this on all worker nodes where hostPath directories were created.

### 3.5 Verify Clean State
```bash
helm list -n <nifi-namespace>
kubectl get pods -n <nifi-namespace>
kubectl get pvc -n <nifi-namespace>
kubectl get svc -n <nifi-namespace>
kubectl get secret -n <nifi-namespace>
kubectl get configmap -n <nifi-namespace>
kubectl get ingress -n <nifi-namespace>
kubectl get all -n <nifi-namespace>
```
Ensure no NiFi-related resources remain.

## Ingress Controller Selection

This chart supports **NGINX** (default) and **Traefik** ingress controllers.

### NGINX Ingress Controller (Default)
Uses standard Kubernetes Ingress resources with NGINX-specific annotations for session affinity, timeouts, and SSL configuration.

**Configuration:**
```yaml
ingressController:
  name: nginx
```

### Traefik Ingress Controller
Uses Gateway API (Gateway, HTTPRoute) and Traefik CRDs (ServersTransport, Middleware, TraefikService) for advanced routing capabilities.

**Configuration:**
```yaml
ingressController:
  name: traefik
  localCert: true
```

**Traefik Gateway Options:**

1. **Dedicated Gateway** (`localCert: true`):
   - Creates a dedicated Gateway with its own TLS certificate
   - Recommended for production deployments requiring separate certificates

2. **Shared Gateway** (`localCert: false`):
   - Uses a shared Traefik gateway with default TLS certificate
   - Specify shared gateway details in `shared_gateway.name` and `shared_gateway.namespace`

## Custom Volumes (hostPath) Prerequisites

If enabling customConf, customLib, customExtensions, or dpmScripts:

1. **Create directories on ALL worker nodes:**
   ```bash
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/conf
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/lib
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/extensions
   sudo mkdir -p /var/lib/docker/dynamic-local-path-mounts/nifi/dpm-scripts
   ```

2. **Copy your custom files to ALL worker nodes:**
   - Custom NiFi configs → `/var/lib/docker/dynamic-local-path-mounts/nifi/conf/`
   - Custom JAR libraries → `/var/lib/docker/dynamic-local-path-mounts/nifi/lib/`
   - Custom NAR extensions → `/var/lib/docker/dynamic-local-path-mounts/nifi/extensions/`
   - DPM scripts → `/var/lib/docker/dynamic-local-path-mounts/nifi/dpm-scripts/`

3. **Ensure identical data exists at the same paths on all worker nodes**

4. **Enable the required options in values.yaml:**
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
