import json
import asyncio
import logging
from pathlib import Path
from typing import Optional

from langchain_core.prompts import ChatPromptTemplate
from datasets import Dataset

from app.services.llm import get_chat_model
from app.services.vectorstore import get_vectorstore_service

logger = logging.getLogger("ohohops.eval.dataset_builder")


async def build_ragas_dataset(namespace: Optional[str] = None, samples: Optional[int] = None) -> Dataset:
    """
    Reads the seed questions, queries the real Pinecone vectorstore,
    and generates answers using the real Gemini model to build a
    genuine evaluation dataset for RAGAS 0.2.x.

    ``samples`` optionally caps how many seed questions are evaluated (useful for
    cheap smoke runs); ``namespace`` scopes the Pinecone retrieval.
    """
    fixture_path = Path(__file__).parent / "fixtures" / "seed_questions.json"

    with open(fixture_path, "r", encoding="utf-8") as f:
        seeds = json.load(f)

    if samples is not None:
        seeds = seeds[:samples]

    vectorstore = get_vectorstore_service()
    llm = get_chat_model()

    # Simple RAG prompt
    prompt = ChatPromptTemplate.from_messages([
        ("system", "Answer the user's question using ONLY the provided context.\n\nContext:\n{context}"),
        ("user", "{question}")
    ])

    chain = prompt | llm

    # Ragas 0.2.x required column names
    dataset_dict = {
        "user_input": [],         # the question
        "retrieved_contexts": [], # list of retrieved chunk texts
        "response": [],           # the model's answer
        "reference": []           # the curated ground truth
    }

    logger.info(f"Building dataset for {len(seeds)} seed questions...")

    for seed in seeds:
        question = seed["question"]
        ground_truth = seed["ground_truth"]

        # 1. Real Retrieval
        docs = await vectorstore.asearch(question, top_k=3, namespace=namespace)
        context_texts = [doc.page_content for doc in docs]
        combined_context = "\n\n".join(context_texts) if context_texts else "No context found."

        # 2. Real Generation
        ai_msg = await chain.ainvoke({
            "context": combined_context,
            "question": question
        })

        # 3. Format
        dataset_dict["user_input"].append(question)
        dataset_dict["retrieved_contexts"].append(context_texts)
        dataset_dict["response"].append(ai_msg.content)
        dataset_dict["reference"].append(ground_truth)

    logger.info("Dataset built successfully!")
    return Dataset.from_dict(dataset_dict)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(build_ragas_dataset())
