# to deploy the Rancher local pv

## Prerequisites

### Install prerequisites on nodes

Note: Skip the pre-requisite-installer.sh script if RKE2 was installed using 1fcp-community.

```bash
source scripts/pre-req-installer.sh master        # master node pre-requisites
source scripts/pre-req-installer.sh worker        # worker node pre-requisites
source scripts/pre-req-installer.sh master ntp    # master + NTP
source scripts/pre-req-installer.sh worker ntp    # worker + NTP
```


# Check with default Configuration of app_config.yaml and modify as per requirements.

```
rancher_local_pv:
  name: local-path-provisioner
  namespace: localpv
  image:
    repository: docker.io/rancher
    name: local-path-provisioner
    tag: v0.0.31
  rancher_resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 100m
      memory: 128Mi
  class: rancher-dynamic-local-path
  rbac: false
  nodePathMap: /var/lib/docker/dynamic-local-path-mounts/
  helper:
    repository: docker.io
    name: busybox
    tag: 1.37.0
  helper_resources:
    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: 100m
      memory: 128Mi
```
Ansible Commands to Deploy & Cleanup rancher-local-provisioner Application:

Note: Below Ansible commands must be run from one of the master nodes in the cluster.

1. Run ansible playbook to install rancher-local-provisioner
    ```
    touch logs/rancher-local-pv.log
    export ANSIBLE_STDOUT_CALLBACK=debug
    export ANSIBLE_LOG_PATH=logs/rancher-local-pv.log
    time ansible-playbook -i dep_hosts choose_deploy.yaml -t deploy-rancher-local-pv -v
    ```

2. Run ansible playbook to uninstall rancher-local-provisioner 
    ```
    touch logs/rancher-local-pv-cleanup.log
    export ANSIBLE_STDOUT_CALLBACK=debug
    export ANSIBLE_LOG_PATH=logs/rancher-local-pv-cleanup.log
    time ansible-playbook -i dep_hosts choose_deploy.yaml -t cleanup-rancher-local-pv -v
    ```

