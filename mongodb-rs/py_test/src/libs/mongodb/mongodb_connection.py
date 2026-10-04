"""
MongoDB Connection Manager for integration testing.
Handles MongoDB authentication and replica set connections.
"""
import os
from typing import Dict, List, Optional
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, OperationFailure, ServerSelectionTimeoutError

from src.libs.common.logger import Logger


class MongoDBConnection:
    """Manages MongoDB connections for testing."""
    
    def __init__(self):
        """Initialize MongoDB connection manager."""
        self.logger = Logger()
        
        # Load all configuration from APP_* variables
        self.namespace = os.getenv("APP_NAMESPACE", "default")
        self.statefulset_name = os.getenv("APP_RESOURCE_NAME", "mongodb-rs")
        self.replica_count = int(os.getenv("APP_EXPECTED_REPLICAS", "3"))
        self.service_name = os.getenv("APP_SERVICE_NAME", "mongodb-headless")
        self.port = int(os.getenv("APP_PORT", "27017"))
        self.user = os.getenv("APP_USER", "root")
        self.password = os.getenv("APP_PASSWORD", "0Admin123")
        self.auth_database = os.getenv("APP_AUTH_DATABASE", "admin")
        self.replica_set_name = os.getenv("APP_REPLICA_SET_NAME", "rs0")
        
        # Determine if using local port-forward or cluster DNS
        self.use_port_forward = os.getenv("APP_ENABLE_PORT_FORWARD", "true").lower() == "true"
        
        self.client = None
        
        mode = "local (port-forward)" if self.use_port_forward else "cluster (K8s DNS)"
        self.logger.info(f"MongoDBConnection initialized for namespace: {self.namespace}, mode: {mode}")
    
    
    def get_connection_string(self, pod_name: str = None) -> str:
        """
        Get MongoDB connection string.
        
        Args:
            pod_name: Specific pod name (e.g., 'mongodb-0'), or None for replica set connection
        
        Returns:
            MongoDB connection string
        """
        if self.use_port_forward:
            # Local connection via port-forward (database namespace)
            if pod_name:
                # Direct connection to specific pod via localhost
                # Assumes: kubectl port-forward -n database mongodb-0 27017:27017
                return f"mongodb://{self.user}:{self.password}@localhost:{self.port}/?authSource={self.auth_database}&directConnection=true"
            else:
                # For port-forward mode, connect to first pod only (no replica set)
                return f"mongodb://{self.user}:{self.password}@localhost:{self.port}/?authSource={self.auth_database}&directConnection=true"
        else:
            # Cluster connection (inside K8s cluster via DNS)
            if pod_name:
                # Direct connection to specific pod
                host = f"{pod_name}.{self.service_name}.{self.namespace}.svc.cluster.local"
                return f"mongodb://{self.user}:{self.password}@{host}:{self.port}/?authSource={self.auth_database}"
            else:
                # Replica set connection
                hosts = [
                    f"{self.statefulset_name}-{i}.{self.service_name}.{self.namespace}.svc.cluster.local:{self.port}"
                    for i in range(self.replica_count)
                ]
                hosts_str = ",".join(hosts)
                return f"mongodb://{self.user}:{self.password}@{hosts_str}/?authSource={self.auth_database}&replicaSet={self.replica_set_name}"


    def connect(self, pod_name: str = None, timeout: int = 5000) -> MongoClient:
        """
        Connect to MongoDB.
        
        Args:
            pod_name: Specific pod name for direct connection, or None for replica set
            timeout: Connection timeout in milliseconds
        
        Returns:
            MongoClient instance
        
        Raises:
            ConnectionFailure: If connection fails
        """
        connection_string = self.get_connection_string(pod_name)
        
        try:
            self.logger.info(f"Connecting to MongoDB: {pod_name or 'replica set'}")
            self.client = MongoClient(
                connection_string,
                serverSelectionTimeoutMS=timeout,
                connectTimeoutMS=timeout
            )
            
            # Test connection
            self.client.admin.command('ping')
            self.logger.info(f"Successfully connected to MongoDB")
            
            return self.client
            
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            self.logger.error(f"Failed to connect to MongoDB: {e}")
            raise ConnectionFailure(f"Failed to connect to MongoDB: {e}")
    
    def test_authentication(self) -> bool:
        """
        Test MongoDB authentication.
        
        Returns:
            True if authentication successful
        """
        try:
            if not self.client:
                self.connect()
            
            # Try to list databases (requires authentication)
            dbs = self.client.list_database_names()
            self.logger.info(f"Authentication successful. Databases: {dbs}")
            return True
            
        except OperationFailure as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    def get_replica_set_status(self) -> Dict:
        """
        Get replica set status.
        
        Returns:
            Replica set status dictionary
        """
        try:
            if not self.client:
                self.connect()
            
            status = self.client.admin.command('replSetGetStatus')
            self.logger.info(f"Retrieved replica set status")
            return status
            
        except OperationFailure as e:
            self.logger.error(f"Failed to get replica set status: {e}")
            raise
    
    def get_replica_set_config(self) -> Dict:
        """
        Get replica set configuration.
        
        Returns:
            Replica set configuration dictionary
        """
        try:
            if not self.client:
                self.connect()
            
            config = self.client.admin.command('replSetGetConfig')
            self.logger.info(f"Retrieved replica set configuration")
            return config
            
        except OperationFailure as e:
            self.logger.error(f"Failed to get replica set config: {e}")
            raise
    
    def validate_replica_set_members(self) -> Dict[str, bool]:
        """
        Validate all replica set members are healthy.
        
        Returns:
            Dictionary mapping member names to health status
        """
        try:
            status = self.get_replica_set_status()
            members = status.get('members', [])
            
            results = {}
            for member in members:
                name = member.get('name', 'unknown')
                state = member.get('stateStr', 'UNKNOWN')
                health = member.get('health', 0) == 1
                
                is_healthy = health and state in ['PRIMARY', 'SECONDARY']
                results[name] = is_healthy
                
                status_icon = "✓" if is_healthy else "✗"
                self.logger.info(f"{status_icon} Member {name}: {state}, Health: {health}")
            
            return results
            
        except Exception as e:
            self.logger.error(f"Failed to validate replica set members: {e}")
            raise
    
    def test_write_operation(self, test_db: str = "test", test_collection: str = "test_collection") -> bool:
        """
        Test write operation to MongoDB.
        
        Args:
            test_db: Test database name
            test_collection: Test collection name
        
        Returns:
            True if write successful
        """
        try:
            if not self.client:
                self.connect()
            
            db = self.client[test_db]
            collection = db[test_collection]
            
            # Insert test document
            test_doc = {"test": "data", "timestamp": "test"}
            result = collection.insert_one(test_doc)
            
            self.logger.info(f"Write operation successful. Inserted ID: {result.inserted_id}")
            
            # Clean up
            collection.delete_one({"_id": result.inserted_id})
            self.logger.info(f"Test document cleaned up")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Write operation failed: {e}")
            return False
    
    def test_read_operation(self, test_db: str = "test", test_collection: str = "test_collection") -> bool:
        """
        Test read operation from MongoDB.
        
        Args:
            test_db: Test database name
            test_collection: Test collection name
        
        Returns:
            True if read successful
        """
        try:
            if not self.client:
                self.connect()
            
            db = self.client[test_db]
            collection = db[test_collection]
            
            # Insert test document
            test_doc = {"test": "read_data", "value": 123}
            result = collection.insert_one(test_doc)
            
            # Read it back
            found_doc = collection.find_one({"_id": result.inserted_id})
            
            if found_doc and found_doc.get("test") == "read_data":
                self.logger.info(f"Read operation successful")
                
                # Clean up
                collection.delete_one({"_id": result.inserted_id})
                return True
            else:
                self.logger.error(f"Read operation failed: document not found or incorrect")
                return False
            
        except Exception as e:
            self.logger.error(f"Read operation failed: {e}")
            return False
    
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            self.logger.info("MongoDB connection closed")
            self.client = None
