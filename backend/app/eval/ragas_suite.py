import sys
import asyncio
import argparse
import logging
from typing import Optional

from ragas import evaluate
from ragas.metrics import faithfulness, context_recall
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings

from app.core.config import get_settings
from app.services.ledger import create_ledger
from app.core.schemas import OperationalLogEntry
from app.eval.dataset_builder import build_ragas_dataset

logger = logging.getLogger("ohohops.eval.ragas")
logging.basicConfig(level=logging.INFO)


async def run_evaluation(namespace: Optional[str] = None, samples: Optional[int] = None):
    """
    Runs a Ragas evaluation on a real test dataset to measure the accuracy of the
    SRE RAG pipeline. Persists the fidelity score to the operational ledger when
    one is configured. Exits non-zero on failure so CI can gate on it.
    """
    settings = get_settings()

    # Configure Ragas to use our Gemini configuration
    eval_llm = ChatGoogleGenerativeAI(
        model=settings.gemini_chat_model,
        google_api_key=settings.gemini_api_key,
    )
    eval_embeddings = GoogleGenerativeAIEmbeddings(
        model=settings.gemini_embedding_model,
        google_api_key=settings.gemini_api_key,
    )

    logger.info("Building real RAGAS evaluation dataset...")
    dataset = await build_ragas_dataset(namespace=namespace, samples=samples)

    logger.info("Starting RAGAS evaluation (Faithfulness & Context Recall)...")

    try:
        # Run the Ragas metrics
        result = evaluate(
            dataset,
            metrics=[faithfulness, context_recall],
            llm=eval_llm,
            embeddings=eval_embeddings,
        )

        # Ragas 0.2.x extraction via Pandas
        df = result.to_pandas()
        faith_score = float(df["faithfulness"].mean()) if "faithfulness" in df.columns else 0.0
        recall_score = float(df["context_recall"].mean()) if "context_recall" in df.columns else 0.0

        logger.info(
            f"OK: RAGAS Evaluation Complete!\nFaithfulness: {faith_score}\nContext Recall: {recall_score}"
        )

        # Persist the score to the durable ledger if it is configured.
        ledger = await create_ledger(settings.supabase_db_url)
        if ledger is None:
            logger.warning("Ledger not configured — skipping score persistence.")
            return

        logger.info("Writing fidelity score to Operational Ledger...")
        entry = OperationalLogEntry(
            event_source="eval/ragas",
            agent_action="ragas_evaluation",
            execution_payload=f"Faithfulness: {faith_score} | Context Recall: {recall_score}",
            execution_status="success",
            ragas_fidelity_score=faith_score,
        )

        await ledger.log_event(entry)
        await ledger.close()

    except Exception as e:
        logger.error(f"ERROR: RAGAS evaluation failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run Ragas Evaluation")
    parser.add_argument("--namespace", type=str, default=None, help="Pinecone namespace to evaluate")
    parser.add_argument("--samples", type=int, default=None, help="Cap the number of seed questions evaluated")
    args = parser.parse_args()

    asyncio.run(run_evaluation(namespace=args.namespace, samples=args.samples))
