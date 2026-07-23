import logging
import re
import chromadb
from typing import List, Dict

from chromadb.config import Settings as ChromaSettings
from langchain_chroma import Chroma
from langchain_core.documents import Document

from app.core.config import get_settings
from app.services.embeddings import get_embeddings
from app.services.vectorstore import VectorStore

logger = logging.getLogger("ohohops.vectorstore_chroma")

class ChromaVectorStoreService(VectorStore):
    def __init__(self):
        self.settings = get_settings()
        self.embeddings = get_embeddings()
        
        # Setup Chroma HTTP Client
        self.chroma_client = chromadb.HttpClient(
            host=self.settings.chroma_host,
            port=self.settings.chroma_port,
            settings=ChromaSettings(allow_reset=True, anonymized_telemetry=False)
        )
        
        # Cache for Langchain Chroma wrappers by namespace
        self._collections: Dict[str, Chroma] = {}
        
    def _sanitize_collection_name(self, namespace: str) -> str:
        """Sanitize namespace to a valid Chroma collection name.
        Must be between 3 and 63 characters.
        Must start and end with an alphanumeric character.
        Can contain only alphanumeric characters, underscores or hyphens.
        """
        ns = namespace or "default"
        prefix = self.settings.chroma_collection_prefix
        name = f"{prefix}{ns}"
        
        # Replace invalid chars with underscore
        name = re.sub(r'[^a-zA-Z0-9_-]', '_', name)
        
        # Trim to 63 chars max
        name = name[:63]
        
        # Ensure it starts and ends with alphanumeric
        while name and not name[0].isalnum():
            name = name[1:]
        while name and not name[-1].isalnum():
            name = name[:-1]
            
        # Fallback if entirely sanitized away
        if not name:
            name = "ohohops_default"
            
        return name

    def _get_or_create_collection(self, namespace: str = None) -> Chroma:
        """Returns a cached Langchain Chroma wrapper for the given namespace."""
        ns_key = namespace or "default"
        if ns_key not in self._collections:
            collection_name = self._sanitize_collection_name(namespace)
            logger.info(f"Initializing Chroma collection '{collection_name}' for namespace '{ns_key}'")
            
            # This creates the collection if it doesn't exist
            self._collections[ns_key] = Chroma(
                client=self.chroma_client,
                collection_name=collection_name,
                embedding_function=self.embeddings,
            )
        return self._collections[ns_key]

    async def aupsert_documents(self, documents: List[Document], namespace: str = None) -> None:
        """Async wrapper to upsert LangChain Document chunks in batches."""
        if not documents:
            logger.warning("No documents provided to upsert.")
            return
            
        vectorstore = self._get_or_create_collection(namespace)
        collection_name = vectorstore._collection.name
        logger.info(f"Upserting {len(documents)} documents to Chroma collection '{collection_name}' in batches...")
        
        import asyncio
        batch_size = 100 # Chroma can handle larger batches locally
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Upserting batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
            # langchain's aadd_documents wraps the sync method in run_in_executor
            await vectorstore.aadd_documents(batch)
            
        logger.info("Upsert complete.")

    async def asearch(self, query: str, top_k: int = None, namespace: str = None) -> List[Document]:
        """Async semantic search returning the most relevant Document chunks."""
        top_k = top_k or self.settings.retrieval_top_k
        vectorstore = self._get_or_create_collection(namespace)
        logger.info(f"Searching Chroma for query: '{query}' (top_k={top_k}, namespace={namespace})")
        # langchain's asimilarity_search wraps sync search
        results = await vectorstore.asimilarity_search(query, k=top_k)
        return results

    async def aget_unique_files(self, namespace: str = None) -> List[str]:
        """Hack to retrieve unique file paths from the vectorstore for the UI picker."""
        vectorstore = self._get_or_create_collection(namespace)
        results = await vectorstore.asimilarity_search(" ", k=1000)
        paths = set()
        for doc in results:
            if "path" in doc.metadata:
                paths.add(doc.metadata["path"])
        return sorted(list(paths))
