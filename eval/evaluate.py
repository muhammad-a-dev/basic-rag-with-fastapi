from rag.retriever import query_retriever, generate_augmented_prompt, llm_model, vectorstore_initializer, test_query_retriever
from rag.ingestion import embedding_model
from datasets import Dataset

from ragas import evaluate
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper



test_set = [
    {
        "question": "According to David Lay Williams and Alan J. Kellner, what specific category of rulers does Lord Voldemort perfectly fit into?",
        "ground_truth": "Voldemort fits perfectly into Plato's category of 'least trustworthy rulers.'"
    },
    {
        "question": "What are the four less-desirable forms of government that Plato describes in addition to his ideal society?",
        "ground_truth": "The four less-desirable governments are timocracy (rule by those motivated by honor), oligarchy (rule by a small group, usually the wealthy), democracy (rule by the common people), and tyranny (rule by a tyrant)."
    },
    {
        "question": "How do Tom Riddle's childhood actions in the orphanage mirror Plato's description of tyrannical men in their early stages?",
        "ground_truth": "Plato describes early-stage tyrannical men as those who steal, commit burglary, snatch purses, rob travelers, defile temples, and enslave people. This finds a parallel in Tom Riddle's childhood at the orphanage, where he steals from other children and commits escalating acts of cruelty toward animals and other children."
    },
    {
        "question": "According to Plato's 'Myth of Metals' in the Republic, what metals correspond to the souls of the class best suited to rule and protect the city?",
        "ground_truth": "Those with gold or silver in their souls belong in the guardian class; gold souls are best suited to rule, while silver souls protect and defend the city."
    },
    {
        "question": "In the Symposium, what does Plato state is the only path to true immortality, and how must it be accomplished?",
        "ground_truth": "The ascent to the Beautiful itself is the only path to true immortality, and it must be accomplished 'in the proper sequence and in the correct manner.'"
    }
]

results = []

for test in test_set:
    question = test["question"]
    ground_truth = test["ground_truth"]

    # Simulate retrieval and response generation
    vectorstore = vectorstore_initializer(embedding_model())  # Mocked vector store initialization
    retrieved_docs = test_query_retriever(vectorstore, question)  # Mocked retrieval

    augmented_prompt = generate_augmented_prompt(retrieved_docs, question)
    model_response = llm_model().invoke(augmented_prompt)  # Mocked response generation

    # I need question,answer,contexts[],ground_truth
    query_retriever_data = {
        "question": question,
        "answer": model_response.content,
        "contexts": [doc.page_content for doc in retrieved_docs],
        "ground_truth": ground_truth
    }

    results.append(query_retriever_data)


    print(f"Question: {question}")
    print(f"Ground Truth: {ground_truth}")
    print(f"Model Response: {model_response.content}")
    print("-" * 50)


dataset = Dataset.from_list(results)

ragas_llm = LangchainLLMWrapper(llm_model())
ragas_embeddings = LangchainEmbeddingsWrapper(embedding_model())

# evaluate
score = evaluate(
  dataset,
  metrics=[faithfulness, answer_relevancy],
  llm=ragas_llm,
  embeddings=ragas_embeddings
)

print(score)
