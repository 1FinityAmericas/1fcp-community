"""
IngressControllerKind class provides methods to deploy an ingress controller for a kind cluster. 
It includes functionality to apply the YAML and wait for the ingress controller pods to become ready, 
ensuring that the deployment is successful before proceeding with any tests that depend on the ingress controller.
"""

import os
import subprocess
import time
from typing import Dict, List, Optional
from src.libs.common.logger import Logger
from src.libs.common.k8s_client import K8sClient, K8sClientError

class IngressControllerKind:

    def __init__(self, kubeconfig_path: Optional[str] = None):
        """Initialize IngressControllerKind manager."""
        self.logger = Logger()
        self.k8s_client = K8sClient(kubeconfig_path)

    def deploy_ingress_controller(self, timeout: int = 180):
        """
        Deploy ingress controller to kind cluster using provided YAML.
        """

        yaml_path = "files/ingress_controller_for_kind.yaml"

        try:
            self.logger.info("Deploying Ingress Controller to kind cluster...")

            # Apply YAML
            subprocess.run(
                ["kubectl", "--kubeconfig", os.path.expanduser("~/.kube/config"), "apply", "-f", yaml_path],
                check=True
            )

            self.logger.info("Ingress YAML applied successfully.")

            # Wait for ingress controller pods to be ready
            self._wait_for_ingress_ready(timeout)

            self.logger.info("Ingress Controller deployed and ready.")

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to deploy ingress controller: {e}")
            raise Exception(f"Ingress deployment failed: {e}")
    
    def _wait_for_ingress_ready(self, timeout: int = 180):
        """
        Wait until ingress controller pods are ready.
        """

        namespace = "ingress-nginx" 
        start_time = time.time()

        while time.time() - start_time < timeout:
            try:
                result = subprocess.check_output(
                    [
                        "kubectl", "--kubeconfig", os.path.expanduser("~/.kube/config"),
                        "get", "pods", "-n", namespace,
                        "-l", "app.kubernetes.io/component=controller",
                        "-o", "jsonpath={.items[*].status.containerStatuses[*].ready}"
                    ]
                ).decode()

                if "true" in result:
                    return

            except subprocess.CalledProcessError:
                pass

            self.logger.info("Waiting for ingress controller to become ready...")
            time.sleep(5)

        raise Exception("Ingress controller did not become ready within timeout.")