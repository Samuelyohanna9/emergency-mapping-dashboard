from graphviz import Digraph

# Create a directed graph
dot = Digraph(comment='Emergency Response System Architecture', format='png')

# Set graph attributes
dot.attr(rankdir='LR')  # Left-to-right layout
dot.attr('node', shape='box', style='filled', color='lightblue')  # Node styling

# Add nodes
dot.node('A', 'PostgreSQL/PostGIS\n(Backend)')
dot.node('B', 'Flask API\n(Backend)')
dot.node('C', 'GeoJSON Data')
dot.node('D', 'OSRM\n(External Service)')
dot.node('E', 'Leaflet.js\n(Frontend)')
dot.node('F', 'Chart.js\n(Frontend)')

# Add edges to represent data flow
dot.edge('A', 'B', label='Spatial Data')
dot.edge('B', 'C', label='Serve GeoJSON')
dot.edge('C', 'E', label='Fetch Data')
dot.edge('E', 'D', label='Routing Request')
dot.edge('D', 'E', label='Routing Response')
dot.edge('E', 'F', label='Visualize Statistics')

# Render the graph
dot.render('architecture_diagram', view=True)

print("Diagram saved as 'architecture_diagram.png'")