# RKE2 Installer

Ansible-based installer for an RKE2 Kubernetes cluster on RHEL 8.10. Supports single-master and HA multi-master deployments with optional kube-vip, local Docker registry, IPv4/IPv6 dual-stack, swap, Azure VIP fix, and node lifecycle management.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Configure dep\_hosts](#configure-dep_hosts)
- [Install RKE2](#install-rke2)
- [Node Management](#node-management)
- [Local Docker Registry](#local-docker-registry)
- [HA with kube-vip](#ha-with-kube-vip)
- [Azure VIP Fix](#azure-vip-fix)
- [Swap Configuration](#swap-configuration)
- [Uninstall RKE2](#uninstall-rke2)

---

## Prerequisites

### VM Specifications

| Resource | Minimum      |
|----------|-------------|
| RAM      | 8 GB        |
| CPU      | 8 vCPUs     |
| Disk (`/var/lib/docker`) | 100 GB (master) |

### Install prerequisites on nodes

Use the pre-built script for RHEL 8.10:

```bash
source scripts/pre-req-installer.sh master        # master node pre-requisites
source scripts/pre-req-installer.sh worker        # worker node pre-requisites
source scripts/pre-req-installer.sh master ntp    # master + NTP
source scripts/pre-req-installer.sh worker ntp    # worker + NTP
```

**Or manually on each node:**

<details>
<summary>RHEL 8.10 master</summary>

```bash
sudo yum install python3.12-pip -y
sudo pip3 install --upgrade pip
/usr/bin/python3.12 -m venv py3
source py3/bin/activate
pip install --upgrade pip wheel ansible-core==2.17
ansible-galaxy collection install ansible.posix containers.podman
sudo yum install fio-3.19 -y
sudo yum install -y podman sshpass nfs-utils git vim bzip2 tree iptables
sudo yum --setopt=tsflags=noscripts install iscsi-initiator-utils -y
sudo systemctl enable --now iscsid
```
</details>

<details>
<summary>RHEL 8.10 workers</summary>

```bash
sudo yum install python3.12-pip -y
sudo pip3 install --upgrade pip
sudo yum install fio-3.19 -y
sudo yum install -y sshpass nfs-utils vim bzip2 tar tree iptables
sudo yum --setopt=tsflags=noscripts install iscsi-initiator-utils -y
sudo systemctl enable --now iscsid
```
</details>

---

## Configure dep_hosts

Edit the `dep_hosts` inventory file before running any playbooks.

### SSH Authentication

**Password-based SSH:**
```ini
# Uncomment these, comment out ansible_ssh_private_key_file
ansible_password=<password>
ansible_sudo_pass=<sudo-password>
ansible_user=<user>
ansible_group=<group>
```

**Key-based SSH (PEM file):**
```ini
# Uncomment this, comment out ansible_password / ansible_sudo_pass
ansible_ssh_private_key_file=<pem_key_file>
ansible_user=<user>
ansible_group=<group>
```
> Place the PEM file in the `rke2-installer/` directory and set permissions: `chmod 400 <pem_key_file>`

### Node inventory

```ini
[kubenodes]
master1 ip=192.168.27.60  host=master1  group='node-config-master'   ip6=2001:abc:0:224:1c1d:c468:7f54:867f
master2 ip=192.168.27.61  host=master2  group='node-config-master'   ip6=2001:abc:0:224:1c1d:c468:7f54:893f
master3 ip=192.168.27.62  host=master3  group='node-config-master'   ip6=2001:abc:0:224:1c1d:c468:7f54:834f
worker1 ip=192.168.27.63  host=worker1  group='node-config-compute'  ip6=2001:abc:0:224::12
worker2 ip=192.168.27.64  host=worker2  group='node-config-compute'  ip6=2001:abc:0:224::13
worker3 ip=192.168.27.65  host=worker3  group='node-config-compute'  ip6=2001:abc:0:224::14

[kubemasters]
master1
master2
master3

[kubeworkers]
worker1
worker2
worker3
```

> The installer adds a `#1fcp` label to all host entries in `/etc/hosts` for identification.

---

## Install RKE2

> **Important:** Before running, ensure custom TLS certs (if required) are present at:
> - `/etc/pki/tls/certs/rke2-ca.crt`
> - `/etc/pki/tls/private/rke2-ca.key`

```bash
touch logs/rke2.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/rke2.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t rke2 -v
```

After installation, activate `kubectl`:

```bash
source ~/.bashrc
```

The nginx ingress controller ships with global rate limiting by default (50 req/s, 50 concurrent connections per IP). Override at the application level:

```yaml
# Per-ingress annotations
nginx.ingress.kubernetes.io/limit-connections: "100"
nginx.ingress.kubernetes.io/limit-rps: "30"
```

Edit the global configmap live:

```bash
kubectl edit cm rke2-ingress-nginx-controller -n kube-system
```

---

## Node Management

### Add nodes

Update the `[new_nodes]` section in `dep_hosts`, then run:

```bash
touch logs/ansible_add_node.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_add_node.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t add-node -v
```

### Delete nodes

Update the `[delete_nodes]` section in `dep_hosts`, then run:

```bash
touch logs/ansible_delete_node.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_delete_node.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t delete-node -v
```

---

## Local Docker Registry

To enable a local Docker registry, set in `dep_hosts`:

```ini
ext_docker_registry=true
```

The deployed registry uses the default DNS `<your-registry-dns>`.

To configure an external proxy registry, set `proxy: true` in `roles/app_config/host_vars/app_config.yaml`:

```yaml
docker_registry:
  proxy: true
  proxy_reg: https://<your-upstream-registry>
  proxy_username: <username>
  proxy_password: <password>
```

**Install local registry:**

```bash
touch logs/ansible_local_reg.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_local_reg.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t local-reg -v
```

**Cleanup local registry:**

```bash
touch logs/ansible_local_reg_cleanup.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/ansible_local_reg_cleanup.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t local-reg-cleanup -v
```

---

## HA with kube-vip

For multi-master HA deployments, set the following in `dep_hosts`:

```ini
ha_rke2=true
ha_rke2_interface=ens192
ha_rke2_vip_address=<vip-address>
ha_rke2_vip_hostname=master.<vip-address>.nip.io
# stack_type: 'single' (IPv4 only) or 'dual' (IPv4 + IPv6)
```

**Install kube-vip:**

```bash
touch logs/vip.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/vip.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t vip -v
```

**Remove kube-vip:**

```bash
touch logs/vip-remove.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/vip-remove.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t vip-remove -v
```

---

## Azure VIP Fix

On Azure, kube-vip requires a secondary IP configuration on the VM NIC to route VIP traffic. This role deploys a cron job on all master nodes that reconciles VIP assignment every 3 minutes.

Update `roles/app_config/host_vars/app_config.yaml`:

```yaml
azure_vip_fix:
  enable: true
  azure_client_id: <your-azure-managed-identity-client-id>
```

**Deploy Azure VIP fix:**

```bash
touch logs/azure-vip-fix.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/azure-vip-fix.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t azure-vip-fix -v
```

**Remove Azure VIP fix:**

```bash
touch logs/remove-azure-vip-fix.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/remove-azure-vip-fix.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t remove-azure-vip-fix -v
```

---

## Swap Configuration

Enable swap in `dep_hosts`:

```ini
swap_nodes=true
```

**Enable swap kubelet config:**

```bash
touch logs/kubelet-swap-enable.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/kubelet-swap-enable.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t kubelet-swap-enable -v
```

**Disable swap kubelet config:**

```bash
touch logs/kubelet-swap-disable.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/kubelet-swap-disable.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t kubelet-swap-disable -v
```

---

## Uninstall RKE2

```bash
touch logs/rke2-remove.log
export ANSIBLE_STDOUT_CALLBACK=debug
export ANSIBLE_LOG_PATH=logs/rke2-remove.log
time ansible-playbook -i dep_hosts choose_deploy.yaml -t rke2-remove -v
```

---

## License

[Apache License 2.0](LICENSE)
