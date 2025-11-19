import importlib
import sys
from typing import TYPE_CHECKING

try:
    qt_widgets = importlib.import_module("PyQt6.QtWidgets")
    QApplication = qt_widgets.QApplication
    QMainWindow = qt_widgets.QMainWindow
    QWidget = qt_widgets.QWidget
    QHBoxLayout = qt_widgets.QHBoxLayout
    QVBoxLayout = qt_widgets.QVBoxLayout
    QListWidget = qt_widgets.QListWidget
    QTableWidget = qt_widgets.QTableWidget
    QTableWidgetItem = qt_widgets.QTableWidgetItem
    QPushButton = qt_widgets.QPushButton
    QStatusBar = qt_widgets.QStatusBar

    qt_core = importlib.import_module("PyQt6.QtCore")
    Qt = qt_core.Qt
except Exception:
    # PyQt6 is optional for running tests; avoid import errors during tests
    # Provide lightweight placeholders so the module can be imported and tested
    class _Placeholder:
        def __init__(self, *args, **kwargs):
            pass
    QApplication = QMainWindow = QWidget = _Placeholder
    QHBoxLayout = QVBoxLayout = QListWidget = QTableWidget = QTableWidgetItem = QPushButton = QStatusBar = _Placeholder
    Qt = None

# Provide a typing-friendly alias for the base QMainWindow so mypy has a stable
# symbol to check against even when PyQt6 isn't installed at runtime.
if TYPE_CHECKING:
    from PyQt6.QtWidgets import QMainWindow as _QMainWindow
else:
    _QMainWindow = QMainWindow

from ..managers.cleaner_manager import CleanerManager


class MainWindow(_QMainWindow):
    """Minimal main window for the Smart Cleaner GUI skeleton."""

    def __init__(self):
        # If Qt classes are objects due to missing PyQt6, don't init GUI
        if not callable(getattr(super(), '__init__', None)):
            return
        super().__init__()
        self.setWindowTitle("Smart Cleaner - PyQt6 (Skeleton)")
        self.resize(900, 600)
        self.manager = CleanerManager()
        self._build_ui()

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        h = QHBoxLayout()
        central.setLayout(h)

        # Left: plugins list
        self.plugin_list = QListWidget()
        self.plugin_list.setFixedWidth(280)
        self.plugin_list.currentTextChanged.connect(self.on_plugin_selected)
        h.addWidget(self.plugin_list)

        # Right: items and actions
        right = QVBoxLayout()
        h.addLayout(right)

        # Actions bar
        actions = QHBoxLayout()
        self.scan_btn = QPushButton("Scan")
        self.scan_btn.clicked.connect(self.on_scan)
        self.clean_btn = QPushButton("Clean")
        self.clean_btn.clicked.connect(self.on_clean)
        self.undo_btn = QPushButton("Undo")
        self.undo_btn.clicked.connect(self.on_undo)
        actions.addWidget(self.scan_btn)
        actions.addWidget(self.clean_btn)
        actions.addWidget(self.undo_btn)
        actions.addStretch()
        right.addLayout(actions)

        # Table of items
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Description", "Size", "Safety"])
        right.addWidget(self.table)

        # Status bar
        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")

    def on_scan(self):
        self.status.showMessage("Scanning...")
        results = self.manager.scan_all()
        self._populate_plugins(results)
        self.status.showMessage("Scan complete")

    def _populate_plugins(self, results):
        self.plugin_list.clear()
        self._scan_results = results
        for plugin in results.keys():
            self.plugin_list.addItem(plugin)
        # select first
        if results:
            first = next(iter(results.keys()))
            self.plugin_list.setCurrentRow(0)
            self._populate_items_for_plugin(first)

    def on_plugin_selected(self, plugin_name):
        if plugin_name:
            self._populate_items_for_plugin(plugin_name)

    def _populate_items_for_plugin(self, plugin_name):
        items = self._scan_results.get(plugin_name, [])
        self.table.setRowCount(0)
        for item in items:
            row = self.table.rowCount()
            self.table.insertRow(row)
            # description
            self.table.setItem(row, 0, QTableWidgetItem(item.description))
            # use CleanableItem.get_size_human() if available, otherwise fallback
            size_text = getattr(item, 'get_size_human', None)
            if callable(size_text):
                size_text = item.get_size_human()
            else:
                size_text = self._format_size(item.size)
            self.table.setItem(row, 1, QTableWidgetItem(size_text))
            # show safety level name if it's an enum, otherwise string
            safety_text = item.safety.name if hasattr(item.safety, 'name') else str(item.safety)
            self.table.setItem(row, 2, QTableWidgetItem(safety_text))

    def on_clean(self):
        self.status.showMessage("Cleaning (simulated)...")
        # Build selection: all items for simplicity
        items_by_plugin = self._scan_results
        results = self.manager.clean_selected(items_by_plugin, dry_run=False)
        total = sum(r.get('total_size', 0) for r in results.values())
        self.status.showMessage(f"Clean complete. Freed {self._format_size(total)}")

    def on_undo(self):
        # Placeholder
        self.status.showMessage("Undo not implemented in skeleton")

    def _format_size(self, bytes):
        for unit in ['B','KB','MB','GB','TB']:
            if bytes < 1024.0:
                return f"{bytes:.2f} {unit}"
            bytes /= 1024.0
        return f"{bytes:.2f} PB"


def run():
    # If PyQt6 isn't available, print a helpful message
    if "PyQt6" not in globals():
        print("PyQt6 is not installed. Install PyQt6 to run the GUI: pip install PyQt6")
        return
    app = QApplication(sys.argv)
    win = MainWindow()
    win.show()
    sys.exit(app.exec())
