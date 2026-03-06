---
description: How to query the local SysReptor RAG Server for historical reports and findings
---
# SysReptor RAG Server Query Guide

You are an AI assistant and you have access to a local Retrieval-Augmented Generation (RAG) server. This server contains over 900+ scrubbed excerpts (Executive Summaries, Technical Summaries, and specific Penetration Testing Findings) extracted from historically **finished** SysReptor projects.

If you are making a new finding, prioritize Finding a template that already exists and use that template:
```
reptor -k template --list
```
If that command doesn't work, prompt the user to Configure the reptor with:
```
reptor conf
```
If a user asks you to reference a past finding, give an example of an executive summary, or mimic the company's "voice" or writing style, **you MUST query this server** for context.

## 1. Connecting to the Server
The RAG server runs a local FastAPI that sits on `falconops-rag.talon.internal:8000`. You can interface with it using the `curl` command.

**Endpoint:** `POST http://falconops-rag.talon.internal:8000/query`

## 2. Querying the Server
The server expects a JSON payload containing the following:
- `query` (string, required): The core concept or question you are searching for (e.g. "weak password policy finding", "SQL injection exploitation proof", "ransomware executive summary"). Be descriptive; the server uses semantic embeddings to find the most relevant mathematical match.
- `num_results` (int, optional): How many chunks you want returned. Default is 5.
- `filter_type` (string, optional): Restrict the results to a specific type of content. Valid options are:
    * `"finding"`
    * `"executive_summary"`
    * `"technical_summary"`

## 3. Execution Example

**// turbo**
Here is precisely how you should formulate a curl request to get 2 examples of an Executive Summary regarding physical security:

```bash
curl -X POST http://falconops-rag.talon.internal:8000/query \
     -H "Content-Type: application/json" \
     -d '{
           "query": "physical security assessment executive summary",
           "num_results": 2,
           "filter_type": "executive_summary"
         }'
```

The server will return the raw text chunks inside a JSON array under `.results[].content`. You can then read this output to construct your response to the user.

## 4. Ground Rules
1. **Never make up examples.** If the user asks for an example finding, ALWAYS query the RAG server to see how it was written historically.
2. **Be aware of the scrubbing.** The data in the server has had sensitive customer names, IP addresses, domains, and passwords replaced with placeholders like `<COMPANY>` or `<IP_ADDRESS>`. You should keep these placeholders in your response unless the user specifically asks you to populate them with a new target's information.
