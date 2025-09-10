# Lichen Protocol Chunker

A tool for chunking and embedding Lichen Protocol JSONs for RAG (Retrieval-Augmented Generation) applications.

## Features

- **Schema Validation**: Validates protocol JSONs against a comprehensive schema
- **Section-Aware Chunking**: Chunks protocols by sections with configurable token limits
- **Pluggable Embeddings**: Supports OpenAI and Sentence-BERT backends
- **FAISS Indexing**: Builds and maintains vector indexes for fast similarity search
- **CLI Interface**: Command-line tools for batch processing
- **Streamlit UI**: Drag-and-drop web interface for interactive processing

## Quick Start

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd lichen-chunker
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

### Configuration

1. Copy the environment template:
```bash
cp env.example .env
```

2. Edit `.env` to configure your settings:
```bash
# OpenAI API Key (optional - will use SBERT fallback if not set)
OPENAI_API_KEY=your_api_key_here

# Default embedding backend
EMBEDDING_BACKEND=openai

# Chunking parameters
MAX_TOKENS=600
OVERLAP_TOKENS=60

# Index location
INDEX_PATH=./index
```

### Usage

#### CLI Usage

Process a single protocol file:
```bash
python -m src.lichen_chunker.cli process samples/the_leadership_im_actually_carrying.json --backend sbert
```

Process multiple files:
```bash
python -m src.lichen_chunker.cli process samples/*.json --backend openai --max-tokens 800
```

Validate files:
```bash
python -m src.lichen_chunker.cli validate samples/*.json
```

Search the index:
```bash
python -m src.lichen_chunker.cli search "leadership burden" --top-k 5
```

#### Streamlit UI

Launch the web interface:
```bash
streamlit run ui/app.py
```

Then:
1. Upload protocol JSON files using the drag-and-drop interface
2. Configure chunking parameters in the sidebar
3. Click "Process Files" to chunk and embed
4. Use the search tab to query the index

## Project Structure

```
lichen-chunker/
├── README.md
├── requirements.txt
├── pyproject.toml
├── env.example
├── libs/
│   ├── protocol_template_schema_v1.json
│   └── protocol_template_locked_v1.json
├── samples/
│   └── the_leadership_im_actually_carrying.json
├── src/lichen_chunker/
│   ├── __init__.py
│   ├── types.py
│   ├── schema_validation.py
│   ├── chunking.py
│   ├── embeddings/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── openai_backend.py
│   │   └── sbert_backend.py
│   ├── indexer.py
│   ├── io_utils.py
│   ├── pipeline.py
│   └── cli.py
├── ui/
│   └── app.py
├── tests/
│   ├── test_validation.py
│   ├── test_chunking.py
│   └── test_pipeline_e2e.py
├── data/          # Generated chunk files
└── index/         # Generated FAISS indexes
```

## API Reference

### CLI Commands

- `validate`: Validate protocol JSON files against schema
- `chunk`: Chunk protocol files into sections
- `embed`: Embed chunks and build FAISS index
- `index`: Build or update FAISS index
- `process`: End-to-end processing (validate, chunk, embed, index)
- `search`: Search the index
- `stats`: Show index statistics

### Embedding Backends

#### OpenAI Backend
- Model: `text-embedding-3-large` (3072 dimensions)
- Requires: `OPENAI_API_KEY` environment variable
- Usage: `--backend openai`

#### Sentence-BERT Backend
- Model: `all-MiniLM-L6-v2` (384 dimensions)
- Offline: No API key required
- Usage: `--backend sbert`

### Chunking Strategy

The chunker creates section-aware chunks with the following structure:

1. **Protocol-level sections**: Title, Purpose, Outcomes, etc.
2. **Theme-level sections**: Each theme with its outcomes and questions
3. **Token-bounded**: Configurable max tokens with overlap
4. **Metadata-rich**: Each chunk includes protocol ID, section info, tokens, hash

### Index Structure

The FAISS index stores:
- `index.faiss`: Vector index file
- `docstore.pkl`: Metadata for each vector
- `metadata.parquet`: Human-readable metadata table

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/ tests/
ruff check src/ tests/
```

### Adding New Embedding Backends

1. Create a new backend class inheriting from `EmbeddingBackend`
2. Implement the required methods: `embed_text`, `embed_batch`, `dimension`, `name`
3. Add the backend to the pipeline factory

## Troubleshooting

### Common Issues

1. **"No module named 'faiss'"**: Install FAISS with `pip install faiss-cpu`
2. **"OpenAI API key not found"**: Set `OPENAI_API_KEY` environment variable or use `--backend sbert`
3. **"Schema validation failed"**: Check that your protocol JSON matches the required schema
4. **"Index not found"**: Run the processing pipeline first to create the index

### Performance Tips

1. Use SBERT backend for offline processing
2. Adjust `max_tokens` based on your use case (smaller = more chunks, larger = fewer chunks)
3. Use `--rebuild` flag to clear and rebuild indexes when needed

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]

