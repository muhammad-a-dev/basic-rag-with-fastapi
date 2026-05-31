from fastapi import APIRouter


router = APIRouter()


@router.get("/ingest")
def ingest():
    return {"message": "Ingest endpoint"}

@router.get("/query")
def query():
    return {"message": "Query endpoint"}
