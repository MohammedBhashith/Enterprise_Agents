from graph import app_graph


def generate_graph():
    try:
        # Get Mermaid diagram
        mermaid_code = app_graph.get_graph().draw_mermaid()

        print("\nMermaid Diagram:\n")
        print(mermaid_code)

        # Convert to PNG (no Graphviz needed)
        png_data = app_graph.get_graph().draw_mermaid_png()

        with open("langgraph_full.png", "wb") as f:
            f.write(png_data)

        print("\nGraph image generated: langgraph_full.png")

    except Exception as e:
        print("Error:", e)
        print("\nIf PNG fails, copy Mermaid code above into:")
        print("https://mermaid.live")


if __name__ == "__main__":
    generate_graph()