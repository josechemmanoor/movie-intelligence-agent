# Movie Intelligence & Follow-up Assistant

An AI agent for querying subtitle (`.srt`) datasets of up to 100 movies, retrieving relevant dialogue/scenes with precise timestamp citations, and sending scene summaries/quote analysis through an MCP email tool.

## Features

- Parses `.srt` files with robust timestamp handling.
- Extracts movie title, subtitle timestamps, dialogue and neighboring context.
- Chunks subtitle content while preserving source metadata.
- Embeds chunks with `sentence-transformers`.
- Stores vectors in ChromaDB for semantic retrieval.
- Uses Gemini for grounded question answering.
- Every answer includes movie title and timestamp citations.
- Routes informational queries to RAG.
- Routes email/action requests to RAG + MCP email tool.
- Asks for clarification when movie/quote/recipient is ambiguous or missing.
- Streamlit chat UI.
- MCP server exposing a standard `send_email` tool.
- No credentials are committed to the repository.

## Project Structure

```text
movie-intelligence-agent/
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── subtitle_parser.py
│   ├── vector_store.py
│   ├── rag.py
│   ├── agent.py
│   ├── mcp_email_server.py
│   └── app.py
├── data/
│   └── movies/
│       └── put .srt files here
├── tests/
│   └── test_subtitle_parser.py
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 1. Setup

Python 3.10+ is recommended.

```bash
python -m venv .venv
```

Windows:

```bash
.venv\Scripts\activate
```

macOS/Linux:

```bash
source .venv/bin/activate
```

Install:

```bash
pip install -r requirements.txt
```

Create `.env` from `.env.example` and add your Gemini API key.

## 2. Add subtitles

Put up to 100 `.srt` files in:

```text
data/movies/
```

Example:

```text
data/movies/Interstellar.srt
data/movies/Inception.srt
data/movies/The_Dark_Knight.srt
```

The filename is used as the default movie title.

## 3. Build the vector index

```bash
python -m src.vector_store
```

The command parses all `.srt` files, creates semantic chunks, embeds them, and stores them in ChromaDB.

To rebuild the collection:

```bash
python -m src.vector_store --reset
```

## 4. Test RAG directly

```bash
python -m src.rag
```

Or use the Streamlit UI:

```bash
streamlit run src/app.py
```

## 5. MCP email tool

The MCP server exposes:

- `send_email(to, subject, body)`

Run it directly:

```bash
python -m src.mcp_email_server
```

The agent can also invoke the MCP tool in-process for the Streamlit workflow. This keeps the demo simple while still implementing the MCP server using the Model Context Protocol SDK.

Configure SMTP in `.env`. For Gmail, use an App Password rather than your normal account password.

## Query examples

### Informational

```text
What does Cooper say about his father?
```

Expected response includes:

```text
[Interstellar | 00:xx:xx - 00:xx:xx]
```

### Scene retrieval

```text
Find the scene where Cooper talks about leaving his children.
```

### Email action

```text
Email me a summary of the scene where Cooper talks about leaving his children.
Recipient: example@gmail.com
```

### Ambiguous request

```text
Send me the scene where he talks about his father.
```

If multiple movies/characters/scenes are possible, the agent asks for clarification instead of guessing.

## Architecture

```text
                         ┌─────────────────┐
                         │ Streamlit UI    │
                         └────────┬────────┘
                                  │
                                  ▼
                         ┌─────────────────┐
                         │ Agent / Router  │
                         └──────┬─────┬────┘
                                │     │
                   Information  │     │ Action
                                ▼     ▼
                         ┌─────────┐ ┌──────────────┐
                         │   RAG   │ │ RAG + MCP    │
                         └────┬────┘ │ Email Tool   │
                              │      └──────┬───────┘
                              ▼             │
                         ┌─────────┐        ▼
                         │ Chroma  │     SMTP Email
                         │ Vector  │
                         │ Store   │
                         └─────────┘
```

## Evaluation mapping

| Requirement | Implementation |
|---|---|
| `.srt` parsing | `subtitle_parser.py` |
| Timecode preservation | `start_seconds`, `end_seconds`, formatted timestamps |
| Metadata | movie title, timestamp range, subtitle index, source file |
| Chunking | overlapping subtitle windows |
| Vector retrieval | ChromaDB + SentenceTransformer |
| QA | Gemini grounded generation |
| Citation | movie + timestamp citation formatter |
| Intent routing | `agent.py` |
| Email action | `agent.py` + MCP server |
| MCP tooling | `mcp_email_server.py` |
| Ambiguity | clarification logic |
| UI | Streamlit |
| Documentation | this README |

## Important submission note

Do not commit `.env` or API keys.

Before submitting:

```bash
git status
git add .
git commit -m "Complete movie intelligence and MCP assistant"
git push
```

Make sure your GitHub repository contains meaningful commits showing development history.
