"""
Integration tests for Apache Kafka — application level only.
Tests validation against actual Kubernetes cluster.
Requires a running K8s cluster with valid kubeconfig and Kafka deployment.

The kafka-client pod is deployed once for the entire module via the
kafka_pod fixture in conftest.py and shared across all test classes.

Run:
  pytest tests/test_kafka_validator.py --html=report.html --self-contained-html -s
"""
import uuid
import pytest
import time

from src.libs.common.logger import Logger
from src.libs.kafka.kafka_manager import KafkaManager, KafkaManagerError


# Helper
def _unique_topic(prefix: str = "pytest") -> str:
    """Generate a unique topic name to avoid collisions between test runs."""
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

@pytest.mark.usefixtures("kafka_pod")
class TestKafkaBrokerReadiness:
    """Verify Kafka broker is ready to accept connections before running any other tests."""

    _RETRIES  = 3
    _INTERVAL = 15

    def setup_method(self):
        self.logger = Logger()
        self.kafka  = KafkaManager()

    def test_broker_is_ready(self):
        """Test that Kafka broker is ready to accept connections."""
        last_error = None

        for attempt in range(1, self._RETRIES + 1):
            try:
                self.kafka.is_broker_ready()
                self.logger.info(f"Kafka broker is ready")
                return
            except KafkaManagerError as e:
                last_error = e
                self.logger.warning(
                    f"Broker not ready (attempt {attempt}/{self._RETRIES}), "
                    f"retrying in {self._INTERVAL}s..."
                )
                if attempt < self._RETRIES:
                    time.sleep(self._INTERVAL)

        pytest.exit(
            f"Kafka broker not ready after {self._RETRIES} attempts. "
            f"Last error: {last_error}"
        )

@pytest.mark.usefixtures("kafka_pod")
class TestKafkaTopicOperations:
    """Validate topic lifecycle: list, create, delete."""

    def setup_method(self):
        self.logger      = Logger()
        self.kafka       = KafkaManager()
        self.test_topics = []

    def teardown_method(self):
        for topic in self.test_topics:
            try:
                if self.kafka.topic_exists(topic):
                    self.kafka.delete_topic(topic)
                    self.logger.info(f"Teardown: deleted topic '{topic}'")
            except KafkaManagerError as e:
                if KafkaManager.DELETION_DISABLED_MARKER in str(e):
                    self.logger.warning(f"Teardown: deletion disabled on broker, cannot delete '{topic}'")
                else:
                    self.logger.warning(f"Teardown: could not delete '{topic}': {e}")

    def test_create_topic(self):
        """Test topic creation."""
        topic = _unique_topic("create")
        self.test_topics.append(topic)

        result = self.kafka.create_topic(topic)

        assert result is True, f"create_topic() returned {result} for '{topic}'"
        assert self.kafka.topic_exists(topic), (
            f"Topic '{topic}' was created but not found in list_topics()"
        )
        self.logger.info(f"Topic created and visible: '{topic}'")

    def test_create_topic_with_multiple_partitions(self):
        """Test topic creation with multiple partitions."""
        topic = _unique_topic("multi-partition")
        self.test_topics.append(topic)
        partitions = 3

        self.logger.info(f"Creating topic '{topic}' with partitions={partitions}")
        result = self.kafka.create_topic(topic, partitions=partitions)

        assert result is True, (
            f"create_topic() with 3 partitions returned {result} for '{topic}'"
        )
        assert self.kafka.topic_exists(topic), (
            f"Multi-partition topic '{topic}' not visible after creation"
        )
        self.logger.info(f"Multi-partition topic created: '{topic}'")

    def test_create_topic_with_replication(self):
        """Test topic creation with replication."""
        topic = _unique_topic("replicated")
        self.test_topics.append(topic)
        rf = 3

        self.logger.info(f"Creating topic '{topic}' with replication factor={rf}")
        result = self.kafka.create_topic(topic, replication_factor=rf)

        assert result is True, (
            f"create_topic() with replication_factor=3 returned {result} for '{topic}'"
        )
        assert self.kafka.topic_exists(topic), (
            f"Replicated topic '{topic}' not visible after creation"
        )
        self.logger.info(f"Replicated topic created: '{topic}'")

    def test_list_topics(self):
        """Test topic list fetch."""
        topics = self.kafka.list_topics()

        assert isinstance(topics, list), (
            f"list_topics() should return a list, got {type(topics)}"
        )
        self.logger.info(f"list_topics() succeeded | topics found: {topics}")

    def test_delete_topic(self):
        """Test topic deletion."""
        topic = _unique_topic("delete")

        self.kafka.create_topic(topic)
        assert self.kafka.topic_exists(topic), (
            f"Topic '{topic}' was not created — cannot test deletion"
        )

        try:
            result = self.kafka.delete_topic(topic)
        except KafkaManagerError as e:
            if KafkaManager.DELETION_DISABLED_MARKER in str(e):
                pytest.xfail("Broker has topic deletion disabled — expected on this cluster")
            raise

        assert result is True, f"delete_topic() returned {result} for '{topic}'"
        assert not self.kafka.topic_exists(topic), (
            f"Topic '{topic}' still visible in list_topics() after deletion"
        )
        self.logger.info(f"Topic deleted and no longer visible: '{topic}'")


@pytest.mark.usefixtures("kafka_pod")
class TestKafkaProducerConsumer:
    """Validate the full message lifecycle: produce a message and consume it back."""

    def setup_method(self):
        self.logger      = Logger()
        self.kafka       = KafkaManager()
        self.test_topics = []

    def teardown_method(self):
        for topic in self.test_topics:
            try:
                if self.kafka.topic_exists(topic):
                    self.kafka.delete_topic(topic)
                    self.logger.info(f"Teardown: deleted topic '{topic}'")
            except KafkaManagerError as e:
                if KafkaManager.DELETION_DISABLED_MARKER in str(e):
                    self.logger.warning(f"Teardown: deletion disabled on broker, cannot delete '{topic}'")
                else:
                    self.logger.warning(f"Teardown: could not delete '{topic}': {e}")

    def test_produce_message(self):
        """Test producing data to the topic."""
        topic   = _unique_topic("produce")
        payload = "test-message-payload"
        self.test_topics.append(topic)

        self.kafka.create_topic(topic)
        result = self.kafka.produce_message(topic, message=payload)

        assert result is True, (
            f"produce_message() returned {result} for topic '{topic}'"
        )
        self.logger.info(f"Message '{payload}' produced to '{topic}'")

    def test_consume_message(self):
        """Test consuming data from the topic."""
        topic         = _unique_topic("consume")
        expected_body = "hello-from-pytest"
        self.test_topics.append(topic)

        self.kafka.create_topic(topic)
        self.kafka.produce_message(topic, message=expected_body)

        messages = self.kafka.consume_messages(topic, count=1)

        assert len(messages) == 1, (
            f"Expected 1 message from '{topic}', consumed {len(messages)}"
        )
        assert messages[0] == expected_body, (
            f"Message value mismatch.\n"
            f"  Expected : '{expected_body}'\n"
            f"  Got      : '{messages[0]}'"
        )
        self.logger.info(f"Round-trip passed: produced and consumed '{expected_body}'")
