"""
Integration tests for Apache Cassandra — application level only.
Tests validation against actual Kubernetes cluster.
Requires a running K8s cluster with valid kubeconfig and Cassandra StatefulSet.

All pod connectivity and exec calls go through K8sClient.exec_in_pod.

Run:
  pytest tests/test_02_cassandra_validator.py --html=report.html --self-contained-html -s
"""
import os
from pathlib import Path

import yaml

from src.libs.cassandra.cassandra_connection import CassandraConnection, CassandraManagerError
from src.libs.common.k8s_client import K8sClientError as K8sError
from src.libs.common.logger import Logger


_files_dir    = Path(__file__).parent.parent / "files"
_POD_MANIFEST = _files_dir / "cassandra_client.yaml"
_POD_NAME     = os.getenv("APP_CASSANDRA_CLIENT_POD", "cassandra-client")


class TestCassandraAuthentication:
    """Test Cassandra authentication and connection."""

    def setup_method(self):
        self.logger = Logger()
        self.conn   = CassandraConnection()

    def teardown_method(self):
        """Delete the cassandra-client pod after all tests in this class complete."""
        self.conn.k8s.delete_pod(_POD_NAME, self.conn.namespace)
        self.conn.close()

    def test_deploy_client_pod(self):
        """Deploy the cassandra-client pod and verify it becomes Ready."""
        with open(_POD_MANIFEST) as f:
            manifest = yaml.safe_load(f)

        result = self.conn.cassandra_client_pod(manifest=manifest, pod_name=_POD_NAME)

        assert result is True, "cassandra_client_pod() should return True when pod is Ready"

    def test_connect_to_cassandra(self):
        """Connect to the default Cassandra pod via exec_in_pod."""
        self.logger.info("Testing connection to Cassandra")

        result = self.conn.connect()

        assert result is True, "connect() should return True on success"
        assert self.conn.pod_name is not None, "pod_name must be set after connect()"

        self.logger.info(f"Successfully connected via pod '{self.conn.pod_name}'")

    def test_authentication_success(self):
        """Authenticate with correct credentials and verify system.local query."""
        self.logger.info("Testing Cassandra authentication")

        self.conn.connect()
        result = self.conn.test_authentication()

        assert result is True, "Authentication should succeed with correct credentials"

        self.logger.info("Cassandra authentication successful")


