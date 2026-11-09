# Cassandra

Ansible-based deployment of Apache Cassandra on Kubernetes (RKE2) using Helm. Supports non-root container execution, DNS policy override via hostNetwork, and image lifecycle management.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Cleanup](#cleanup)

---

## Prerequisites

### Install prerequisites on nodes

Note: Skip the pre-requisite-installer.sh script if RKE2 was installed using 1fcp-community.

```bash
source scripts/pre-req-installer.sh master        # master node pre-requisites
source scripts/pre-req-installer.sh worker        # worker node pre-requisites
source scripts/pre-req-installer.sh master ntp    # master + NTP
source scripts/pre-req-installer.sh worker ntp    # worker + NTP
```

---

## Configuration

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying. Key parameters:

| Parameter              | Description                                      | Default                      |
|------------------------|--------------------------------------------------|------------------------------|
| `image.tag`            | Cassandra image version                          | `4.1.5-debian-12-r0-patched` |
| `namespace`            | Kubernetes namespace for Cassandra               | Defined in config            |
| `replicaCount`         | Number of Cassandra replicas                     | Defined in config            |
| `storageClassName`     | Storage class for persistent volumes             | `rancher-dynamic-local-path` |

Also update the `dep_hosts` inventory file with the correct node IPs, hostnames, and SSH credentials.

---

Note: Below Ansible commands must be run from one of the master nodes in the cluster.


## Deployment

```bash
touch logs/ansible_cassandra_deploy.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_cassandra_deploy.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-cassandra -v
```

---

## Cleanup

```bash
touch logs/ansible_cassandra_cleanup.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_cassandra_cleanup.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-cassandra -v
```

---


## License

[Apache License 2.0](LICENSE)
