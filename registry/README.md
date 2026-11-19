
## Table of Contents

- [Prerequisites](#prerequisites)
- [Configuration](#configuration)
- [Deployment](#deployment)
- [Cleanup](#cleanup)

---

## Prerequisites

1. An RKE2 cluster must be running with a configured `dep_hosts` inventory file.
2. Ensure node IPs, hostnames, and SSH credentials are set correctly in `dep_hosts`.

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

Review and edit `roles/app_config/host_vars/app_config.yaml` before deploying:
```yaml
#
deployment:
  env: linux


reg_ca_cert_exists: false
docker_registry:
  namespace: registry
  registry:
    image:
      repo: docker.io/library/registry
      tag: 3.0.0
      enabled: true
  reg_path: /var/lib/docker/dynamic-local-path-mounts/
  path: registry
  resources:
    requests:
      cpu: "0.5"
      memory: "2Gi"
    limits:
      cpu: "2"
      memory: "4Gi"
```

## Deployment

> **Important:** Always run the cleanup playbook before deploying to ensure a clean state.
> **Note:** Below Ansible commands must be run from one of the master nodes in the cluster.


### Step 1 – – Deploy registry

1. Run ansible playbook with 'deploy-registry' tag in order to install local docker registry

```bash

touch log/ansible-deploy-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=log/ansible-deploy-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-registry -v

```

2. Run ansible playbook with 'deploy-registry' tag in order to install local docker registry if certs are present already 

```bash
    
touch log/ansible-deploy-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=log/ansible-deploy-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-registry -v -e "rotate_cert=false"

```

## Cleanup

1. Run ansible playbook with 'cleanup-registry' tag in order to clean local docker registry

```bash
touch log/ansible-cleanup-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=log//ansible-cleanup-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-registry -v

```
2. Run ansible playbook with 'cleanup-registry' tag in order to clean local docker registry if dont want to cleanup registry certs

```bash
touch log/ansible-cleanup-registry.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=log//ansible-cleanup-registry.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-registry -v -e "rotate_cert=false"

```
---

## License

[Apache License 2.0](LICENSE)
                               
