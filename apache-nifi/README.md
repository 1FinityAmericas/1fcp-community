# Apache NiFi

Ansible-based deployment of Apache NiFi on Kubernetes (RKE2). Supports single-user authentication, TLS ingress, HA clustering, and custom package injection via hostPath volumes.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [TLS Certificate Configuration](#tls-certificate-configuration)
- [Custom Packages (hostPath Volumes)](#custom-packages-hostpath-volumes)
- [Deployment](#deployment)
- [Cleanup](#cleanup)
- [Debug Mode](#debug-mode)

---

## Prerequisites


### 1. Configure `dep_hosts`

Edit the `dep_hosts` inventory file and set the following:

**Ingress hostname:**

```ini
ingress_host: apache-nifi.<masterip>.nip.io
```

Replace `<masterip>` with the actual master IP or kubeVIP address.

**External Docker Registry DNS:**

```ini
ext_doc_reg_dns='<your-registry-dns>'
```

**Kubernetes provider:**

```ini
# Options: 'aks', 'eks', 'gke' (cloud), or 'rke2' (on-prem, default)
k8s_provider='rke2'
```

---

## Configuration

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying:

```yaml
apache_nifi:
  app_name: apache_nifi
  path: apache-nifi
  image:
    repository: apache/nifi
    tag: 2.9.0
    enabled: true
  replicaCount: 3
  namespace: nifi
  ingress:
    enabled: true
  auth:
    mode: singleUser
    username: admin
    password: 0NifiAdmin@123   # Minimum 12 characters
  resources:
    requests:
      memory: "2Gi"
      cpu: 2
    limits:
      memory: "4Gi"
      cpu: 4
  jvm:
    xms: 1g
    xmx: 2g
    extra: ""
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
    seccompProfile:
      type: RuntimeDefault
  persistence:
    enabled: true
    accessModes:
      - ReadWriteOnce
    size: 10Gi
    storageClassName: "rancher-dynamic-local-path"
  customConf:
    enabled: false
    storageSize: "100Mi"
    hostPath: /var/lib/docker/dynamic-local-path-mounts/nifi/conf
  customLib:
    enabled: false
    storageSize: "5Gi"
    hostPath: /var/lib/docker/dynamic-local-path-mounts/nifi/lib
  customExtensions:
    enabled: false
    storageSize: "5Gi"
    hostPath: /var/lib/docker/dynamic-local-path-mounts/nifi/extensions
  dpmScripts:
    enabled: false
    storageSize: "1Gi"
    hostPath: /var/lib/docker/dynamic-local-path-mounts/nifi/dpm-scripts
  properties:
    cluster:
      isNode: true
      nodeReadTimeout: "5 min"
      nodeConnectionTimeout: "30 sec"
      requestReplicationClaimTimeout: "5 min"

```

**Cluster properties** (`properties.cluster`) are passed as environment variables to NiFi pods and written to `nifi.properties` at startup via `start.sh`.

---

## TLS Certificate Configuration

When `ingress.enabled: true`, the Helm chart creates a TLS secret for HTTPS ingress.

**Option A – Auto-generated (default):** If no certificate files are provided, the Helm chart auto-generates a self-signed certificate using `genSignedCert`.

**Option B – Custom certificates:** Place your `.crt` and `.key` files in:

```
apps/helm-charts/certs/tls.crt
apps/helm-charts/certs/tls.key
```

**Generating certificates manually with OpenSSL:**

Create `openssl.cnf`:

```ini
[ req ]
default_bits       = 2048
distinguished_name = req_distinguished_name
req_extensions     = req_ext
prompt             = no

[ req_distinguished_name ]
CN = <ingress_host>

[ req_ext ]
keyUsage            = critical, digitalSignature, keyEncipherment
extendedKeyUsage    = serverAuth, clientAuth
basicConstraints    = critical, CA:FALSE
subjectAltName      = @alt_names

[ alt_names ]
DNS.1  = localhost
DNS.2  = 127.0.0.1
DNS.3  = <ingress_host>

# Per-pod SANs
DNS.4  = nifi-0.<headlessService>.<namespace>.svc.<clusterDomain>
DNS.5  = nifi-1.<headlessService>.<namespace>.svc.<clusterDomain>
DNS.6  = nifi-2.<headlessService>.<namespace>.svc.<clusterDomain>

# Wildcard + service SANs
DNS.7  = *.<headlessService>.<namespace>.svc.<clusterDomain>
DNS.8  = *.<namespace>.svc.<clusterDomain>
DNS.9  = <headlessService>.<namespace>.svc.<clusterDomain>
DNS.10 = nifi.<namespace>.svc.<clusterDomain>
```

Generate key and certificate:

```bash
openssl genrsa -out tls.key 2048
openssl req -x509 -new -nodes -key tls.key -sha256 -days 3650 \
  -out tls.crt -config openssl.cnf -extensions req_ext
```

---

## Custom Packages (hostPath Volumes)

1. Copy custom tarballs into `apps/custom_pkg/`:

   | Content            | Directory                    |
   |--------------------|------------------------------|
   | NiFi configs       | `apps/custom_pkg/conf/`      |
   | JAR libraries      | `apps/custom_pkg/lib/`       |
   | DPM scripts        | `apps/custom_pkg/dpm-scripts/` |
   | NiFi extensions    | `apps/custom_pkg/extensions/` |

2. The Ansible playbook automatically copies and extracts these to the hostPath directories on all worker nodes.
3. Set the corresponding `enabled: true` flags in `app_config.yaml` (`customConf`, `customLib`, `customExtensions`, `dpmScripts`).

---

## Deployment

```bash
touch logs/nifi.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/nifi.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-nifi -v
```

---

## Cleanup

```bash
touch logs/nifi_cleanup.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/nifi_cleanup.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-nifi -v
```

---

## Push Images

```bash
touch logs/nifi_push_images.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/nifi_push_images.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t push-images -v
```

---

## Debug Mode

To enable debug logging, uncomment the following in `apps/helm-charts/templates/statefulset.yaml`:

```yaml
env:
  - name: NIFI_LOG_LEVEL
    value: "DEBUG"
  # Enable Java remote debugging (optional)
  # - name: JAVA_DEBUG
  #   value: "true"
  # - name: JAVA_DEBUG_PORT
  #   value: "8000"
```

---

## License

[Apache License 2.0](LICENSE)
