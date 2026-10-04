"""
Apache nifi Connection Manager for integration testing.
Handles Apache nifi authentication and replica set connections.
"""
import os
import subprocess
import json
import base64
import tempfile
import time
from typing import Dict, List, Optional
import requests
from src.libs.common.logger import Logger
from src.libs.common.ingress_controller_kind import IngressControllerKind
from src.libs.common.k8s_client import K8sClient, K8sClientError
from src.libs.common.cluster_utils import detect_cluster_type, get_ingress_host, ClusterType


class ApacheNifiFlow:
    """Manages Apache nifi flow for testing."""
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """Initialize Apache nifi flow manager."""
        self.logger = Logger()
        self.k8s_client = K8sClient(kubeconfig_path)
        self.ingress_manager = IngressControllerKind(kubeconfig_path)
        
        # Load all configuration from APP_* variables
        self.namespace = os.getenv("APP_NAMESPACE", "default")
        self.statefulset_name = os.getenv("APP_RESOURCE_NAME", "nifi")
        self.replica_count = int(os.getenv("APP_EXPECTED_REPLICAS", "3"))
        self.service_name = os.getenv("APP_SERVICE_NAME", "nifi-headless")
        self.cluster_type = os.getenv("CLUSTER_TYPE", "kind")
        self.verify_ssl = os.getenv("APP_VERIFY_SSL", "false").lower() == "true"
        self.auto_extract_cert = os.getenv("APP_AUTO_EXTRACT_CERT", "true").lower() == "true"
        self.port = int(os.getenv("APP_PORT", "8443"))
        self.protocol = os.getenv("APP_PROTOCOL", "https")
        self.user = os.getenv("APP_USER", "admin")
        self.password = os.getenv("APP_PASSWORD", "0Admin@123456789")
        
        # Determine if using local port-forward or cluster DNS
        self.use_port_forward = os.getenv("APP_ENABLE_PORT_FORWARD", "true").lower() == "true"
        
        self.session = None
        
        mode = "local (port-forward)" if self.use_port_forward else "cluster (K8s DNS)"
        self.logger.info(f"ApacheNifi connection initialized for namespace: {self.namespace}, mode: {mode}")


    def get_base_url(self, pod_name: str = None) -> str:
        """
        Get NiFi base URL.

        Args:
            pod_name: Specific pod name (e.g., 'nifi-0'), or None for service-level access

        Returns:
            Base URL string
        """
        if self.use_port_forward:
            return f"{self.protocol}://localhost:{self.port}"
        
        # If testing a specific pod
        if pod_name:
            host = f"{pod_name}.{self.service_name}.{self.namespace}.svc.cluster.local"
            return f"{self.protocol}://{host}:{self.port}"
        
        # Get ingress host from Kubernetes ingress resource
        host = get_ingress_host(namespace=self.namespace, ingress_name=self.statefulset_name)
        if not host:
            self.logger.warning("Could not fetch ingress host, using default")
            host = f"{self.statefulset_name}.cluster.local"

        return f"{self.protocol}://{host}"

        
    def _extract_tls_cert(self):
        try:
            result = subprocess.check_output([
                "kubectl", "--kubeconfig", os.path.expanduser("~/.kube/config"), "get",
                "secret", "apache-nifi-secret",
                "-n", self.namespace, "-o", "json"
            ])

            secret = json.loads(result)
            cert_b64 = secret["data"]["tls.crt"]
            cert = base64.b64decode(cert_b64)

            temp_cert = tempfile.NamedTemporaryFile(delete=False)
            temp_cert.write(cert)
            temp_cert.close()

            return temp_cert.name

        except Exception as e:
            self.logger.warning(f"Could not extract TLS cert: {e}")
            return False
    
    def create_ingress_controller(self):
        """Creating ingress controller for kind cluster"""

        self.logger.info("Creating ingress controller if running on kind cluster...")

        cluster_type = detect_cluster_type()
        
        if cluster_type == ClusterType.KIND:
            self.ingress_manager.deploy_ingress_controller()
    
    def connect(self, pod_name: str = None, timeout: int = 10):

        base_url = self.get_base_url(pod_name)

        try:
            self.logger.info(f"Connecting to NiFi: {pod_name or 'service'}")

            self.session = requests.Session()
            if self.verify_ssl:

                cert_path = None

                if self.auto_extract_cert:
                    cert_path = self._extract_tls_cert()

                if cert_path:
                    self.logger.info("Using extracted TLS certificate for verification")
                    self.session.verify = cert_path
                else:
                    self.logger.warning("TLS cert not extracted. Falling back to system CA")
                    self.session.verify = True

            else:
                self.logger.warning("SSL verification disabled")
                self.session.verify = False

            # Get token
            token_response = self.session.post(
                f"{base_url}/nifi-api/access/token",
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "X-Requested-With": "XMLHttpRequest"
                },
                data=f"username={self.user}&password={self.password}",
                timeout=timeout
            )
            token_response.raise_for_status()

            token = token_response.text.strip()

            # Set required headers
            self.session.headers.update({
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "X-Requested-With": "XMLHttpRequest"
            })

            # Test connection
            response = self.session.get(
                f"{self.get_base_url()}/nifi-api/flow/about",
                timeout=timeout
            )
            response.raise_for_status()

            self.logger.info("Successfully connected to NiFi")
            return self.session

        except Exception as e:
            self.logger.error(f"Failed to connect to NiFi: {e}")
            raise

        
    def test_authentication(self) -> bool:
        """
        Test NiFi authentication.

        Returns:
            True if authentication successful
        """
        try:
            if not self.session:
                self.connect()

            base_url = self.get_base_url()
            response = self.session.get(f"{base_url}/nifi-api/flow/about")

            if response.status_code == 200:
                self.logger.info("Authentication successful.")
                return True
            else:
                self.logger.error(
                    f"Authentication failed. Status: {response.status_code}"
                )
                return False

        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

   
    def close(self):
        """Close NiFi session connection."""

        try:
            if self.session:
                self.logger.info("Closing NiFi session...")
                self.session.close()
                self.logger.info("NiFi session closed successfully.")
                self.session = None
                self.client = None  # if you're aliasing client to session

        except Exception as e:
            self.logger.error(f"Failed to close NiFi session: {e}")
            raise Exception(f"Error closing NiFi session: {e}")
