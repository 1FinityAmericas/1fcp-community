"""
Pytest configuration for loading environment files.
This file is automatically loaded by pytest.
"""
import os
import sys
import time
import requests
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent))


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


# Load environment files automatically when conftest.py is imported
config_dir = Path(__file__).parent / "config"

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


def pytest_configure(config):
    """Pytest hook that runs before test collection. Waits for Apache NiFi to be ready."""
    import pytest
    requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)
    
    max_wait_seconds = 300
    poll_interval = 10
    
    protocol = os.getenv("APP_PROTOCOL", "https")
    port = os.getenv("APP_PORT", "8443")
    use_port_forward = os.getenv("APP_ENABLE_PORT_FORWARD", "true").lower() == "true"
    namespace = os.getenv("APP_NAMESPACE", "nifi")
    resource_name = os.getenv("APP_RESOURCE_NAME", "nifi")
    user = os.getenv("APP_USER", "admin")
    password = os.getenv("APP_PASSWORD", "0Admin@123456789")
    
    if use_port_forward:
        base_url = f"{protocol}://localhost:{port}"
    else:
        from src.libs.common.cluster_utils import get_ingress_host, detect_cluster_type, ClusterType
        from src.libs.common.ingress_controller_kind import IngressControllerKind
        
        cluster_type = detect_cluster_type()
        if cluster_type == ClusterType.KIND:
            print("⏳ Deploying ingress controller for Kind cluster...")
            ingress_manager = IngressControllerKind()
            ingress_manager.deploy_ingress_controller()
            print("✓ Ingress controller deployed and ready")
        
        host = get_ingress_host(namespace=namespace, ingress_name=resource_name)
        base_url = f"{protocol}://{host}" if host else f"{protocol}://{resource_name}.cluster.local"
    
    token_url = f"{base_url}/nifi-api/access/token"
    
    print(f"⏳ Waiting for Apache NiFi token endpoint to be ready at {token_url}...")
    
    start_time = time.time()
    last_error = None
    
    while (time.time() - start_time) < max_wait_seconds:
        try:
            response = requests.post(
                token_url,
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest"
                },
                data=f"username={user}&password={password}",
                timeout=30,
                verify=False
            )
            if response.status_code in (200, 201):
                elapsed = int(time.time() - start_time)
                print(f"✓ Apache NiFi is ready (took {elapsed}s)")
                return
        except requests.exceptions.RequestException as e:
            last_error = e
        
        elapsed = int(time.time() - start_time)
        print(f"  ... waiting for NiFi ({elapsed}s elapsed)")
        time.sleep(poll_interval)
    
    print(f"✗ Apache NiFi not ready after {max_wait_seconds}s. Last error: {last_error}")
    pytest.exit("Apache NiFi application is not ready. Aborting tests.", returncode=1)



