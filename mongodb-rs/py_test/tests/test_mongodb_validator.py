"""
Integration tests for MongoDB Validator.
Tests validation against actual Kubernetes cluster.
Requires a running K8s cluster with valid kubeconfig and MongoDB deployment.
"""
import os
import pytest

from src.libs.mongodb.mongodb_connection import MongoDBConnection
from src.libs.common.logger import Logger


class TestMongoDBAuthentication:
    """Test MongoDB authentication and connection."""

    def setup_method(self):
        """Set up MongoDB connection for each test."""
        self.logger = Logger()
        self.logger.info("Setting up MongoDB connection for authentication test")
        self.mongo_conn = MongoDBConnection()


    def test_connect_to_replica_set(self):
        """Test connection to MongoDB replica set."""
        self.logger.info("Testing connection to MongoDB replica set")

        client = self.mongo_conn.connect()

        assert client is not None, "MongoDB client should not be None"
        assert self.mongo_conn.client is not None, "Connection should be established"

        self.logger.info("Successfully connected to MongoDB replica set")

    def test_authentication_success(self):
        """Test MongoDB authentication with correct credentials."""
        self.logger.info("Testing MongoDB authentication")

        self.mongo_conn.connect()
        result = self.mongo_conn.test_authentication()

        assert result is True, "Authentication should succeed with correct credentials"

        self.logger.info("MongoDB authentication successful")



class TestMongoDBReplicaSet:
    """Test MongoDB replica set functionality."""

    def setup_method(self):
        """Set up MongoDB connection for each test."""
        self.logger = Logger()
        self.logger.info("Setting up MongoDB connection for replica set test")
        self.mongo_conn = MongoDBConnection()
        self.mongo_conn.connect()

    def teardown_method(self):
        """Clean up MongoDB connection after each test."""
        if self.mongo_conn:
            self.mongo_conn.close()

    def test_get_replica_set_status(self):
        """Test retrieving replica set status."""
        self.logger.info("Testing replica set status retrieval")

        status = self.mongo_conn.get_replica_set_status()

        assert status is not None
        assert "set" in status
        assert "members" in status

        replica_set_name = status.get("set")
        members = status.get("members", [])

        self.logger.info(f"Replica set name: {replica_set_name}")
        self.logger.info(f"Number of members: {len(members)}")

        assert len(members) == self.mongo_conn.replica_count, \
            f"Expected {self.mongo_conn.replica_count} members, found {len(members)}"

        print(f"\nReplica Set Status:")
        print(f"  Name: {replica_set_name}")
        print(f"  Members: {len(members)}")

        for member in members:
            print(f"    - {member.get('name')}: {member.get('stateStr')} (health: {member.get('health')})")

    def test_get_replica_set_config(self):
        """Test retrieving replica set configuration."""
        self.logger.info("Testing replica set configuration retrieval")

        config = self.mongo_conn.get_replica_set_config()

        assert config is not None
        assert "config" in config

        rs_config = config.get("config", {})
        members = rs_config.get("members", [])

        self.logger.info(f"Replica set config version: {rs_config.get('version')}")
        self.logger.info(f"Configured members: {len(members)}")

        assert len(members) == self.mongo_conn.replica_count, \
            f"Expected {self.mongo_conn.replica_count} configured members"

        print(f"\nReplica Set Configuration:")
        print(f"  Version: {rs_config.get('version')}")
        print(f"  Members: {len(members)}")


    def test_validate_all_members_healthy(self):
        """Test that all replica set members are healthy."""
        self.logger.info("Testing replica set member health")

        member_health = self.mongo_conn.validate_replica_set_members()

        assert member_health is not None
        assert len(member_health) == self.mongo_conn.replica_count, \
            f"Expected {self.mongo_conn.replica_count} members"

        unhealthy_members = [name for name, healthy in member_health.items() if not healthy]

        print(f"\nReplica Set Member Health:")
        for name, healthy in member_health.items():
            status = "Healthy" if healthy else "Unhealthy"
            print(f"  {name}: {status}")

        assert len(unhealthy_members) == 0, \
            f"Unhealthy members found: {unhealthy_members}"

        self.logger.info(f"All {len(member_health)} replica set members are healthy")

    def test_primary_exists(self):
        """Test that replica set has a PRIMARY member."""
        self.logger.info("Testing for PRIMARY member")

        status = self.mongo_conn.get_replica_set_status()
        members = status.get("members", [])

        primary_members = [m for m in members if m.get("stateStr") == "PRIMARY"]

        assert len(primary_members) == 1, \
            f"Expected exactly 1 PRIMARY member, found {len(primary_members)}"

        primary = primary_members[0]
        self.logger.info(f"PRIMARY member: {primary.get('name')}")

        print(f"\nPRIMARY Member: {primary.get('name')}")

    def test_secondary_members_exist(self):
        """Test that replica set has SECONDARY members."""
        self.logger.info("Testing for SECONDARY members")

        status = self.mongo_conn.get_replica_set_status()
        members = status.get("members", [])

        secondary_members = [m for m in members if m.get("stateStr") == "SECONDARY"]

        expected_secondaries = self.mongo_conn.replica_count - 1
        assert len(secondary_members) == expected_secondaries, \
            f"Expected {expected_secondaries} SECONDARY members, found {len(secondary_members)}"

        self.logger.info(f"Found {len(secondary_members)} SECONDARY members")

        print(f"\nSECONDARY Members:")
        for member in secondary_members:
            print(f"  - {member.get('name')}")


