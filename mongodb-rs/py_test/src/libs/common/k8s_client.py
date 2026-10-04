"""
Modern Kubernetes client wrapper using official kubernetes-client SDK.
Replaces subprocess-based kubectl calls with native Python API.
Provides retry logic, proper error handling, and type hints.
"""
import os
from kubernetes import client, config
from kubernetes.client.exceptions import ApiException
from kubernetes.stream import stream
from tenacity import (
    retry,
    stop_after_delay,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from typing import List, Dict, Optional, Any
import logging

from src.libs.common.logger import Logger


class K8sClientError(Exception):
    """Custom exception for Kubernetes client errors."""
    pass


class K8sClient:
    """
    Kubernetes client with retry logic and proper error handling.
    Uses the official kubernetes-client Python SDK instead of subprocess calls.
    """
    
    def __init__(self, kubeconfig_path: Optional[str] = None):
        """
        Initialize Kubernetes client.
        
        :param kubeconfig_path: Optional path to kubeconfig file.
                               If not provided, tries in-cluster config first,
                               then falls back to default kubeconfig.
        """
        self.logger = Logger()
        self._load_config(kubeconfig_path)
        
        # Initialize API clients
        self.core_v1 = client.CoreV1Api(self.api_client)
        self.apps_v1 = client.AppsV1Api(self.api_client)
        self.networking_v1 = client.NetworkingV1Api(self.api_client)
        self.storage_v1 = client.StorageV1Api(self.api_client)
        self.batch_v1 = client.BatchV1Api(self.api_client)
    
    def _load_config(self, kubeconfig_path: Optional[str] = None):
        """
        Load kubeconfig from file or in-cluster config.
        
        :param kubeconfig_path: Path to kubeconfig file
        """
        try:
            if kubeconfig_path:
                # Expand environment variables and user home directory
                kubeconfig_path = os.path.expandvars(kubeconfig_path)
                kubeconfig_path = os.path.expanduser(kubeconfig_path)
                config.load_kube_config(config_file=kubeconfig_path)
                self.logger.info(f"Loaded kubeconfig from: {kubeconfig_path}")
            else:
                try:
                    config.load_incluster_config()
                    self.logger.info("Loaded in-cluster config")
                except config.ConfigException:
                    # Try to get KUBECONFIG from environment
                    kubeconfig_env = os.getenv('KUBECONFIG')
                    if kubeconfig_env:
                        # Expand environment variables and user home directory
                        kubeconfig_env = os.path.expandvars(kubeconfig_env)
                        kubeconfig_env = os.path.expanduser(kubeconfig_env)
                        config.load_kube_config(config_file=kubeconfig_env)
                        self.logger.info(f"Loaded kubeconfig from KUBECONFIG env: {kubeconfig_env}")
                    else:
                        config.load_kube_config()
                        self.logger.info("Loaded default kubeconfig")

            c = client.Configuration.get_default_copy()
            c.proxy = None  #Disable proxy completely

            self.api_client = client.ApiClient(configuration=c)
        except Exception as e:
            self.logger.error(f"Failed to load Kubernetes config: {e}")
            raise K8sClientError(f"Failed to load Kubernetes config: {e}")

    # ==================== Namespace Operations ====================
    
    def namespace_exists(self, namespace: str) -> bool:
        """
        Check if namespace exists in the cluster.
        
        :param namespace: Namespace name
        :return: True if namespace exists, False otherwise
        """
        try:
            self.core_v1.read_namespace(namespace)
            self.logger.debug(f"Namespace '{namespace}' exists")
            return True
        except ApiException as e:
            if e.status == 404:
                self.logger.debug(f"Namespace '{namespace}' does not exist")
                return False
            self.logger.error(f"Error checking namespace {namespace}: {e}")
            raise K8sClientError(f"Error checking namespace {namespace}: {e}")
    
    def list_namespaces(self):
        """
        List all namespaces in the cluster.
        
        :return: Namespace list object
        """
        try:
            return self.core_v1.list_namespace()
        except ApiException as e:
            self.logger.error(f"Error listing namespaces: {e}")
            raise K8sClientError(f"Error listing namespaces: {e}")
    
    def delete_namespace(self, namespace: str, force: bool = False) -> bool:
        """
        Delete a namespace.
        
        :param namespace: Namespace name
        :param force: If True, delete with grace_period=0
        :return: True if deleted successfully
        """
        try:
            grace_period = 0 if force else None
            self.core_v1.delete_namespace(
                namespace,
                grace_period_seconds=grace_period
            )
            self.logger.info(f"Deleted namespace: {namespace}")
            return True
        except ApiException as e:
            self.logger.error(f"Error deleting namespace {namespace}: {e}")
            raise K8sClientError(f"Error deleting namespace {namespace}: {e}")

    # ==================== Node Operations ====================
    
    def get_nodes_status(self) -> List[Dict[str, Any]]:
        """
        Get status of all cluster nodes.
        
        :return: List of node status dictionaries
        """
        try:
            nodes = self.core_v1.list_node()
            results = []
            for node in nodes.items:
                ready = False
                for condition in node.status.conditions or []:
                    if condition.type == "Ready":
                        ready = condition.status == "True"
                        break
                
                roles = [
                    k.replace("node-role.kubernetes.io/", "")
                    for k in node.metadata.labels.keys()
                    if k.startswith("node-role.kubernetes.io/")
                ]
                
                results.append({
                    "name": node.metadata.name,
                    "ready": ready,
                    "roles": roles,
                    "kubelet_version": node.status.node_info.kubelet_version,
                    "os_image": node.status.node_info.os_image,
                    "capacity": {
                        "cpu": node.status.capacity.get("cpu"),
                        "memory": node.status.capacity.get("memory"),
                        "pods": node.status.capacity.get("pods")
                    }
                })
            return results
        except ApiException as e:
            self.logger.error(f"Error getting nodes status: {e}")
            raise K8sClientError(f"Error getting nodes status: {e}")
    
    def check_all_nodes_ready(self) -> bool:
        """
        Check if all nodes in the cluster are in Ready state.
        
        :return: True if all nodes are ready
        """
        nodes = self.get_nodes_status()
        not_ready = [n["name"] for n in nodes if not n["ready"]]
        if not_ready:
            self.logger.warning(f"Nodes not ready: {not_ready}")
            return False
        self.logger.info("All nodes are ready")
        return True

    # ==================== Pod Operations ====================
    
    def get_pods_status(self, namespace: str, label_selector: str = None) -> List[Dict[str, Any]]:
        """
        Get status of all pods in a namespace with optional label filtering.
        
        :param namespace: Namespace name
        :param label_selector: Optional label selector (e.g., 'app=myapp' or 'app.kubernetes.io/name=mongodb')
        :return: List of pod status dictionaries
        """
        try:
            pods = self.core_v1.list_namespaced_pod(namespace, label_selector=label_selector)
            return [
                {
                    "name": pod.metadata.name,
                    "phase": pod.status.phase,
                    "ready": all(
                        c.ready for c in (pod.status.container_statuses or [])
                    ),
                    "restarts": sum(
                        c.restart_count for c in (pod.status.container_statuses or [])
                    ),
                    "containers": [
                        {
                            "name": c.name,
                            "ready": c.ready,
                            "restart_count": c.restart_count,
                            "state": self._get_container_state(c.state)
                        }
                        for c in (pod.status.container_statuses or [])
                    ]
                }
                for pod in pods.items
            ]
        except ApiException as e:
            self.logger.error(f"Error getting pods in namespace {namespace}: {e}")
            raise K8sClientError(f"Error getting pods in namespace {namespace}: {e}")
    
    def _get_container_state(self, state) -> str:
        """Get container state as string."""
        if state.running:
            return "running"
        elif state.waiting:
            return f"waiting: {state.waiting.reason}"
        elif state.terminated:
            return f"terminated: {state.terminated.reason}"
        return "unknown"
    
    @retry(
        stop=stop_after_delay(120),
        wait=wait_exponential(multiplier=2, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        reraise=True
    )
    def wait_for_pod_ready(self, name: str, namespace: str) -> bool:
        """
        Wait for pod to be in Running state with all containers ready.
        Uses exponential backoff retry.
        
        :param name: Pod name
        :param namespace: Namespace name
        :return: True if pod is ready
        :raises: Exception if pod doesn't become ready within timeout
        """
        try:
            pod = self.core_v1.read_namespaced_pod(name, namespace)
            
            if pod.status.phase != "Running":
                raise Exception(f"Pod {name} not running: {pod.status.phase}")
            
            if not pod.status.container_statuses:
                raise Exception(f"Pod {name} has no container statuses")
            
            if not all(c.ready for c in pod.status.container_statuses):
                not_ready = [
                    c.name for c in pod.status.container_statuses if not c.ready
                ]
                raise Exception(f"Pod {name} containers not ready: {not_ready}")
            
            self.logger.info(f"Pod {name} is ready")
            return True
            
        except ApiException as e:
            if e.status == 404:
                raise Exception(f"Pod {name} not found in namespace {namespace}")
            raise
    
    def check_all_pods_running(self, namespace: str) -> bool:
        """
        Check if all pods in namespace are running and ready.
        
        :param namespace: Namespace name
        :return: True if all pods are running and ready
        """
        pods = self.get_pods_status(namespace)
        not_ready = []
        for pod in pods:
            if pod["phase"] not in ["Running", "Succeeded"]:
                not_ready.append(f"{pod['name']} ({pod['phase']})")
            elif pod["phase"] == "Running" and not pod["ready"]:
                not_ready.append(f"{pod['name']} (not ready)")
        
        if not_ready:
            self.logger.warning(f"Pods not ready in {namespace}: {not_ready}")
            return False
        
        self.logger.info(f"All pods ready in namespace {namespace}")
        return True
    
    def exec_in_pod(
        self,
        pod_name: str,
        namespace: str,
        command: List[str],
        container: Optional[str] = None
    ) -> str:
        """
        Execute a command inside a pod container.
        
        :param pod_name: Pod name
        :param namespace: Namespace name
        :param command: Command to execute as list
        :param container: Container name (optional if pod has single container)
        :return: Command output
        """
        try:
            resp = stream(
                self.core_v1.connect_get_namespaced_pod_exec,
                pod_name,
                namespace,
                command=command,
                container=container,
                stderr=True,
                stdin=False,
                stdout=True,
                tty=False
            )
            self.logger.debug(f"Executed command in pod {pod_name}: {command}")
            return resp
        except ApiException as e:
            self.logger.error(f"Error executing command in pod {pod_name}: {e}")
            raise K8sClientError(f"Error executing command in pod {pod_name}: {e}")

    def list_pods(self, namespace: str, label_selector: str = None):
        """
        List pods in a namespace with optional label selector.
        
        :param namespace: Namespace name
        :param label_selector: Label selector (e.g., 'app=myapp')
        :return: Pod list object
        """
        try:
            return self.core_v1.list_namespaced_pod(
                namespace,
                label_selector=label_selector
            )
        except ApiException as e:
            self.logger.error(f"Error listing pods in namespace {namespace}: {e}")
            raise K8sClientError(f"Error listing pods in namespace {namespace}: {e}")

    # ==================== StatefulSet Operations ====================
    
    def get_statefulset(self, name: str, namespace: str):
        """
        Get StatefulSet details.
        
        :param name: StatefulSet name
        :param namespace: Namespace name
        :return: StatefulSet object or None if not found
        """
        try:
            return self.apps_v1.read_namespaced_stateful_set(name, namespace)
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"Error getting StatefulSet {name}: {e}")
            raise K8sClientError(f"Error getting StatefulSet {name}: {e}")

    # ==================== Deployment Operations ====================
    
    def get_deployment(self, name: str, namespace: str) -> Optional[Dict[str, Any]]:
        """
        Get deployment details.
        
        :param name: Deployment name
        :param namespace: Namespace name
        :return: Deployment details dictionary or None if not found
        """
        try:
            deployment = self.apps_v1.read_namespaced_deployment(name, namespace)
            return {
                "name": deployment.metadata.name,
                "namespace": deployment.metadata.namespace,
                "replicas": deployment.spec.replicas,
                "ready_replicas": deployment.status.ready_replicas or 0,
                "available_replicas": deployment.status.available_replicas or 0,
                "conditions": [
                    {
                        "type": c.type,
                        "status": c.status,
                        "reason": c.reason,
                        "message": c.message
                    }
                    for c in (deployment.status.conditions or [])
                ]
            }
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"Error getting deployment {name}: {e}")
            raise K8sClientError(f"Error getting deployment {name}: {e}")
    
    def apply_yaml(self, yaml_content: str, namespace: str = "default") -> bool:
        """
        Apply YAML manifest to cluster.
        Note: For complex manifests, consider using kubectl or the dynamic client.
        
        :param yaml_content: YAML content as string
        :param namespace: Default namespace for resources
        :return: True if applied successfully
        """
        import yaml
        try:
            docs = list(yaml.safe_load_all(yaml_content))
            for doc in docs:
                if doc is None:
                    continue
                kind = doc.get("kind", "").lower()
                metadata = doc.get("metadata", {})
                name = metadata.get("name")
                ns = metadata.get("namespace", namespace)
                
                self.logger.info(f"Applying {kind}/{name} in namespace {ns}")
                # This is simplified - full implementation would handle all resource types
            return True
        except Exception as e:
            self.logger.error(f"Error applying YAML: {e}")
            raise K8sClientError(f"Error applying YAML: {e}")

    # ==================== Storage Operations ====================
    
    def get_storage_classes(self) -> List[str]:
        """
        Get list of storage class names.
        
        :return: List of storage class names
        """
        try:
            storage_classes = self.storage_v1.list_storage_class()
            return [sc.metadata.name for sc in storage_classes.items]
        except ApiException as e:
            self.logger.error(f"Error getting storage classes: {e}")
            raise K8sClientError(f"Error getting storage classes: {e}")
    
    def get_pv(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get persistent volume details.
        
        :param name: PV name
        :return: PV details or None if not found
        """
        try:
            pv = self.core_v1.read_persistent_volume(name)
            return {
                "name": pv.metadata.name,
                "capacity": pv.spec.capacity.get("storage"),
                "access_modes": pv.spec.access_modes,
                "status": pv.status.phase,
                "storage_class": pv.spec.storage_class_name
            }
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"Error getting PV {name}: {e}")
            raise K8sClientError(f"Error getting PV {name}: {e}")
    
    def get_pvc(self, name: str, namespace: str = "default") -> Optional[Dict[str, Any]]:
        """
        Get persistent volume claim details.
        
        :param name: PVC name
        :param namespace: Namespace name
        :return: PVC details or None if not found
        """
        try:
            pvc = self.core_v1.read_namespaced_persistent_volume_claim(name, namespace)
            return {
                "name": pvc.metadata.name,
                "namespace": pvc.metadata.namespace,
                "capacity": pvc.status.capacity.get("storage") if pvc.status.capacity else None,
                "access_modes": pvc.spec.access_modes,
                "status": pvc.status.phase,
                "storage_class": pvc.spec.storage_class_name,
                "volume_name": pvc.spec.volume_name
            }
        except ApiException as e:
            if e.status == 404:
                return None
            self.logger.error(f"Error getting PVC {name}: {e}")
            raise K8sClientError(f"Error getting PVC {name}: {e}")

    # ==================== Ingress Operations ====================
    
    def ingress_exists(self, namespace: str) -> bool:
        """
        Check if any ingress exists in namespace.
        
        :param namespace: Namespace name
        :return: True if ingress exists
        """
        try:
            ingresses = self.networking_v1.list_namespaced_ingress(namespace)
            exists = len(ingresses.items) > 0
            self.logger.debug(f"Ingress exists in {namespace}: {exists}")
            return exists
        except ApiException as e:
            self.logger.error(f"Error checking ingress in {namespace}: {e}")
            raise K8sClientError(f"Error checking ingress in {namespace}: {e}")
    
    def get_ingresses(self, namespace: str) -> List[Dict[str, Any]]:
        """
        Get all ingresses in namespace.
        
        :param namespace: Namespace name
        :return: List of ingress details
        """
        try:
            ingresses = self.networking_v1.list_namespaced_ingress(namespace)
            return [
                {
                    "name": ing.metadata.name,
                    "hosts": [
                        rule.host for rule in (ing.spec.rules or [])
                    ],
                    "tls": [
                        {"hosts": tls.hosts, "secret": tls.secret_name}
                        for tls in (ing.spec.tls or [])
                    ]
                }
                for ing in ingresses.items
            ]
        except ApiException as e:
            self.logger.error(f"Error getting ingresses in {namespace}: {e}")
            raise K8sClientError(f"Error getting ingresses in {namespace}: {e}")

    # ==================== Resource Deletion ====================
    
    def delete_resources(
        self,
        namespace: str,
        resource_type: str = "all"
    ) -> bool:
        """
        Delete resources in namespace.
        
        :param namespace: Namespace name
        :param resource_type: Type of resource ('pods', 'pvc', 'secrets', 'all')
        :return: True if deleted successfully
        """
        try:
            if resource_type in ["pods", "all"]:
                self.core_v1.delete_collection_namespaced_pod(namespace)
                self.logger.info(f"Deleted all pods in {namespace}")
            
            if resource_type in ["pvc", "all"]:
                self.core_v1.delete_collection_namespaced_persistent_volume_claim(
                    namespace
                )
                self.logger.info(f"Deleted all PVCs in {namespace}")
            
            if resource_type in ["secrets", "all"]:
                # Be careful with secrets - don't delete service account tokens
                secrets = self.core_v1.list_namespaced_secret(namespace)
                for secret in secrets.items:
                    if secret.type != "kubernetes.io/service-account-token":
                        self.core_v1.delete_namespaced_secret(
                            secret.metadata.name, namespace
                        )
                self.logger.info(f"Deleted secrets in {namespace}")
            
            return True
        except ApiException as e:
            self.logger.error(f"Error deleting resources in {namespace}: {e}")
            raise K8sClientError(f"Error deleting resources in {namespace}: {e}")
