from fastapi import FastAPI
from api.routes import router as api_router
import logging
logging.basicConfig(
  level=logging.INFO,
  format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

app = FastAPI()

app.include_router(api_router, prefix="/api")


@app.get("/")
def read_root():
    return {"Hello": "World"}