class TestMongoDBOperations:
    """Test MongoDB CRUD operations."""
    
    def setup_method(self):
        """Set up MongoDB connection for each test."""
        self.logger = Logger()
        self.logger.info("Setting up MongoDB connection for operations test")
        self.mongo_conn = MongoDBConnection()
        self.mongo_conn.connect()
        self.test_db = "pytest_test_db"
        self.test_collection = "pytest_test_collection"
    
    def teardown_method(self):
        """Clean up MongoDB connection and test data after each test."""
        if self.mongo_conn and self.mongo_conn.client:
            # Clean up test database
            try:
                self.mongo_conn.client.drop_database(self.test_db)
                self.logger.info(f"Cleaned up test database: {self.test_db}")
            except Exception as e:
                self.logger.warning(f"Failed to clean up test database: {e}")
            
            self.mongo_conn.close()
    
    def test_write_operation(self):
        """Test write operation to MongoDB."""
        self.logger.info("Testing MongoDB write operation")
        
        result = self.mongo_conn.test_write_operation(
            test_db=self.test_db,
            test_collection=self.test_collection
        )
        
        assert result is True, "Write operation should succeed"
        
        self.logger.info("Write operation successful")
    
    def test_read_operation(self):
        """Test read operation from MongoDB."""
        self.logger.info("Testing MongoDB read operation")
        
        result = self.mongo_conn.test_read_operation(
            test_db=self.test_db,
            test_collection=self.test_collection
        )
        
        assert result is True, "Read operation should succeed"
        
        self.logger.info("Read operation successful")
    
    def test_insert_and_query(self):
        """Test insert and query operations."""
        self.logger.info("Testing insert and query operations")
        
        db = self.mongo_conn.client[self.test_db]
        collection = db[self.test_collection]
        
        # Insert multiple documents
        statefulset_name = self.mongo_conn.statefulset_name
        test_docs = [
            {"name": f"{statefulset_name}-0", "role": "primary", "port": 27017},
            {"name": f"{statefulset_name}-1", "role": "secondary", "port": 27017},
            {"name": f"{statefulset_name}-2", "role": "secondary", "port": 27017}
        ]
        
        result = collection.insert_many(test_docs)
        assert len(result.inserted_ids) == 3, "Should insert 3 documents"
        
        self.logger.info(f"Inserted {len(result.inserted_ids)} documents")
        
        # Query documents
        found_docs = list(collection.find({"role": "secondary"}))
        assert len(found_docs) == 2, "Should find 2 secondary documents"
        
        self.logger.info(f"Query returned {len(found_docs)} documents")
        
        # Count documents
        count = collection.count_documents({})
        assert count == 3, "Should have 3 total documents"
        
        self.logger.info(f"Total document count: {count}")
        
        print(f"\nMongoDB Operations Test:")
        print(f"  Inserted: {len(result.inserted_ids)} documents")
        print(f"  Queried: {len(found_docs)} secondary documents")
        print(f"  Total count: {count}")
    
    def test_update_operation(self):
        """Test update operation."""
        self.logger.info("Testing MongoDB update operation")
        
        db = self.mongo_conn.client[self.test_db]
        collection = db[self.test_collection]
        
        # Insert test document
        doc = {"name": "test", "value": 100}
        insert_result = collection.insert_one(doc)
        
        # Update document
        update_result = collection.update_one(
            {"_id": insert_result.inserted_id},
            {"$set": {"value": 200, "updated": True}}
        )
        
        assert update_result.modified_count == 1, "Should update 1 document"
        
        # Verify update
        updated_doc = collection.find_one({"_id": insert_result.inserted_id})
        assert updated_doc["value"] == 200
        assert updated_doc["updated"] is True
        
        self.logger.info("Update operation successful")
    
    def test_delete_operation(self):
        """Test delete operation."""
        self.logger.info("Testing MongoDB delete operation")
        
        db = self.mongo_conn.client[self.test_db]
        collection = db[self.test_collection]
        
        # Insert test documents
        docs = [{"name": f"doc_{i}"} for i in range(5)]
        insert_result = collection.insert_many(docs)
        
        # Delete one document
        delete_result = collection.delete_one({"name": "doc_0"})
        assert delete_result.deleted_count == 1, "Should delete 1 document"
        
        # Delete multiple documents
        delete_many_result = collection.delete_many({"name": {"$in": ["doc_1", "doc_2"]}})
        assert delete_many_result.deleted_count == 2, "Should delete 2 documents"
        
        # Verify remaining documents
        remaining = collection.count_documents({})
        assert remaining == 2, "Should have 2 documents remaining"
        
        self.logger.info("Delete operations successful")
        
        print(f"\nDelete Operations:")
        print(f"  Deleted single: 1 document")
        print(f"  Deleted multiple: 2 documents")
        print(f"  Remaining: {remaining} documents")



