from PyQt6.QtWidgets import (
    QGraphicsView, QGraphicsScene, QGraphicsEllipseItem,
    QGraphicsLineItem, QGraphicsTextItem, QWidget, QVBoxLayout, QLabel,
    QHBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QRectF, QSize, pyqtSignal

from assets.icons import icon
from PyQt6.QtGui import (
    QBrush, QPen, QColor, QFont, QFontMetrics, QPainter,
    QRadialGradient,
)

from zametka_dbs.graph.data import NoteGraph
from zametka_dbs.graph.layout import ForceLayout


class GraphView(QWidget):
    """
    Interactive graph visualization of note connections.

    - Force-directed layout (animated)
    - Nodes are clickable → opens the note
    - Drag nodes, zoom, pan
    """

    node_clicked = pyqtSignal(str)  # emits file path

    COLORS = {
        "bg": QColor("#0a0a0a"),
        "edge": QColor("#333333"),
        "edge_active": QColor("#fab283"),
        "node": QColor("#fab283"),
        "node_hover": QColor("#9d7cd8"),
        "node_text": QColor("#eeeeee"),
        "glow": QColor("#fab283"),
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("graph-widget")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("graph-header")
        header.setFixedHeight(30)
        hdr_layout = QHBoxLayout(header)
        hdr_layout.setContentsMargins(10, 0, 14, 0)
        hdr_layout.setSpacing(4)
        hdr_icon = QLabel()
        hdr_icon.setPixmap(icon("network").pixmap(14, 14))
        hdr_icon.setFixedWidth(18)
        hdr_layout.addWidget(hdr_icon)
        hdr_text = QLabel("Graph View")
        hdr_text.setObjectName("graph-header-label")
        hdr_layout.addWidget(hdr_text)
        hdr_layout.addStretch()
        layout.addWidget(header)

        self._scene = QGraphicsScene()
        self._view = QGraphicsView(self._scene)
        self._view.setObjectName("graph-canvas")
        self._view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self._view.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self._view.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self._view.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._view.setStyleSheet("QGraphicsView { background: #0a0a0a; border: none; }")
        self.setStyleSheet("""
            QWidget#graph-header {
                border-bottom: 1px solid #1a1a1a;
                background-color: #0a0a0a;
            }
            QLabel#graph-header-label {
                color: #808080;
                font-size: 11px;
                font-weight: 600;
                letter-spacing: 1px;
                text-transform: uppercase;
            }
        """)
        layout.addWidget(self._view)

        self._graph = NoteGraph()
        self._layout = None
        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)
        self._node_items: dict[str, NoteGraphicsItem] = {}
        self._edge_items: list[QGraphicsLineItem] = []
        self._hovered_node = None

        self._view.scale(1.0, 1.0)

    def set_graph(self, graph: NoteGraph):
        self._graph = graph
        self._rebuild_scene()

    def build_from_links(self, all_links: dict[str, list[str]]):
        self._graph = NoteGraph()
        self._graph.build_from_links(all_links)
        self._rebuild_scene()

    def _rebuild_scene(self):
        self._scene.clear()
        self._node_items.clear()
        self._edge_items.clear()

        w = self._view.viewport().width() or 800
        h = self._view.viewport().height() or 600

        # Edges
        edge_pen = QPen(self.COLORS["edge"], 1)
        edge_color = QColor(self.COLORS["edge"])
        edge_color.setAlpha(120)
        edge_pen.setColor(edge_color)
        for edge in self._graph.edges:
            line = QGraphicsLineItem()
            line.setPen(edge_pen)
            self._scene.addItem(line)
            self._edge_items.append(line)

        # Nodes
        for node_id, node in self._graph.nodes.items():
            item = NoteGraphicsItem(node, self.COLORS)
            self._scene.addItem(item)
            self._node_items[node_id] = item

        self._layout = ForceLayout(self._graph, w, h)
        self._timer.start(16)  # ~60 fps

    def _tick(self):
        if self._layout and not self._layout.settled:
            self._layout.tick()
            self._update_positions()
            self._view.centerOn(0, 0)
        else:
            self._timer.stop()

    def _update_positions(self):
        # Update edge lines
        for i, edge in enumerate(self._graph.edges):
            if i < len(self._edge_items):
                line = self._edge_items[i]
                line.setLine(
                    edge.source.x, edge.source.y,
                    edge.target.x, edge.target.y,
                )

        # Update node positions
        for node_id, node in self._graph.nodes.items():
            item = self._node_items.get(node_id)
            if item:
                item.setPos(node.x, node.y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._layout:
            self._layout.reset(
                self._view.viewport().width(),
                self._view.viewport().height(),
            )
            self._timer.start(16)

    def wheelEvent(self, event):
        # Zoom with scroll wheel
        factor = 1.15
        if event.angleDelta().y() > 0:
            self._view.scale(factor, factor)
        else:
            self._view.scale(1 / factor, 1 / factor)


class NoteGraphicsItem(QGraphicsEllipseItem):
    """
    Visual node in the graph: circle + label.
    Clickable → emits signal via parent.
    """

    RADIUS = 8
    FONT = QFont("Segoe UI", 10)

    def __init__(self, node, colors):
        self._node = node
        self._colors = colors
        self._hovered = False

        r = self.RADIUS
        super().__init__(-r, -r, r * 2, r * 2)

        # Glow
        glow_r = r * 3
        gradient = QRadialGradient(0, 0, glow_r)
        glow_color = QColor(colors["glow"])
        glow_color.setAlpha(40)
        gradient.setColorAt(0, glow_color)
        gradient.setColorAt(1, QColor(0, 0, 0, 0))
        self.setBrush(QBrush(gradient))

        # Node body
        self._body = QGraphicsEllipseItem(-r, -r, r * 2, r * 2, self)
        self._body.setBrush(QBrush(colors["node"]))
        self._body.setPen(QPen(QColor("#0a0a0a"), 1))

        # Label
        self._label = QGraphicsTextItem(node.label, self)
        self._label.setFont(self.FONT)
        self._label.setDefaultTextColor(colors["node_text"])
        label_offset = -QFontMetrics(self.FONT).height() / 2
        self._label.setPos(r + 4, label_offset)

        self.setAcceptHoverEvents(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    @property
    def node_path(self) -> str:
        return self._node.path

    def hoverEnterEvent(self, event):
        self._hovered = True
        self._body.setBrush(QBrush(self._colors["node_hover"]))
        self._body.setScale(1.3)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event):
        self._hovered = False
        self._body.setBrush(QBrush(self._colors["node"]))
        self._body.setScale(1.0)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            # Find the parent QGraphicsScene to get the GraphView
            scene = self.scene()
            if isinstance(scene, QGraphicsScene):
                # Get the view from the scene's parent
                view = scene.parent()
                if isinstance(view, GraphView):
                    view.node_clicked.emit(self._node.path)
            else:
                # Fallback: iterate through the widget hierarchy
                parent = self
                while parent:
                    parent = parent.parent()
                    if isinstance(parent, GraphView):
                        parent.node_clicked.emit(self._node.path)
                        break
        super().mousePressEvent(event)
