"""
Port Forward Manager for Kubernetes testing.
Automatically manages kubectl port-forward process for any Kubernetes resource.
"""
import os
import subprocess
import time
import signal
import atexit
from typing import Optional

from src.libs.common.logger import Logger


class PortForwardManager:
    """Manages kubectl port-forward process for any Kubernetes resource."""
    
    def __init__(self, namespace: str = None, resource: str = None, 
                 local_port: int = None, remote_port: int = None,
                 auto_start: bool = False):
        """
        Initialize port forward manager.
        
        Args:
            namespace: Kubernetes namespace (defaults to env var or 'default')
            resource: Resource to forward (e.g., 'pod/mongodb-0', 'svc/myservice')
            local_port: Local port to bind (defaults to remote_port)
            remote_port: Remote port on the resource
            auto_start: Automatically start port-forward on initialization
        """
        self.logger = Logger()
        self.process: Optional[subprocess.Popen] = None
        
        # Allow override via parameters or fall back to environment variables
        self.namespace = namespace or os.getenv("APP_NAMESPACE", "default")
        self.resource = resource
        self.local_port = local_port
        self.remote_port = remote_port
        
        # Register cleanup on exit
        atexit.register(self.stop)
        
        # Auto-start if requested
        if auto_start and self.resource and self.remote_port:
            self.start()
    
    def is_running(self) -> bool:
        """Check if port-forward process is running."""
        if self.process is None:
            return False
        
        # Check if process is still alive
        return self.process.poll() is None
    
    def start(self, resource: str = None, local_port: int = None, remote_port: int = None) -> bool:
        """
        Start kubectl port-forward process.
        
        Args:
            resource: Resource to forward (e.g., 'pod/mongodb-0', 'mongodb-0', 'svc/myservice')
            local_port: Local port to bind (defaults to remote_port)
            remote_port: Remote port on the resource
        
        Returns:
            True if started successfully, False otherwise
        """
        # Use provided parameters or fall back to instance variables
        resource = resource or self.resource
        remote_port = remote_port or self.remote_port
        local_port = local_port or self.local_port or remote_port
        
        if not resource or not remote_port:
            self.logger.error("Resource and remote_port must be specified")
            return False
        
        # Update instance variables
        self.resource = resource
        self.local_port = local_port
        self.remote_port = remote_port
        
        # Check if already running
        if self.is_running():
            self.logger.info("Port-forward already running")
            return True
        
        # Stop any existing port-forward on this port
        self._kill_existing_port_forward()
        
        # Build kubectl command
        cmd = ["kubectl"]
        
        # Add kubeconfig flag if available
        kubeconfig = os.getenv('KUBECONFIG')
        if kubeconfig:
            # Expand environment variables and user home directory
            kubeconfig = os.path.expandvars(kubeconfig)  # Expands $HOME, $USER, etc.
            kubeconfig = os.path.expanduser(kubeconfig)  # Expands ~
            cmd.extend(["--kubeconfig", kubeconfig])
        
        cmd.extend([
            "port-forward",
            "-n", self.namespace,
            resource,
            f"{local_port}:{remote_port}"
        ])
        
        try:
            self.logger.info(f"Starting port-forward: {' '.join(cmd)}")
            
            # Pass current environment to subprocess (includes KUBECONFIG from cluster.env)
            env = os.environ.copy()
            
            # Log KUBECONFIG for debugging
            if 'KUBECONFIG' in env:
                self.logger.debug(f"Using KUBECONFIG: {env['KUBECONFIG']}")
            else:
                self.logger.warning("KUBECONFIG not set - kubectl will use default config")
            
            # Start process in background
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                env=env,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            # Wait a moment for port-forward to establish
            time.sleep(2)
            
            # Check if process is still running
            if self.is_running():
                self.logger.info(f"✓ Port-forward started: localhost:{local_port} -> {resource}:{remote_port}")
                return True
            else:
                stderr = self.process.stderr.read().decode() if self.process.stderr else ""
                self.logger.error(f"Port-forward failed to start: {stderr}")
                return False
                
        except FileNotFoundError:
            self.logger.error("kubectl command not found. Please ensure kubectl is installed and in PATH")
            return False
        except Exception as e:
            self.logger.error(f"Failed to start port-forward: {e}")
            return False
    
    def stop(self):
        """Stop kubectl port-forward process."""
        if self.process and self.is_running():
            try:
                self.logger.info("Stopping port-forward...")
                
                # Send SIGTERM (graceful shutdown)
                if os.name == 'nt':
                    # Windows
                    self.process.terminate()
                else:
                    # Unix-like
                    self.process.send_signal(signal.SIGTERM)
                
                # Wait for process to terminate
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate
                    self.process.kill()
                    self.process.wait()
                
                self.logger.info("Port-forward stopped")
                
            except Exception as e:
                self.logger.warning(f"Error stopping port-forward: {e}")
            finally:
                self.process = None
    
    def _kill_existing_port_forward(self):
        """Kill any existing port-forward process on the same port."""
        try:
            if os.name == 'nt':
                # Windows: Find and kill process using the port
                cmd = f'netstat -ano | findstr ":{self.local_port}"'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.stdout:
                    # Extract PID and kill
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if 'LISTENING' in line:
                            parts = line.split()
                            pid = parts[-1]
                            subprocess.run(f'taskkill /F /PID {pid}', shell=True, capture_output=True)
                            self.logger.info(f"Killed existing process on port {self.local_port}")
            else:
                # Unix-like: Use lsof to find and kill
                cmd = f"lsof -ti:{self.local_port}"
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.stdout:
                    pids = result.stdout.strip().split('\n')
                    for pid in pids:
                        if pid:
                            subprocess.run(['kill', '-9', pid], capture_output=True)
                            self.logger.info(f"Killed existing process on port {self.local_port}")
        except Exception as e:
            self.logger.debug(f"Could not kill existing port-forward: {e}")
    
    def restart(self) -> bool:
        """
        Restart port-forward process.
        
        Returns:
            True if restarted successfully
        """
        self.stop()
        time.sleep(1)
        return self.start()


