"""
Pytest configuration for loading environment files.
This file is automatically loaded by pytest.
"""
import os
import sys
import pytest
import yaml
import subprocess
from pathlib import Path

from src.libs.common.k8s_client import K8sClient, K8sClientError

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))

# Directory paths
config_dir = Path(__file__).parent / "config"
files_dir  = Path(__file__).parent / "files"

def _load_env_file(env_file: Path, override: bool = True):
    """
    Load environment variables from a .env file.
    
    Args:
        env_file: Path to the .env file
        override: If True, override existing environment variables (default: True)
    """
    if env_file.exists():
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip().strip('"\'')
                    
                    # Override existing env vars or only set if not exists
                    if override or key not in os.environ:
                        os.environ[key] = value

# Load cluster configuration (K8s-specific settings only)
cluster_env = config_dir / "cluster.env"
if cluster_env.exists():
    _load_env_file(cluster_env, override=True)
    print(f"✓ Loaded cluster.env (KUBECONFIG: {os.getenv('KUBECONFIG')})")

# Load application configuration (includes all app settings)
app_env = config_dir / "app.env"
if app_env.exists():
    _load_env_file(app_env)
    print(f"✓ Loaded app.env (APP_NAMESPACE: {os.getenv('APP_NAMESPACE')}, APP_RESOURCE_TYPE: {os.getenv('APP_RESOURCE_TYPE')})")
    
    # Auto-start port-forward if enabled
    enable_port_forward = os.getenv("APP_ENABLE_PORT_FORWARD", "true").lower() == "true"
    
    if enable_port_forward:
        try:
            from src.libs.common.port_forward_manager import start_port_forward
            
            # Start port-forward in background (auto-configures from APP_* variables)
            success = start_port_forward()
            if success:
                port = os.getenv("APP_PORT", "27017")
                print(f"✓ Port-forward started automatically (localhost:{port})")
            else:
                namespace = os.getenv("APP_NAMESPACE", "default")
                port = os.getenv("APP_PORT", "27017")
                print("\n⚠ Warning: Could not start port-forward automatically")
                print(f"  Please run manually: kubectl port-forward -n {namespace} {os.getenv('APP_RESOURCE_NAME', 'mongodb-rs')}-0 {port}:{port}")
        except Exception as e:
            namespace = os.getenv("APP_NAMESPACE", "default")
            port = os.getenv("APP_PORT", "27017")
            print(f"\n⚠ Warning: Port-forward auto-start failed: {e}")
            print(f"  Please run manually: kubectl port-forward -n {namespace} {os.getenv('APP_RESOURCE_NAME', 'mongodb-rs')}-0 {port}:{port}")


# ─── Kafka client pod fixture
 
_POD_MANIFEST      = files_dir / "kafka_client.yaml"
_MAX_RETRIES       = 2
_POD_READY_TIMEOUT = int(os.getenv("APP_POD_READY_TIMEOUT", "60"))
_POD_NAME          = os.getenv("APP_Kafka_CLIENT_POD", "kafka-client")
 
@pytest.fixture(scope="module")
def kafka_pod():
    """
    Deploy the kafka-client pod once for the entire test module.
    Shared across all test classes in the module.
    Deleted after the last test in the module completes.
    """
    namespace      = os.getenv("APP_NAMESPACE", "default")
    total_attempts = _MAX_RETRIES + 1
    k8s            = K8sClient()

    with open(_POD_MANIFEST) as f:
        manifest = yaml.safe_load(f)
 
    # Clean up any leftover pod from a previous interrupted run
    k8s.delete_pod(_POD_NAME, namespace) 
 
    last_error = None
    for attempt in range(1, total_attempts + 1):
        try:
            print(f"\n Deploying kafka-client pod (attempt {attempt}/{total_attempts})")
            k8s.create_pod(manifest, namespace)
            k8s.wait_for_pod_ready(_POD_NAME, namespace)
            print("kafka-client pod is Ready")
            last_error = None
            break
        except (K8sClientError, Exception) as e:
            last_error = e
            print(f"Attempt {attempt} failed: {e}")
            k8s.delete_pod(_POD_NAME, namespace)
 
    if last_error:
        pytest.fail(
            f"kafka-client pod failed to become Ready after {total_attempts} attempts. "
            f"Check image availability and cluster resources."
        )
 
    yield
 
    print("\nTearing down kafka-client pod...")
    k8s.delete_pod(_POD_NAME, namespace)
    print("kafka-client pod deleted")
