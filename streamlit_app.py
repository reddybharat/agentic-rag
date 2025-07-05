import streamlit as st
import basic.builder
import os
from PIL import Image

# Set page config
st.set_page_config(
    page_title="Agentic RAG System",
    page_icon="🤖",
    layout="wide"
)

# Title and description
st.title("🤖 Agentic RAG System")
st.markdown("Ask questions and get AI-powered responses using our graph-based agent system.")

# Initialize the graph
@st.cache_resource
def get_graph():
    """Cache the graph to avoid rebuilding it on every interaction"""
    return basic.builder.build_graph()

# Get the graph
app = get_graph()

# Create two columns for layout
col1, col2 = st.columns([2, 1])

with col1:
    # User input section
    st.subheader("Ask Your Question")
    query = st.text_area(
        "Enter your query here:",
        placeholder="e.g., Give me list of Top 10 richest people in the world currently",
        height=100
    )
    
    # Button to generate response
    if st.button("🚀 Generate Response", type="primary", use_container_width=True):
        if query.strip():
            with st.spinner("Generating response..."):
                try:
                    # Generate response
                    response = app.invoke({"query": query})
                    
                    # Display response
                    st.subheader("Response")
                    st.write(response.get("answer", "No response generated"))
                    
                    # Save and display the graph image
                    st.subheader("Graph Visualization")
                    graph_bytes = app.get_graph().draw_mermaid_png()
                    
                    # Save the graph image
                    graph_path = "graph.png"
                    with open(graph_path, "wb") as f:
                        f.write(graph_bytes)
                    
                    # Display the image
                    if os.path.exists(graph_path):
                        image = Image.open(graph_path)
                        st.image(image, caption="Agent Graph Structure", width=400, height=300)
                    
                except Exception as e:
                    st.error(f"Error generating response: {str(e)}")
        else:
            st.warning("Please enter a query first.")

with col2:
    # Sidebar with information
    st.subheader("ℹ️ About")
    st.markdown("""
    This system uses a graph-based agent architecture to process your queries and generate responses.
    
    **How it works:**
    1. Enter your question in the text area
    2. Click the "Generate Response" button
    3. The system processes your query through the agent graph
    4. View the response and graph visualization
    """)
    
    # Display system info
    st.subheader("🔧 System Info")
    st.markdown(f"""
    - **Graph Nodes**: {len(app.get_graph().nodes)}
    - **Status**: Ready
    """)

# Footer
st.markdown("---")
st.markdown("*Powered by LangGraph and Streamlit*") 