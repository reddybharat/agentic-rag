import streamlit as st
from src.graphs import builder
import os
from PIL import Image
from src.utils.logger import logger
from dotenv import load_dotenv
load_dotenv()

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
    # Web search toggle
    web_search = st.toggle(
        "Enable Web Search",
        value=False,
        help="Toggle to allow the agent to use web search in addition to your uploaded files."
    )
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

    # First row: Quick test buttons
    st.markdown("**Quick Test Queries:**")
    colA, colB, colC = st.columns(3)
    with colA:
        weather_clicked = st.button("Weather in London", type="secondary", use_container_width=True)
    with colB:
        richest_clicked = st.button("Top 10 Richest People", type="secondary", use_container_width=True)
    with colC:
        ai_news_clicked = st.button("Latest AI News", type="secondary", use_container_width=True)

    # Second row: Query input and submit
    query = st.text_area(
        "Enter your question:",
        height=100,
        key="query_main"
    )
    submit_clicked = st.button("Submit", type="primary", use_container_width=True, disabled=not query.strip())

    # Handle button logic
    query_to_use = query
    if weather_clicked:
        query_to_use = "What is the weather at London?"
    elif richest_clicked:
        query_to_use = "Give me list of Top 10 richest people in the world currently"
    elif ai_news_clicked:
        query_to_use = "What are the latest advancements in AI?"

    if submit_clicked or weather_clicked or richest_clicked or ai_news_clicked:
        with st.spinner("Processing..."):
            try:
                response = app.invoke({
                    "files_uploaded": file_paths,  # file_paths will be [] if no files
                    "query": query_to_use,
                    "data_ingested": False,
                    "answer": "",
                    "messages": [],  # Restore or add message history support
                    "web_search": web_search
                })
                st.session_state['data_ingested'] = response.get("data_ingested", False)
                st.session_state['file_paths'] = file_paths
                
                st.subheader("Response")
                st.markdown(response.get("answer", "No response generated"))

                # Save the graph image for later display in col2
                try:
                    graph_obj = app.get_graph() if hasattr(app, 'get_graph') else app
                    graph_bytes = graph_obj.draw_mermaid_png()
                except AttributeError:
                    # Fallback: try draw_mermaid() and convert to image if needed
                    mermaid_code = graph_obj.draw_mermaid()
                    # Optionally, use a library to convert mermaid to PNG if available
                    graph_bytes = None  # Placeholder if conversion is not implemented
                graph_path = "graph.png"
                if graph_bytes:
                    with open(graph_path, "wb") as f:
                        f.write(graph_bytes)
                st.session_state['graph_ready'] = True
            except Exception as e:
                st.session_state['data_ingested'] = False
                st.session_state['graph_ready'] = False
                st.error(f"Error: {str(e)}")

with col2:
    # About section
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
    try:
        graph_obj = app.get_graph() if hasattr(app, 'get_graph') else app
        node_count = len(graph_obj.nodes)
    except Exception:
        node_count = 'Unknown'
    st.markdown(f"""
    - **Graph Nodes**: {node_count}
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