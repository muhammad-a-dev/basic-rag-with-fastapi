
from fastapi import APIRouter, File, UploadFile, HTTPException
from fastapi.responses import StreamingResponse
import os
from rag.ingestion import load_document, chunk_document, embedding_model
from rag.retriever import query_retriever, generate_augmented_prompt, response_generator, llm_model, vectorstore_initializer
from api.schemas import QueryRequest
from langchain_community.vectorstores import Chroma





router = APIRouter()
chat_history = {}



@router.post("/ingest")
async def ingest(file: UploadFile = File(...)):
    # 1. Validate file extension
    allowed_extensions = [".pdf", ".txt"]
    file_ext = os.path.splitext(file.filename)[1].lower()  # Get the file extension and convert to lowercase

    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Invalid file type. Only PDF and TXT files are allowed."
        )

    # 2. Ensure the temp directory exists
    target_dir = "temp"
    os.makedirs(target_dir, exist_ok=True)
    file_location = os.path.join(target_dir, file.filename)

    # 3. Save the uploaded file temporarily
    # Using 'async' and 'await' with file.read() prevents blocking the server
    try:
        contents = await file.read()
        with open(file_location, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        await file.close()  # Always close the file to free up memory

    # TODO: Add your code here to process the file and add it to the vector store

    document = load_document(file_location)
    chunks = chunk_document(document)
    embeddings = embedding_model()
    vectorstore = Chroma(persist_directory="chroma_db", embedding_function=embeddings)
    vectorstore.add_documents(chunks)


    return {"status": "success", "chunks_stored": len(chunks)}



@router.post("/query")
def query(request: QueryRequest):
    question = request.question
    session_id = request.session_id

    if len(question) == 0 or len(question) > 500:
        raise HTTPException(status_code=400, detail="Question must be between 1 and 500 characters long.")




    if session_id not in chat_history:
        chat_history[session_id] = []






    vectorstore = vectorstore_initializer(embedding_model())
    response = query_retriever(vectorstore, question)

    if not response:
        return {"response": "No relevant documents found to answer the question.", "sources": []}


    print("response from retriever: ", response)
    sources = list(set([doc.metadata['source'].replace("temp\\", "") for doc in response]))




    augmented_prompt = generate_augmented_prompt(response, question, history=chat_history[session_id])
    print(augmented_prompt)

    def stream_and_save_response():
        collected_response = ""

        for chunk in response_generator(model=llm_model(), augmented_prompt=augmented_prompt):
            yield chunk
            collected_response += chunk

        chat_history[session_id].append({"user": question, "ai": collected_response})


    return StreamingResponse(stream_and_save_response(), media_type="text/plain", headers={"X-Sources": ", ".join(sources)})











