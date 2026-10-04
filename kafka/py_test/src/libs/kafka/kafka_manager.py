"""
Kafka Client for integration testing.
Executes all Kafka operations inside the kafka-client pod via kubectl exec.
All configuration loaded from APP_* environment variables (config/app.env).
"""
import os
import subprocess
from typing import List

from src.libs.common.k8s_client import K8sClient, K8sClientError as K8sError
from src.libs.common.logger import Logger


class KafkaManagerError(Exception):
    pass


class KafkaManager:

    DELETION_DISABLED_MARKER = "Topic deletion is disabled"    

    def __init__(self):
        self.logger    = Logger()
        self.namespace = os.getenv("APP_NAMESPACE", "default")
        self.pod_name  = os.getenv("APP_KAFKA_CLIENT_POD", "kafka-client")
        self.service   = os.getenv("APP_SERVICE_NAME", "kafka-headless")
        self.port      = os.getenv("APP_PORT", "9092")
        self.k8s       = K8sClient()

        self.bootstrap_server = self._build_bootstrap_server()
        self.logger.info(f"KafkaClient initialised | bootstrap={self.bootstrap_server}")
    
    def _build_bootstrap_server(self) -> str:
        """
        Build the Kafka bootstrap server address from app.env variables.
    
        Returns:
            str: bootstrap server address
        """
        return f"{self.service}.{self.namespace}:{self.port}"        

    def _exec(self, command: List[str]) -> str:
        """
        Execute a command inside the kafka-client pod.

        Args:
            command (List[str]): command and arguments to run inside the pod

        Returns:
            str: stdout output of the command

        Raises:
            KafkaClientError: if the command exits with a non-zero return code
        """
        try:
            stdout, stderr = self.k8s.exec_in_pod(
                pod_name=self.pod_name,
                namespace=self.namespace,
                command=command
            )
        except K8sError as e:
            raise KafkaClientError(str(e)) from e

        # stderr alone (no stdout) means the command failed
        if stderr:
            raise KafkaManagerError(stderr)

        return stdout

    def is_broker_ready(self) -> bool:
        """
        Check if the Kafka broker is reachable and accepting connections.

         Returns:
            bool: True if broker is ready, False otherwise
        """
        stdout, stderr = self.k8s.exec_in_pod(
            pod_name=self.pod_name,
            namespace=self.namespace,
            command=[
                "kafka-broker-api-versions",
                "--bootstrap-server", self.bootstrap_server
            ]
        )
        if stderr or not stdout:
            raise KafkaManagerError(
                f"Broker not reachable at {self.bootstrap_server}: {stderr or 'no response'}"
            )
        return True

    def list_topics(self) -> List[str]:
        """
        List all user topics. Internal topics (prefix '__') are excluded.

        Returns:
            List[str]: topic names, empty list on a fresh cluster
        """
        output = self._exec(["kafka-topics", "--bootstrap-server", self.bootstrap_server, "--list"])
        return [t for t in output.splitlines() if t and not t.startswith("__")]

    def topic_exists(self, topic: str) -> bool:
        """
        Check if a topic exists on the cluster.

        Args:
            topic (str): topic name to check

        Returns:
            bool: True if topic exists, False otherwise
        """
        return topic in self.list_topics()

    def create_topic(self, topic: str, partitions: int = 1, replication_factor: int = 1) -> bool:
        """
        Create a topic on the cluster.

        Args:
            topic (str):              topic name
            partitions (int):         number of partitions. Defaults to 1.
            replication_factor (int): replication factor. Defaults to 1.

        Returns:
            bool: True on success

        Raises:
            KafkaClientError: if topic creation fails
        """
        self._exec([
            "kafka-topics", "--bootstrap-server", self.bootstrap_server,
            "--create", "--topic", topic,
            "--partitions", str(partitions),
            "--replication-factor", str(replication_factor),
        ])
        self.logger.info(f"Topic created: '{topic}'")
        return True

    def delete_topic(self, topic: str) -> bool:
        """
        Delete a topic from the cluster.

        Args:
            topic (str): topic name to delete

        Returns:
            bool: True on success

        Raises:
            KafkaClientError: if deletion fails or is disabled on the broker
        """
        self._exec([
            "kafka-topics", "--bootstrap-server", self.bootstrap_server,
            "--delete", "--topic", topic,
        ])
        self.logger.info(f"Topic deleted: '{topic}'")
        return True

    def produce_message(self, topic: str, message: str) -> bool:
        """
        Produce a single message to a topic.

        Args:
            topic (str):   destination topic name
            message (str): message payload

        Returns:
            bool: True on success

        Raises:
            KafkaClientError: if produce fails
        """
        self._exec([
            "bash", "-c",
            f"echo '{message}' | kafka-console-producer"
            f" --bootstrap-server {self.bootstrap_server}"
            f" --topic {topic}",
        ])
        self.logger.info(f"Message produced → topic='{topic}'")
        return True

    def consume_messages(self, topic: str, count: int = 1, timeout_ms: int = 15000) -> List[str]:
        """
        Consume messages from a topic from the beginning.

        Args:
            topic (str):          topic to consume from
            count (int):          number of messages to consume. Defaults to 1.
            timeout_ms (int):     consumer timeout in ms. Defaults to 15000.

        Returns:
            List[str]: list of decoded message values

        Raises:
            KafkaClientError: on consumer error
        """
        stdout, _ = self.k8s.exec_in_pod(     # stderr ignored — consumer always writes summary/timeout to stderr
                pod_name=self.pod_name,
                namespace=self.namespace,
                command=[
                    "kafka-console-consumer",
                    "--bootstrap-server", self.bootstrap_server,
                    "--topic", topic,
                    "--from-beginning",
                    "--max-messages", str(count),
                    "--timeout-ms", str(timeout_ms),
                ]
        )        
        messages = [
            m for m in stdout.splitlines()
            if m and not m.startswith("Processed a total of")
        ]
        self.logger.info(f"Consumed {len(messages)}/{count} messages from '{topic}'")
        return messages
