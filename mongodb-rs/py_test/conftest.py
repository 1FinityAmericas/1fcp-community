"""
Pytest configuration for loading environment files.
This file is automatically loaded by pytest.
"""
import os
import sys
import time
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

def _wait_for_pods_ready():
    """
    Wait for all MongoDB replica set pods to be Running and ready before proceeding.
    
    Uses environment variables:
    - APP_NAMESPACE: Kubernetes namespace
    - APP_RESOURCE_NAME: Replica set StatefulSet name (e.g., 'mongodb-rs-rs0')
    - APP_EXPECTED_REPLICAS: Expected replica set pod count
    - APP_WAIT_FOR_PODS_TIMEOUT: Timeout in seconds (falls back to K8S_TIMEOUT)
    """
    namespace = os.getenv("APP_NAMESPACE", "default")
    resource_name = os.getenv("APP_RESOURCE_NAME", "mongodb-rs")
    expected_replicas = int(os.getenv("APP_EXPECTED_REPLICAS", "1"))
    
    timeout = int(os.getenv("APP_WAIT_FOR_PODS_TIMEOUT", os.getenv("K8S_TIMEOUT", "300")))
    poll_interval = 5

    try:
        from src.libs.common.k8s_client import K8sClient, K8sClientError
    except ImportError as e:
        print(f"\n⚠ Warning: Could not import K8sClient, skipping pod readiness check: {e}")
        return

    print(f"\nWaiting for {expected_replicas} pod(s) for StatefulSet '{resource_name}' "
          f"in namespace '{namespace}' (timeout: {timeout}s)...", flush=True)

    try:
        k8s = K8sClient()
    except Exception as e:
        print(f"\n⚠ Warning: Could not initialise K8sClient, skipping pod readiness check: {e}", flush=True)
        return

    deadline = time.time() + timeout
    last_status = []

    while time.time() < deadline:
        try:
            pods = k8s.get_pods_status(namespace, label_selector=os.getenv("APP_LABEL_SELECTOR"))
        except Exception as e:
            print(f"  ✗ Error fetching pod status: {e}", flush=True)
            time.sleep(poll_interval)
            continue

        # Filter pods belonging to the replica set StatefulSet
        rs_pods = [
            p for p in pods
            if p["name"].startswith(f"{resource_name}-")
        ]

        ready_pods = [
            p for p in rs_pods
            if p["phase"] == "Running" and p["ready"]
        ]
        not_ready = [
            f"{p['name']} ({p['phase']}, ready={p['ready']})"
            for p in rs_pods
            if not (p["phase"] == "Running" and p["ready"])
        ]
        last_status = not_ready
        
        ready_rs_count = len(ready_pods)
        
        if ready_rs_count >= expected_replicas and not not_ready:
            print(f"✓ All {ready_rs_count} pod(s) for '{resource_name}' are Running and ready", flush=True)
            return

        elapsed = int(time.time() - (deadline - timeout))
        remaining = int(deadline - time.time())
        print(f"  [{elapsed}s elapsed, {remaining}s left] "
              f"{ready_rs_count}/{expected_replicas} ready — waiting: {not_ready}", flush=True)
        time.sleep(poll_interval)

    raise RuntimeError(
        f"Timed out after {timeout}s waiting for pods to be ready in namespace '{namespace}'. "
        f"Not ready: {last_status}"
    )


def _wait_for_replica_set_health():
    """
    Wait for all MongoDB replica set members to be healthy before proceeding.
    
    Uses environment variables:
    - APP_NAMESPACE: Kubernetes namespace
    - APP_RESOURCE_NAME: Replica set StatefulSet name (e.g., 'mongodb-rs-rs0')
    - APP_EXPECTED_REPLICAS: Expected replica set member count
    - APP_WAIT_FOR_MONGO_HEALTH_TIMEOUT: Timeout in seconds (falls back to K8S_TIMEOUT)
    """
    namespace = os.getenv("APP_NAMESPACE", "default")
    resource_name = os.getenv("APP_RESOURCE_NAME", "mongodb-rs")
    expected_replicas = int(os.getenv("APP_EXPECTED_REPLICAS", "1"))
    
    timeout = int(os.getenv("APP_WAIT_FOR_MONGO_HEALTH_TIMEOUT", os.getenv("K8S_TIMEOUT", "300")))
    poll_interval = 5

    try:
        from src.libs.mongodb.mongodb_connection import MongoDBConnection
    except ImportError as e:
        print(f"\n⚠ Warning: Could not import MongoDBConnection, skipping replica set health check: {e}")
        return

    print(f"\nWaiting for {expected_replicas} replica set member(s) to be healthy "
          f"(timeout: {timeout}s)...", flush=True)

    deadline = time.time() + timeout
    last_status = []

    while time.time() < deadline:
        try:
            mongo_conn = MongoDBConnection()
            mongo_conn.connect()
            member_health = mongo_conn.validate_replica_set_members()
        except Exception as e:
            print(f"  ✗ Error checking replica set health: {e}", flush=True)
            time.sleep(poll_interval)
            continue

        unhealthy_members = [name for name, healthy in member_health.items() if not healthy]
        last_status = unhealthy_members
        
        if len(member_health) == expected_replicas and not unhealthy_members:
            print(f"✓ All {len(member_health)} replica set member(s) are healthy", flush=True)
            mongo_conn.close()
            return

        elapsed = int(time.time() - (deadline - timeout))
        remaining = int(deadline - time.time())
        print(f"  [{elapsed}s elapsed, {remaining}s left] "
              f"{len(member_health) - len(unhealthy_members)}/{expected_replicas} healthy — "
              f"waiting: {unhealthy_members}", flush=True)
        time.sleep(poll_interval)
        mongo_conn.close()

    raise RuntimeError(
        f"Timed out after {timeout}s waiting for replica set members to be healthy. "
        f"Not healthy: {last_status}"
    )

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
    
    _wait_for_pods_ready()
    
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
    
    _wait_for_replica_set_health()



