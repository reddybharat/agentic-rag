import streamlit as st
from src.graphs import builder
import os
from PIL import Image
from src.utils.logger import logger

# Set page config
st.set_page_config(
    page_title="Agentic RAG System",
    page_icon="🤖",
    layout="wide"
)

# Title and description
st.title("🤖 Agentic RAG System")
st.markdown("Upload PDFs and ask questions. The agent will ingest and answer in one step!")

# Initialize the graph
@st.cache_resource
def get_graph():
    """Cache the graph to avoid rebuilding it on every interaction"""
    return builder.build_graph()

# Get the graph
app = get_graph()

# Initialize session state
if 'data_ingested' not in st.session_state:
    st.session_state['data_ingested'] = False
if 'file_paths' not in st.session_state:
    st.session_state['file_paths'] = []

# Layout
col1, col2 = st.columns([2, 1])

with col1:
    st.subheader("Upload PDF files and ask a question")
    uploaded_files = st.file_uploader(
        "Upload PDF files (multiple allowed):",
        type=["pdf"],
        accept_multiple_files=True,
        key="file_uploader_main"
    )

    import tempfile
    import shutil
    import os
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f)
            file_paths.append(file_path)

    query = st.text_area(
        "Enter your question:",
        placeholder="e.g., Give me list of Top 10 richest people in the world currently",
        height=100,
        key="query_main"
    )

    if st.button("Submit", type="primary", use_container_width=True, disabled=not (file_paths and query.strip())):
        with st.spinner("Processing..."):
            try:
                response = app.invoke({
                    "files_uploaded": file_paths,
                    "query": query,
                    "data_ingested": False,
                    "answer": ""
                })
                st.session_state['data_ingested'] = response.get("data_ingested", False)
                st.session_state['file_paths'] = file_paths
                st.subheader("Response")
                st.write(response.get("answer", "No response generated"))

                # Save the graph image for later display in col2
                graph_bytes = app.get_graph().draw_mermaid_png()
                graph_path = "graph.png"
                with open(graph_path, "wb") as f:
                    f.write(graph_bytes)
                st.session_state['graph_ready'] = True
            except Exception as e:
                st.session_state['data_ingested'] = False
                st.session_state['graph_ready'] = False
                st.error(f"Error: {str(e)}")

with col2:
    # Sidebar with information
    st.subheader("ℹ️ About")
    st.markdown("""
    This system uses a graph-based agent architecture to process your queries and generate responses.
    
    **How it works:**
    1. Upload your PDF files and enter your question
    2. The system ingests and answers in one step
    3. View the response and graph visualization
    """)
    # Display system info
    st.subheader("🔧 System Info")
    st.markdown(f"""
    - **Graph Nodes**: {len(app.get_graph().nodes)}
    - **Status**: {'Ready' if st.session_state['data_ingested'] else 'Waiting for input'}
    """)

    # Graph Visualization below system info
    if st.session_state.get('graph_ready', False) and os.path.exists("graph.png"):
        st.subheader("Graph Visualization")
        image = Image.open("graph.png")
        st.image(image, caption="Agent Graph Structure")

# Footer
st.markdown("---")
st.markdown("*Powered by LangGraph and Streamlit*")

# Show logs in sidebar
with st.sidebar:
    st.subheader("📝 Internal Logs")
    logs = logger.get_logs()
    if logs:
        st.text_area("Logs", value="\n".join(logs), height=300, key="logs_display")
    else:
        st.info("No logs yet.") 