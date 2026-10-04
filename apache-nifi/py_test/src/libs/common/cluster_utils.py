"""
Cluster utilities for detecting cluster type and container runtime configuration.
Provides decorators for kind-specific and rke2-specific test cases.
"""
import os
import subprocess
import functools
from typing import Optional, Callable
import pytest

from src.libs.common.logger import Logger


class ClusterConfig:
    """Container runtime and cluster configuration."""
    
    # RKE2/K3s container runtime paths
    K8S_CTR_BIN_PATH = os.getenv("K8S_CTR_BIN_PATH", "/var/lib/rancher/rke2/bin/ctr")
    K8S_CTR_SOCKET = os.getenv("K8S_CTR_SOCKET", "/run/k3s/containerd/containerd.sock")
    
    # Kind container runtime paths
    KIND_CTR_BIN_PATH = os.getenv("KIND_CTR_BIN_PATH", "/usr/bin/ctr")
    KIND_CTR_SOCKET = os.getenv("KIND_CTR_SOCKET", "/run/containerd/containerd.sock")
    
    # Container namespace
    CTR_NAMESPACE = os.getenv("CTR_NAMESPACE", "k8s.io")


class ClusterType:
    """Cluster type constants."""
    KIND = "kind"
    RKE2 = "rke2"
    K3S = "k3s"
    UNKNOWN = "unknown"


_cached_cluster_type: Optional[str] = None


def detect_cluster_type() -> str:
    """
    Detect whether the cluster is Kind, RKE2, or K3s.
    
    Returns:
        str: Cluster type ('kind', 'rke2', 'k3s', or 'unknown')
    """
    global _cached_cluster_type
    
    if _cached_cluster_type is not None:
        return _cached_cluster_type
    
    logger = Logger()
    
    try:
        kubeconfig = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config"))
        kubeconfig = os.path.expandvars(kubeconfig)
        kubeconfig = os.path.expanduser(kubeconfig)
        
        node_name = subprocess.check_output(
            ["kubectl", "--kubeconfig", kubeconfig, 
             "get", "nodes", "-o",
             "jsonpath={.items[0].metadata.name}"],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        logger.info(f"Node Name: {node_name}")
        
        if node_name.startswith("kind-"):
            _cached_cluster_type = ClusterType.KIND
        elif "k3s" in node_name.lower():
            _cached_cluster_type = ClusterType.K3S
        else:
            _cached_cluster_type = ClusterType.RKE2
            
        return _cached_cluster_type
        
    except Exception as e:
        logger.warning(f"Cluster detection failed: {e}")
        _cached_cluster_type = ClusterType.UNKNOWN
        return _cached_cluster_type


def get_ctr_config() -> dict:
    """
    Get container runtime configuration based on cluster type.
    
    Returns:
        dict: Container runtime configuration with 'bin_path', 'socket', and 'namespace'
    """
    cluster_type = detect_cluster_type()
    
    if cluster_type == ClusterType.KIND:
        return {
            "bin_path": ClusterConfig.KIND_CTR_BIN_PATH,
            "socket": ClusterConfig.KIND_CTR_SOCKET,
            "namespace": ClusterConfig.CTR_NAMESPACE
        }
    else:
        return {
            "bin_path": ClusterConfig.K8S_CTR_BIN_PATH,
            "socket": ClusterConfig.K8S_CTR_SOCKET,
            "namespace": ClusterConfig.CTR_NAMESPACE
        }


def kind_only(func: Callable) -> Callable:
    """
    Decorator to skip test if not running on Kind cluster.
    
    Usage:
        @kind_only
        def test_kind_specific_feature(self):
            # This test only runs on Kind clusters
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cluster_type = detect_cluster_type()
        if cluster_type != ClusterType.KIND:
            pytest.skip(f"Test requires Kind cluster (current: {cluster_type})")
        return func(*args, **kwargs)
    return wrapper


def rke2_only(func: Callable) -> Callable:
    """
    Decorator to skip test if not running on RKE2 cluster.
    
    Usage:
        @rke2_only
        def test_rke2_specific_feature(self):
            # This test only runs on RKE2 clusters
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cluster_type = detect_cluster_type()
        if cluster_type != ClusterType.RKE2:
            pytest.skip(f"Test requires RKE2 cluster (current: {cluster_type})")
        return func(*args, **kwargs)
    return wrapper


def k3s_only(func: Callable) -> Callable:
    """
    Decorator to skip test if not running on K3s cluster.
    
    Usage:
        @k3s_only
        def test_k3s_specific_feature(self):
            # This test only runs on K3s clusters
            pass
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        cluster_type = detect_cluster_type()
        if cluster_type != ClusterType.K3S:
            pytest.skip(f"Test requires K3s cluster (current: {cluster_type})")
        return func(*args, **kwargs)
    return wrapper


def requires_cluster_type(*cluster_types: str) -> Callable:
    """
    Decorator to skip test if not running on specified cluster type(s).
    
    Usage:
        @requires_cluster_type(ClusterType.KIND, ClusterType.K3S)
        def test_feature_for_kind_or_k3s(self):
            # This test runs on Kind or K3s clusters
            pass
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            current_type = detect_cluster_type()
            if current_type not in cluster_types:
                pytest.skip(f"Test requires cluster type {cluster_types} (current: {current_type})")
            return func(*args, **kwargs)
        return wrapper
    return decorator


def get_ingress_host(namespace: str = "keycloak", ingress_name: str = "keycloak") -> Optional[str]:
    """
    Get the ingress host from Kubernetes ingress resource.
    
    Args:
        namespace: Namespace where ingress is deployed (default: "keycloak")
        ingress_name: Name of the ingress resource (default: "keycloak")
    
    Returns:
        str: Ingress host (e.g., "keycloak.10.156.198.126.nip.io") or None if not found
    """
    logger = Logger()
    
    try:
        kubeconfig = os.getenv("KUBECONFIG", os.path.expanduser("~/.kube/config"))
        kubeconfig = os.path.expandvars(kubeconfig)
        kubeconfig = os.path.expanduser(kubeconfig)
        
        # Get ingress host from the ingress resource
        host = subprocess.check_output(
            [
                "kubectl", "--kubeconfig", kubeconfig,
                "get", "ingress", ingress_name,
                "-n", namespace,
                "-o", "jsonpath={.spec.rules[0].host}",
            ],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        if host:
            logger.info(f"Found ingress host: {host}")
            return host
        
        # Fallback: try to get master IP and construct host
        logger.warning("Ingress host not found, falling back to master IP")
        ip = subprocess.check_output(
            [
                "kubectl", "--kubeconfig", kubeconfig,
                "get", "nodes",
                "-o", "jsonpath={.items[0].status.addresses[?(@.type==\"InternalIP\")].address}",
            ],
            text=True,
            stderr=subprocess.DEVNULL
        ).strip()
        
        if ip:
            return f"{ingress_name}.{ip}.nip.io"
        
        return None
        
    except Exception as e:
        logger.error(f"Unable to fetch ingress host: {e}")
        return None
