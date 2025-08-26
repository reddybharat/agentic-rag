from src.graphs.builder import _build_base_graph, build_graph
from src.graphs.type import RAGAgentState
from langgraph.checkpoint.memory import MemorySaver
import os

def test_graph_structure():
    """Test the graph structure and visualization without running the full pipeline"""
    print("🧪 Testing Graph Structure...")
    
    # Build the base graph (before compilation) for visualization
    base_graph = _build_base_graph()
    print("✅ Base graph built successfully.")
    print(f"Nodes: {list(base_graph.nodes.keys())}")
    print(f"Edges: {base_graph.edges}")
    
    # Try to generate graph visualization from base graph
    try:
        # Try to get Mermaid diagram as text first
        mermaid_text = base_graph.get_graph().draw_mermaid()
        with open("graph.mmd", "w") as f:
            f.write(mermaid_text)
        print("✅ Graph Mermaid diagram saved to graph.mmd")
        
        # Try to get PNG image
        png_graph_data = base_graph.get_graph().draw_mermaid_png()
        file_path = "graph.png"
        with open(file_path, "wb") as f:
            f.write(png_graph_data)
        print(f"✅ Graph PNG saved as '{file_path}' in {os.getcwd()}")
        
    except Exception as e:
        print(f"❌ Could not save graph visualization: {e}")
        print("This might be due to missing mermaid-cli or graphviz dependencies")

def test_graph_compilation():
    """Test the graph compilation with checkpointer and interrupt"""
    print("\n🧪 Testing Graph Compilation...")
    
    # Create a checkpointer for the graph
    checkpointer = MemorySaver()
    
    # Use the build_graph function from builder.py
    graph = build_graph(checkpointer)
    print("✅ Compiled graph built successfully using build_graph().")
    print(f"Compiled graph type: {type(graph)}")
    print("⚠️  Graph has interrupt_after=['rewrite'] - execution will pause after rewrite node")
    
    # Generate PNG from compiled graph
    try:
        print("\n🖼️ Generating PNG from compiled graph...")
        png_graph_data = graph.get_graph().draw_mermaid_png()
        file_path = "graph.png"
        with open(file_path, "wb") as f:
            f.write(png_graph_data)
        print(f"✅ Compiled graph PNG saved as '{file_path}' in {os.getcwd()}")
    except Exception as e:
        print(f"❌ Could not save compiled graph PNG: {e}")
        print("This might be due to missing mermaid-cli or graphviz dependencies")
    
    # Test the graph with a minimal state
    print("\n🧪 Testing Graph with Minimal State...")
    
    # Create initial state with minimal required fields
    initial_state = RAGAgentState(
        files_uploaded=[],
        query="Test query",
        answer="",
        data_ingested=False,
        status="initialized",
        messages=[],
        web_search=True,
        rewrite=False,
        finish=False
    )
    
    # Create a thread for the graph execution
    thread_id = "test_thread"
    
    try:
        # Start the graph execution
        print("🚀 Starting graph execution...")
        print("Expected flow: START → search → rewrite → INTERRUPT (stops here)")
        print("Note: CHAT node will NOT be reached due to interrupt!")
        
        config = {"configurable": {"thread_id": thread_id}}
        
        # Run the graph
        result = graph.invoke(initial_state, config)
        print("✅ Graph execution completed (interrupted after rewrite)")
        print(f"State after interrupt: {result}")
        print(f"Status: {result.get('status', 'No status')}")
        print(f"Answer: {result.get('answer', 'No answer')}")
        
        # To reach the CHAT node, you would need to resume execution:
        print("\n🔄 To reach CHAT node, you would need to resume execution:")
        print("resumed_result = graph.invoke(result, config)")
        
    except Exception as e:
        print(f"❌ Graph execution failed: {e}")
        print("This might be due to missing dependencies or configuration issues")
        print("The graph structure is working, but some nodes may need API keys or other setup")

def main():
    """Main test function"""
    print("🚀 Starting Graph Tests...")
    print("=" * 50)
    
    # Test 1: Graph Structure
    test_graph_structure()
    
    # Test 2: Graph Compilation
    test_graph_compilation()
    
    print("\n" + "=" * 50)
    print("🏁 Graph Tests Completed!")
    print("\n📝 Key Points:")
    print("- Using build_graph() from builder.py")
    print("- Interrupt is set to pause after 'rewrite' node")
    print("- CHAT node is NOT reached because of the interrupt")
    print("- To reach CHAT node, you need to resume execution after the interrupt")
    print("- Run test_graph_cycles.py to see proper interrupt handling")

if __name__ == "__main__":
    main()
