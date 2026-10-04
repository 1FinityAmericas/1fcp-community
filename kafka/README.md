# Kafka

Ansible-based deployment of Apache Kafka on Kubernetes (RKE2) using Helm. Kafka `7.9.2` is deployed as a StatefulSet and connects to a pre-installed ZooKeeper cluster.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Cleanup](#cleanup)
- [Push Images](#push-images)

---

## Prerequisites

### 1. ZooKeeper must be running

Kafka requires ZooKeeper to be deployed and healthy before installation. Verify ZooKeeper is ready:

```bash
kubectl -n <namespace> get all | grep zookeeper
```

Expected output:

```
pod/zookeeper-0               1/1     Running    0          18m
pod/zookeeper-1               1/1     Running    0          18m
pod/zookeeper-2               1/1     Running    0          18m
service/zookeeper             ClusterIP   10.43.135.215   <none>        2181/TCP            18m
service/zookeeper-headless    ClusterIP   None            <none>        2888/TCP,3888/TCP   18m
statefulset.apps/zookeeper    3/3     18m
```

> See the [zookeeper](../zookeeper) sub-project to deploy ZooKeeper first.

### 2. Download Image Tarballs

```bash
chmod +x scripts/get_dependencies.sh
bash scripts/get_dependencies.sh <fcp-version>
```

---

## Configuration

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying. Key parameters:

| Parameter          | Description                            | Default                      |
|--------------------|----------------------------------------|------------------------------|
| `image.tag`        | Kafka image version                    | `7.9.2`                      |
| `namespace`        | Kubernetes namespace                   | Defined in config            |
| `replicaCount`     | Number of Kafka brokers                | Defined in config            |
| `storageClassName` | Storage class for persistent volumes   | `rancher-dynamic-local-path` |

Also update the `dep_hosts` inventory file with the correct node IPs, hostnames, and SSH credentials.

---

## Deployment

```bash
touch logs/ansible_kafka_deploy.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_kafka_deploy.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-kafka -v
```

---

## Cleanup

```bash
touch logs/ansible_kafka_cleanup.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_kafka_cleanup.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-kafka -v
```

---

## Push Images

Push images to the local registry at any time:

```bash
touch logs/ansible_kafka_push_images.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_kafka_push_images.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t push-images -v
```

---

## License

[Apache License 2.0](LICENSE)
