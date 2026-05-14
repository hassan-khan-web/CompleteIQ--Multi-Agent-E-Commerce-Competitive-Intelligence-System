# Copilot Instructions for CompleteIQ E-Commerce Intelligence System

## Project Overview

CompleteIQ is a multi-agent competitive intelligence system for e-commerce. It analyzes competitor products, identifies pricing opportunities, and generates insights through a modular, traced architecture.

**Current Status**: Weeks 1-2 complete (foundation and data processing). Weeks 3-8 are planned for semantic search, agents, orchestration, knowledge graph, integration, and production deployment.

## Environment Setup

### Prerequisites
- Python 3.8+
- Virtual environment: `myenv/` (already exists in repo)
- Dependencies managed via `requirements.txt`

### Setup Commands
```bash
# Activate virtual environment
source myenv/bin/activate

# Install dependencies (if needed)
pip install -r requirements.txt

# Set environment variables (.env required)
# Must contain: OPENAI_API_KEY, LANGFUSE_PUBLIC_KEY, LANGFUSE_SECRET_KEY, LANGFUSE_HOST
```

### Running Scripts
- **Week 1 (EDA)**: `python eda_analysis.py` - Loads data, initializes observability, runs exploratory analysis
- **Week 2 (Processor)**: `python product_catalog_processor.py` - Normalizes product catalogs with Langfuse tracing

## Architecture & Design Patterns

### Module Organization (Weeks 1-8 Plan)

The system grows in phases:

- **Week 1-2** (COMPLETE ✅): Foundation - environment setup, Langfuse observability, product data processing
- **Week 3** (NEXT): `semantic_search_engine.py` - ChromaDB vector store with embedding generation
- **Week 4**: `agents.py` - Three specialized agents (Price Monitor, Catalog Analyzer, Marketing Content)
- **Week 5**: `orchestrator.py` - Parallel multi-agent execution and result aggregation
- **Week 6**: `knowledge_graph_builder.py` - NetworkX graph relationships and PyVis visualization
- **Week 7**: `system_integration.py` + `config.py` - End-to-end system integration with comprehensive tracing
- **Week 8**: `app.py` + `api.py` - Gradio UI and FastAPI backend for production deployment

### Key Architectural Patterns

1. **Langfuse Tracing**
   - Every operation traced for observability
   - Use `langfuse.trace()` context manager for spans
   - Include input/output logging in all spans
   - Session ID generated per run: `SESSION_ID = str(uuid.uuid4())`

2. **Class-Based Architecture**
   - Main logic encapsulated in classes (e.g., `TracedProductCatalogProcessor`)
   - Classes have `__init__()` and domain-specific methods
   - Type hints required: `def method(param: Type) -> ReturnType`

3. **Data Flow**
   - Products loaded → normalized → embedded → indexed → searched → analyzed by agents
   - Each module is stateless except where persistence needed (ChromaDB, vector store)

4. **Pydantic for Structured Outputs** (Week 4+)
   - Agents must use Pydantic models for validated outputs
   - Example structure: `class PriceAnalysis(BaseModel): price_recommendation: float, confidence_score: float`
   - Used for agent outputs to ensure type safety and serialization

5. **Async/Parallel Execution** (Week 5+)
   - Multi-agent orchestration uses asyncio for parallel execution
   - 30-second timeout for agent completion
   - Exponential backoff retry logic (max 3 retries)

### Data Structures

**Product Normalization** (from Week 2):
```python
{
    "company": str,
    "category": str,
    "product_name": str,
    "price": float,
    "currency": str,
    "features": List[str],  # normalized
    "discount_percent": int,  # extracted from discount string
    "effective_price": float,  # price after discount
    "availability": str,
    "sku": str
}
```

**Vector Store Metadata** (Week 3):
- Store `company`, `category`, `product_id` as filterable metadata
- Enable filtered search by company/category

**Agent Output Format** (Week 4):
- All agents return Pydantic models with structured fields
- Must include `confidence_score` (0-1) and `reasoning` (str)
- Serializable to JSON for reporting