class TestMongoDBIndividualPods:
    """Test connectivity to individual MongoDB pods."""
    
    def setup_method(self):
        """Set up for pod connectivity tests."""
        self.logger = Logger()
        self.mongo_conn = MongoDBConnection()
        
        # Generate dynamic pod names based on statefulset name
        statefulset_name = self.mongo_conn.statefulset_name
        replica_count = self.mongo_conn.replica_count
        self.pod_names = [f"{statefulset_name}-{i}" for i in range(replica_count)]
    
    def teardown_method(self):
        """Clean up after tests."""
        if self.mongo_conn:
            self.mongo_conn.close()
    
    def test_connect_to_individual_pod(self):
        """Test connection to individual MongoDB pods."""
        for pod_name in self.pod_names:
            self.logger.info(f"Testing connection to {pod_name}")
            
            client = self.mongo_conn.connect(pod_name=pod_name)
            
            assert client is not None, f"Should connect to {pod_name}"
            
            # Test authentication
            result = self.mongo_conn.test_authentication()
            assert result is True, f"Authentication should succeed on {pod_name}"
            
            self.logger.info(f"Successfully connected to {pod_name}")
            
            print(f"\n{pod_name}: Connected and authenticated")
            
            # Close connection for next test
            self.mongo_conn.close()
