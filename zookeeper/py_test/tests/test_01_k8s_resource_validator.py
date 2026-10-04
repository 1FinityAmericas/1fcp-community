"""
Generic Kubernetes resource validator tests.
Validates any K8s application (pods, deployments, statefulsets, daemonsets) deployed on the cluster.
This is a reusable test module - configure via environment variables to validate any app.
"""
import os
import pytest
from typing import List, Dict, Any

from src.libs.common.k8s_client import K8sClient, K8sClientError
from src.libs.common.logger import Logger
from src.models.validation_result import ValidationResult, ValidationSummary


class TestK8sResourceValidator:
    """
    Generic Kubernetes resource validator.
    
    Configure via environment variables (in config/app.env):
    - APP_NAMESPACE: Namespace to validate (default: 'default')
    - APP_RESOURCE_TYPE: Resource type - 'pod', 'deployment', 'statefulset', 'daemonset' (default: 'pod')
    - APP_RESOURCE_NAME: Resource name to validate (optional, validates all if not set)
    - APP_LABEL_SELECTOR: Label selector to filter resources (e.g., 'app=myapp')
    - APP_EXPECTED_REPLICAS: Expected replica count for deployments/statefulsets (optional)
    """
    
    def setup_method(self):
        """Set up validator with K8s client."""
        self.logger = Logger()
        self.logger.info("Setting up K8s Resource Validator")
        
        # Load application configuration from environment
        self.namespace = os.getenv("APP_NAMESPACE", "default")
        self.resource_type = os.getenv("APP_RESOURCE_TYPE", "pod").lower()
        self.resource_name = os.getenv("APP_RESOURCE_NAME")
        self.label_selector = os.getenv("APP_LABEL_SELECTOR")
        self.expected_replicas = os.getenv("APP_EXPECTED_REPLICAS")
        
        if self.expected_replicas:
            self.expected_replicas = int(self.expected_replicas)
        
        self.client = K8sClient()
        
        self.logger.info(f"Validation config: namespace={self.namespace}, "
                        f"resource_type={self.resource_type}, "
                        f"resource_name={self.resource_name}, "
                        f"label_selector={self.label_selector}")
    
    def test_namespace_exists(self):
        """Test that the target namespace exists."""
        self.logger.info(f"Validating namespace: {self.namespace}")
        
        exists = self.client.namespace_exists(self.namespace)
        
        assert exists, f"Namespace '{self.namespace}' does not exist"
        
        self.logger.info(f"✓ Namespace '{self.namespace}' exists")
    
    def test_validate_pods(self):
        """Test pod validation in the namespace."""
        if self.resource_type != "pod":
            pytest.skip(f"Skipping pod validation (resource_type={self.resource_type})")
        
        self.logger.info(f"Validating pods in namespace: {self.namespace}")
        summary = self._validate_pods()
        
        self.logger.info(f"Pod validation summary: {summary.total} total, "
                        f"{summary.passed_count} passed, {summary.failed_count} failed")
        
        # Print detailed results
        for result in summary.results:
            status = "✓" if result.passed else "✗"
            print(f"{status} {result.resource_name}: {result.message}")
        
        # Assert at least one pod exists and is healthy
        assert summary.total > 0, f"No pods found in namespace '{self.namespace}'"
        assert summary.passed_count > 0, f"No healthy pods found in namespace '{self.namespace}'"
        
        self.logger.info("✓ Pod validation completed successfully")
    
    def test_validate_deployment(self):
        """Test deployment validation."""
        if self.resource_type != "deployment":
            pytest.skip(f"Skipping deployment validation (resource_type={self.resource_type})")
        
        if not self.resource_name:
            pytest.skip("K8S_VALIDATE_RESOURCE_NAME not set for deployment validation")
        
        self.logger.info(f"Validating deployment: {self.resource_name}")
        
        deployment = self.client.get_deployment(self.resource_name, self.namespace)
        
        assert deployment is not None, f"Deployment '{self.resource_name}' not found in namespace '{self.namespace}'"
        
        # Check replicas
        replicas = deployment["replicas"]
        ready_replicas = deployment["ready_replicas"]
        available_replicas = deployment["available_replicas"]
        
        self.logger.info(f"Deployment status: {ready_replicas}/{replicas} ready, "
                        f"{available_replicas}/{replicas} available")
        
        if self.expected_replicas:
            assert replicas == self.expected_replicas, \
                f"Expected {self.expected_replicas} replicas, found {replicas}"
        
        assert ready_replicas == replicas, \
            f"Not all replicas ready: {ready_replicas}/{replicas}"
        assert available_replicas == replicas, \
            f"Not all replicas available: {available_replicas}/{replicas}"
        
        # Check conditions
        for condition in deployment["conditions"]:
            if condition["type"] == "Available":
                assert condition["status"] == "True", \
                    f"Deployment not available: {condition.get('message', 'Unknown')}"
        
        print(f"\n✓ Deployment '{self.resource_name}' validation passed")
        print(f"  Replicas: {ready_replicas}/{replicas} ready")
        print(f"  Status: Available")
        
        self.logger.info("✓ Deployment validation completed successfully")
    
    def test_validate_statefulset(self):
        """Test statefulset validation."""
        if self.resource_type != "statefulset":
            pytest.skip(f"Skipping statefulset validation (resource_type={self.resource_type})")
        
        if not self.resource_name:
            pytest.skip("K8S_VALIDATE_RESOURCE_NAME not set for statefulset validation")
        
        self.logger.info(f"Validating statefulset: {self.resource_name}")
        
        sts = self.client.get_statefulset(self.resource_name, self.namespace)
        
        assert sts is not None, f"StatefulSet '{self.resource_name}' not found in namespace '{self.namespace}'"
        
        # Check replicas
        replicas = sts.spec.replicas
        ready_replicas = sts.status.ready_replicas or 0
        current_replicas = sts.status.current_replicas or 0
        
        self.logger.info(f"StatefulSet status: {ready_replicas}/{replicas} ready, "
                        f"{current_replicas}/{replicas} current")
        
        if self.expected_replicas:
            assert replicas == self.expected_replicas, \
                f"Expected {self.expected_replicas} replicas, found {replicas}"
        
        assert ready_replicas == replicas, \
            f"Not all replicas ready: {ready_replicas}/{replicas}"
        assert current_replicas == replicas, \
            f"Not all replicas current: {current_replicas}/{replicas}"
        
        print(f"\n✓ StatefulSet '{self.resource_name}' validation passed")
        print(f"  Replicas: {ready_replicas}/{replicas} ready")
        print(f"  Current: {current_replicas}/{replicas}")
        
        # Validate individual pods
        self.logger.info("Validating StatefulSet pods...")
        pod_summary = self._validate_pods()
        
        assert pod_summary.total == replicas, \
            f"Expected {replicas} pods, found {pod_summary.total}"
        assert pod_summary.passed_count == replicas, \
            f"Not all StatefulSet pods are healthy: {pod_summary.passed_count}/{replicas}"
        
        self.logger.info("✓ StatefulSet validation completed successfully")
    
    def test_validate_daemonset(self):
        """Test daemonset validation."""
        if self.resource_type != "daemonset":
            pytest.skip(f"Skipping daemonset validation (resource_type={self.resource_type})")
        
        if not self.resource_name:
            pytest.skip("K8S_VALIDATE_RESOURCE_NAME not set for daemonset validation")
        
        self.logger.info(f"Validating daemonset: {self.resource_name}")
        
        try:
            ds = self.client.apps_v1.read_namespaced_daemon_set(self.resource_name, self.namespace)
        except Exception as e:
            raise AssertionError(f"DaemonSet '{self.resource_name}' not found in namespace '{self.namespace}': {e}")
        
        # Check status
        desired = ds.status.desired_number_scheduled
        current = ds.status.current_number_scheduled or 0
        ready = ds.status.number_ready or 0
        available = ds.status.number_available or 0
        
        self.logger.info(f"DaemonSet status: {ready}/{desired} ready, "
                        f"{available}/{desired} available")
        
        assert current == desired, \
            f"Not all pods scheduled: {current}/{desired}"
        assert ready == desired, \
            f"Not all pods ready: {ready}/{desired}"
        assert available == desired, \
            f"Not all pods available: {available}/{desired}"
        
        print(f"\n✓ DaemonSet '{self.resource_name}' validation passed")
        print(f"  Desired: {desired}")
        print(f"  Ready: {ready}/{desired}")
        print(f"  Available: {available}/{desired}")
        
        self.logger.info("✓ DaemonSet validation completed successfully")
    
    def _validate_pods(self) -> ValidationSummary:
        """
        Internal method to validate pods in the namespace.
        
        :return: ValidationSummary with pod results
        """
        summary = ValidationSummary(name=f"Pod Validation - {self.namespace}")
        
        try:
            # Check namespace exists
            if not self.client.namespace_exists(self.namespace):
                self.logger.warning(f"Namespace does not exist: {self.namespace}")
                summary.add_result(ValidationResult(
                    passed=False,
                    resource_type="Namespace",
                    resource_name=self.namespace,
                    namespace=self.namespace,
                    message="Namespace does not exist"
                ))
                summary.complete()
                return summary
            
            # Get pods with optional label selector
            pods = self.client.get_pods_status(self.namespace, label_selector=self.label_selector)
            self.logger.info(f"Retrieved {len(pods)} pods from namespace: {self.namespace}")
            
            if not pods:
                self.logger.info(f"No pods found in namespace: {self.namespace}")
                summary.add_result(ValidationResult(
                    passed=True,
                    resource_type="Namespace",
                    resource_name=self.namespace,
                    namespace=self.namespace,
                    message="No pods found in namespace"
                ))
            else:
                # Filter by resource name if specified
                if self.resource_name:
                    if not pods:
                        summary.add_result(ValidationResult(
                            passed=False,
                            resource_type="Pod",
                            resource_name=self.resource_name,
                            namespace=self.namespace,
                            message=f"Pod '{self.resource_name}' not found"
                        ))
                        summary.complete()
                        return summary
                
                # Validate each pod
                for pod in pods:
                    passed = (
                        pod["phase"] in ["Running", "Succeeded"] and
                        (pod["ready"] or pod["phase"] == "Succeeded")
                    )
                    self.logger.debug(f"Validating pod: {pod['name']} - "
                                    f"Phase: {pod['phase']}, Ready: {pod['ready']}, "
                                    f"Restarts: {pod['restarts']}, Passed: {passed}")
                    summary.add_result(ValidationResult(
                        passed=passed,
                        resource_type="Pod",
                        resource_name=pod["name"],
                        namespace=self.namespace,
                        message=f"Phase: {pod['phase']}, Ready: {pod['ready']}, Restarts: {pod['restarts']}",
                        details=pod
                    ))
        except K8sClientError as e:
            self.logger.error(f"Error validating namespace {self.namespace}: {str(e)}")
            summary.add_result(ValidationResult(
                passed=False,
                resource_type="Namespace",
                resource_name=self.namespace,
                namespace=self.namespace,
                message=f"Error: {str(e)}"
            ))
        
        summary.complete()
        self.logger.info(f"Namespace {self.namespace} validation completed - "
                        f"Total: {summary.total}, Passed: {summary.passed_count}, "
                        f"Failed: {summary.failed_count}")
        return summary
