# Kubernetes Application Testing Framework

Pytest-based integration testing framework for Kubernetes application validation and deployment workflows.

## Features

*   **Generic K8s Resource Validation**: Reusable validator for any K8s app (pods, deployments, statefulsets, daemonsets)
*   **Kafka Validation**: Automated Kafka replica set deployment and health checks
*   **Environment-based Configuration**: All settings loaded from `.env` files

## Quick Start (TL;DR)

1) Create a virtual environment and install deps
   - Linux/macOS:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   python3 -m pip install -r requirements.txt
   ```

2) Update config files to match your cluster

   - Edit `config/cluster.env` (set `KUBECONFIG` - K8s cluster settings only)
   - Edit `config/app.env` (set all APP_* variables - resource, connection, authentication)
   - Port-forwarding auto-starts when `APP_ENABLE_PORT_FORWARD=true`

3) Run tests

   ```bash
   pytest tests/ --html=report.html --self-contained-html -s
   ```

4) Open `report.html` in a browser to view results

## Project Structure

```
py_test/
├── config/
│   ├── cluster.env           # K8s cluster-specific settings (KUBECONFIG, timeouts)
│   ├── app.env               # Application configuration (all APP_* settings)
├── src/
│   ├── libs/
│   │   ├── common/           # Logger, config, K8s client, port-forward
│   │   ├── kafka/            # Kafka connection manager
│   └── models/               # Data models (ValidationResult, etc.)
├── tests/
│   ├── __init__.py
│   ├── test_k8s_resource_validator.py  # Generic K8s resource validator (reusable)
│   ├── test_kafka_validator.py       # Kafka integration tests
├── files/
│   ├── kafka-client.yaml     # Kafka client manifest file
├── conftest.py               # Pytest configuration (env loading)
├── requirements.txt          # Python dependencies
└── README.md
```

## Prerequisites

*   Python 3.8 or higher
*   pip (Python package installer)
*   kubectl (installed and in PATH); access to a Kubernetes cluster with a valid kubeconfig
*   A deployed application in your cluster (tests validate existing deployments)
*   Podman (optional; only if you use container image operations)

## Installation

### 1. Clone the Repository

```bash
git clone https://bitbucket.fnc.fujitsu.com/scm/fcp/kafka.git
cd kafka/py_test
```

### 2. Create Virtual Environment

It's recommended to use a virtual environment to isolate project dependencies.


**On Linux/macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

Once the virtual environment is activated, install the required dependencies:

```bash
python3 -m pip install -r requirements.txt
```

### 4. Configure Environment

**K8s Cluster Settings** (`config/cluster.env`):
- Set `KUBECONFIG` path to your kubeconfig file
  - Linux/macOS: `KUBECONFIG=$HOME/.kube/config`
  - Windows: `KUBECONFIG=%USERPROFILE%\.kube\config`
- Set `K8S_TIMEOUT` and `K8S_API_TIMEOUT` for cluster operations

**Application Settings** (`config/app.env`):

All application configuration in one file:

*K8s Resource Settings:*
- `APP_NAMESPACE` - namespace where your app is deployed
- `APP_RESOURCE_TYPE` - `pod`, `deployment`, `statefulset`, or `daemonset`
- `APP_RESOURCE_NAME` - specific resource name
- `APP_LABEL_SELECTOR` - label selector to filter resources
- `APP_EXPECTED_REPLICAS` - expected replica count

*Connection Settings:*
- `APP_PORT` - application port (e.g., 9092 for Kafka)
- `APP_SERVICE_NAME` - K8s service name (e.g., kafka-headless)
- `APP_ENABLE_PORT_FORWARD` - enable automatic port-forwarding (true=localhost, false=K8s DNS)

*App Settings:*
- `APP_KAFKA_CLIENT_POD` - kafka client pod required for testing Kafka
- `APP_POD_READY_TIMEOUT` - retry timeout (e.g 60)

### 5. Deactivate Virtual Environment (when done)

```bash
deactivate
```

## Testing

Integration tests for Kubernetes applications using pytest.

### Test Structure

```
tests/
├── __init__.py
├── test_k8s_resource_validator.py  # Generic K8s resource validator (reusable)
├── test_kafka_validator.py         # Kafka-specific integration tests
```

#### Generic K8s Resource Validator (`test_k8s_resource_validator.py`)

**Reusable validator for any Kubernetes application** - no code changes needed!

Validates:
- **Pods** - namespace existence, pod health, readiness
- **Deployments** - replica count, availability, rollout status
- **StatefulSets** - replica count, pod health, ordered deployment
- **DaemonSets** - desired vs ready pods across nodes

Configure via environment variables (in `config/app.env`):
- `APP_NAMESPACE` - namespace to validate (default: `default`)
- `APP_RESOURCE_TYPE` - `pod`, `deployment`, `statefulset`, or `daemonset` (default: `pod`)
- `APP_RESOURCE_NAME` - specific resource name (optional)
- `APP_LABEL_SELECTOR` - label selector (e.g., `app=myapp`)
- `APP_EXPECTED_REPLICAS` - expected replica count (optional)

#### Kafka Tests (`test_kafka_validator.py`)

Kafka-specific integration tests:
- `TestKafkaTopicOperations` – topic related operations like create, list, delete
- `TestKafkaProducerConsumer` – produce and consume message

### Configuration

- **`conftest.py`**: Automatic environment file loading before tests
- **`config/cluster.env`**: K8s cluster-specific settings (KUBECONFIG, timeouts)
- **`config/app.env`**: All application settings (resource, connection, authentication)

These files are loaded automatically at test startup—edit them to match your environment.

### Running Tests

**Generic K8s Resource Validator (works for any app):**

Edit `config/app.env` to configure your application, then run:
```bash
# Validate pods in a namespace
# In config/app.env: APP_NAMESPACE=my-namespace, APP_RESOURCE_TYPE=pod, APP_LABEL_SELECTOR=app=myapp
pytest tests/test_k8s_resource_validator.py --html=report.html --self-contained-html -s

