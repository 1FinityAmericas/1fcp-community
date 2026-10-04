"""
Cassandra Connection Manager for integration testing.
Executes Cassandra operations inside the cassandra pod.
- cqlsh commands: via subprocess kubectl exec (reliable for slow interactive tool)
- nodetool / pod readiness: via K8sClient.exec_in_pod
All configuration loaded from APP_* environment variables (config/app.env).
"""
import os
import re
import subprocess
from typing import Dict, List, Optional

from src.libs.common.k8s_client import K8sClient, K8sClientError as K8sError
from src.libs.common.logger import Logger


class CassandraManagerError(Exception):
    """Raised when a Cassandra pod exec command fails."""
    pass


class CassandraConnection:
    """
    Manages Cassandra operations for integration testing.
    cqlsh is executed via subprocess kubectl exec because the kubernetes-client
    stream reader times out before cqlsh finishes returning multi-line output.
    nodetool and pod-readiness checks use K8sClient.exec_in_pod directly.
    """

    def __init__(self):
        self.logger = Logger()

        # Load all configuration from APP_* variables
        self.namespace        = os.getenv("APP_NAMESPACE", "default")
        self.statefulset_name = os.getenv("APP_RESOURCE_NAME", "cassandra")
        self.replica_count    = int(os.getenv("APP_EXPECTED_REPLICAS", "1"))
        self.service_name     = os.getenv("APP_SERVICE_NAME", "cassandra-headless")
        self.port             = int(os.getenv("APP_PORT", "9042"))
        self.user             = os.getenv("APP_USER", "cassandra")
        self.password         = os.getenv("APP_PASSWORD", "cassandra")
        self.keyspace         = os.getenv("APP_KEYSPACE", "system")
        self.datacenter       = os.getenv("APP_DATACENTER", "dc1")
        self.test_keyspace    = os.getenv("APP_TEST_KEYSPACE", "pytest_ks")
        self.test_table       = os.getenv("APP_TEST_TABLE", "pytest_table")

        # K8s client — used for pod readiness, exec, and pod lifecycle
        self.k8s      = K8sClient()
        self.pod_name = f"{self.statefulset_name}-0"

        # Kubeconfig path — expand both ~ and $HOME/$KUBECONFIG env vars
        kubeconfig_raw  = os.getenv("KUBECONFIG", "~/.kube/config")
        self.kubeconfig = os.path.expandvars(os.path.expanduser(kubeconfig_raw))

        self.logger.info(
            f"CassandraConnection initialized | namespace={self.namespace} "
            f"| pod={self.pod_name}"
        )

    

    def _exec(self, command: List[str]) -> tuple:
        """
        Execute a command inside the active Cassandra pod via K8sClient.exec_in_pod.
        Suitable for fast commands (nodetool, etc.) that return output quickly.

        Args:
            command: Command and arguments to run inside the pod.

        Returns:
            Tuple of (stdout, stderr) both stripped.

        Raises:
            CassandraManagerError: if exec_in_pod raises K8sError.
        """
        try:
            return self.k8s.exec_in_pod(
                pod_name=self.pod_name,
                namespace=self.namespace,
                command=command,
            )
        except K8sError as e:
            raise CassandraManagerError(str(e)) from e

    def _cqlsh(self, cql: str) -> str:
        """
        Run a CQL statement via cqlsh inside the active Cassandra pod.

        Uses subprocess kubectl exec instead of K8sClient.exec_in_pod because
        cqlsh is a slow interactive tool — the kubernetes-client stream reader
        times out at 1s and returns partial output before cqlsh finishes.
        subprocess.run() waits for the process to fully complete.

        Args:
            cql: CQL query string to execute.

        Returns:
            Combined stdout + stderr output from cqlsh (stripped).

        Raises:
            CassandraManagerError: if the kubectl exec command fails.
        """
        cmd = [
            "kubectl",
            "--kubeconfig", self.kubeconfig,
            "exec", "-n", self.namespace, self.pod_name,
            "--",
            "cqlsh",
            "-u", self.user,
            "-p", self.password,
            "-e", cql,
        ]
        self.logger.debug(f"cqlsh exec on pod '{self.pod_name}': {cql[:80]}")
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
                env=os.environ.copy(),
            )
        except subprocess.TimeoutExpired as e:
            raise CassandraManagerError(f"cqlsh timed out on pod '{self.pod_name}': {e}") from e
        except Exception as e:
            raise CassandraManagerError(f"kubectl exec failed: {e}") from e

        # Combine stdout and stderr — cqlsh may use either depending on version
        output = "\n".join(s for s in [proc.stdout, proc.stderr] if s).strip()

        if proc.returncode != 0 and not proc.stdout:
            raise CassandraManagerError(
                f"cqlsh failed on pod '{self.pod_name}' (rc={proc.returncode}): {output}"
            )

        return output

    
    def is_node_ready(self) -> bool:
        """
        Check if the Cassandra node is reachable and accepting CQL connections.

        Returns:
            True if the node responds to a simple CQL probe.
        """
        try:
            self.connect()
            return True
        except CassandraManagerError:
            return False

    def connect(self, pod_name: Optional[str] = None) -> bool:
        """
        Verify Cassandra connectivity by running a lightweight CQL probe
        inside the target pod via cqlsh.

        Args:
            pod_name: Override the active pod (e.g. 'cassandra-1').
                      Updates self.pod_name for subsequent calls.

        Returns:
            True if the probe succeeds.

        Raises:
            CassandraManagerError: if the probe fails.
        """
        if pod_name:
            self.pod_name = pod_name

        self.logger.info(f"Connecting to Cassandra via pod: {self.pod_name}")

        try:
            self._cqlsh("SELECT release_version FROM system.local;")
            self.logger.info(f"Successfully connected via pod '{self.pod_name}'")
            return True
        except CassandraManagerError as e:
            self.logger.error(f"Failed to connect via pod '{self.pod_name}': {e}")
            raise

    

    def test_authentication(self) -> bool:
        """
        Test Cassandra authentication by querying system.local.
        Returns True only when the output contains 'release_version',
        confirming both auth and query execution succeeded.

        Returns:
            True if authentication is successful.
        """
        try:
            output  = self._cqlsh("SELECT release_version FROM system.local;")
            success = "release_version" in output.lower()
            self.logger.info(f"Authentication {'successful' if success else 'failed'}")
            return success
        except CassandraManagerError as e:
            self.logger.error(f"Authentication failed: {e}")
            return False

    

    def get_nodetool_status(self) -> Dict:
        """
        Run 'nodetool status' inside the pod and parse the output.

        Returns:
            Dict with keys 'set', 'nodes' (list of per-node dicts), 'up_normal' (count).

        Raises:
            CassandraManagerError: if nodetool fails.
        """
        stdout, stderr = self._exec(["nodetool", "status"])
        output = "\n".join(s for s in [stdout, stderr] if s).strip()

        nodes = []
        for line in output.splitlines():
            match = re.match(
                r"^([A-Z]{2})\s+(\S+)\s+(\S+\s+\S+)\s+(\S+)\s+(\S+)\s+(\S+)\s+(\S+)",
                line.strip(),
            )
            if match:
                nodes.append({
                    "status":  match.group(1),
                    "address": match.group(2),
                    "load":    match.group(3),
                    "tokens":  match.group(4),
                    "owns":    match.group(5),
                    "host_id": match.group(6),
                    "rack":    match.group(7),
                })

        up_normal = sum(1 for n in nodes if n["status"] == "UN")
        self.logger.info(f"nodetool status retrieved | up_normal={up_normal}/{len(nodes)}")
        return {
            "set":       self.statefulset_name,
            "nodes":     nodes,
            "up_normal": up_normal,
        }

    def validate_cluster_nodes(self) -> Dict[str, bool]:
        """
        Validate all Cassandra nodes are in Up/Normal (UN) state.

        Returns:
            Dict mapping node address -> True if UN, False otherwise.

        Raises:
            CassandraManagerError: if nodetool fails.
        """
        status = self.get_nodetool_status()
        nodes  = status.get("nodes", [])

        results = {}
        for node in nodes:
            address    = node.get("address", "unknown")
            state      = node.get("status", "UNKNOWN")
            is_healthy = state == "UN"
            results[address] = is_healthy
            self.logger.info(f"{'✓' if is_healthy else '✗'} Node {address}: {state}")

        return results

    def get_keyspace_config(self) -> Dict:
        """
        List all keyspaces visible to this node.

        Returns:
            Dict with 'keyspaces' (list of str) and 'count' (int).

        Raises:
            CassandraManagerError: if cqlsh fails.
        """
        output    = self._cqlsh("DESCRIBE KEYSPACES;")
        keyspaces = output.strip().split()
        self.logger.info(f"Retrieved {len(keyspaces)} keyspaces")
        return {
            "keyspaces": keyspaces,
            "count":     len(keyspaces),
        }

    
    def test_write_operation(
        self,
        test_keyspace: str = "pytest_ks",
        test_table: str    = "pytest_table",
    ) -> bool:
        """
        Create a keyspace/table if absent, insert a test row,
        verify it landed, then clean up.

        Returns:
            True if write + verify succeeded.
        """
        try:
            self._cqlsh(
                f"CREATE KEYSPACE IF NOT EXISTS {test_keyspace} "
                f"WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}; "
                f"CREATE TABLE IF NOT EXISTS {test_keyspace}.{test_table} "
                f"(id int PRIMARY KEY, name text, value text);"
            )
            self._cqlsh(
                f"INSERT INTO {test_keyspace}.{test_table} "
                f"(id, name, value) VALUES (99, 'test_name', 'test_value');"
            )
            output = self._cqlsh(
                f"SELECT * FROM {test_keyspace}.{test_table} WHERE id=99;"
            )
            if "test_name" not in output:
                self.logger.error("Write verification failed: row not found after insert")
                return False

            self.logger.info(f"Write operation successful — id=99 in {test_keyspace}.{test_table}")
            self._cqlsh(f"DELETE FROM {test_keyspace}.{test_table} WHERE id=99;")
            self.logger.info("Test row cleaned up")
            return True

        except CassandraManagerError as e:
            self.logger.error(f"Write operation failed: {e}")
            return False

    def test_read_operation(
        self,
        test_keyspace: str = "pytest_ks",
        test_table: str    = "pytest_table",
    ) -> bool:
        """
        Insert a test row then read it back to confirm read path works.

        Returns:
            True if read returned the expected value.
        """
        try:
            self._cqlsh(
                f"CREATE KEYSPACE IF NOT EXISTS {test_keyspace} "
                f"WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}; "
                f"CREATE TABLE IF NOT EXISTS {test_keyspace}.{test_table} "
                f"(id int PRIMARY KEY, name text, value text);"
            )
            self._cqlsh(
                f"INSERT INTO {test_keyspace}.{test_table} "
                f"(id, name, value) VALUES (98, 'read_name', 'read_value');"
            )
            output = self._cqlsh(
                f"SELECT * FROM {test_keyspace}.{test_table} WHERE id=98;"
            )
            if "read_value" not in output:
                self.logger.error("Read operation failed: expected value not found")
                return False

            self.logger.info("Read operation successful")
            self._cqlsh(f"DELETE FROM {test_keyspace}.{test_table} WHERE id=98;")
            return True

        except CassandraManagerError as e:
            self.logger.error(f"Read operation failed: {e}")
            return False

    
    def cassandra_client_pod(self, manifest: dict, pod_name: str, max_retries: int = 2) -> bool:
        """
        Deploy the cassandra-client pod and wait for it to become Ready.
        Checks for an existing pod first using K8sClient.list_pods, deletes it,
        then deploys fresh. Retries up to max_retries times on failure.

        Uses:
            K8sClient.list_pods   — to check for an existing pod by name
            K8sClient.delete_pod  — to remove a stale pod before deployment
            K8sClient.create_pod  — to create the pod from the manifest
            K8sClient.wait_for_pod_ready — to poll until Running and Ready

        Args:
            manifest:    Parsed YAML manifest dict for the client pod.
            pod_name:    Name of the pod to deploy.
            max_retries: Number of additional attempts after the first (default 2).

        Returns:
            True when the pod is Ready.

        Raises:
            CassandraManagerError: if the pod fails to become Ready after all attempts.
        """
        total_attempts = max_retries + 1

        # Use list_pods to check whether the pod already exists, then delete it
        try:
            existing = self.k8s.list_pods(self.namespace)
            pod_names = [p.metadata.name for p in existing.items]
            if pod_name in pod_names:
                self.logger.info(f"Found existing pod '{pod_name}' — deleting before deployment")
                self.k8s.delete_pod(pod_name, self.namespace)
        except K8sError as e:
            raise CassandraManagerError(f"Failed to check existing pods: {e}") from e

        last_error = None
        for attempt in range(1, total_attempts + 1):
            try:
                self.logger.info(f"Deploying '{pod_name}' (attempt {attempt}/{total_attempts})")
                self.k8s.create_pod(manifest, self.namespace)
                self.k8s.wait_for_pod_ready(pod_name, self.namespace)
                self.logger.info(f"Pod '{pod_name}' is Ready")
                last_error = None
                break
            except Exception as e:
                last_error = e
                self.logger.warning(f"Attempt {attempt} failed: {e}")
                self.k8s.delete_pod(pod_name, self.namespace)

        if last_error:
            raise CassandraManagerError(
                f"Pod '{pod_name}' failed to become Ready after {total_attempts} attempts: "
                f"{last_error}"
            )

        return True

    

    def close(self):
        """No-op — exec_in_pod is stateless. Kept for API compatibility."""
        self.logger.info("CassandraConnection closed")