class TestCassandraOperations:
    """Test Cassandra CRUD operations replicated across all StatefulSet pods."""

    def setup_method(self):
        self.logger        = Logger()
        self.conn          = CassandraConnection()
        self.test_keyspace = "pytest_test_ks"
        self.test_table    = "pytest_test_table"

        # Build pod list from replica count
        self.pod_names = [
            f"{self.conn.statefulset_name}-{i}"
            for i in range(self.conn.replica_count)
        ]

        # Establish connection and create shared keyspace + table once per test
        self.conn.connect()
        self.conn._cqlsh(
            f"CREATE KEYSPACE IF NOT EXISTS {self.test_keyspace} "
            f"WITH replication = {{'class': 'NetworkTopologyStrategy', "
            f"'replication_factor': {self.conn.replica_count}}}; "
            f"CREATE TABLE IF NOT EXISTS {self.test_keyspace}.{self.test_table} "
            f"(id int PRIMARY KEY, name text, value text);"
        )
        self.logger.info(
            f"Test keyspace and table ready: "
            f"{self.test_keyspace}.{self.test_table}"
        )

    def teardown_method(self):
        """Drop the test keyspace after every test to keep the cluster clean."""
        if self.conn:
            try:
                self.conn._cqlsh(f"DROP KEYSPACE IF EXISTS {self.test_keyspace};")
                self.logger.info(f"Cleaned up test keyspace: {self.test_keyspace}")
            except CassandraManagerError as e:
                self.logger.warning(f"Failed to clean up test keyspace: {e}")
            finally:
                self.conn.close()

    def test_insert_and_query(self):
        """Insert rows via cassandra-0 and verify replication on all pods."""
        self.logger.info("Testing insert on cassandra-0 and query across all pods")

        self.conn.pod_name = self.pod_names[0]
        test_docs = [
            {"id": 1, "name": f"{self.conn.statefulset_name}-0", "value": "test_value_1"},
            {"id": 2, "name": f"{self.conn.statefulset_name}-0", "value": "test_value_2"},
            {"id": 3, "name": f"{self.conn.statefulset_name}-0", "value": "test_value_3"},
        ]

        for doc in test_docs:
            self.conn._cqlsh(
                f"INSERT INTO {self.test_keyspace}.{self.test_table} "
                f"(id, name, value) VALUES "
                f"({doc['id']}, '{doc['name']}', '{doc['value']}');"
            )
        self.logger.info(f"Inserted {len(test_docs)} rows via {self.pod_names[0]}")

        for pod_name in self.pod_names:
            self.conn.pod_name = pod_name
            output    = self.conn._cqlsh(
                f"SELECT * FROM {self.test_keyspace}.{self.test_table};"
            )
            row_count = output.count("test_value_")
            assert row_count == len(test_docs), (
                f"Expected {len(test_docs)} rows on {pod_name}, found {row_count}"
            )
            self.logger.info(f"Query from {pod_name}: {row_count} rows confirmed")

        self.conn.pod_name = self.pod_names[0]

        print(f"\nCassandra Insert + Replication Test:")
        print(f"  Write pod: {self.pod_names[0]}")
        print(f"  Inserted : {len(test_docs)} rows")
        for pod_name in self.pod_names:
            print(f"  Read pod : {pod_name} → {len(test_docs)} rows confirmed")

    def test_update_operation(self):
        """Update a row via cassandra-0 and verify the new value on all pods."""
        self.logger.info("Testing update on cassandra-0 and verify from all pods")

        self.conn.pod_name = self.pod_names[0]
        self.conn._cqlsh(
            f"INSERT INTO {self.test_keyspace}.{self.test_table} "
            f"(id, name, value) VALUES (10, 'test', '100');"
        )
        self.conn._cqlsh(
            f"UPDATE {self.test_keyspace}.{self.test_table} "
            f"SET value='200' WHERE id=10;"
        )

        for pod_name in self.pod_names:
            self.conn.pod_name = pod_name
            output = self.conn._cqlsh(
                f"SELECT * FROM {self.test_keyspace}.{self.test_table} WHERE id=10;"
            )
            assert "200" in output, (
                f"Updated value '200' not found on {pod_name}: {output}"
            )
            assert "100" not in output, (
                f"Old value '100' should not be present on {pod_name}: {output}"
            )
            self.logger.info(f"Update verified on {pod_name}")

        self.conn.pod_name = self.pod_names[0]

        print(f"\nUpdated Row (id=10):")
        print(f"  Write pod : {self.pod_names[0]}")
        for pod_name in self.pod_names:
            print(f"  Read pod  : {pod_name} → new value '200' confirmed ✓")

    def test_delete_operation(self):
        """Delete rows via cassandra-0 and verify deletion on all pods."""
        self.logger.info("Testing delete on cassandra-0 and verify from all pods")

        self.conn.pod_name = self.pod_names[0]
        for i in range(5):
            self.conn._cqlsh(
                f"INSERT INTO {self.test_keyspace}.{self.test_table} "
                f"(id, name, value) VALUES ({i}, 'name_{i}', 'val_{i}');"
            )

        # Single-row delete
        self.conn._cqlsh(
            f"DELETE FROM {self.test_keyspace}.{self.test_table} WHERE id=0;"
        )

        for pod_name in self.pod_names:
            self.conn.pod_name = pod_name
            output = self.conn._cqlsh(
                f"SELECT * FROM {self.test_keyspace}.{self.test_table} WHERE id=0;"
            )
            assert "name_0" not in output, (
                f"Row id=0 should be deleted but still found on {pod_name}: {output}"
            )
            self.logger.info(f"Deletion of id=0 confirmed on {pod_name}")

        # Multi-row delete
        self.conn.pod_name = self.pod_names[0]
        self.conn._cqlsh(
            f"DELETE FROM {self.test_keyspace}.{self.test_table} WHERE id IN (1, 2);"
        )

        for pod_name in self.pod_names:
            self.conn.pod_name = pod_name
            output    = self.conn._cqlsh(
                f"SELECT * FROM {self.test_keyspace}.{self.test_table};"
            )
            remaining = output.count("name_")
            assert remaining == 2, (
                f"Expected 2 rows on {pod_name}, found {remaining}. Output: {output}"
            )
            self.logger.info(f"Remaining row count on {pod_name}: {remaining}")

        self.conn.pod_name = self.pod_names[0]

        print(f"\nDelete Operations:")
        print(f"  Write pod       : {self.pod_names[0]}")
        print(f"  Deleted single  : 1 row  (id=0)")
        print(f"  Deleted multiple: 2 rows (id=1, id=2)")
        for pod_name in self.pod_names:
            print(f"  Read pod        : {pod_name} → 2 rows remaining confirmed ✓")


class TestCassandraIndividualPods:
    """Test connectivity and authentication to each Cassandra pod individually."""

    def setup_method(self):
        self.logger = Logger()
        self.conn   = CassandraConnection()

        self.pod_names = [
            f"{self.conn.statefulset_name}-{i}"
            for i in range(self.conn.replica_count)
        ]

    def teardown_method(self):
        if self.conn:
            self.conn.close()

    def test_connect_to_individual_pods(self):
        """Connect to each Cassandra pod via exec_in_pod and verify authentication."""
        for pod_name in self.pod_names:
            self.logger.info(f"Testing connection to {pod_name}")

            result = self.conn.connect(pod_name=pod_name)
            assert result is True, f"connect() should return True for {pod_name}"

            auth = self.conn.test_authentication()
            assert auth is True, f"Authentication should succeed on {pod_name}"

            self.logger.info(f"Successfully connected and authenticated on {pod_name}")
            print(f"\n{pod_name}: Connected and authenticated ✓")

            self.conn.close()


