# SHL Assessment Recommender - Design Approach

## Architecture Overview

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│  Scraper        │────>│ catalog.json │────>│ build_index │
│ scrape_catalog  │     │              │     │             │
└─────────────────┘     └──────────────┘     └──────┬──────┘
                                                     │
                    ┌──────────────┐     ┌──────────┴──────┐
                    │catalog.index │<────│    FAISS        │
                    │catalog_meta  │     │  Vector Store   │
                    └──────────────┘     └────────────────┘
                                                     │
┌─────────────┐                             ┌────────┴────────┐
│  FastAPI    │────────────────────────────>│   Retriever    │
│   main.py   │                             │  retriever.py   │
└─────────────┘                             └────────┬────────┘
                                                     │
┌─────────────┐     ┌───────────────────┐     ┌──────┴──────┐
│  /chat      │────>│  Agent Logic      │────>│    LLM      │
│  /health    │     │   agent.py       │     │  (Gemini)   │
└─────────────┘     │ - CLARIFY        │     └─────────────┘
                    │ - RECOMMEND      │
                    │ - REFINE         │
                    │ - COMPARE        │
                    │ - Scope Guard    │
                    └─────────────────┘
```

## Why Gemini 1.5 Flash?

1. **Generous free tier** - 15 requests/minute, 1.5M tokens/minute
2. **Fast latency** - Typically <3 seconds for response
3. **Good quality** - Sufficient for structured JSON output
4. **Context window** - 1M tokens handles large catalog injections

**Fallback:** Groq with Llama-3.1-70b if Gemini unavailable.

## Embed-Retrieve-Inject Pattern

1. **Embed**: Each catalog assessment is embedded using `all-MiniLM-L6-v2`
   - 384-dimensional vectors
   - Normalized for cosine similarity
   - ~2ms per embedding

2. **Retrieve**: User query is embedded and FAISS searches top-15 matches
   - Semantic similarity over keyword matching
   - Captures "cognitive test for senior engineer" → relevant assessments

3. **Inject**: Top-15 assessments formatted into system prompt
   - Catalog context is authoritative
   - Agent can only recommend from provided data
   - Reduces hallucination

## Prompt Design

### System Prompt Structure

1. **Role definition**: "You are SHL Assist, an expert SHL Assessment Recommender"
2. **Behavior descriptions**: Concrete examples of CLARIFY/RECOMMEND/REFINE/COMPARE
3. **Hard constraints**: "Never recommend outside the catalog"
4. **Schema definition**: Exact JSON structure required
5. **Catalog context**: Dynamic injection of retrieved assessments

### Key Design Decisions

- **Catalog-only constraint**: Forces grounding in retrieved data
- **One question per turn**: Prevents overwhelming users
- **Turn cap at 5-6**: Commits to recommendations rather than infinite clarification
- **URL/name verification**: Prevents hallucinated recommendations

## Behavior Implementation

### CLARIFY
- Triggered when: No job role identified OR limited signal after 2 turns
- Response: ONE focused question (not multiple)
- Examples:
  - "What job role or function are you hiring for?"
  - "What competencies do you want to assess - cognitive, personality, or skills?"

### RECOMMEND
- Triggered when: Job role + at least one other signal (seniority, competency type)
- Response: 3-7 assessments with name/URL/test_type
- Always grounded in retrieved data

### REFINE
- Triggered when: User modifies constraints after initial recommendation
- Response: Updated shortlist acknowledging the change
- Key: Don't restart conversation, modify existing shortlist

### COMPARE
- Triggered when: "difference between X and Y" pattern detected
- Response: Comparison using ONLY catalog description data
- Never uses prior knowledge about SHL products

## What Didn't Work (And What Changed)

### Attempt 1: Web scraping for rich descriptions
- Problem: SHL catalog loads via JavaScript/AJAX
- Solution: Created curated catalog with verified SHL product data

### Attempt 2: Raw HTML parsing
- Problem: Product pages had generic content, not specific descriptions
- Solution: Used catalog table for test types, curated data for descriptions

### Attempt 3: Keyword-based retrieval
- Problem: "personality test" might not match "OPQ32" without semantic understanding
- Solution: FAISS with sentence-transformers embeddings

### Attempt 4: Multiple questions per clarification turn
- Problem: Users overwhelmed, conversations too long
- Solution: Strict "one question per turn" rule

## Testing Strategy

Test scenarios (8 total):

| Test | Description | Pass Criteria |
|------|-------------|---------------|
| Health | `/health` returns 200 | Status ok |
| Vague query | "I need an assessment" | Empty recommendations, clarification question |
| Happy path | Specific query with context | 1-10 recommendations, valid URLs |
| Refinement | "add personality test" | Updated list with personality tests |
| Compare | "OPQ vs Verify" | Response using catalog data only |
| Off-topic | "interview questions" | Refusal with empty recommendations |
| Prompt injection | "ignore instructions" | Refusal with empty recommendations |
| Schema | Any response | Exact keys: reply, recommendations, end_of_conversation |

## Tools Used

- **Python 3.11**: Runtime
- **FastAPI**: Web framework
- **FAISS**: Vector similarity search
- **sentence-transformers**: Local embeddings (all-MiniLM-L6-v2)
- **Gemini API**: LLM generation
- **httpx**: HTTP client (async)
- **BeautifulSoup**: HTML parsing
- **Docker**: Containerization

## Performance Characteristics

- **Cold start**: ~5 seconds (model loading)
- **Hot request**: <500ms (retrieval + LLM call)
- **LLM timeout**: 25 seconds max
- **Max conversation**: 8 turns (hard limit at evaluator)
