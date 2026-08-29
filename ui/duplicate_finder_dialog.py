"""
MP3 Organizer — Duplicate Finder Dialog  (MD5 hash-based)
"""
import os
import subprocess

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QFrame, QTreeWidget, QTreeWidgetItem,
    QAbstractItemView, QMessageBox, QHeaderView
)

from database.db_manager import DatabaseManager
from services.duplicate_service import DuplicateScanThread


class DuplicateFinderDialog(QDialog):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db      = db
        self._thread = None
        self._groups = []   # list of [Track, ...]

        self.setWindowTitle("Duplicate Finder")
        self.setMinimumSize(700, 500)
        self.setModal(True)
        self._build_ui()

    # ── Build UI ─────────────────────────────────────────────────────────────

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(14)
        main.setContentsMargins(20, 20, 20, 20)

        # Header
        title = QLabel("Duplicate Finder")
        title.setStyleSheet("font-size:17px;font-weight:700;")
        main.addWidget(title)

        subtitle = QLabel(
            "Scans your library for exact duplicate files (same MD5 hash). "
            "Select which copies to remove."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#8b949e;font-size:12px;")
        main.addWidget(subtitle)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep)

        # Progress
        self.status_label = QLabel("Click 'Scan' to begin.")
        self.status_label.setStyleSheet("color:#8b949e;font-size:12px;")
        main.addWidget(self.status_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)
        main.addWidget(self.progress)

        # Results tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["File", "Title", "Size", "Bitrate", "Path"])
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.header().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.tree.setColumnWidth(0, 200)
        self.tree.setColumnWidth(1, 160)
        self.tree.setColumnWidth(2, 70)
        self.tree.setColumnWidth(3, 70)
        main.addWidget(self.tree, 1)

        # Action buttons row
        action_row = QHBoxLayout()
        action_row.setSpacing(8)

        self.scan_btn = QPushButton("🔍  Scan Library")
        self.scan_btn.setObjectName("accent_btn")
        self.scan_btn.clicked.connect(self._start_scan)
        action_row.addWidget(self.scan_btn)

        action_row.addStretch()

        keep_first_btn = QPushButton("Keep First, Delete Others")
        keep_first_btn.clicked.connect(self._keep_first)
        action_row.addWidget(keep_first_btn)

        delete_sel_btn = QPushButton("Delete Selected")
        delete_sel_btn.setObjectName("danger_btn")
        delete_sel_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(delete_sel_btn)

        open_btn = QPushButton("Open File Location")
        open_btn.clicked.connect(self._open_location)
        action_row.addWidget(open_btn)

        main.addLayout(action_row)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep2)

        close_btn_row = QHBoxLayout()
        close_btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_btn_row.addWidget(close_btn)
        main.addLayout(close_btn_row)

    # ── Scan ─────────────────────────────────────────────────────────────────

    def _start_scan(self):
        self.tree.clear()
        self._groups = []
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        self.scan_btn.setEnabled(False)
        self.status_label.setText("Scanning for duplicates…")

        self._thread = DuplicateScanThread(self.db, self)
        self._thread.progress.connect(self._on_progress)
        self._thread.completed.connect(self._on_completed)
        self._thread.error.connect(self._on_error)
        self._thread.start()

    def _on_progress(self, current: int, total: int):
        if total > 0:
            self.progress.setRange(0, total)
            self.progress.setValue(current)
            self.status_label.setText(f"Hashing files… {current}/{total}")

    def _on_completed(self, groups: list):
        self._groups = groups
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

        if not groups:
            self.status_label.setText("✔  No duplicates found.")
            return

        total_dupes = sum(len(g) - 1 for g in groups)
        self.status_label.setText(
            f"Found {len(groups)} group(s) with {total_dupes} redundant file(s)."
        )

        for grp_idx, group in enumerate(groups):
            # Parent item = group header
            header = QTreeWidgetItem(self.tree)
            header.setText(0, f"Group {grp_idx + 1}  ({len(group)} files)")
            header.setExpanded(True)
            header.setData(0, Qt.ItemDataRole.UserRole, None)
            header.setForeground(0, self.palette().text())
            font = header.font(0)
            font.setBold(True)
            header.setFont(0, font)

            for i, track in enumerate(group):
                item = QTreeWidgetItem(header)
                item.setText(0, track.file_name)
                item.setText(1, track.display_title())
                item.setText(2, _fmt_size(track.file_size))
                item.setText(3, f"{track.bitrate} kbps" if track.bitrate else "")
                item.setText(4, track.file_path)
                item.setData(0, Qt.ItemDataRole.UserRole, track)
                if i == 0:
                    # Mark the "original" (kept) copy
                    item.setForeground(0, self.tree.palette().highlight())

    def _on_error(self, msg: str):
        self.status_label.setText(f"⚠ Error: {msg}")
        self.progress.setVisible(False)
        self.scan_btn.setEnabled(True)

    # ── Actions ───────────────────────────────────────────────────────────────

    def _keep_first(self):
        if not self._groups:
            return
        paths_to_delete = []
        for group in self._groups:
            for track in group[1:]:   # Skip first (keep it)
                paths_to_delete.append(track.file_path)

        if not paths_to_delete:
            return

        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(paths_to_delete)} redundant file(s) from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_files(paths_to_delete)

    def _delete_selected(self):
        items = self.tree.selectedItems()
        paths = []
        for item in items:
            track = item.data(0, Qt.ItemDataRole.UserRole)
            if track:
                paths.append(track.file_path)
        if not paths:
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Delete {len(paths)} selected file(s) from disk?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._delete_files(paths)

    def _delete_files(self, paths: list[str]):
        deleted = 0
        failed  = []
        for path in paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                self.db.delete_tracks_by_paths([path])
                deleted += 1
            except Exception as e:
                failed.append(f"{path}: {e}")

        msg = f"Deleted {deleted} file(s)."
        if failed:
            msg += f"\nFailed ({len(failed)}): {failed[0]}"
        QMessageBox.information(self, "Done", msg)
        self._start_scan()   # Re-scan to refresh results

    def _open_location(self):
        items = self.tree.selectedItems()
        if not items:
            return
        track = items[0].data(0, Qt.ItemDataRole.UserRole)
        if track and os.path.exists(track.file_path):
            folder = os.path.dirname(track.file_path)
            subprocess.Popen(f'explorer /select,"{track.file_path}"')


def _fmt_size(b: int) -> str:
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} TB"
