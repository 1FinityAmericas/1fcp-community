"""
ZooKeeper client for integration testing.
Executes all ZooKeeper operations inside existing ZooKeeper pods via kubectl exec.
All configuration loaded from APP_* environment variables (config/app.env).
"""
import os
from typing import Dict, List

from src.libs.common.k8s_client import K8sClient, K8sClientError as K8sError
from src.libs.common.logger import Logger


class ZooKeeperManagerError(Exception):
    pass


class ZooKeeperManager:

    def __init__(self):
        self.logger          = Logger()
        self.namespace       = os.getenv("APP_NAMESPACE", "default")
        self.replica_count   = int(os.getenv("APP_EXPECTED_REPLICAS", "3"))
        self.statefulset     = os.getenv("APP_RESOURCE_NAME", "zookeeper")
        self.port            = os.getenv("APP_PORT", "2181")
        self.container       = os.getenv("APP_CONTAINER_NAME", "zookeeper-server")
        self.k8s             = K8sClient()

        self.logger.info(
            f"ZooKeeperManager initialised | namespace={self.namespace} "
            f"replicas={self.replica_count}"
        )

    def _pod_name(self, index: int) -> str:
        """
        Build the pod name for a given StatefulSet index.

        Args:
            index (int): pod number (0-based)

        Returns:
            str: pod name e.g. 'zookeeper-0'
        """
        return f"{self.statefulset}-{index}"

    def _exec(self, pod_name: str, command: List[str], ignore_stderr: bool = False) -> str:
        """
        Execute a command inside the given ZooKeeper pod.

        Args:
            pod_name (str):      target pod name
            command (List[str]): command and arguments to run inside the pod

        Returns:
            str: stdout output of the command
        """
        try:
            stdout, stderr = self.k8s.exec_in_pod(
                pod_name=pod_name,
                namespace=self.namespace,
                command=command,
                container=self.container
            )
        except K8sError as e:
            raise ZooKeeperManagerError(str(e)) from e

        if not ignore_stderr and not stdout and stderr:
            raise ZooKeeperManagerError(
                f"Command failed on pod '{pod_name}': {stderr}"
            )

        return stdout

    def is_ready(self) -> bool:
        """
        Check if ZooKeeper is initialised and serving requests.

        Runs: echo srvr | nc localhost <port>

        Three failure states are handled explicitly:
          1. Pod not found / unreachable   → K8sError raised by _exec
          2. Port not open yet             → nc writes 'Ncat: Connection refused'
                                            to stderr, _exec raises on empty stdout
          3. ZooKeeper starting up         → stdout contains 'not currently serving
                                             requests' before ensemble is ready

        Returns:
            bool: True if ZooKeeper is serving requests
        """
        pod_name = self._pod_name(0)

        try:
            stdout = self._exec(pod_name, [
                "bash", "-c", f"echo srvr | nc localhost {self.port}"
            ])
        except ZooKeeperManagerError as e:
            # Covers: pod not found, Ncat: Connection refused
            raise ZooKeeperManagerError(
                f"ZooKeeper port not reachable on '{pod_name}': {e}"
            ) from e

        # ZooKeeper process is up but ensemble has not formed quorum yet
        if not stdout.strip() or "not currently serving requests" in stdout:
            raise ZooKeeperManagerError(
                f"ZooKeeper on '{pod_name}' is not yet serving requests"
            )

        return True

    def get_server_stats(self, pod_name: str) -> Dict[str, str]:
        """
        Fetch server stats from a ZooKeeper pod using the 'srvr' command.

        Runs: echo srvr | nc localhost <port>

        Args:
            pod_name (str): target ZooKeeper pod name

        Returns:
            Dict[str, str]: parsed key-value stats
        """
        stdout = self._exec(pod_name, ["bash", "-c", f"echo srvr | nc localhost {self.port}"])

        if not stdout.strip():
            raise ZooKeeperManagerError(
                f"'srvr' returned empty response from pod '{pod_name}'"
            )

        stats = {}
        for line in stdout.splitlines():
            line = line.strip()
            if not line or ":" not in line:
                continue
            key, _, value = line.partition(":")
            stats[key.strip().lower().replace(" ", "_")] = value.strip()

        if "mode" not in stats:
            raise ZooKeeperManagerError(
                f"'srvr' response from '{pod_name}' did not contain 'Mode' field. "
                f"Raw output:\n{stdout}"
            )

        return stats

    def list_root_znodes(self) -> List[str]:
        """
        List all znodes at the root of the ZooKeeper data tree.

        Runs: zookeeper-shell localhost:<port> ls /

        Returns:
            List[str]: znode names under '/', e.g. ['zookeeper', 'brokers', 'cluster']
        """
        pod_name = self._pod_name(0)

        # stderr is ignored — zookeeper-shell writes connection banners to stderr
        stdout = self._exec(
            pod_name,
            ["bash", "-c", f"zookeeper-shell localhost:{self.port} ls /"],
            ignore_stderr=True
        )

        data_line = None
        for line in stdout.splitlines():
            stripped = line.strip()
            if stripped.startswith("[") and stripped.endswith("]"):
                data_line = stripped
                break

        if data_line is None:
            raise ZooKeeperManagerError(
                f"'zookeeper-shell ls /' returned no znode list from '{pod_name}'. "
                f"Raw output:\n{stdout}"
            )

        # Parse '[admin, brokers, cluster]' -> ['admin', 'brokers', 'cluster']
        znodes = [z.strip() for z in data_line.strip("[]").split(",") if z.strip()]
        self.logger.info(f"Root znodes: {znodes}")
        return znodes
