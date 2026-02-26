import json
import chromadb
from sentence_transformers import SentenceTransformer
import warnings
import os

warnings.filterwarnings("ignore")

DB_DIR = "./chroma_db"
DATA_FILE = "scrubbed_rag_data.json"
COLLECTION_NAME = "sysreptor_rag"

def main():
    print("[*] Loading data...")
    if not os.path.exists(DATA_FILE):
        print(f"[-] {DATA_FILE} not found!")
        return

    with open(DATA_FILE, "r") as f:
        projects = json.load(f)

    # Initialize ChromaDB client (persistent)
    client = chromadb.PersistentClient(path=DB_DIR)

    # We will use the all-MiniLM-L6-v2 model which is fast and lightweight
    print("[*] Initializing embedding model...")
    model = SentenceTransformer('all-MiniLM-L6-v2')

    # Get or create collection
    collection = client.get_or_create_collection(name=COLLECTION_NAME)

    documents = []
    metadatas = []
    ids = []

    doc_counter = 0

    print("[*] Parsing projects and chunking data...")
    for project in projects:
        project_id = project['source_project_id']

        # 1. Add Executive Summary
        if project.get('executive_summary'):
            exec_text = ""
            for k, v in project['executive_summary'].items():
                exec_text += f"{k}: {v}\n"
            if exec_text.strip():
                documents.append(exec_text)
                metadatas.append({"project_id": project_id, "type": "executive_summary"})
                ids.append(f"exec_{project_id}")
                doc_counter += 1

        # 2. Add Technical Summary
        if project.get('technical_summary'):
            tech_text = ""
            for k, v in project['technical_summary'].items():
                tech_text += f"{k}: {v}\n"
            if tech_text.strip():
                documents.append(tech_text)
                metadatas.append({"project_id": project_id, "type": "technical_summary"})
                ids.append(f"tech_{project_id}")
                doc_counter += 1

        # 3. Add Individual Findings
        for idx, finding in enumerate(project.get('findings', [])):
            finding_text = f"Title: {finding.get('title', '')}\n"
            finding_text += f"Severity: {finding.get('severity', '')}\n"
            finding_text += f"Summary: {finding.get('summary', '')}\n"
            finding_text += f"Technical Description: {finding.get('technical_description', '')}\n"
            finding_text += f"Vulnerability Description: {finding.get('vulnerability_description', '')}\n"
            finding_text += f"Business Impact: {finding.get('business_impact', '')}\n"
            finding_text += f"Recommendation: {finding.get('recommendation', '')}\n"
            # Exploitation proof often has a lot of code, we include it but prioritize the text above
            if finding.get('exploitation_proof'):
               finding_text += f"Exploitation Proof: {finding.get('exploitation_proof')}\n"

            if finding_text.strip():
                documents.append(finding_text)
                metadatas.append({
                    "project_id": project_id, 
                    "type": "finding",
                    "title": str(finding.get('title', 'Unknown'))
                })
                ids.append(f"finding_{project_id}_{idx}")
                doc_counter += 1

    print(f"[*] Prepared {len(documents)} document chunks. Computing embeddings and inserting to DB...")
    
    # Batch add to ChromaDB. ChromaDB can handle calculating embeddings if we pass an embedding function,
    # but since we initialized sentence transformers directly, we can manually generate them or pass them.
    # To keep dependencies light and robust, we generate them directly:
    
    # We add in batches to avoid memory issues
    batch_size = 100
    for i in range(0, len(documents), batch_size):
        end_idx = min(i + batch_size, len(documents))
        batch_docs = documents[i:end_idx]
        batch_metas = metadatas[i:end_idx]
        batch_ids = ids[i:end_idx]
        
        print(f"[*] Embedding batch {i} to {end_idx}...")
        batch_embeddings = model.encode(batch_docs).tolist()

        collection.add(
            embeddings=batch_embeddings,
            documents=batch_docs,
            metadatas=batch_metas,
            ids=batch_ids
        )

    print(f"[+] Successfully ingested {doc_counter} chunks into ChromaDB at {DB_DIR}!")

if __name__ == "__main__":
    main()
