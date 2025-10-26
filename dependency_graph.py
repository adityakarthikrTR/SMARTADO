"""
Dependency Graph Visualization for Azure DevOps Work Items

Creates interactive network graphs showing work item relationships,
dependencies, blockers, and critical paths.
"""

import plotly.graph_objects as go
import networkx as nx
from typing import Dict, List, Set, Tuple
import streamlit as st


class DependencyGraphBuilder:
    """Build interactive dependency graphs from work items"""

    def __init__(self):
        """Initialize graph builder"""
        self.graph = nx.DiGraph()  # Directed graph
        self.work_items_data = {}  # Store work item details

    def add_work_items(self, work_items: List[Dict]):
        """
        Add work items and their relationships to the graph.

        Args:
            work_items: List of work item dictionaries with full details
        """
        # First pass: Add all nodes
        for item in work_items:
            item_id = item.get('id')
            if not item_id:
                continue

            fields = item.get('fields', {})

            # Store work item data
            self.work_items_data[item_id] = {
                'id': item_id,
                'title': fields.get('System.Title', 'Untitled'),
                'type': fields.get('System.WorkItemType', 'Unknown'),
                'state': fields.get('System.State', 'Unknown'),
                'assignee': self._get_assignee(fields),
                'story_points': fields.get('Microsoft.VSTS.Scheduling.StoryPoints', 0),
                'is_blocked': False  # Will be determined by relationships
            }

            # Add node to graph
            self.graph.add_node(
                item_id,
                **self.work_items_data[item_id]
            )

        # Second pass: Add edges (relationships)
        for item in work_items:
            item_id = item.get('id')
            relations = item.get('relations', [])

            if not relations:
                continue

            for rel in relations:
                rel_type = rel.get('rel', '')
                url = rel.get('url', '')

                if '/workitems/' not in url:
                    continue

                # Extract related work item ID
                try:
                    rel_id = int(url.split('/')[-1])
                except (ValueError, IndexError):
                    continue

                # Only add edge if both nodes exist in graph
                if rel_id not in self.graph:
                    continue

                # Add edges based on relationship type
                if 'System.LinkTypes.Hierarchy-Reverse' in rel_type:
                    # Parent relationship
                    self.graph.add_edge(rel_id, item_id, rel_type='parent')
                elif 'System.LinkTypes.Hierarchy-Forward' in rel_type:
                    # Child relationship
                    self.graph.add_edge(item_id, rel_id, rel_type='child')
                elif 'System.LinkTypes.Dependency-Forward' in rel_type:
                    # This item depends on rel_id (successor)
                    self.graph.add_edge(item_id, rel_id, rel_type='depends_on')
                elif 'System.LinkTypes.Dependency-Reverse' in rel_type:
                    # rel_id depends on this item (predecessor)
                    self.graph.add_edge(rel_id, item_id, rel_type='depends_on')
                elif 'System.LinkTypes.Related' in rel_type:
                    # Related (bidirectional)
                    self.graph.add_edge(item_id, rel_id, rel_type='related')

        # Identify blocked items
        self._identify_blockers()

    def _get_assignee(self, fields: Dict) -> str:
        """Extract assignee name from fields"""
        assignee = fields.get('System.AssignedTo', {})
        if isinstance(assignee, dict):
            return assignee.get('displayName', 'Unassigned')
        return 'Unassigned'

    def _identify_blockers(self):
        """Identify work items that are blocked"""
        for node in self.graph.nodes():
            # Check if this item has incoming dependency edges
            predecessors = list(self.graph.predecessors(node))
            for pred in predecessors:
                edge_data = self.graph.get_edge_data(node, pred)
                if edge_data and edge_data.get('rel_type') == 'depends_on':
                    # This item depends on pred, check if pred is not done
                    pred_state = self.graph.nodes[pred].get('state', '')
                    if pred_state not in ['Closed', 'Done', 'Resolved']:
                        self.graph.nodes[node]['is_blocked'] = True
                        break

    def create_plotly_figure(self) -> go.Figure:
        """
        Create an interactive Plotly figure from the graph.

        Returns:
            Plotly Figure object
        """
        if len(self.graph.nodes()) == 0:
            # Return empty figure
            fig = go.Figure()
            fig.add_annotation(
                text="No work items to visualize",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=20, color="gray")
            )
            return fig

        # Use spring layout for node positioning
        pos = nx.spring_layout(self.graph, k=2, iterations=50)

        # Create edge traces
        edge_traces = self._create_edge_traces(pos)

        # Create node trace
        node_trace = self._create_node_trace(pos)

        # Create figure
        fig = go.Figure(
            data=edge_traces + [node_trace],
            layout=go.Layout(
                title={
                    'text': "🕸️ Work Item Dependency Graph",
                    'x': 0.5,
                    'xanchor': 'center',
                    'font': {'size': 24}
                },
                showlegend=True,
                hovermode='closest',
                margin=dict(b=20, l=5, r=5, t=80),
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                plot_bgcolor='white',
                height=700
            )
        )

        return fig

    def _create_edge_traces(self, pos: Dict) -> List[go.Scatter]:
        """Create edge traces for different relationship types"""
        edges_by_type = {'parent': [], 'child': [], 'depends_on': [], 'related': []}

        for edge in self.graph.edges(data=True):
            source, target, data = edge
            rel_type = data.get('rel_type', 'related')

            x0, y0 = pos[source]
            x1, y1 = pos[target]

            edges_by_type[rel_type].append((x0, y0, x1, y1))

        # Create traces for each relationship type
        traces = []

        # Parent-child edges (blue, solid)
        if edges_by_type['parent'] or edges_by_type['child']:
            parent_child_edges = edges_by_type['parent'] + edges_by_type['child']
            x_coords = []
            y_coords = []
            for x0, y0, x1, y1 in parent_child_edges:
                x_coords.extend([x0, x1, None])
                y_coords.extend([y0, y1, None])

            traces.append(go.Scatter(
                x=x_coords, y=y_coords,
                mode='lines',
                line=dict(width=2, color='#0078d4'),
                hoverinfo='none',
                showlegend=True,
                name='Parent-Child'
            ))

        # Dependency edges (red, dashed)
        if edges_by_type['depends_on']:
            x_coords = []
            y_coords = []
            for x0, y0, x1, y1 in edges_by_type['depends_on']:
                x_coords.extend([x0, x1, None])
                y_coords.extend([y0, y1, None])

            traces.append(go.Scatter(
                x=x_coords, y=y_coords,
                mode='lines',
                line=dict(width=2, color='#cc293d', dash='dash'),
                hoverinfo='none',
                showlegend=True,
                name='Depends On'
            ))

        # Related edges (gray, dotted)
        if edges_by_type['related']:
            x_coords = []
            y_coords = []
            for x0, y0, x1, y1 in edges_by_type['related']:
                x_coords.extend([x0, x1, None])
                y_coords.extend([y0, y1, None])

            traces.append(go.Scatter(
                x=x_coords, y=y_coords,
                mode='lines',
                line=dict(width=1, color='#cccccc', dash='dot'),
                hoverinfo='none',
                showlegend=True,
                name='Related'
            ))

        return traces

    def _create_node_trace(self, pos: Dict) -> go.Scatter:
        """Create node trace with styling based on work item properties"""
        node_x = []
        node_y = []
        node_colors = []
        node_sizes = []
        node_text = []
        node_hover = []

        # Color mapping for work item types
        type_colors = {
            'Epic': '#ff6b00',
            'Feature': '#773b93',
            'User Story': '#009ccc',
            'Task': '#f2cb1d',
            'Bug': '#cc293d'
        }

        for node in self.graph.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)

            node_data = self.graph.nodes[node]
            work_item_type = node_data.get('type', 'Unknown')
            title = node_data.get('title', 'Untitled')
            state = node_data.get('state', 'Unknown')
            assignee = node_data.get('assignee', 'Unassigned')
            is_blocked = node_data.get('is_blocked', False)

            # Color by type, but red border if blocked
            color = type_colors.get(work_item_type, '#999999')
            if is_blocked:
                color = '#ff0000'  # Red for blocked

            node_colors.append(color)

            # Size based on story points (default 20, max 50)
            story_points = node_data.get('story_points', 0) or 0
            size = min(20 + story_points * 3, 50)
            node_sizes.append(size)

            # Node label
            node_text.append(f"#{node}")

            # Hover text
            blocked_text = "🚫 BLOCKED" if is_blocked else ""
            hover_text = f"<b>#{node}: {title}</b><br>" \
                        f"Type: {work_item_type}<br>" \
                        f"State: {state}<br>" \
                        f"Assigned: {assignee}<br>" \
                        f"Points: {story_points}<br>" \
                        f"{blocked_text}"
            node_hover.append(hover_text)

        node_trace = go.Scatter(
            x=node_x, y=node_y,
            mode='markers+text',
            hoverinfo='text',
            text=node_text,
            hovertext=node_hover,
            textposition="top center",
            showlegend=False,
            marker=dict(
                size=node_sizes,
                color=node_colors,
                line=dict(width=2, color='white')
            )
        )

        return node_trace

    def get_blocked_items(self) -> List[Dict]:
        """Get list of blocked work items"""
        blocked = []
        for node in self.graph.nodes():
            if self.graph.nodes[node].get('is_blocked'):
                blocked.append(self.work_items_data[node])
        return blocked

    def get_critical_path(self) -> List[int]:
        """
        Identify critical path (longest path through dependencies).

        Returns:
            List of work item IDs in critical path
        """
        try:
            # Find longest path
            longest_path = nx.dag_longest_path(self.graph)
            return longest_path
        except:
            # Graph has cycles or other issues
            return []

    def get_stats(self) -> Dict:
        """Get graph statistics"""
        return {
            'total_items': len(self.graph.nodes()),
            'total_relationships': len(self.graph.edges()),
            'blocked_items': len(self.get_blocked_items()),
            'isolated_items': len([n for n in self.graph.nodes() if self.graph.degree(n) == 0]),
            'max_depth': nx.dag_longest_path_length(self.graph) if nx.is_directed_acyclic_graph(self.graph) else 0
        }
