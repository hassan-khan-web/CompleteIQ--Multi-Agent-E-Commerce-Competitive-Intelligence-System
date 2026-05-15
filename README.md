# 🌌 CompleteIQ — Multi-Agent Competitive Intelligence

CompleteIQ is a production-grade E-commerce Intelligence System that uses a team of AI agents to monitor competitors, analyze product features, and optimize market positioning in real-time.

## ✨ Key Features

- **🤖 Multi-Agent Orchestration**: Three specialized agents (**Beacon**, **Nexus**, **Verse**) work together to provide 360° market insights.
- **🔍 Semantic Search**: Advanced vector-based search using ChromaDB to find similar competitor products even without keyword matches.
- **🕸️ Interactive Knowledge Graph**: A visual map of the entire product ecosystem, showing relationships between companies, categories, and features.
- **📊 Gradio Dashboard**: A beautiful, responsive web interface for running analyses and exploring the data.
- **⚡ Real-time Analytics**: Jaccard similarity-based feature gap analysis and automated pricing recommendations.

## 📁 Project Structure

- `app.py`: The main Gradio web application.
- `system_integration.py`: The core backend logic and agent orchestrator.
- `agents/`: Implementation of the specialized AI agents.
- `docs/`: Documentation, setup guides, and project milestones.
- `datasets/`: E-commerce product catalogs for analysis.
- `chroma_db/`: Persistent vector storage for semantic search.

## 🛠️ Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env with your API keys

# 3. Launch the dashboard
python app.py
```

## 📚 Documentation

For detailed setup instructions, architecture overview, and usage examples, please refer to the **[Setup Guide](docs/SETUP.md)**.

For the project development history and weekly progress, see the **[Milestones](docs/milestones/)**.

---
*Developed as a comprehensive competitive intelligence solution for modern e-commerce.*
