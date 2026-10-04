# 1FCP Community

A collection of Ansible-based Kubernetes deployment packages for the **1FCP (Fujitsu Cloud Platform)** community. Each sub-project provides Helm chart templates, Ansible playbooks, and configuration files to deploy and manage a specific application on an RKE2 Kubernetes cluster.

## Projects

| Project | Description | Image Version |
|---------|-------------|---------------|
| [rke2-installer](rke2-installer/) | RKE2 Kubernetes cluster installer with kube-vip, local registry, and HA support | RKE2 v1.x |
| [registry-ha](registry-ha/) | High Availability Docker Registry backed by MinIO | Registry `3.0.0`, MinIO `2025-09-07` |
| [zookeeper](zookeeper/) | Apache ZooKeeper StatefulSet (required by Kafka) | `7.9.2` |
| [kafka](kafka/) | Apache Kafka StatefulSet (requires ZooKeeper) | `7.9.2` |
| [cassandra](cassandra/) | Apache Cassandra StatefulSet | `4.1.5` |
| [mongodb-rs](mongodb-rs/) | MongoDB Replica Set via Percona Server for MongoDB Operator | MongoDB `7.0.31`, Operator `1.22.0` |
| [apache-nifi](apache-nifi/) | Apache NiFi cluster with TLS ingress and Gateway API support | `2.9.0-debian13` |

---

## Getting Started

All projects follow the same general workflow:

1. **Download images** – Run `scripts/get_dependencies.sh <version>` to pull image tarballs.
2. **Configure inventory** – Edit `dep_hosts` with your node IPs, hostnames, and SSH credentials.
3. **Configure application** – Edit `roles/app_config/host_vars/app_config.yaml` for app-specific settings.
4. **Deploy** – Run the Ansible playbook with the appropriate tag.

See each project's `README.md` for detailed instructions.

---

## Deployment Order

For a full stack deployment, follow this recommended order:

```
rke2-installer  →  registry-ha  →  zookeeper  →  kafka
                                              →  cassandra
                                              →  mongodb-rs
                                              →  apache-nifi
```

> `kafka` depends on `zookeeper`. All application deployments require `rke2-installer` and optionally `registry-ha` for image hosting.

---

## Platform Requirements

- **OS:** RHEL 8.10
- **Ansible:** `ansible-core >= 2.17`
- **Python:** `3.12`
- **Kubernetes:** RKE2

---

## License

[Apache License 2.0](LICENSE)
