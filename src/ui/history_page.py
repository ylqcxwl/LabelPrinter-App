from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, QMessageBox)
from src.database import Database
import traceback

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        layout = QVBoxLayout(self)
        
        h = QHBoxLayout()
        self.search = QLineEdit(); self.search.setPlaceholderText("搜SN/箱号...")
        self.search.returnPressed.connect(self.load)
        b1 = QPushButton("查"); b1.clicked.connect(self.load)
        b2 = QPushButton("删"); b2.clicked.connect(self.delete)
        h.addWidget(self.search); h.addWidget(b1); h.addWidget(b2)
        layout.addLayout(h)
        
        self.table = QTableWidget()
        # 必须确保列数和查询字段数一致
        cols = ["ID", "箱号", "名称", "规格", "型号", "颜色", "SN", "69码", "时间"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.hideColumn(0)
        layout.addWidget(self.table)
        
        # 延时加载防止初始化未完成时崩溃
        self.load()

    def load(self):
        try:
            k = f"%{self.search.text()}%"
            self.table.setRowCount(0)
            c = self.db.conn.cursor()
            # 增加 try-except 保护查询
            sql = "SELECT id, box_no, name, spec, model, color, sn, code69, print_date FROM records WHERE sn LIKE ? OR box_no LIKE ? ORDER BY id DESC LIMIT 100"
            c.execute(sql, (k, k))
            for r_idx, row in enumerate(c.fetchall()):
                self.table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    val_str = str(val) if val is not None else ""
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(val_str))
        except Exception as e:
            print(f"History Load Error: {e}")
            # 不弹窗打扰用户，只在控制台输出

    def delete(self):
        try:
            rows = sorted(set(i.row() for i in self.table.selectedIndexes()), reverse=True)
            if not rows: return QMessageBox.warning(self,"提示","未选中")
            
            ids = [self.table.item(r, 0).text() for r in rows]
            if QMessageBox.question(self,"确认",f"删 {len(ids)} 条?",QMessageBox.Yes)==QMessageBox.Yes:
                placeholders = ",".join("?" * len(ids))
                self.db.cursor.execute(f"DELETE FROM records WHERE id IN ({placeholders})", ids)
                self.db.conn.commit()
                self.load()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
