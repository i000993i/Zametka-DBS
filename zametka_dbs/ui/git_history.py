import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QTextEdit, QTabWidget,
)
from PyQt6.QtCore import Qt, QSize, QProcess, pyqtSignal

from assets.icons import icon


class _GitWorker(QProcess):
    done = pyqtSignal(str, str)

    def __init__(self, args, cwd):
        super().__init__()
        self._args = args
        self._cwd = cwd
        self._stdout = b""
        self._stderr = b""
        self.readyReadStandardOutput.connect(self._on_stdout)
        self.readyReadStandardError.connect(self._on_stderr)
        self.finished.connect(self._on_finished)

    def start(self):
        self.setWorkingDirectory(self._cwd)
        super().start("git", self._args)

    def _on_stdout(self):
        self._stdout += self.readAllStandardOutput()

    def _on_stderr(self):
        self._stderr += self.readAllStandardError()

    def _on_finished(self, exit_code, exit_status):
        out = bytes(self._stdout).decode("utf-8", errors="replace")
        err = bytes(self._stderr).decode("utf-8", errors="replace")
        self.done.emit(out, err)


class GitHistoryWidget(QWidget):
    diff_requested = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._vault_path = ""
        self._commit_cache = []
        self._worker = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setObjectName("sidebar-header")
        header.setFixedHeight(30)
        hdr = QHBoxLayout(header)
        hdr.setContentsMargins(10, 0, 10, 0)
        hdr_icon = QLabel()
        hdr_icon.setPixmap(icon("git-branch").pixmap(14, 14))
        hdr_icon.setFixedWidth(18)
        hdr.addWidget(hdr_icon)
        hdr_label = QLabel("HISTORY")
        hdr_label.setObjectName("vault-label")
        hdr.addWidget(hdr_label)
        hdr.addStretch()

        self._refresh_btn = QPushButton()
        self._refresh_btn.setIcon(icon("refresh"))
        self._refresh_btn.setIconSize(QSize(14, 14))
        self._refresh_btn.setObjectName("icon-btn")
        self._refresh_btn.setFixedSize(22, 22)
        self._refresh_btn.setToolTip("Refresh")
        self._refresh_btn.clicked.connect(self._refresh)
        hdr.addWidget(self._refresh_btn)
        layout.addWidget(header)

        self._tabs = QTabWidget()
        self._tabs.setObjectName("git-tabs")

        self._changes_list = QListWidget()
        self._changes_list.setObjectName("git-list")
        self._changes_list.itemClicked.connect(self._on_change_clicked)
        self._tabs.addTab(self._changes_list, "Changes")

        self._list = QListWidget()
        self._list.setObjectName("git-list")
        self._list.itemClicked.connect(self._on_commit_clicked)
        self._tabs.addTab(self._list, "Commits")

        layout.addWidget(self._tabs, 1)

        self._action_row = QWidget()
        action_layout = QHBoxLayout(self._action_row)
        action_layout.setContentsMargins(8, 4, 8, 4)
        action_layout.setSpacing(4)

        self._stage_btn = QPushButton("Stage")
        self._stage_btn.setObjectName("git-action-btn")
        self._stage_btn.clicked.connect(self._stage_selected)
        self._stage_btn.setVisible(False)
        action_layout.addWidget(self._stage_btn)

        self._unstage_btn = QPushButton("Unstage")
        self._unstage_btn.setObjectName("git-action-btn")
        self._unstage_btn.clicked.connect(self._unstage_selected)
        self._unstage_btn.setVisible(False)
        action_layout.addWidget(self._unstage_btn)

        action_layout.addStretch()
        layout.addWidget(self._action_row)

        self._diff_view = QTextEdit()
        self._diff_view.setReadOnly(True)
        self._diff_view.setObjectName("git-diff")
        self._diff_view.setVisible(False)
        layout.addWidget(self._diff_view)

        self._no_git_label = QLabel("Not a git repository")
        self._no_git_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._no_git_label.setStyleSheet("font-size: 12px; padding: 20px;")
        layout.addWidget(self._no_git_label)

    def set_vault_path(self, path: str):
        self._vault_path = path
        self._refresh()

    def _is_git_repo(self) -> bool:
        if not self._vault_path:
            return False
        git_dir = os.path.join(self._vault_path, ".git")
        return os.path.isdir(git_dir)

    def _refresh(self):
        self._commit_cache.clear()
        self._list.clear()
        self._changes_list.clear()
        self._diff_view.clear()
        self._diff_view.setVisible(False)
        self._action_row.setVisible(False)

        if not self._is_git_repo():
            self._no_git_label.setVisible(True)
            self._tabs.setVisible(False)
            return

        self._no_git_label.setVisible(False)
        self._tabs.setVisible(True)

        self._run_git(["git", "status", "--porcelain"],
                       lambda out: self._on_status_ready(out))
        self._run_git(["git", "log", "--oneline", "--abbrev-commit",
                        "--pretty=format:%h||%an||%ar||%s"],
                       lambda out: self._on_log_ready(out))

    def _run_git(self, args, callback):
        w = _GitWorker(args, self._vault_path)
        w.done.connect(lambda out, err: callback(out) if not err else None)
        w.done.connect(lambda: w.deleteLater())
        w.start()

    def _on_status_ready(self, stdout: str):
        self._changes_list.clear()
        for line in stdout.strip().split("\n"):
            line = line.strip()
            if not line:
                continue
            status = line[:2]
            filepath = line[3:]
            label = {"M ": "Modified", "??": "Untracked", "A ": "Added",
                     "D ": "Deleted", "R ": "Renamed", "MM": "Modified"}.get(status, status)
            item = QListWidgetItem(f"[{label}] {filepath}")
            item.setData(Qt.ItemDataRole.UserRole, filepath)
            item.setData(Qt.ItemDataRole.UserRole + 1, status)
            self._changes_list.addItem(item)

    def _on_log_ready(self, stdout: str):
        self._commit_cache.clear()
        self._list.clear()
        for line in stdout.strip().split("\n"):
            if not line:
                continue
            parts = line.split("||", 3)
            if len(parts) == 4:
                sha, author, rel_date, subject = parts
                self._commit_cache.append((sha, author, rel_date, subject))
        for sha, author, rel_date, subject in self._commit_cache:
            item = QListWidgetItem(f"{sha}  {subject}")
            item.setData(Qt.ItemDataRole.UserRole, sha)
            item.setToolTip(f"{author} - {rel_date}")
            self._list.addItem(item)

    def _on_change_clicked(self, item):
        filepath = item.data(Qt.ItemDataRole.UserRole)
        status = item.data(Qt.ItemDataRole.UserRole + 1)
        if not filepath:
            return
        is_staged = status[0] != " " and status[0] != "?"
        self._stage_btn.setVisible(not is_staged and "?" not in status)
        self._unstage_btn.setVisible(is_staged)
        self._action_row.setVisible(self._stage_btn.isVisible() or self._unstage_btn.isVisible())

        if "?" in status:
            full_path = os.path.join(self._vault_path, filepath)
            if os.path.isfile(full_path):
                try:
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        content = f.read()
                    self._diff_view.setPlainText(content[:3000])
                    self._diff_view.setVisible(True)
                except OSError:
                    pass
        else:
            args = (["git", "diff", "--cached", "--", filepath] if is_staged
                    else ["git", "diff", "--", filepath])
            self._run_git(args, lambda out: self._on_diff_ready(out))

    def _on_diff_ready(self, stdout: str):
        self._diff_view.setPlainText(stdout[:5000] or "No diff")
        self._diff_view.setVisible(True)

    def _stage_selected(self):
        item = self._changes_list.currentItem()
        if not item:
            return
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath:
            self._run_git(["git", "add", filepath], lambda _: self._refresh())

    def _unstage_selected(self):
        item = self._changes_list.currentItem()
        if not item:
            return
        filepath = item.data(Qt.ItemDataRole.UserRole)
        if filepath:
            self._run_git(["git", "restore", "--staged", filepath], lambda _: self._refresh())

    def _on_commit_clicked(self, item):
        sha = item.data(Qt.ItemDataRole.UserRole)
        if not sha:
            return
        self._stage_btn.setVisible(False)
        self._unstage_btn.setVisible(False)
        self._action_row.setVisible(False)
        self._run_git(
            ["git", "show", sha, "--stat", "--format=%H%n%an%n%ar%n%s%n%b"],
            lambda out: self._on_show_ready(out),
        )

    def _on_show_ready(self, stdout: str):
        self._diff_view.setPlainText(stdout[:5000])
        self._diff_view.setVisible(True)
