# MongoDB Replica Set

Ansible-based deployment of a MongoDB Replica Set on Kubernetes (RKE2) using the [Percona Server for MongoDB Operator](https://www.percona.com/doc/kubernetes-operator-for-psmongodb/index.html). Supports TLS, custom certificates, HA replica sets, and optional PMM monitoring and backup.

## Table of Contents

- [TLS Certificate Configuration](#tls-certificate-configuration)
- [Configuration](#configuration)
- [Service Naming](#service-naming)
- [Deployment](#deployment)
- [Cleanup](#cleanup)

---


## TLS Certificate Configuration

By default, the Percona MongoDB Operator auto-generates TLS certificates when TLS is enabled. To use organization-managed custom certificates, follow the steps below.

### Step 1 – Define certificate variables

```bash
export CLUSTER_NAME=mongodb-rs
export NAMESPACE=database
export VALID_DAYS=3650
export CA_ORG="My Root CA"
export SERVER_ORG="My MongoDB"
```

### Step 2 – Generate Root CA

```bash
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days ${VALID_DAYS} \
  -out ca.crt -subj "/O=${CA_ORG}"
```

Verify: `openssl x509 -in ca.crt -text -noout`

### Step 3 – Generate dynamic TLS configuration

Create `tls.cnf`:

```ini
[req]
default_bits=4096
prompt=no
default_md=sha256
distinguished_name=dn
req_extensions=req_ext

[dn]
O=$ENV::SERVER_ORG

[req_ext]
keyUsage=critical,digitalSignature,keyEncipherment
extendedKeyUsage=serverAuth,clientAuth
basicConstraints=critical,CA:FALSE
subjectAltName=@alt_names

[alt_names]
DNS.1=localhost
IP.1=127.0.0.1

# rs0
DNS.2=$ENV::CLUSTER_NAME-rs0
DNS.3=$ENV::CLUSTER_NAME-rs0.$ENV::NAMESPACE
DNS.4=$ENV::CLUSTER_NAME-rs0.$ENV::NAMESPACE.svc.cluster.local
DNS.5=*.$ENV::CLUSTER_NAME-rs0
DNS.6=*.$ENV::CLUSTER_NAME-rs0.$ENV::NAMESPACE
DNS.7=*.$ENV::CLUSTER_NAME-rs0.$ENV::NAMESPACE.svc.cluster.local
DNS.8=$ENV::CLUSTER_NAME-rs0.$ENV::NAMESPACE.svc.clusterset.local
DNS.9=*.$ENV::CLUSTER_NAME-rs0.$ENV::NAMESPACE.svc.clusterset.local
DNS.10=*.$ENV::NAMESPACE.svc.clusterset.local

# mongos
DNS.11=$ENV::CLUSTER_NAME-mongos
DNS.12=$ENV::CLUSTER_NAME-mongos.$ENV::NAMESPACE
DNS.13=$ENV::CLUSTER_NAME-mongos.$ENV::NAMESPACE.svc.cluster.local

# cfg
DNS.19=$ENV::CLUSTER_NAME-cfg
DNS.20=$ENV::CLUSTER_NAME-cfg.$ENV::NAMESPACE
DNS.21=$ENV::CLUSTER_NAME-cfg.$ENV::NAMESPACE.svc.cluster.local
```

### Step 4 – Generate server TLS certificate

```bash
openssl genrsa -out tls.key 4096
openssl req -new -key tls.key -out tls.csr -config tls.cnf
openssl x509 -req -in tls.csr -CA ca.crt -CAkey ca.key -CAcreateserial \
  -out tls.crt -days ${VALID_DAYS} -sha256 -extfile tls.cnf -extensions req_ext
```

Verify: `openssl x509 -in tls.crt -text -noout | grep -A2 "Subject Alternative"`

### Step 5 – Create Kubernetes TLS secrets

Percona MongoDB requires two TLS secrets: `ssl` and `ssl-internal`.

```bash
# External TLS secret
kubectl create secret tls psmdb-db-ssl \
  -n database --cert=tls.crt --key=tls.key
kubectl patch secret psmdb-db-ssl -n database \
  --patch="{\"data\":{\"ca.crt\":\"$(base64 -w 0 ca.crt)\"}}"

# Internal TLS secret
kubectl create secret tls psmdb-db-ssl-internal \
  -n database --cert=tls.crt --key=tls.key
kubectl patch secret psmdb-db-ssl-internal -n database \
  --patch="{\"data\":{\"ca.crt\":\"$(base64 -w 0 ca.crt)\"}}"
```

Expected secrets:

```bash
kubectl get secret -n database | grep mongodb-rs
# mongodb-rs-ssl
# mongodb-rs-ssl-internal
```

### Step 6 – Reference secrets in configuration

```yaml
tls:
  mode: preferTLS
  certValidityDuration: 2160h
  allowInvalidCertificates: true

secrets:
  ssl: mongodb-rs-ssl
  sslInternal: mongodb-rs-ssl-internal
```

---

## Configuration

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying:

```yaml
mongodb_rs:
  app_name: mongodb-rs
  namespace: database

  psmdb_operator:
    namespace: mongodb-operator
    replicaCount: 1
    image:
      repository: percona-server-mongodb-operator
      tag: 1.22.0
      enabled: true
    watchNamespaces: database
    env:
      resyncPeriod: 5s

  psmdb_cluster:
    crVersion: 1.22.0
    image:
      repository: percona-server-mongodb
      tag: 7.0.31
      enabled: true
    tls:
      mode: preferTLS
      certValidityDuration: 2160h
      allowInvalidCertificates: true
    replsets:
      rs0:
        name: rs0
        size: 3
        resources:
          limits:
            cpu: "2000m"
            memory: "4Gi"
          requests:
            cpu: "1000m"
            memory: "4Gi"
        volumeSpec:
          pvc:
            storageClassName: rancher-dynamic-local-path
            resources:
              requests:
                storage: 3Gi

  pmm:
    enabled: false
  backup:
    enabled: false
  logcollector:
    enabled: false

systemUsers:
  MONGODB_DATABASE_ADMIN_USER: databaseAdmin
  MONGODB_DATABASE_ADMIN_PASSWORD: databaseAdmin123456
  MONGODB_CLUSTER_ADMIN_USER: clusterAdmin
  MONGODB_CLUSTER_ADMIN_PASSWORD: clusterAdmin123456
  MONGODB_USER_ADMIN_USER: userAdmin
  MONGODB_USER_ADMIN_PASSWORD: userAdmin123456

external_registry:
  username: automation
  password: automation
```

---

## Service Naming

Applications connecting to MongoDB must use Percona's default service naming convention:

| Field              | Value                                                                          |
|--------------------|--------------------------------------------------------------------------------|
| **Service name**   | `mongodb-rs-rs0` (format: `<cluster-name>-rs0`)                               |
| **Namespace**      | `database`                                                                     |
| **Connection string** | `mongodb://user:password@mongodb-rs-rs0.database.svc.cluster.local:27017/?replicaSet=rs0` |

---

## Deployment

```bash
touch logs/ansible_mongodb_rs.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_mongodb_rs.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-mongodb-rs -v
```

---

## Cleanup

```bash
touch logs/ansible_mongodb_rs_cleanup.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_mongodb_rs_cleanup.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-mongodb-rs -v
```

---


## License

[Apache License 2.0](LICENSE)
