import streamlit as st
import os
from src.helpers.summarizer import serialize_messages
from src.helpers.graph_operations import start_new_chat, continue_chat, finish_chat
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(
    page_title="Agentic RAG System",
    page_icon="🤖",
    layout="wide"
)

# Custom CSS for better styling
st.markdown("""
<style>
    body, .stApp {
        background-color: #18181B !important;
        color: #E5E7EB !important;
    }
    .main-header {
        background: linear-gradient(135deg, #23272F 0%, #2D3140 100%) !important;
        padding: 2rem;
        border-radius: 10px;
        color: white !important;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .chat-message {
        padding: 1.5rem;
        border-radius: 12px;
        margin-bottom: 1.5rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.15);
        border: 1px solid rgba(255,255,255,0.07);
        color: #E5E7EB !important;
    }
    .user-message {
        background: linear-gradient(135deg, #23272F 0%, #2D3140 100%) !important;
        color: #E5E7EB !important;
        margin-left: 15%;
        margin-right: 5%;
        border-left: 4px solid #6366F1;
    }
    .bot-message {
        background: linear-gradient(135deg, #23272F 0%, #3B3355 100%) !important;
        color: #E5E7EB !important;
        margin-left: 5%;
        margin-right: 15%;
        border-left: 4px solid #4B5563;
    }
    .status-card {
        background: #23272F !important;
        color: #E5E7EB !important;
        border-left: 4px solid #6366F1;
    }
    .quick-query-btn, .stButton > button {
        background: #23272F !important;
        color: #E5E7EB !important;
        border: 1px solid #23272F;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .quick-query-btn:hover, .stButton > button:hover {
        background: #18181B !important;
        color: #A5B4FC !important;
    }
    .stTextArea > div > div > textarea {
        background: #23272F !important;
        color: #E5E7EB !important;
        border: 1px solid #23272F;
        border-radius: 8px;
    }
    .stTextArea > div > div > textarea:focus {
        border-color: #6366F1;
        box-shadow: 0 0 0 2px #6366F1;
    }
    .stSidebar {
        background: #18181B !important;
    }
    .stExpander > div > div > div {
        background: #23272F !important;
        color: #E5E7EB !important;
    }
    .stMarkdown > div > div > div {
        color: #E5E7EB !important;
    }
    .stInfo, .stSuccess, .stWarning, .stError {
        background: #23272F !important;
        color: #E5E7EB !important;
        border: 1px solid #23272F;
    }
    .block-container {
        max-width: 66vw !important;
        margin-left: auto !important;
        margin-right: auto !important;
        padding-left: 2rem !important;
        padding-right: 2rem !important;
        border: 1.5px solid rgba(255,255,255,0.10) !important;
        border-radius: 16px !important;
        box-sizing: border-box;
    }
</style>
""", unsafe_allow_html=True)

# Header with gradient background
st.markdown("""
<div class="main-header">
    <h1>🤖 Agentic RAG System</h1>
    <p><strong>LangGraph under the hood</strong></p>
</div>
""", unsafe_allow_html=True)

# About section
if 'about_expanded' not in st.session_state:
    st.session_state['about_expanded'] = False

with st.expander("ℹ️ How it works", expanded=st.session_state['about_expanded']):
    st.markdown("""
    **This system uses a graph-based agent architecture to process your queries and generate responses.**

    ### Features:
    - **Web Search Mode**: Enable to search the web for real-time information
    - **Document Processing**: Upload PDF files and ask questions about your documents
    - **Smart Routing**: The system automatically routes queries to the best processing method
    - **Conversation Memory**: Maintains context across multiple interactions
    
    ### Quick Start:
    1. **For Web Search**: Enable the toggle and use quick query buttons or type your own question
    2. **For Documents**: Upload PDF files and ask questions about the content
    3. **View Results**: See responses and understand how the agent processed your query
    """)

# --- Session State Initialization ---
if 'data_ingested' not in st.session_state:
    st.session_state['data_ingested'] = False
if 'file_paths' not in st.session_state:
    st.session_state['file_paths'] = []
if 'status' not in st.session_state:
    st.session_state['status'] = 'Waiting for input'
if 'messages' not in st.session_state:
    st.session_state['messages'] = []
if 'latest_result' not in st.session_state:
    st.session_state['latest_result'] = None
if 'finish' not in st.session_state:
    st.session_state['finish'] = False
if 'thread_id' not in st.session_state:
    st.session_state['thread_id'] = None
if 'is_processing' not in st.session_state:
    st.session_state['is_processing'] = False

if 'query_counter' not in st.session_state:
    st.session_state['query_counter'] = 0

# --- Reset chat button ---
def start_new_chat_wrapper(initial_query, web_search, messages, file_paths):
    # Serialize messages to ensure they are JSON serializable
    serialized_messages = serialize_messages(messages)
    
    try:
        data = start_new_chat(initial_query, web_search, serialized_messages, file_paths)
        st.session_state['thread_id'] = data['thread_id']
        state = data['state']
        # Messages from API are already in the correct format, no need to serialize again
        st.session_state['messages'] = state.get('messages', [])
        st.session_state['latest_result'] = state.get('answer', None)
        st.session_state['data_ingested'] = state.get('data_ingested', False)
        st.session_state['file_paths'] = file_paths
        st.session_state['status'] = state.get('status', 'Waiting for input')
        # Clear the query input by incrementing counter
        st.session_state['query_counter'] += 1
        # Rerun to immediately show the updated conversation
        st.rerun()
    except Exception as e:
        st.session_state['thread_id'] = None
        st.error(f"Error starting new chat: {e}")

