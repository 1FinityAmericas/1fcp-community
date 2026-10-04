# Registry HA

Ansible-based deployment of a High Availability Docker Registry on Kubernetes (RKE2) using Helm. The registry (`3.0.0`) is backed by MinIO object storage (`RELEASE.2025-09-07T16-13-09Z`) for distributed blob storage.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Cleanup](#cleanup)

---

## Prerequisites

1. An RKE2 cluster must be running with a configured `dep_hosts` inventory file.
2. Ensure node IPs, hostnames, and SSH credentials are set correctly in `dep_hosts`.

---

## Configuration

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying:

```yaml
docker_registry:
  namespace: registry
  image:
    repository: <your-registry-dns>
    name: registry
    tag: 3.0.0
  registry:
    image:
      repo: docker.io/library/registry
      tag: 3.0.0
      enabled: true
  minio:
    image:
      repo: quay.io/minio/minio
      tag: RELEASE.2025-09-07T16-13-09Z
      enabled: true
      basePath: /var/lib/minio-vol/
  reg_path: /var/lib/docker/dynamic-local-path-mounts/
  path: registry-ha
  securityContext:
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  resources:
    requests:
      cpu: "0.5"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"
  proxy: false
```

---

## Deployment

> **Important:** Always run the cleanup playbook before deploying to ensure a clean state.

### Step 1 – Cleanup existing registry

```bash
touch logs/ansible-cleanup-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible-cleanup-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-registry -v
```

### Step 2 – Deploy registry

```bash
touch logs/ansible-deploy-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible-deploy-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-registry -v
```

---

## Cleanup

```bash
touch logs/ansible-cleanup-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible-cleanup-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-registry -v
```

---

## License

[Apache License 2.0](LICENSE)
