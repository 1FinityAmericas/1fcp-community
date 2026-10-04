# Molecule Tests for cassandra 

This directory contains Molecule scenarios for validating the cassandra Ansible roles and playbooks.

## Prerequisites

- Python 3, Ansible, Molecule, and ansible-lint installed
- Kubernetes cluster reachable from the machine running Molecule
- `kubectl` and `helm` available in `PATH`
- Correct inventory and cluster configuration files

## Quick Start

Use the default configs in `molecule/configs/` and run scenarios directly:

```bash
# From repo root
molecule test -s default          # syntax and prerequisite checks
molecule test -s deploy-cassandra
molecule test -s cleanup-cassandra
```

## Available Scenarios

### 1. `default` - Syntax Validation
Validates YAML and playbook syntax for all project files.

### 2. `deploy-cassandra` - cassandra Deployment
Deploys cassandra to the Kubernetes cluster using `choose_deploy.yaml` and verifies the deployment.

### 3. `cleanup-cassandra` - cassandra Cleanup
Removes cassandra resources from the cluster and verifies cleanup.

## Configuration

### Option 1: Using Environment Variables (Recommended)

Export environment variables with **absolute paths** before running Molecule:

```bash
export INVENTORY_FILE=/path/to/cassandra/molecule/configs/dep_hosts_kind
export CLUSTER_CONFIG_FILE=/path/to/cassandra/molecule/configs/cluster_config.yaml
export APP_CONFIG_FILE=/path/to/cassandra/molecule/configs/app_config.yaml
```

### Option 2: Using Molecule Default Configs

If environment variables are not set, Molecule will use default configuration files from `molecule/configs/`:

- `molecule/configs/dep_hosts_kind` - Inventory file
- `molecule/configs/cluster_config.yaml` - Cluster configuration
- `molecule/configs/app_config.yaml` - Application configuration

Edit these files to match your environment:


## Running the Tests

### Run Individual Scenarios

```bash
# Syntax validation only
molecule test -s default

# Deploy cassandra ReplicaSet
molecule test -s deploy-cassandra

# Cleanup cassandra ReplicaSet
molecule test -s cleanup-cassandra
```

### Run All Scenarios in Sequence

```bash
molecule test -s default && \
molecule test -s deploy-cassandra && \
molecule test -s cleanup-cassandra
```

### Development Workflow

```bash
# Run converge only (no cleanup)
molecule converge -s deploy-cassandra

```

## Environment Variable Priority

The scenarios use the following priority order:

1. **Shell environment variables** (highest priority)
2. **Molecule defaults** from `molecule.yml`
3. **Playbook defaults** (lowest priority)

This allows flexible configuration for different environments (CI/CD, local testing, production).

