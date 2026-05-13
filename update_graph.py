import json

# Load both files
with open('trails/vermont_long_trail/compiled/route_overlay.json', 'r') as f:
    overlay_data = json.load(f)

with open('trails/vermont_long_trail/compiled/operational_graph.json', 'r') as f:
    graph_data = json.load(f)

# Create mapping from overlay_id to full node data
overlay_map = {node['overlay_id']: node for node in overlay_data['overlay_nodes']}

# Update operational graph overlay nodes
updated_count = 0
for node in graph_data['nodes']:
    if node.get('node_type') == 'overlay':
        overlay_id = node.get('overlay_id')
        if overlay_id in overlay_map:
            overlay_node = overlay_map[overlay_id]
            node['shelter'] = overlay_node.get('shelter', False)
            node['camping'] = overlay_node.get('camping', False)
            node['water'] = overlay_node.get('water', False)
            node['resupply'] = overlay_node.get('resupply', False)
            updated_count += 1

print(f'Updated {updated_count} overlay nodes with shelter data')

# Save updated operational graph
with open('trails/vermont_long_trail/compiled/operational_graph.json', 'w') as f:
    json.dump(graph_data, f, indent=2)

print('Operational graph updated successfully')