"""
Integration tests for Apache ZooKeeper — application level only.
Tests run against an actual Kubernetes cluster with a live ZooKeeper deployment.
"""
import pytest
import time

from src.libs.common.logger import Logger
from src.libs.zookeeper.zookeeper_manager import ZooKeeperManager, ZooKeeperManagerError

class TestZooKeeperReadiness:
    """
    Verify that ZooKeeper is fully initialised and serving requests before
    any other tests run.
    """

    _RETRIES  = 5
    _INTERVAL = 20

    def setup_method(self):
        self.logger    = Logger()
        self.zookeeper = ZooKeeperManager()

    def test_zookeeper_is_ready(self):
        """Test that ZooKeeper is initialised and serving requests."""
        last_error = None
        time.sleep(10)

        for attempt in range(1, self._RETRIES + 1):
            try:
                self.zookeeper.is_ready()
                self.logger.info("ZooKeeper is ready")
                return
            except ZooKeeperManagerError as e:
                last_error = e
                self.logger.warning(
                    f"ZooKeeper not ready (attempt {attempt}/{self._RETRIES}), "
                    f"retrying in {self._INTERVAL}s... | error={e}"
                )
                if attempt < self._RETRIES:
                    time.sleep(self._INTERVAL)

        pytest.exit(
            f"ZooKeeper not ready after {self._RETRIES} attempts. "
            f"Last error: {last_error}"
        )

class TestZooKeeperHealth:
    """
    Validate that every ZooKeeper pod in the ensemble is alive and the
    ensemble has formed a valid quorum with exactly one leader.
    """

    def setup_method(self):
        self.logger    = Logger()
        self.zookeeper = ZooKeeperManager()

    def test_all_pods_healthy(self):
        """Test that all ZooKeeper pods are responsive and quorum is formed."""
        replica_count = self.zookeeper.replica_count
        self.logger.info(f"Checking {replica_count} ZooKeeper pods")

        leaders   = []
        followers = []
        failures  = []

        for i in range(replica_count):
            pod_name = self.zookeeper._pod_name(i)
            try:
                stats = self.zookeeper.get_server_stats(pod_name)
                mode  = stats["mode"]

                self.logger.info(
                    f"  {pod_name} | mode={mode} "
                    f"connections={stats.get('connections', 'N/A')} "
                    f"outstanding={stats.get('outstanding', 'N/A')} "
                    f"node_count={stats.get('node_count', 'N/A')}"
                )

                if mode == "leader":
                    leaders.append(pod_name)
                elif mode == "follower":
                    followers.append(pod_name)
                else:
                    failures.append(f"{pod_name}: unexpected mode '{mode}'")

            except ZooKeeperManagerError as e:
                failures.append(f"{pod_name}: {e}")

        # All pods must have responded
        assert not failures, (
            f"One or more ZooKeeper pods failed to respond:\n"
            + "\n".join(failures)
        )

        # Exactly one leader must exist — no leader means election failed
        assert len(leaders) == 1, (
            f"Expected exactly 1 leader across the ensemble, "
            f"found {len(leaders)}: {leaders}"
        )

        # Remaining pods must all be followers
        assert len(followers) == replica_count - 1, (
            f"Expected {replica_count - 1} followers, "
            f"found {len(followers)}: {followers}"
        )

        self.logger.info("------- ZooKeeper Quorum Summary -------")
        self.logger.info(f"  Ensemble size : {replica_count}")
        self.logger.info(f"  Quorum formed : YES  ({replica_count // 2 + 1} votes needed, {replica_count} available)")
        self.logger.info(f"  Leader        : {leaders[0]}")
        self.logger.info(f"  Followers     : {followers}")
        self.logger.info("----------------------------------------")


class TestZooKeeperDataPlane:
    """
    Validate that the ZooKeeper data tree is accessible and the root znode
    is readable from within the cluster.
    """
    SYSTEM_ZNODE = "zookeeper"

    def setup_method(self):
        self.logger    = Logger()
        self.zookeeper = ZooKeeperManager()

    def test_root_znode_accessible(self):
        """Test that the root znode is accessible and returns a valid znode list."""
        self.logger.info("Listing root znodes via zookeeper-shell ls /")

        znodes = self.zookeeper.list_root_znodes()

        # Root must return at least one znode
        assert len(znodes) > 0, (
            "Root znode '/' returned an empty list — "
            "ZooKeeper data tree is not initialised"
        )

        # ZooKeeper's own internal system znode must always be present
        assert self.SYSTEM_ZNODE in znodes, (
            f"System znode '/{self.SYSTEM_ZNODE}' not found in root. "
            f"Got: {znodes}"
        )

        self.logger.info(f"Root znodes accessible | znodes={znodes}")
