# LangChain Demo

[English](README_EN.md) | [中文](README.md)

This is a collection of LangChain application examples demonstrating various use cases of LangChain.

### Project Structure

```
langchain-demo/
├── demo/
│   ├── langchain/           # LangChain Basic Features
│   │   ├── callback_demo.py     # Callback Examples
│   │   ├── json_parser_demo.py  # JSON Parsing
│   │   ├── memory_chain_demo.py # Memory Chain
│   │   ├── mysql_chain_demo.py  # MySQL Query
│   │   ├── react_chain_demo.py  # ReAct Pattern
│   │   ├── route_chain_demo.py  # Route Chain
│   │   └── tool_calling_demo.py # Tool Calling
│   ├── langgraph/           # LangGraph Features
│   │   ├── visualization_demo.py    # Graph Visualization
│   │   ├── simple_qa_demo.py       # Simple QA System
│   │   └── team_collaboration_demo.py # Team Collaboration
│   └── langsmith/           # LangSmith Features
│       └── stock_analysis_demo.py   # Stock Analysis
└── rag/                    # RAG Applications
    └── rag_web_app.py      # RAG Web App
```

### Setup

1. Create environment:
```bash
conda create -n langchain-demo python=3.11
conda activate langchain-demo
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env file with your configurations
```

### Running Examples

Each example can be run independently:

```bash
python demo/langchain/mysql_chain_demo.py
python demo/langgraph/simple_qa_demo.py
python demo/langsmith/stock_analysis_demo.py
```

### License

MIT License 