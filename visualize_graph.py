from graph import app_graph

def save_graph_visual():
    try:
        png_data = app_graph.get_graph().draw_mermaid_png()

        with open("langgraph_workflow.png", "wb") as f:
            f.write(png_data)

        print("LangGraph visual saved as langgraph_workflow.png")

    except Exception as e:
        print("Could not generate PNG automatically.")
        print("Reason:", e)
        print("\nUse this Mermaid diagram manually:\n")

        print("""
graph TD
    A[User Query] --> B[Router Node]
    B --> C[RBAC Node]
    C --> D{Conditional Routing}

    D -->|Policy Question| E[Policy RAG Agent]
    D -->|Leave Workflow| F[HR Agent]
    D -->|IT Workflow| G[IT Agent]
    D -->|Unknown Query| H[Fallback Node]

    E --> I[Final Response]
    F --> I
    G --> I
    H --> I
""")


if __name__ == "__main__":
    save_graph_visual()