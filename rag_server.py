from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
import warnings
import uvicorn

warnings.filterwarnings("ignore")

app = FastAPI(title="SysReptor RAG Retrieval Server")

DB_DIR = "./chroma_db"
COLLECTION_NAME = "sysreptor_rag"

# Global states
client = None
collection = None
model = None

@app.on_event("startup")
async def startup_event():
    global client, collection, model
    print("[*] Initializing RAG components...")
    client = chromadb.PersistentClient(path=DB_DIR)
    try:
        collection = client.get_collection(name=COLLECTION_NAME)
    except Exception as e:
        print(f"[-] Error loading collection: {e}. Make sure to run ingest_data.py first.")
        
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("[+] RAG components initialized and ready.")

class QueryRequest(BaseModel):
    query: str
    num_results: int = 5
    filter_type: str = None  # e.g., 'finding', 'executive_summary', 'technical_summary'

@app.post("/query")
async def query_rag(request: QueryRequest):
    if collection is None:
        raise HTTPException(status_code=500, detail="Chroma DB collection not initialized.")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Convert query to embedding
    query_embedding = model.encode([request.query]).tolist()

    # Apply metadata filter if requested
    where_clause = None
    if request.filter_type:
        where_clause = {"type": request.filter_type}

    # Query Chroma
    results = collection.query(
        query_embeddings=query_embedding,
        n_results=request.num_results,
        where=where_clause
    )

    # Format output
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    response_items = []
    for doc, meta, dist in zip(documents, metadatas, distances):
        response_items.append({
            "content": doc,
            "metadata": meta,
            "distance": dist  # Lower distance = more similar
        })

    return {"results": response_items}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
