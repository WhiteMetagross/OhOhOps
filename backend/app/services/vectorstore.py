import logging
from typing import List, Protocol

from pinecone import Pinecone, ServerlessSpec
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document

from app.core.config import get_settings
from app.services.embeddings import get_embeddings

logger = logging.getLogger("ohohops.vectorstore")

class VectorStore(Protocol):
    async def aupsert_documents(self, documents: List[Document], namespace: str = None) -> None: ...
    async def asearch(self, query: str, top_k: int = None, namespace: str = None) -> List[Document]: ...
    async def aget_unique_files(self, namespace: str = None) -> List[str]: ...


class PineconeVectorStoreService:
    def __init__(self, pc_client: Pinecone = None):
        self.settings = get_settings()
        # Use provided client (e.g., from app.state) or create a new one
        self.pc = pc_client or Pinecone(api_key=self.settings.pinecone_api_key)
        self.index_name = self.settings.pinecone_index
        
        # Ensure index exists (synchronous API call, happens once on init)
        self._ensure_index()
        
        self.embeddings = get_embeddings()
        
        # Initialize LangChain wrapper
        self.vectorstore = PineconeVectorStore(
            index_name=self.index_name,
            embedding=self.embeddings,
            pinecone_api_key=self.settings.pinecone_api_key
        )

    def _ensure_index(self):
        """Creates the Pinecone index if it does not already exist."""
        try:
            # list_indexes() returns an iterable of IndexModel objects in pinecone>=3.0
            existing_indexes = [idx.name for idx in self.pc.list_indexes()]
            
            if self.index_name not in existing_indexes:
                logger.info(f"Creating Pinecone index: '{self.index_name}'...")
                self.pc.create_index(
                    name=self.index_name,
                    dimension=self.settings.embedding_dimension,
                    metric=self.settings.pinecone_metric,
                    spec=ServerlessSpec(
                        cloud=self.settings.pinecone_cloud,
                        region=self.settings.pinecone_region
                    )
                )
                logger.info(f"Index '{self.index_name}' created successfully.")
            else:
                logger.info(f"Pinecone index '{self.index_name}' already exists.")
        except Exception as e:
            logger.error(f"Failed to ensure Pinecone index exists: {e}")
            raise

    async def aupsert_documents(self, documents: List[Document], namespace: str = None):
        """Async wrapper to upsert LangChain Document chunks in batches to avoid rate limits."""
        if not documents:
            logger.warning("No documents provided to upsert.")
            return
            
        ns = namespace or "default"
        logger.info(f"Upserting {len(documents)} documents to vector store '{self.index_name}' (namespace: {ns}) in batches...")
        
        import asyncio
        if self.settings.use_local_embeddings:
            batch_size = 100
            sleep_time = 0
        elif self.settings.openai_api_key:
            batch_size = 20
            sleep_time = 1.5
        else:
            # Gemini Free Tier allows 15 RPM. By bundling 100 chunks into a single request
            # with a 4.5s sleep, we safely process 1,300 chunks per minute without hitting the quota.
            batch_size = 100
            sleep_time = 4.5
        
        for i in range(0, len(documents), batch_size):
            batch = documents[i:i + batch_size]
            logger.info(f"Upserting batch {i//batch_size + 1}/{(len(documents)-1)//batch_size + 1}...")
            await self.vectorstore.aadd_documents(batch, namespace=ns)
            if i + batch_size < len(documents) and sleep_time > 0:
                await asyncio.sleep(sleep_time)
                
        logger.info("Upsert complete.")

    async def asearch(self, query: str, top_k: int = None, namespace: str = None) -> List[Document]:
        """Async semantic search returning the most relevant Document chunks."""
        top_k = top_k or self.settings.retrieval_top_k
        ns = namespace or "default"
        logger.info(f"Searching vector store for query: '{query}' (top_k={top_k}, namespace={ns})")
        results = await self.vectorstore.asimilarity_search(query, k=top_k, namespace=ns)
        return results

    async def aget_unique_files(self, namespace: str = None) -> List[str]:
        """Hack to retrieve unique file paths from the vectorstore for the UI picker."""
        # Query with a dummy space to pull a large sample of chunks and extract paths
        ns = namespace or "default"
        results = await self.vectorstore.asimilarity_search(" ", k=1000, namespace=ns)
        paths = set()
        for doc in results:
            if "path" in doc.metadata:
                paths.add(doc.metadata["path"])
        return sorted(list(paths))


# Process-wide singleton
_vectorstore_service: VectorStore | None = None

def get_vectorstore_service(pc_client: Pinecone | None = None) -> VectorStore:
    """Returns a cached instance of the VectorStore (Pinecone or Chroma)."""
    global _vectorstore_service
    if _vectorstore_service is None:
        settings = get_settings()
        if settings.is_local:
            from app.services.vectorstore_chroma import ChromaVectorStoreService
            _vectorstore_service = ChromaVectorStoreService()
        else:
            _vectorstore_service = PineconeVectorStoreService(pc_client)
    return _vectorstore_service
