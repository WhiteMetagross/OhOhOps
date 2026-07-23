import asyncio
import sys
from app.services.vectorstore import get_vectorstore_service
from langchain_core.documents import Document

async def main():
    print("Initializing configured vector store...")
    service = get_vectorstore_service()
    
    doc = Document(
        page_content="OhOhOps is an autonomous SRE agent that self-heals infrastructure.",
        metadata={"path": "test.txt", "language": "text"}
    )
    
    print("\nUpserting test document...")
    await service.aupsert_documents([doc])
    
    print("Waiting for indexing...")
    await asyncio.sleep(2)
    
    print("\nSearching vector database for 'self-healing agent'...")
    results = await service.asearch("self-healing agent", top_k=1)
    
    if results:
        print(f"OK: Match found! Content: {results[0].page_content}")
    else:
        print("ERROR: No match found.")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
