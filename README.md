# 🌌 Omnilytics — Multi-Agent E-Commerce Competitive Intelligence System

**Omnilytics** is a state-of-the-art, production-grade E-Commerce Intelligence Substrate powered by a collaborative triad of specialized AI agents. Designed for modern e-commerce enterprises, Omnilytics autonomously monitors competitor catalogs, evaluates feature overlap via semantic vector search, synthesizes market positioning, and generates tailored marketing copy in real-time.

---

## ✨ Key Features & Capabilities

- **🤖 Multi-Agent Triad Architecture**:
  - 💰 **Beacon (Price Monitor)**: Scours competitor catalogs to calculate price differentials, recommending tactical adjustments (`REDUCE`, `MAINTAIN`, `INCREASE`) backed by explicit economic reasoning.
  - 🔬 **Nexus (Catalog Analyzer)**: Evaluates macro-level catalog strength, categorizing company positioning (`PREMIUM`, `VALUE`, `BALANCED`) and extracting strategic market insights.
  - ✍️ **Verse (Marketing Content)**: Generates highly engaging, tone-tailored marketing headlines, descriptions, and unique selling points based on competitive feature advantages.
- **🎯 Granular Product Selection**: Run lightning-fast, quota-friendly competitive analyses on individual products (3 API calls) or perform comprehensive full-catalog sweeps (26 API calls).
- **🔍 Advanced Semantic Search**: Uses ChromaDB and state-of-the-art embedding models (`openai/text-embedding-3-small`) to discover competitor feature overlap without relying on exact keyword matches.
- **🕸️ Interactive Knowledge Graph**: Dynamically builds an interactive network visualization (`vis.js`) mapping the entire product ecosystem, company ownership, category taxonomies, and direct competitive relationships.
- **📊 Premium Gradio UI**: A sleek, modern, glassmorphism-inspired web dashboard featuring real-time execution metrics, interactive graphs, and rich markdown reporting.

---

## 📁 System Architecture & Directory Structure

```
Omnilytics/
├── app.py                         # Main Gradio Web Application & UI Definitions
├── config.py                      # System Configuration & Environment Validation
├── system_integration.py          # Core System Integration & Report Generation Engine
├── product_catalog_processor.py   # Catalog Ingestion, Normalization & Validation
├── semantic_search_engine.py      # ChromaDB Vector Store & Semantic Search Pipeline
├── knowledge_graph_builder.py     # NetworkX Knowledge Graph & HTML Visualization Engine
├── agents/                        # Specialized AI Agents & LLM Tooling
│   ├── beacon.py                  # Beacon Agent Implementation
│   ├── nexus.py                   # Nexus Agent Implementation
│   ├── verse.py                   # Verse Agent Implementation
│   ├── llm_utils.py               # Global Rate Limiting, 429 Retry & Chain Factories
│   └── base_models.py             # Pydantic v2 Domain Data Models
├── orchestrators/                 # Multi-Agent Orchestration Layer
│   └── multi_agent_orchestrator.py # Sequential Agent Execution & Error Handling
├── datasets/                      # Raw Input E-Commerce Product Catalogs (JSON)
├── docs/                          # Comprehensive System Documentation & Setup Guides
└── lib/                           # Local JS/CSS Dependencies for Graph Visualization
```

---

## 🚀 Quick Start Guide

### 1. Prerequisites & Installation
Ensure you have Python 3.10+ installed. Clone the repository and install the required dependencies:

```bash
git clone https://github.com/hassan-khan-web/Omnilytics--Multi-Agent-E-Commerce-Competitive-Intelligence-System.git
cd Omnilytics--Multi-Agent-E-Commerce-Competitive-Intelligence-System
pip install -r requirements.txt
```

### 2. Environment Configuration
Create a `.env` file in the root directory and add your API credentials:

```env
# OpenRouter API Key for free-tier LLM execution (DeepSeek, Nemotron, Gemma)
OPENROUTER_API_KEY=sk_or_v1_YOUR_OPENROUTER_KEY

# Optional Langfuse Observability Credentials
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_HOST=http://localhost:3000
```

### 3. Launch the Web Dashboard
Start the Gradio server:

```bash
python app.py
```

Navigate to `http://localhost:7860` in your browser to access the Omnilytics platform!

---

## 📚 Official Documentation

- **[System Setup & Architecture Guide](docs/SETUP.md)** — Detailed technical overview of system boot sequences, vector indexing, and agent contracts.
- **[LLM Agents Testing & Setup Archive](docs/LLM_AGENTS_TESTING_SETUP.md)** — Archival documentation covering model selection rationale, prompt templates, and standalone validation suites.
- **[Project Milestones & Development History](docs/milestones/)** — Comprehensive weekly progress reports tracking the evolution of the Omnilytics platform.

---
*Omnilytics — Empowering E-Commerce Enterprises with Autonomous Competitive Intelligence.*