class TestCassandraClientPodReplication:
    """
    Deploy the cassandra-client pod, exec into it to create a keyspace/table
    and insert rows via the Cassandra service, then verify the data has
    replicated to every Cassandra StatefulSet pod.
    """

    _TEST_KEYSPACE = "pytest_client_ks"
    _TEST_TABLE    = "pytest_client_table"

    def setup_method(self):
        self.logger = Logger()
        self.conn   = CassandraConnection()

        self.pod_names = [
            f"{self.conn.statefulset_name}-{i}"
            for i in range(self.conn.replica_count)
        ]

        # Deploy the cassandra-client pod fresh for this test class
        with open(_POD_MANIFEST) as f:
            manifest = yaml.safe_load(f)

        self.conn.cassandra_client_pod(manifest=manifest, pod_name=_POD_NAME)
        self.logger.info(f"cassandra-client pod '{_POD_NAME}' is Ready")

    def teardown_method(self):
        """Drop the test keyspace and delete the client pod after every test."""
        if self.conn:
            try:
                self.conn._cqlsh(f"DROP KEYSPACE IF EXISTS {self._TEST_KEYSPACE};")
                self.logger.info(f"Dropped keyspace: {self._TEST_KEYSPACE}")
            except CassandraManagerError as e:
                self.logger.warning(f"Failed to drop test keyspace: {e}")
            finally:
                self.conn.k8s.delete_pod(_POD_NAME, self.conn.namespace)
                self.logger.info(f"cassandra-client pod '{_POD_NAME}' deleted")
                self.conn.close()

    def _exec_in_client_pod(self, cql: str) -> str:
        """
        Run a CQL statement by exec-ing into the cassandra-client pod.
        Uses K8sClient.exec_in_pod directly since the client pod is separate
        from the Cassandra StatefulSet pods that _cqlsh targets.

        Args:
            cql: CQL statement to execute.

        Returns:
            Combined stdout + stderr output (stripped).

        Raises:
            CassandraManagerError: if the exec fails.
        """
        command = [
            "cqlsh",
            f"{self.conn.service_name}.{self.conn.namespace}.svc.cluster.local",
            str(self.conn.port),
            "-u", self.conn.user,
            "-p", self.conn.password,
            "-e", cql,
        ]
        try:
            stdout, stderr = self.conn.k8s.exec_in_pod(
                pod_name=_POD_NAME,
                namespace=self.conn.namespace,
                command=command,
            )
            return "\n".join(s for s in [stdout, stderr] if s).strip()
        except K8sError as e:
            raise CassandraManagerError(
                f"exec into client pod '{_POD_NAME}' failed: {e}"
            ) from e

    def test_client_pod_write_replicates_to_all_pods(self):
        """
        Exec into the cassandra-client pod to create a keyspace, table and
        insert rows via the Cassandra headless service. Then verify every
        Cassandra StatefulSet pod has the data by querying each one directly.
        """
        self.logger.info("Creating keyspace and table via cassandra-client pod")

        self._exec_in_client_pod(
            f"CREATE KEYSPACE IF NOT EXISTS {self._TEST_KEYSPACE} "
            f"WITH replication = {{'class': 'NetworkTopologyStrategy', "
            f"'replication_factor': {self.conn.replica_count}}};"
        )
        self._exec_in_client_pod(
            f"CREATE TABLE IF NOT EXISTS {self._TEST_KEYSPACE}.{self._TEST_TABLE} "
            f"(id int PRIMARY KEY, name text, value text);"
        )

        test_rows = [
            {"id": 1, "name": "client_row_1", "value": "value_1"},
            {"id": 2, "name": "client_row_2", "value": "value_2"},
            {"id": 3, "name": "client_row_3", "value": "value_3"},
        ]

        for row in test_rows:
            self._exec_in_client_pod(
                f"INSERT INTO {self._TEST_KEYSPACE}.{self._TEST_TABLE} "
                f"(id, name, value) VALUES ({row['id']}, '{row['name']}', '{row['value']}');"
            )
        self.logger.info(f"Inserted {len(test_rows)} rows via cassandra-client pod '{_POD_NAME}'")

        # Verify every Cassandra pod has all rows
        for pod_name in self.pod_names:
            self.conn.pod_name = pod_name
            output    = self.conn._cqlsh(
                f"SELECT * FROM {self._TEST_KEYSPACE}.{self._TEST_TABLE};"
            )
            for row in test_rows:
                assert row["name"] in output, (
                    f"Row '{row['name']}' not found on {pod_name} after client-pod insert"
                )
            row_count = output.count("client_row_")
            assert row_count == len(test_rows), (
                f"Expected {len(test_rows)} rows on {pod_name}, found {row_count}"
            )
            self.logger.info(f"Replication confirmed on {pod_name}: {row_count} rows")

        print(f"\nClient Pod Replication Test:")
        print(f"  Write pod : {_POD_NAME} (cassandra-client via service)")
        print(f"  Rows      : {len(test_rows)}")
        for pod_name in self.pod_names:
            print(f"  Read pod  : {pod_name} -> {len(test_rows)} rows confirmed ✓")
