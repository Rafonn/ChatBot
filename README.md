# Intelligent Assistant for Industrial Operations

This project is an intelligent assistant designed to support industrial operations by integrating real-time data, document search, and service order management. It leverages advanced language models and retrieval-augmented generation (RAG) to provide contextual answers and automate information retrieval from multiple sources.

## Features

- **Real-Time Machine & Product Status:** Query live status of machines and products from the database.
- **Document Search (RAG):** Search manuals, procedures, and internal documents using semantic search with OpenAI embeddings and Chroma vector store.
- **Service Order Management:** Integrate with external APIs (e.g., Dude) to fetch and filter service orders.
- **Chat Interface:** Multi-user chat support with persistent chat history and logging.
- **Caching:** Uses Redis for LLM response caching and custom embedding cache for efficient document retrieval.

## Project Structure

```
main.py
src/
  agents/
    agents.py           # Main assistant logic and tool definitions
  cache/
    cache.py            # Embedding cache logic
  db/
    ...                 # Database connectors and loggers
  dude/
    ...                 # Service order API integration
  RAG/
    ...                 # RAG pipeline and vector DB
  tools/
    ...                 # Utilities and input schemas
```

## Why These Technologies?

### Python
Python is the backbone of this project due to its rich ecosystem for data processing, machine learning, and rapid prototyping. Its readability and extensive library support make it ideal for integrating multiple complex systems.

### LangChain & OpenAI
The assistant uses [LangChain](https://github.com/langchain-ai/langchain) to orchestrate language model interactions and tool usage. LangChain provides a modular way to combine LLMs with external tools, enabling the assistant to reason, retrieve, and act. OpenAI's GPT models are used for their advanced natural language understanding and generation, ensuring high-quality conversational experiences.

### Chroma Vector Store & Embeddings
For document search and retrieval-augmented generation (RAG), the project uses [Chroma](https://www.trychroma.com/) as a vector database. Documents and manuals are embedded using OpenAI's embedding models, allowing for semantic search and contextual answers. This approach enables the assistant to provide precise information from large unstructured datasets.

### Redis Cache
To optimize performance and reduce latency, Redis is used for caching LLM responses and embeddings. This ensures that repeated queries are served quickly and reduces API costs, while also supporting scalability for multiple concurrent users.

### SQL Server & API Integrations
Operational data, such as machine and product status, is stored in SQL Server databases, reflecting the industrial context where robust, transactional data storage is required. The assistant integrates with external APIs (such as the Dude service order system) to fetch and filter real-time service orders, providing a unified interface for users.

### Modular Tooling
The assistant is built around a modular tool system, where each @tool-decorated function encapsulates a specific capability (e.g., live status queries, document search, service order retrieval). This design allows for easy extension and maintenance as new requirements emerge.


## Usage

- The assistant can be run in multi-user mode (see `main.py`).
- It supports natural language queries about machines, products, documents, and service orders.
- Example queries:
  - "Qual o status da máquina A?"
  - "Buscar informações sobre segurança no manual de procedimentos."
  - "Quais ordens de serviço estão em andamento a máquina 1?"

## Customization

- **Add new tools:** Implement new @tool functions in [`src/agents/agents.py`](src/agents/agents.py).
- **Document ingestion:** Add or update documents and re-run the RAG indexer.
- **Database/API integration:** Extend connectors in [`src/db/`](src/db/) and [`src/dude/`](src/dude/).
