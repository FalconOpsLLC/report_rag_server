# SysReptor RAG Server

This directory contains a lightweight, fully self-contained Retrieval-Augmented Generation (RAG) server designed to provide context from historical, finished SysReptor Penetration tests. It exposes an easy-to-use REST API so that other AI agents can query the dataset locally or across a network.

## Features
- **Retrieval Only:** It returns raw JSON chunks containing Executive Summaries, Technical Summaries, and Findings based on semantic vector similarity.
- **Fast & Local:** Powered by `ChromaDB` and the `all-MiniLM-L6-v2` embedding model. It does not require any OpenAI/external API keys to run the database.
- **Scrubbed Data:** All data inside the vector database has had customer names, IP addresses, domains, and heuristic passwords scrubbed.

## Deployment Instructions

To deploy this RAG server on another machine, follow these steps:

1. **Move files:** Copy this entire directory (specifically `rag_server.py`, `ingest_data.py`, `scrubbed_rag_data.json`, and `requirements-rag.txt`) to the target server.
2. **Setup agents to use this RAG** Move the agent_workflows to the local machine running the agent, so the agent can have the proper system prompt to know how to use this rag server
4. **Setup virtual environment:** 
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
5. **Install Dependencies:**
    ```bash
    pip install -r requirements-rag.txt
    ```
6. **Ingest Data:** Create the local vector database instance in the `./chroma_db` folder:
    ```bash
    python3 ingest_data.py
    ```
7. **Run the Server:** Start the FastAPI server. It is configured to listen on `0.0.0.0`, meaning it will be accessible from any network interface on port `8000`:
    ```bash
    python3 rag_server.py
    ```
    *(Alternatively, use `nohup python3 rag_server.py &` to run in the background)*

---

## Agent Integration Guide (For AI Agents)

If you are an AI assistant trying to use the knowledge inside this RAG server, you can interface with it using standard HTTP requests (e.g., `curl` or `requests` library in Python).

### Endpoint
`POST http://<server_ip>:8000/query`

### Parameters

| Field | Type | Required | Description |
| ---- | ---- | ---- | --- |
| `query` | `string` | Yes | The natural language question you are trying to answer. |
| `num_results` | `int` | No | Number of chunks to return (Default: 5). |
| `filter_type` | `string` | No | Specifically scope results. Valid options: `"finding"`, `"executive_summary"`, `"technical_summary"`. Defaults to returning everything combined. |

### Example Request (`curl`)

```bash
curl -X POST http://127.0.0.0:8000/query \
     -H "Content-Type: application/json" \
     -d '{
           "query": "How do we write an executive summary regarding ransomware?",
           "num_results": 3,
           "filter_type": "executive_summary"
         }'
```

### Example Response

```json
{
  "results": [
    {
      "content": "The objective of the assessment was to identify vulnerabilities within...",
      "metadata": {
        "project_id": "70ba26e4-2b69-4142-bfc5-77be90335990",
        "type": "executive_summary"
      },
      "distance": 0.42
    }
  ]
}
```

### Tips for Agents
- If your initial query doesn't yield exactly what you want, try rephrasing the `query` string with different keywords. This uses Semantic Vector Search, so phrasing matters.
- Always check the `type` inside the `metadata` to ensure you are referencing the correct part of a report (e.g. don't paste an executive summary snippet into a finding template!).
