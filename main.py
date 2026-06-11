import sys

# Configure standard streams to use UTF-8 encoding to avoid Windows console UnicodeEncodeError
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass
if sys.stderr.encoding != 'utf-8':
    try:
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

from graph import graph

def run_agentic_rag(query: str):
    print("\n=========================================")
    print("Running Agentic RAG System...")
    print("=========================================")
    print(f"Input Query: '{query}'\n")

    inputs = {
        "messages": [
            {
                "role": "user",
                "content": query,
            }
        ]
    }

    # Stream the steps from the compiled graph
    for chunk in graph.stream(inputs):
        for node, update in chunk.items():
            print(f"\n--- Update from node: '{node}' ---")
            update["messages"][-1].pretty_print()
            
    print("\nExecution finished successfully!")

if __name__ == "__main__":
    # If arguments are passed, use them as the query; otherwise use the default query
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        query = "What does Lilian Weng say about types of reward hacking?"
        
    run_agentic_rag(query)
