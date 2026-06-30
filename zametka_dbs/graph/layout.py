"""
Force-directed layout engine based on Fruchterman–Reingold.

Physics:
  - Nodes repel each other (Coulomb-like)
  - Connected nodes attract (spring-like)
  - Center gravity pulls everything toward center
  - Velocity damping for convergence
"""

import math
import random

from .data import NoteGraph, GraphNode


class ForceLayout:
    """
    Runs a force-directed layout simulation on a NoteGraph.

    Call `tick()` repeatedly (e.g., via QTimer) to animate.
    """

    def __init__(
        self,
        graph: NoteGraph,
        width: float = 800,
        height: float = 600,
        repulsion: float = 5000.0,
        attraction: float = 0.01,
        gravity: float = 0.01,
        damping: float = 0.85,
        min_velocity: float = 0.1,
    ):
        self.graph = graph
        self.width = width
        self.height = height
        self.repulsion = repulsion
        self.attraction = attraction
        self.gravity = gravity
        self.damping = damping
        self.min_velocity = min_velocity
        self.settled = False

        self._init_positions()

    def _init_positions(self):
        cx, cy = self.width / 2, self.height / 2
        radius = min(self.width, self.height) * 0.35
        nodes = list(self.graph.nodes.values())
        n = len(nodes)

        if n == 0:
            return
        if n == 1:
            nodes[0].x, nodes[0].y = cx, cy
            return

        # Place in a circle initially
        for i, node in enumerate(nodes):
            angle = (2 * math.pi * i) / n + random.uniform(-0.1, 0.1)
            node.x = cx + radius * math.cos(angle)
            node.y = cy + radius * math.sin(angle)

    def tick(self) -> bool:
        """
        Run one simulation step. Returns True if still moving.
        """
        if self.settled:
            return False

        nodes = list(self.graph.nodes.values())
        n = len(nodes)
        if n < 2:
            self.settled = True
            return False

        max_velocity = 0.0
        cx, cy = self.width / 2, self.height / 2

        # Forces for each node
        forces = {node.id: [0.0, 0.0] for node in nodes}

        # Repulsion: all nodes repel all others
        for i in range(n):
            for j in range(i + 1, n):
                ni, nj = nodes[i], nodes[j]
                dx = ni.x - nj.x
                dy = ni.y - nj.y
                dist = max((dx * dx + dy * dy) ** 0.5, 1.0)
                force = self.repulsion / (dist * dist)
                fx = (dx / dist) * force
                fy = (dy / dist) * force
                forces[ni.id][0] += fx
                forces[ni.id][1] += fy
                forces[nj.id][0] -= fx
                forces[nj.id][1] -= fy

        # Attraction: connected nodes attract
        for edge in self.graph.edges:
            ni, nj = edge.source, edge.target
            if ni.id == nj.id:
                continue
            dx = nj.x - ni.x
            dy = nj.y - ni.y
            dist = max((dx * dx + dy * dy) ** 0.5, 1.0)
            force = self.attraction * dist
            fx = (dx / dist) * force
            fy = (dy / dist) * force
            forces[ni.id][0] += fx
            forces[ni.id][1] += fy
            forces[nj.id][0] -= fx
            forces[nj.id][1] -= fy

        # Center gravity
        for node in nodes:
            dx = cx - node.x
            dy = cy - node.y
            forces[node.id][0] += dx * self.gravity
            forces[node.id][1] += dy * self.gravity

        # Apply forces, damping
        for node in nodes:
            if node.fixed:
                continue

            node.vx = (node.vx + forces[node.id][0]) * self.damping
            node.vy = (node.vy + forces[node.id][1]) * self.damping
            node.x += node.vx
            node.y += node.vy

            speed = (node.vx * node.vx + node.vy * node.vy) ** 0.5
            max_velocity = max(max_velocity, speed)

        # Check if settled
        self.settled = max_velocity < self.min_velocity
        return not self.settled

    def reset(self, width: float = None, height: float = None):
        if width is not None:
            self.width = width
        if height is not None:
            self.height = height
        self.settled = False
        self._init_positions()
