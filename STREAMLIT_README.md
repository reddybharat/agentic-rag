# Streamlit Agentic RAG Application

This is a Streamlit web application that provides a user-friendly interface for the Agentic RAG system.

## Features

- **Interactive Query Interface**: Text area for entering questions
- **One-Click Response Generation**: Button to trigger the agent graph
- **Graph Visualization**: Automatic display of the agent graph structure
- **Real-time Processing**: Live response generation with loading indicators
- **Error Handling**: Graceful error handling and user feedback

## Installation

1. Install dependencies:
```bash
pip install -e .
```

2. Make sure you have the required environment variables set up (API keys, etc.)

## Running the Application

To run the Streamlit app:

```bash
streamlit run streamlit_app.py
```

The application will open in your default web browser at `http://localhost:8501`.

## Usage

1. **Enter a Query**: Type your question in the text area
2. **Generate Response**: Click the "Generate Response" button
3. **View Results**: See the AI response and graph visualization
4. **Repeat**: Ask more questions as needed

## File Structure

- `streamlit_app.py` - Main Streamlit application
- `basic/` - Core agent system files
  - `builder.py` - Graph builder
  - `nodes.py` - Graph nodes
  - `type.py` - Type definitions
  - `llm_runner.py` - LLM integration

## Troubleshooting

- If you encounter import errors, make sure all dependencies are installed
- Check that your environment variables are properly configured
- Ensure you have sufficient API credits for the LLM service 