## Key Code Conventions

### Type Hints
- Always use type hints on function parameters and return types
- Use `Optional[T]` for nullable types, avoid bare `None`
- Use `List[T]`, `Dict[K, V]`, `Tuple[T, ...]` for collections

### Function Naming
- Public methods: `snake_case`
- Private methods: `_snake_case` prefix
- Classes: `PascalCase`
- Constants: `UPPER_CASE`

### Error Handling
- Use try-except with specific exceptions (not bare `except`)
- Log errors with context: `print(f"[ERROR] {operation}: {e}")`
- Implement retry logic for API calls (use `tenacity` library)

### Session Management
- Generate session ID at script start: `SESSION_ID = str(uuid.uuid4())`
- Pass session ID to Langfuse traces for correlation
- Print session ID for debugging

### Feature Normalization
- Standardize feature strings (lowercase, consistent naming)
- Remove duplicates from feature lists
- Preserve source intent (don't over-normalize)

### Discount Parsing
- Extract percentage from strings like "10% off", "20% off + Free Case"
- Return tuple: `(percentage: int, description: str)`
- Default to 0% if parsing fails

## Dependencies & Libraries

**Core Libraries** (in requirements.txt):
- `openai==1.59.6` - GPT-4 and embeddings
- `langfuse==2.57.1` - Observability and tracing
- `langchain==0.3.14` + `langchain-openai`, `langchain-community`, `langchain-core` - Agent framework
- `chromadb` - Vector store (Week 3)
- `pandas` - Data processing
- `matplotlib`, `seaborn` - Visualization
- `networkx`, `pyvis` - Knowledge graph and visualization (Week 6)
- `pydantic>=2.0` - Data validation (Week 4+)
- `tenacity` - Retry logic
- `fastapi`, `uvicorn` - API server (Week 8)
- `gradio` - Web UI (Week 8)

**Important Versions**:
- Pydantic must be >=2.0 for compatibility with LangChain
- Python-dotenv required for environment loading

## Testing & Validation

### Validation Checkpoints

Each week has validation points. Example (Week 3):
- ChromaDB initialized with collection
- All products embedded successfully
- Semantic search returns relevant results
- Filtering by company/category works
- Metadata preserved in vector store

### Test Data
- 12 products across 3 categories (Wireless Headphones, Smart Watches, Portable Speakers)
- 2 competing companies (Company X, Company Y)
- Each product has features, pricing, discounts, availability

### Running Quick Tests
When implementing a new module:
1. Test with all 12 sample products
2. Verify Langfuse tracing captures operations
3. Check data integrity (no nulls, proper types)
4. Validate performance (should complete in reasonable time)

## Observability & Logging

### Langfuse Tracing

Initialize at script start:
```python
langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
    host=os.getenv("LANGFUSE_HOST", "https://jp.cloud.langfuse.com")
)
```

Use for operation tracing:
```python
with langfuse.trace(name="operation_name") as trace:
    # Log input/output
    trace.input = {"key": value}
    result = perform_operation()
    trace.output = result
```

### Print Statements
- Use structured format: `print(f"[LEVEL] message")` where LEVEL = "INFO", "WARN", "ERROR"
- Log operation start/end with timing info
- Include relevant context (IDs, counts, status)

## Important Notes

### Environment Variables Required
- `OPENAI_API_KEY`: OpenAI API key (sk-proj-*)
- `LANGFUSE_PUBLIC_KEY`, `LANGFUSE_SECRET_KEY`: Langfuse credentials
- `LANGFUSE_HOST`: Defaults to `https://jp.cloud.langfuse.com` if not set
- `DATA_DIR`: Path to datasets (default: `./datasets/ecommerce/`)

### Dataset Handling
- `eda_analysis.py` automatically clones dataset from GitHub if not present
- Falls back to mock data if clone fails
- Dataset stored in `./datasets/ecommerce/`

### Vector Store Location
- ChromaDB persisted in `./chroma_db/` directory
- Should be gitignored (already in .gitignore)

### Adding New Agents (Week 4+)
1. Define Pydantic output model
2. Create agent class with LangChain framework
3. Implement tracing within agent methods
4. Add to orchestrator for parallel execution
5. Validate output with Pydantic schema

### Graph Visualization (Week 6)
- Use PyVis for interactive HTML output
- Node attributes: id, label, company, category, price
- Edge attributes: type (e.g., "competes_with", "has_feature"), weight
- Export to `outputs/knowledge_graph.html` for viewing

## Week-by-Week Deliverables

See `docs/IMPLEMENTATION_PLAN_WEEKS_3_TO_8.md` for detailed breakdown.

**Quick Reference**:
- **Week 3**: Semantic search with ChromaDB (4-6 hours)
- **Week 4**: Three specialized agents with Pydantic outputs (6-8 hours)
- **Week 5**: Multi-agent orchestration with async execution (4-6 hours)
- **Week 6**: Knowledge graph with NetworkX and visualization (4-6 hours)
- **Week 7**: System integration and end-to-end tracing (3-4 hours)
- **Week 8**: Gradio UI and production deployment (3-5 hours)

## Common Patterns

### Processing a Catalog
```python
processor = TracedProductCatalogProcessor()
normalized_products = processor.process_catalog_with_tracing(catalog_dict)
```

### Comparing Products
```python
comparison = processor.compare_products(product_x, product_y)
# Returns: {"matching_features": [...], "differences": [...], "price_gap": {...}}
```

### API Key Handling
- Load via `from dotenv import load_dotenv; load_dotenv()`
- Access via `os.getenv("KEY_NAME")`
- Check for missing keys and warn if needed

## File Locations

```
CompleteIQ-E-commerce/
├── eda_analysis.py                (Week 1 - exploration & setup)
├── product_catalog_processor.py    (Week 2 - normalization & comparison)
├── semantic_search_engine.py       (Week 3 - vector store & search)
├── agents.py                       (Week 4 - price, catalog, marketing agents)
├── orchestrator.py                 (Week 5 - multi-agent coordination)
├── knowledge_graph_builder.py      (Week 6 - graph relationships)
├── system_integration.py           (Week 7 - end-to-end integration)
├── config.py                       (Week 7 - configuration management)
├── app.py                          (Week 8 - Gradio UI)
├── api.py                          (Week 8 - FastAPI backend, optional)
├── .env                            (secrets, not in git)
├── requirements.txt                (dependencies)
├── .github/
│   └── copilot-instructions.md     (this file)
├── docs/
│   ├── WEEK_BY_WEEK_SUMMARY.md
│   ├── IMPLEMENTATION_PLAN_WEEKS_3_TO_8.md
│   └── week_*_progress.md
├── datasets/
│   └── ecommerce/                  (cloned from GitHub, not in git)
└── chroma_db/                      (vector store, not in git)
```

## Tips for Working on Future Weeks

1. **Before Starting a Week**: Read the validation checkpoints and test data requirements
2. **Trace Everything**: Use Langfuse spans for all significant operations
3. **Keep Modules Independent**: Each week's module should be testable in isolation
4. **Test with Sample Data**: Use the 12 products across 2 companies for quick validation
5. **Follow Naming Conventions**: Classes are PascalCase, methods are snake_case
6. **Document Agent Outputs**: Use Pydantic models to self-document expected outputs
7. **Handle Errors Gracefully**: Use retry logic for API calls, fallbacks for failures
8. **Check Requirements**: Review docs/IMPLEMENTATION_PLAN_WEEKS_3_TO_8.md before starting

## Performance Considerations

- **Embedding Batch Size**: Max 128 products per OpenAI API call
- **Agent Timeout**: 30 seconds for each agent in orchestrator
- **Vector Search**: Top-K should be configurable (default 5)
- **Memory**: System runs on 4GB minimum, 8GB recommended

## Debugging Tips

- Check Langfuse dashboard for operation traces and token usage
- Print session ID early in each script for correlation
- Use `.env` file validation to catch missing API keys early
- Test with small datasets first before scaling to all products
