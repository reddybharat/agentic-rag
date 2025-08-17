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


# Session state for About expander
if 'about_expanded' not in st.session_state:
    st.session_state['about_expanded'] = True

with st.expander("ℹ️ About", expanded=st.session_state['about_expanded']):
    st.markdown("""
    This system uses a graph-based agent architecture to process your queries and generate responses.

    **How it works:**
    - If you enable Web Search, you can either use the quick query buttons for trending/general questions or enter your own custom query.
    - If Web Search is disabled, you can upload your own PDF files and ask custom questions about your documents.
    - The system ingests your data and answers in one step.
    - View the response and graph visualization to understand how the agent processed your query.
    """)

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
if 'status' not in st.session_state:
    st.session_state['status'] = 'Waiting for input'




# Main content area is now a single column
st.subheader("Upload PDF files and ask a question")
# Web search toggle
web_search = st.toggle(
    "Enable Web Search",
    value=False,
    help="Toggle to allow the agent to use web search in addition to your uploaded files."
)

import tempfile
import shutil
import os
temp_dir = tempfile.mkdtemp()
file_paths = []

# UI logic: show quick queries if web_search is ON, else show file uploader
if web_search:
    # Show quick queries only
    st.markdown("**Quick Test Queries:**")
    colA, colB, colC = st.columns(3)
    with colA:
        weather_clicked = st.button("Weather in London", type="secondary", use_container_width=True)
    with colB:
        richest_clicked = st.button("Top 10 Richest People", type="secondary", use_container_width=True)
    with colC:
        ai_news_clicked = st.button("Latest AI News", type="secondary", use_container_width=True)
    uploaded_files = None
else:
    # Show file uploader only
    uploaded_files = st.file_uploader(
        "Upload PDF files (multiple allowed):",
        type=["pdf"],
        accept_multiple_files=True,
        key="file_uploader_main"
    )
    weather_clicked = richest_clicked = ai_news_clicked = False
    if uploaded_files:
        for uploaded_file in uploaded_files:
            file_path = os.path.join(temp_dir, uploaded_file.name)
            with open(file_path, "wb") as f:
                shutil.copyfileobj(uploaded_file, f)
            file_paths.append(file_path)

# Query input and submit
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
            # Update status
            if web_search:
                st.session_state['status'] = 'Ready (Web Search)'
            elif file_paths:
                st.session_state['status'] = 'Ready (PDF Uploaded)'
            else:
                st.session_state['status'] = 'Waiting for input'

            # Add anchor for response and scroll to it
            st.markdown('<a id="response"></a>', unsafe_allow_html=True)
            st.subheader("Response")
            st.markdown(response.get("answer", "No response generated"))
            st.markdown("<script>window.location.hash = 'response';</script>", unsafe_allow_html=True)

            # Save the graph image for later display in About section
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
            st.session_state['status'] = 'Error'
            st.error(f"Error: {str(e)}")



# Footer
st.markdown("---")
st.markdown("*Powered by LangGraph and Streamlit*")