# --- Main Input Area ---
# Only show file upload if no conversation has started yet
if not st.session_state['messages']:
    import tempfile
    import shutil
    temp_dir = tempfile.mkdtemp()
    file_paths = []
    st.markdown("**📄 Document Upload:**")
    col1, col2 = st.columns([1, 1])
    with col1:
        uploaded_files = st.file_uploader(
            "Upload PDF files (multiple allowed):",
            type=["pdf"],
            accept_multiple_files=True,
            key="file_uploader_main",
            help="Select one or more PDF files to analyze"
        )
        if uploaded_files:
            st.success(f"✅ Uploaded {len(uploaded_files)} file(s)")
            for uploaded_file in uploaded_files:
                file_path = os.path.join(temp_dir, uploaded_file.name)
                with open(file_path, "wb") as f:
                    shutil.copyfileobj(uploaded_file, f)
                file_paths.append(file_path)
            st.session_state['data_ingested'] = False
            st.session_state['file_paths'] = file_paths
        else:
            st.session_state['data_ingested'] = True
            st.session_state['file_paths'] = []
else:
    uploaded_files = None
    file_paths = st.session_state.get('file_paths', [])

# --- Chat History Area (directly above query box) ---
if st.session_state['messages']:
    for msg in st.session_state['messages']:
        # Handle different message formats
        if hasattr(msg, 'content'):
            # LangChain message object
            role = msg.__class__.__name__
            content = msg.content
        elif isinstance(msg, dict):
            # Dictionary format
            role = msg.get('type', msg.get('role', 'unknown'))
            content = msg.get('content', str(msg))
        else:
            # Fallback
            role = 'unknown'
            content = str(msg)
        
        # Normalize role names
        if role in ["HumanMessage", "user", "human"]:
            role = "human"
        elif role in ["AIMessage", "bot", "ai", "assistant"]:
            role = "ai"
        
        if role == 'human':
            st.markdown(
                f"""
                <div class="chat-message user-message">
                    <strong>👤 You:</strong><br>{content}
                </div>
                """, unsafe_allow_html=True)
        elif role == 'ai':
            st.markdown(
                f"""
                <div class="chat-message bot-message">
                    <strong>🤖 Assistant:</strong><br><br>
                    {content}
                </div>
                """, unsafe_allow_html=True)
        else:
            st.markdown(
                f"""
                <div class="chat-message" style="background-color:rgba(255,255,255,0.1); color:rgba(255,255,255,0.7);">
                    <strong>{role}:</strong><br>{content}
                </div>
                """, unsafe_allow_html=True)
else:
    st.info("💡 Start a conversation by asking a question or using a quick query!")


# Use a unique key that changes when we want to clear the input
query_key = f"query_main_{st.session_state.get('query_counter', 0)}"

spinner_placeholder = st.empty()  # Reserve space above the text area

query = st.text_area(
    "Enter your question here...",
    value="",
    height=100,
    key=query_key,
    disabled=st.session_state['is_processing']
)

# --- Chat/Submit/Finish Buttons ---
if st.session_state['messages']:
    col1, col2, col_spacer = st.columns([1, 1, 3])
    with col1:
        submit_clicked = st.button("Submit", type="primary", use_container_width=True, disabled=not query.strip() or st.session_state['is_processing'])
    with col2:
        finish_clicked = st.button("Finish & Reset", type="secondary", use_container_width=True, disabled=st.session_state['is_processing'])
    reset_clicked = False
else:
    col1, col2, col_spacer = st.columns([1, 1, 3])
    with col1:
        submit_clicked = st.button("Submit", type="primary", use_container_width=True, disabled=not query.strip() or st.session_state['is_processing'])
    with col2:
        st.empty()
    finish_clicked = False
    reset_clicked = False

# Handle Finish & Reset button
if finish_clicked:
    if st.session_state.get('thread_id'):
        try:
            # First finish the chat
            data = finish_chat(st.session_state['thread_id'])
            st.session_state['status'] = 'Chat finished.'
            st.success(f"Chat finished successfully! Thread ID: {data.get('thread_id', 'N/A')}")
        except Exception as e:
            st.error(f"Error finishing chat: {e}")
    
    # Then reset the chat state
    st.session_state['messages'] = []
    st.session_state['data_ingested'] = False
    st.session_state['file_paths'] = []
    st.session_state['status'] = 'Waiting for input'
    st.session_state['latest_result'] = None
    st.session_state['finish'] = False
    st.session_state['thread_id'] = None
    st.session_state['query_counter'] += 1
    st.rerun()

# Handle Submit button
elif submit_clicked:
    query_to_use = query.strip()
    if query_to_use:
        if st.session_state.get('thread_id') is None:
            with st.spinner("Thinking..."):
                start_new_chat_wrapper(query_to_use, False, st.session_state['messages'], file_paths)
        else:
            st.session_state['is_processing'] = True
            with st.spinner("🧠 Thinking..."):
                try:
                    serialized_messages = serialize_messages(st.session_state['messages'])
                    data = continue_chat(
                        st.session_state['thread_id'],
                        query_to_use,
                        False,
                        serialized_messages,
                        file_paths,
                        st.session_state['data_ingested'],
                        st.session_state['status']
                    )
                    state = data['state']
                    st.session_state['messages'] = state.get('messages', [])
                    st.session_state['latest_result'] = state.get('answer', None)
                    st.session_state['data_ingested'] = state.get("data_ingested", False)
                    st.session_state['file_paths'] = file_paths
                    st.session_state['status'] = state.get('status', st.session_state['status'])
                    st.session_state['is_processing'] = False
                    st.session_state['query_counter'] += 1
                    st.rerun()
                except Exception as e:
                    st.session_state['data_ingested'] = False
                    st.session_state['status'] = 'Error'
                    st.session_state['is_processing'] = False
                    st.error(f"Error: {str(e)}")