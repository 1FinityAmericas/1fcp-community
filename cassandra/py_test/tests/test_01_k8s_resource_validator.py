"""
Generic Kubernetes resource validator tests.
Validates any K8s application (pods, deployments, statefulsets, daemonsets) deployed on the cluster.
This is a reusable test module - configure via environment variables to validate any app.
"""
import os
from typing import List, Dict, Any

import pytest

from src.libs.common.k8s_client import K8sClient, K8sClientError
from src.libs.common.logger import Logger
from src.models.validation_result import ValidationResult, ValidationSummary
from src.libs.cassandra.cassandra_connection import CassandraConnection


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
        self.namespace         = os.getenv("APP_NAMESPACE", "default")
        self.resource_type     = os.getenv("APP_RESOURCE_TYPE", "pod").lower()
        self.resource_name     = os.getenv("APP_RESOURCE_NAME")
        self.label_selector    = os.getenv("APP_LABEL_SELECTOR")
        self.expected_replicas = os.getenv("APP_EXPECTED_REPLICAS")

        if self.expected_replicas:
            self.expected_replicas = int(self.expected_replicas)

        self.client = K8sClient()

        self.logger.info(f"Validation config: namespace={self.namespace}, "
                         f"resource_type={self.resource_type}, "
                         f"resource_name={self.resource_name}, "
                         f"label_selector={self.label_selector}")

    

    def test_wait_for_cassandra_ready(self):
        """Wait for Cassandra StatefulSet and all pods to be fully ready before any validation."""
        if self.resource_type != "statefulset":
            pytest.skip(f"Skipping Cassandra readiness wait (resource_type={self.resource_type})")

        if not self.resource_name:
            pytest.skip("APP_RESOURCE_NAME not set — cannot wait for StatefulSet readiness")

        expected = self.expected_replicas or 1
        self.logger.info(
            f"Waiting for Cassandra StatefulSet '{self.resource_name}' "
            f"({expected} replicas) to be fully ready..."
        )
        self.client.wait_for_cassandra_ready(
            statefulset_name  = self.resource_name,
            namespace         = self.namespace,
            expected_replicas = expected,
            timeout           = 800,
            interval          = 100,
        )
        self.logger.info("✓ Cassandra resources are ready — proceeding with validation")

    

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

        for result in summary.results:
            status = "✓" if result.passed else "✗"
            print(f"{status} {result.resource_name}: {result.message}")

        assert summary.total > 0,        f"No pods found in namespace '{self.namespace}'"
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

        assert deployment is not None, \
            f"Deployment '{self.resource_name}' not found in namespace '{self.namespace}'"

        replicas           = deployment["replicas"]
        ready_replicas     = deployment["ready_replicas"]
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

        assert sts is not None, \
            f"StatefulSet '{self.resource_name}' not found in namespace '{self.namespace}'"

        replicas         = sts.spec.replicas
        ready_replicas   = sts.status.ready_replicas   or 0
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

        self.logger.info("Validating StatefulSet pods...")
        # Derive label selector from the StatefulSet's own spec so pods are
        # always found regardless of what APP_LABEL_SELECTOR is set to
        match_labels        = sts.spec.selector.match_labels
        original_selector   = self.label_selector
        self.label_selector = ",".join(f"{k}={v}" for k, v in match_labels.items())
        self.logger.info(f"Derived label selector from StatefulSet spec: {self.label_selector}")
        try:
            pod_summary = self._validate_pods()
        finally:
            self.label_selector = original_selector

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
            raise AssertionError(
                f"DaemonSet '{self.resource_name}' not found in namespace '{self.namespace}': {e}"
            )

        desired   = ds.status.desired_number_scheduled
        current   = ds.status.current_number_scheduled or 0
        ready     = ds.status.number_ready             or 0
        available = ds.status.number_available         or 0

        self.logger.info(f"DaemonSet status: {ready}/{desired} ready, "
                         f"{available}/{desired} available")

        assert current == desired,   f"Not all pods scheduled: {current}/{desired}"
        assert ready == desired,     f"Not all pods ready: {ready}/{desired}"
        assert available == desired, f"Not all pods available: {available}/{desired}"

        print(f"\n✓ DaemonSet '{self.resource_name}' validation passed")
        print(f"  Desired  : {desired}")
        print(f"  Ready    : {ready}/{desired}")
        print(f"  Available: {available}/{desired}")

        self.logger.info("✓ DaemonSet validation completed successfully")

    # ==================== Cassandra-specific K8s checks ====================

    def test_cassandra_node_status(self):
        """Validate Cassandra node health via nodetool status and keyspace config."""
        if self.resource_type != "statefulset":
            pytest.skip(f"Skipping Cassandra node status (resource_type={self.resource_type})")

        conn = CassandraConnection()
        self.logger.info("--- Cassandra Node Status Validation ---")

        # --- nodetool status ---
        self.logger.info("Fetching nodetool status...")
        status = conn.get_nodetool_status()

        assert status is not None,  "get_nodetool_status() returned None"
        assert "set"   in status,   "nodetool status missing 'set' key"
        assert "nodes" in status,   "nodetool status missing 'nodes' key"

        nodes = status.get("nodes", [])
        self.logger.info(f"StatefulSet : {status.get('set')}")
        self.logger.info(f"Node count  : {len(nodes)} (expected: {conn.replica_count})")

        assert len(nodes) == conn.replica_count, \
            f"Expected {conn.replica_count} nodes, found {len(nodes)}"

        for node in nodes:
            self.logger.info(
                f"  Node {node.get('address')} → "
                f"status={node.get('status')} rack={node.get('rack')}"
            )

        # --- keyspace config ---
        self.logger.info("Fetching keyspace configuration...")
        config    = conn.get_keyspace_config()
        keyspaces = config.get("keyspaces", [])

        assert config is not None,    "get_keyspace_config() returned None"
        assert "keyspaces" in config, "keyspace config missing 'keyspaces' key"
        assert len(keyspaces) > 0,    "Expected at least 1 keyspace, found 0"

        self.logger.info(f"Keyspace count : {config.get('count')}")
        self.logger.info(f"Keyspaces      : {keyspaces}")

        # --- node health ---
        self.logger.info("Validating node health (UN = Up/Normal)...")
        node_health     = conn.validate_cluster_nodes()
        unhealthy_nodes = [addr for addr, healthy in node_health.items() if not healthy]

        assert len(node_health) == conn.replica_count, \
            f"Expected {conn.replica_count} node(s) in health map, found {len(node_health)}"

        for addr, healthy in node_health.items():
            icon = "✓" if healthy else "✗"
            self.logger.info(f"  {icon} {addr}: {'Healthy (UN)' if healthy else 'Unhealthy'}")

        assert len(unhealthy_nodes) == 0, \
            f"Unhealthy nodes found: {unhealthy_nodes}"

        self.logger.info(f"All {len(node_health)} node(s) are healthy (UN)")
        self.logger.info("--- Cassandra Node Status Validation Complete ---")

    # ==================== Internal helpers ====================

    def _validate_pods(self) -> ValidationSummary:
        """Internal method to validate pods in the namespace."""
        summary = ValidationSummary(name=f"Pod Validation - {self.namespace}")

        try:
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

            pods = self.client.get_pods_status(self.namespace, label_selector=self.label_selector)
            self.logger.info(f"Retrieved {len(pods)} pods from namespace: {self.namespace}")

            if not pods:
                summary.add_result(ValidationResult(
                    passed=True,
                    resource_type="Namespace",
                    resource_name=self.namespace,
                    namespace=self.namespace,
                    message="No pods found in namespace"
                ))
            else:
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
                        message=f"Phase: {pod['phase']}, Ready: {pod['ready']}, "
                                f"Restarts: {pod['restarts']}",
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
