import basic.builder
app = basic.builder.build_graph()

# Save the graph image as 'graph.png'
graph_bytes = app.get_graph().draw_mermaid_png()
with open(".\\basic\graph.png", "wb") as f:
    f.write(graph_bytes)

# Optionally, display the image (uncomment if needed)
# display(Image("graph.png"))

query = "Give me list of Top 10 richest people in the world currently"
response = app.invoke({"query": query})

print(f"Query: {query}\nResponse: {response}")