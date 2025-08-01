from src.graphs import builder

def main():
    # Build the graph using the builder
    graph = builder.build_graph()
    print("Graph built successfully.")
    print(f"Nodes: {getattr(graph, 'nodes', 'Unknown')}")
    print(f"Edges: {getattr(graph, 'edges', 'Unknown')}")

if __name__ == "__main__":
    main()
