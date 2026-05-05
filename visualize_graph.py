from graphviz import Digraph

dot = Digraph(format='png')
dot.attr(rankdir='TB', size='10')

# Nodes
dot.node('A', 'User Query (Streamlit UI)')
dot.node('B', 'Intent Detection (Router)')
dot.node('C', 'RBAC Check')
dot.node('D', 'Route Decision')

# Branches
dot.node('E', 'Conversation Node')
dot.node('F', 'Guardrail Node')

dot.node('G', 'HR RAG Agent')
dot.node('H', 'HR Workflow Agent')

dot.node('I', 'IT Ticket Agent')
dot.node('J', 'Asset Request Agent')

dot.node('K', 'Final Response')
dot.node('L', 'Save Memory')
dot.node('M', 'Save Logs')
dot.node('N', 'Display Output')

# Edges
dot.edge('A', 'B')
dot.edge('B', 'C')
dot.edge('C', 'D')

dot.edge('D', 'E', label='Greeting')
dot.edge('D', 'F', label='Out of Scope')

dot.edge('D', 'G', label='HR Policy')
dot.edge('G', 'K')

dot.edge('D', 'H', label='Leave Flow')
dot.edge('H', 'K')

dot.edge('D', 'I', label='IT Ticket')
dot.edge('I', 'K')

dot.edge('D', 'J', label='Asset Request')
dot.edge('J', 'K')

dot.edge('K', 'L')
dot.edge('L', 'M')
dot.edge('M', 'N')

# Render
dot.render('enterprise_langgraph', view=True)