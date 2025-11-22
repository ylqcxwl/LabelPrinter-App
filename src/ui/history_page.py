from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, QMessageBox)
from src.database import Database

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        layout = QVBoxLayout(self)
        
        h = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("搜SN/箱号...")
        b_search = QPushButton("查"); b_search.clicked.connect(self.load)
        b_del = QPushButton("删"); b_del.clicked.connect(self.delete)
        h.addWidget(self.search); h.addWidget(b_search); h.addWidget(b_del)
        layout.addLayout(h)
        
        self.table = QTableWidget()
        # 关键修复：表头顺序
        cols = ["ID", "箱号", "名称", "规格", "型号", "颜色", "SN", "69码", "时间"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.hideColumn(0)
        layout.addWidget(self.table)
        self.load()

    def load(self):
        k = f"%{self.search.text()}%"
        self.table.setRowCount(0)
        c = self.db.conn.cursor()
        # 关键修复：SQL SELECT 顺序必须与表头一致
        c.execute("SELECT id, box_no, name, spec, model, color, sn, code69, print_date FROM records WHERE sn LIKE ? OR box_no LIKE ? ORDER BY id DESC LIMIT 100", (k,k))
        for r_idx, row in enumerate(c.fetchall()):
            self.table.insertRow(r_idx)
            for c_idx, val in enumerate(row):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def delete(self):
        ids = [self.table.item(i.row(),0).text() for i in self.table.selectedIndexes()]
        if ids:
            self.db.cursor.execute(f"DELETE FROM records WHERE id IN ({','.join(ids)})")
            self.db.conn.commit(); self.load()