# Or override via environment variables:
export APP_NAMESPACE=my-namespace
export APP_RESOURCE_TYPE=pod
export APP_LABEL_SELECTOR=app=myapp
pytest tests/test_k8s_resource_validator.py --html=report.html --self-contained-html -s

# Validate a deployment
export APP_NAMESPACE=my-namespace
export APP_RESOURCE_TYPE=deployment
export APP_RESOURCE_NAME=my-deployment
export APP_EXPECTED_REPLICAS=3
pytest tests/test_k8s_resource_validator.py --html=report.html --self-contained-html -s

# Validate a statefulset
export APP_NAMESPACE=database
export APP_RESOURCE_TYPE=statefulset
export APP_RESOURCE_NAME=kafka
export APP_EXPECTED_REPLICAS=3
pytest tests/test_k8s_resource_validator.py --html=report.html --self-contained-html -s

# Validate a daemonset
export APP_NAMESPACE=kube-system
export APP_RESOURCE_TYPE=daemonset
export APP_RESOURCE_NAME=kube-proxy
pytest tests/test_k8s_resource_validator.py --html=report.html --self-contained-html -s
```

**Kafka-Specific Tests:**
```bash
# Authentication tests
pytest tests/test_kafka_validator.py::TestKafkaTopicOperations --html=report.html --self-contained-html -s

# Replica set tests
pytest tests/test_kafka_validator.py::TestKafkaProducerConsumer --html=report.html --self-contained-html -s

# Run all Kafka tests in this file
pytest tests/test_kafka_validator.py --html=report.html --self-contained-html -s
```


**Run All Tests:**
```bash
pytest tests/ --html=report.html --self-contained-html -s
```

### Environment Variables

**Configuration Files (loaded automatically):**
- `config/cluster.env` - K8s cluster settings (KUBECONFIG, K8S_TIMEOUT, K8S_API_TIMEOUT)
- `config/app.env` - All application settings (APP_NAMESPACE, APP_RESOURCE_TYPE, APP_PORT, APP_USER, APP_PASSWORD, APP_CONNECTION_MODE, etc.)

**Application Settings (APP_* variables):**
```bash
# Edit config/app.env or override via environment:

# K8s Resource Configuration
export APP_NAMESPACE=database
export APP_RESOURCE_TYPE=statefulset
export APP_RESOURCE_NAME=kafka
export APP_LABEL_SELECTOR=app=kafka
export APP_EXPECTED_REPLICAS=3

# Connection Configuration
export APP_PORT=27017
export APP_SERVICE_NAME=kafka-headless
export APP_ENABLE_PORT_FORWARD=true  # true=port-forward to localhost, false=use K8s DNS

# Authentication Configuration
export APP_USER=root
export APP_PASSWORD=0Admin123
export APP_AUTH_DATABASE=admin
export APP_REPLICA_SET_NAME=rs0
```

**K8s Cluster Settings (K8S_* variables):**
```bash
# Edit config/cluster.env or override:
export KUBECONFIG=$HOME/.kube/config
export K8S_TIMEOUT=120
export K8S_API_TIMEOUT=30
```

### Test Details

#### Generic K8s Resource Validator (`test_k8s_resource_validator.py`)

**Reusable for any Kubernetes application** - configure via environment variables:

1. **Namespace Validation**: Verifies the target namespace exists
2. **Pod Validation**: Validates pod phase (Running/Succeeded), readiness, and restart counts
3. **Deployment Validation**: Checks replica count, ready replicas, available replicas, and conditions
4. **StatefulSet Validation**: Validates replica count, ready replicas, current replicas, and individual pod health
5. **DaemonSet Validation**: Checks desired vs scheduled/ready/available pods across all nodes

#### Kafka Integration Tests (`test_kafka_validator.py`)

Kafka-specific application-level tests:

1. **Kafka Broker Readiness**: Checking broker connection
1. **Topic Operations**: Creating, listing and deleting topic
2. **Producer and Consumer**: Producing and consuming message from the topic validation

### Troubleshooting

- kubectl not found: Install kubectl and ensure it’s in PATH. Verify with `kubectl version --client`.
- KUBECONFIG path: Update `config/cluster.env` so `KUBECONFIG` points to your kubeconfig (see Configure Environment section).
- Connection refused: Ensure port-forward is running when `APP_ENABLE_PORT_FORWARD=true`. If auto-start fails, run manually:
  ```bash
  kubectl -n ndl port-forward kafka-0 9092:9092
  ```
