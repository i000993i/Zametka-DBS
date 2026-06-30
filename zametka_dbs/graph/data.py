"""
Graph data structure: nodes = notes, edges = [[wikilinks]] connections.
"""


class GraphNode:
    __slots__ = ("id", "label", "path", "x", "y", "vx", "vy", "fixed", "weight")

    def __init__(self, node_id: str, label: str, path: str = ""):
        self.id = node_id
        self.label = label
        self.path = path
        self.x = 0.0
        self.y = 0.0
        self.vx = 0.0
        self.vy = 0.0
        self.fixed = False
        self.weight = 1.0

    def pos(self):
        return self.x, self.y

    def distance_to(self, other: "GraphNode") -> float:
        dx = self.x - other.x
        dy = self.y - other.y
        return (dx * dx + dy * dy) ** 0.5


class GraphEdge:
    __slots__ = ("source", "target", "weight")

    def __init__(self, source: GraphNode, target: GraphNode, weight: float = 1.0):
        self.source = source
        self.target = target
        self.weight = weight


class NoteGraph:
    """
    Directed graph of notes and their [[wikilinks]] connections.

    Build from a BacklinkIndex or from raw link data.
    """

    def __init__(self):
        self.nodes: dict[str, GraphNode] = {}
        self.edges: list[GraphEdge] = []

    def add_node(self, node_id: str, label: str = "", path: str = "") -> GraphNode:
        if node_id not in self.nodes:
            self.nodes[node_id] = GraphNode(node_id, label or node_id, path)
        return self.nodes[node_id]

    def add_edge(self, source_id: str, target_id: str, weight: float = 1.0):
        source = self.add_node(source_id)
        target = self.add_node(target_id)
        self.edges.append(GraphEdge(source, target, weight))

    def build_from_links(self, all_links: dict[str, list[str]]):
        """
        Build graph from forward links dict:
          { note_path: [linked_path, ...] }
        """
        self.nodes.clear()
        self.edges.clear()

        seen = set()
        for source_path, targets in all_links.items():
            source_id = self._path_to_id(source_path)
            self.add_node(source_id, label=source_id, path=source_path)
            seen.add(source_path)

            for target_path in targets:
                target_id = self._path_to_id(target_path)
                self.add_node(target_id, label=target_id, path=target_path)
                self.add_edge(source_id, target_id)
                seen.add(target_path)

    def _path_to_id(self, path: str) -> str:
        import os
        name = os.path.splitext(os.path.basename(path))[0]
        return name

    def get_node(self, node_id: str) -> GraphNode | None:
        return self.nodes.get(node_id)

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def edge_count(self) -> int:
        return len(self.edges)
