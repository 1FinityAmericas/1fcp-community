"""
Pytest configuration for loading environment files.
This file is automatically loaded by pytest.
"""
import os
import sys
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



