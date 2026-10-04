"""
Integration tests for Apache Nifi Validator.
Tests validation against actual Kubernetes cluster.
Requires a running K8s cluster with valid kubeconfig and Apache Nifi deployment.
"""
import os
import subprocess
import time
from src.libs.apachenifi.apache_nifi_flow import ApacheNifiFlow
from src.libs.common.logger import Logger


class TestApacheNifiAuthentication:
    """Test ApacheNifi authentication and connection."""

    def setup_method(self):
        """Set up ApacheNifi connection for each test."""
        self.logger = Logger()
        self.logger.info("Setting up ApacheNifi connection for authentication test")
        self.nifi_conn = ApacheNifiFlow()

    

    def test_connection(self):
        """Test connection to Apache nifi."""
        self.logger.info("Testing connection to Apache Nifi")

        client = self.nifi_conn.connect()

        assert client is not None, "Apache nifi connection should not be None"
        assert self.nifi_conn.session is not None, "Connection should be established"

        self.logger.info("Successfully connected to Apache Nifi")

    def test_authentication_success(self):
        """Test Apache Nifi authentication with correct credentials."""
        self.logger.info("Testing Apache Nifi authentication")

        self.nifi_conn.connect()
        result = self.nifi_conn.test_authentication()

        assert result is True, "Authentication should succeed with correct credentials"

        self.logger.info("Apache nifi authentication successful")
