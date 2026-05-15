# 🛠️ CompleteIQ: Setup & Usage Guide

CompleteIQ is a multi-agent competitive intelligence system designed for e-commerce. It automates the process of monitoring competitors, analyzing feature gaps, and generating marketing insights using AI agents.

## 📋 Prerequisites

- **Python 3.10+**
- **OpenAI API Key** (or OpenRouter API Key)
- **Langfuse Account** (Optional, for observability)

## 🚀 Installation

1. **Clone the Repository**
   ```bash
   git clone <repository-url>
   cd CompleteIQ-E-commerce
   ```

2. **Create a Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory:
   ```env
   OPENAI_API_KEY=your_key_here
   OPENROUTER_API_KEY=your_key_here  # Optional: defaults to OpenAI key
   LANGFUSE_PUBLIC_KEY=your_key
   LANGFUSE_SECRET_KEY=your_key
   LANGFUSE_HOST=https://jp.cloud.langfuse.com
   ```

## 🎮 How to Use

### 1. Launch the Dashboard (Recommended)
The easiest way to interact with the system is via the Gradio web interface:
```bash
python app.py
```
Open `http://localhost:7860` in your browser.

**Features in the UI:**
- **Dashboard**: Real-time health check of all AI agents and system components.
- **Semantic Search**: Find products across catalogs using natural language.
- **Knowledge Graph**: Explore an interactive network of products, features, and competitors.
- **Competitive Analysis**: Run deep analysis on specific products using the Beacon, Nexus, and Verse agents.

### 2. Run via Terminal (API Mode)
You can also run the system integration directly:
```bash
python system_integration.py
```
This will initialize the system, process catalogs, and generate a JSON analysis report in the `outputs/` folder.

## 🏗️ System Architecture

- **Beacon Agent**: Specializes in pricing and availability analysis.
- **Nexus Agent**: Focuses on feature parity and technical gaps.
- **Verse Agent**: Generates marketing copy and strategic positioning.
- **Semantic Search**: Powered by ChromaDB and vector embeddings.
- **Knowledge Graph**: Built with NetworkX for relationship mapping.

---
*For historical progress and technical details, see the [Milestones](./milestones/) folder.*