# Global instance
_port_forward_manager: Optional[PortForwardManager] = None


def get_port_forward_manager() -> PortForwardManager:
    """Get or create the global port forward manager instance."""
    global _port_forward_manager
    
    if _port_forward_manager is None:
        _port_forward_manager = PortForwardManager()
    
    return _port_forward_manager


def start_port_forward(resource: str = None, namespace: str = None, 
                       local_port: int = None, remote_port: int = None) -> bool:
    """
    Start port-forward (convenience function).
    
    Args:
        resource: Resource to forward (e.g., 'pod/mongodb-0', 'mongodb-0')
        namespace: Kubernetes namespace
        local_port: Local port to bind
        remote_port: Remote port on the resource
    
    Returns:
        True if started successfully
    
    Example:
        # Auto-config from environment (uses APP_* variables)
        start_port_forward()
        
        # Custom resource
        start_port_forward(resource='pod/myapp-0', namespace='myns', remote_port=8080)
    """
    # Auto-configure from environment if no resource specified
    if not resource:
        # Use APP_* variables for all configuration
        namespace = namespace or os.getenv("APP_NAMESPACE", "default")
        resource_name = os.getenv("APP_RESOURCE_NAME", "mongodb-rs")
        resource = f"{resource_name}-0"
        remote_port = remote_port or int(os.getenv("APP_PORT", "27017"))
        local_port = local_port or remote_port
    
    if not resource or not remote_port:
        return False
    
    manager = PortForwardManager(namespace=namespace)
    return manager.start(resource=resource, local_port=local_port, remote_port=remote_port)


def stop_port_forward():
    """Stop port-forward (convenience function)."""
    manager = get_port_forward_manager()
    manager.stop()
