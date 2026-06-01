from langchain.chat_models import init_chat_model
from langchain_community.vectorstores import Chroma
import os
import logging
logger = logging.getLogger(__name__)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
chroma_path = os.path.join(BASE_DIR, "chroma_db")

def llm_model():
    """
    This function initializes and returns an instance of a chat model using the init_chat_model function from the langchain library.
    The model is configured to use the "groq:openai/gpt-oss-120b" model with a temperature setting of 0, which means it will generate deterministic responses.
    :return: An instance of the initialized chat model that can be used for generating responses based on input prompts.
    """
    model = init_chat_model(
        "groq:openai/gpt-oss-120b",
        temperature=0,
    )
    return model


def vectorstore_initializer(embedding_model):
    """
    This function initializes and returns an instance of the Chroma vector store, which is used for storing and retrieving document embeddings.
    The vector store is configured to persist data in the "chroma_db" directory and uses the provided embedding model for creating embeddings.
    :param embedding_model: An instance of an embedding model that will be used to generate embeddings for the documents stored in the vector store.
    :return: An instance of the initialized Chroma vector store that can be used for storing and retrieving document embeddings.
    """
    vectorstore = Chroma(persist_directory=chroma_path, embedding_function=embedding_model)
    logger.info(f"Initialized Chroma vector store with persistence at {chroma_path}")

    return vectorstore



def query_retriever(vectorstore, question):
    """

    :param vectorstore:
    :param question:
    :return:
    """
    retriever = vectorstore.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={"k": 3,
                       "score_threshold": 0.5
                       })
    docs = retriever.invoke(question)

    return docs


def test_query_retriever(vectorstore, question):
    """
    This function is a test utility for the query_retriever function. It retrieves documents based on the input question and prints the content of each retrieved document.
    :param vectorstore: An instance of the Chroma vector store that is used for retrieving document embeddings.
    :param question: The input question for which relevant documents are being retrieved. This is a string that represents the user's query.
    """
    # make
    retriever = vectorstore.similarity_search(
        question,
        k=3,

    )

    return retriever


def generate_augmented_prompt(docs, question, history=None):
    """
    This function generates an augmented prompt by combining the retrieved documents and the input question.
    The prompt is structured to instruct the model to answer the question based solely on the provided documents, and to indicate if the answer is not contained within those documents.
    :param docs: A list of retrieved documents that are relevant to the input question. Each document is expected to have a 'page_content' attribute containing the text content.
    :param question: The input question for which an answer is being sought. This is a string that represents the user's query.
    :param history: An optional parameter that represents the conversation history between the user and the AI. It is expected to be a list of dictionaries, where each dictionary contains 'user' and 'ai' keys representing the user's input and the AI's response, respectively.
    :return: A formatted string that serves as an augmented prompt for the model, containing both the retrieved documents and the original question.
    """
    docs_content = "\n\n".join([doc.page_content for doc in docs])
    # history to string
    if history:
        history = "\n\n".join([f"User: {h['user']}\nAI: {h['ai']}" for h in history])
    else:
        history = "No conversation history."

    augmented_prompt = (f"Answer the question based on the following retrieved documents only:\n\n{docs_content}\n\nQuestion: {question}."
                        f"conversation history: {history}. If the answer is not contained within the retrieved documents, say you don't know with a reason or general reply or counter question based on the situation. Max 30 words.")

    return augmented_prompt


def response_generator(model, augmented_prompt):
    """
    This function generates a response from the chat model based on the provided augmented prompt.
    It invokes the model with the augmented prompt and returns the generated response content.
    :param model: An instance of a chat model that has been initialized and is capable of generating responses based on input prompts.
    :param augmented_prompt: A formatted string that contains the retrieved documents and the original question, structured to guide the model in generating an appropriate response.
    :return: The content of the response generated by the model, which is expected to be an answer to the question based on the provided documents.
    """

    for chunk in model.stream(augmented_prompt):


        yield chunk.content





