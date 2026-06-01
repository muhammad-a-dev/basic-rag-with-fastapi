
from fastapi import APIRouter, File, UploadFile, HTTPException
import os
from rag.ingestion import load_document, chunk_document, embedding_model
from rag.retriever import query_retriever, generate_augmented_prompt, response_generator, llm_model
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

    if session_id not in chat_history:
        chat_history[session_id] = []




    vectorstore = Chroma(persist_directory="chroma_db", embedding_function=embedding_model())
    response = query_retriever(vectorstore, question)
    sources = list(set([doc.metadata['source'].replace("temp\\", "") for doc in response]))



    augmented_prompt = generate_augmented_prompt(response, question, history=chat_history[session_id])
    print(augmented_prompt)
    ai_response = response_generator(model=llm_model(), augmented_prompt=augmented_prompt)
    chat_history[session_id].append({"user": question, "ai": ai_response})



    return {"response": ai_response, "sources": sources}








