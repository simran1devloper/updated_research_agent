import os
import uuid
from datetime import datetime
from config import Config
from qdrant_client import QdrantClient
from qdrant_client.http import models

class MemoryManager:
    def __init__(self):
        # Initialize Qdrant client with local storage
        try:
            self.client = QdrantClient(path=Config.QDRANT_PATH)
            print(f"DEBUG: Qdrant initialized at {Config.QDRANT_PATH}")
        except Exception as e:
            if "already accessed" in str(e):
                print(f"⚠️ Warning: Qdrant storage locked. Falling back to in-memory storage for this session.")
                self.client = QdrantClient(location=":memory:")
            else:
                raise e
        
        self.collection_name = "research_memory"

    def add_memory(self, text: str, metadata: dict = None):
        """
        Save a text blob (e.g., report, interaction) to memory.
        """
        if metadata is None:
            metadata = {}
        
        metadata["timestamp"] = str(datetime.now())
        
        # Add document (FastEmbed will handle embedding and collection creation if needed)
        self.client.add(
            collection_name=self.collection_name,
            documents=[text],
            metadata=[metadata],
            ids=[str(uuid.uuid4())]
        )
        print(f"DEBUG: Saved to memory: {text[:50]}...")

    def get_context(self, query: str, n_results: int = 2):
        """
        Retrieve relevant context for a query.
        """
        try:
            # Check if collection exists first to avoid error if nothing has been added yet
            if not self.client.collection_exists(self.collection_name):
                return []
                
            results = self.client.query(
                collection_name=self.collection_name,
                query_text=query,
                limit=n_results
            )
            # Extract document content from results
            documents = [hit.document for hit in results]
            return documents
        except Exception as e:
            print(f"DEBUG: Memory retrieval skipped or failed: {e}")
            return []

# Singleton instance
memory = MemoryManager()
