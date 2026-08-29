"""
MP3 Organizer — Smart Playlist Dialog
Create smart playlists with rule-based criteria.
"""
import json

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QFrame, QComboBox, QWidget, QScrollArea,
    QMessageBox, QSizePolicy
)

from config import SMART_CRITERIA_FIELDS, SMART_CRITERIA_OPS
from database.db_manager import DatabaseManager


class _RuleRow(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.field_cb = QComboBox()
        self.field_cb.addItems(SMART_CRITERIA_FIELDS)
        layout.addWidget(self.field_cb)

        self.op_cb = QComboBox()
        self.op_cb.addItems(SMART_CRITERIA_OPS)
        layout.addWidget(self.op_cb)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Value…")
        layout.addWidget(self.value_edit, 1)

        remove_btn = QPushButton("✕")
        remove_btn.setObjectName("icon_btn")
        remove_btn.setFixedSize(26, 26)
        remove_btn.clicked.connect(self.deleteLater)
        layout.addWidget(remove_btn)

    def to_dict(self):
        return {
            'field': self.field_cb.currentText(),
            'op':    self.op_cb.currentText(),
            'value': self.value_edit.text().strip(),
        }


class SmartPlaylistDialog(QDialog):
    def __init__(self, db: DatabaseManager, parent=None):
        super().__init__(parent)
        self.db = db
        self.setWindowTitle("New Smart Playlist")
        self.setMinimumWidth(500)
        self.setModal(True)
        self._rules: list[_RuleRow] = []
        self._build_ui()

    def _build_ui(self):
        main = QVBoxLayout(self)
        main.setSpacing(14)
        main.setContentsMargins(20, 20, 20, 20)

        title = QLabel("New Smart Playlist")
        title.setStyleSheet("font-size:16px;font-weight:700;")
        main.addWidget(title)

        # Name
        name_row = QHBoxLayout()
        name_row.addWidget(QLabel("Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("e.g. Tamil Songs, Rock Playlist…")
        name_row.addWidget(self.name_edit, 1)
        main.addLayout(name_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep)

        main.addWidget(QLabel("Match tracks where ALL of these rules apply:"))

        # Rules area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setMaximumHeight(220)

        self.rules_container = QWidget()
        self.rules_layout    = QVBoxLayout(self.rules_container)
        self.rules_layout.setContentsMargins(0, 0, 0, 0)
        self.rules_layout.setSpacing(6)
        self.rules_layout.addStretch()
        scroll.setWidget(self.rules_container)
        main.addWidget(scroll)

        add_rule_btn = QPushButton("＋  Add Rule")
        add_rule_btn.clicked.connect(self._add_rule)
        main.addWidget(add_rule_btn)

        # Add a default rule
        self._add_rule()

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        main.addWidget(sep2)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        save_btn = QPushButton("Create Playlist")
        save_btn.setObjectName("accent_btn")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        main.addLayout(btn_row)

    def _add_rule(self):
        row = _RuleRow()
        # Insert before the stretch
        self.rules_layout.insertWidget(self.rules_layout.count() - 1, row)
        self._rules.append(row)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Error", "Please enter a playlist name.")
            return
        rules = []
        for i in range(self.rules_layout.count() - 1):
            w = self.rules_layout.itemAt(i).widget()
            if isinstance(w, _RuleRow) and w.to_dict()['value']:
                rules.append(w.to_dict())
        if not rules:
            QMessageBox.warning(self, "Error", "Please add at least one rule with a value.")
            return
        self.db.create_playlist(name, is_smart=True, criteria=json.dumps(rules))
        self.accept()
