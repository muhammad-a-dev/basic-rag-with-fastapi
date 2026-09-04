"""Offline RAGAS evaluation script.

Requires real provider credentials and an ingested corpus.
This module is intentionally not executed by CI.
"""

from __future__ import annotations

import logging

from datasets import Dataset
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import answer_relevancy, faithfulness

from rag.ingestion import embedding_model
from rag.retriever import (
    generate_augmented_prompt,
    llm_model,
    similarity_search,
    vectorstore_initializer,
)

logger = logging.getLogger(__name__)

TEST_SET = [
    {
        "question": (
            "According to David Lay Williams and Alan J. Kellner, what specific category "
            "of rulers does Lord Voldemort perfectly fit into?"
        ),
        "ground_truth": (
            "Voldemort fits perfectly into Plato's category of 'least trustworthy rulers.'"
        ),
    },
    {
        "question": (
            "What are the four less-desirable forms of government that Plato describes "
            "in addition to his ideal society?"
        ),
        "ground_truth": (
            "The four less-desirable governments are timocracy (rule by those motivated "
            "by honor), oligarchy (rule by a small group, usually the wealthy), democracy "
            "(rule by the common people), and tyranny (rule by a tyrant)."
        ),
    },
]


def run_evaluation() -> None:
    """Run faithfulness / answer relevancy metrics against the local vector store."""
    logging.basicConfig(level=logging.INFO)
    results: list[dict] = []
    vectorstore = vectorstore_initializer(embedding_model())
    model = llm_model()

    for item in TEST_SET:
        question = item["question"]
        ground_truth = item["ground_truth"]
        retrieved_docs = similarity_search(vectorstore, question)
        prompt = generate_augmented_prompt(retrieved_docs, question)
        model_response = model.invoke(prompt)

        results.append(
            {
                "question": question,
                "answer": model_response.content,
                "contexts": [doc.page_content for doc in retrieved_docs],
                "ground_truth": ground_truth,
            }
        )
        logger.info("Evaluated question: %s", question)

    dataset = Dataset.from_list(results)
    score = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=LangchainLLMWrapper(model),
        embeddings=LangchainEmbeddingsWrapper(embedding_model()),
    )
    logger.info("RAGAS score: %s", score)


if __name__ == "__main__":
    run_evaluation()
