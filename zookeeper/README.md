# Zookeeper

Ansible-based deployment of Apache ZooKeeper on Kubernetes (RKE2) using Helm. ZooKeeper `7.9.2` is deployed as a StatefulSet and is a required dependency for Kafka.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Cleanup](#cleanup)

---

## Prerequisites

### 1. Configure `dep_hosts`

Open and edit the inventory file:

```bash
vi dep_hosts
```

Update the IP addresses and hostnames for your master and worker nodes, along with SSH credentials.

---

## Configuration

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying. Key parameters:

| Parameter          | Description                            | Default                      |
|--------------------|----------------------------------------|------------------------------|
| `image.tag`        | ZooKeeper image version                | `7.9.2`                      |
| `namespace`        | Kubernetes namespace                   | Defined in config            |
| `replicaCount`     | Number of ZooKeeper replicas (odd)     | `3`                          |
| `storageClassName` | Storage class for persistent volumes   | `rancher-dynamic-local-path` |

---

## Deployment

```bash
touch logs/deploy-zookeeper.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/deploy-zookeeper.log
ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-zookeeper -v
```

---

## Cleanup

```bash
touch logs/cleanup-zookeeper.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/cleanup-zookeeper.log
ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-zookeeper -v
```

---


## License

[Apache License 2.0](LICENSE)
