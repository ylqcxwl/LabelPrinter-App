from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, QTableWidgetItem, QLineEdit
from src.database import Database

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        layout = QVBoxLayout(self)
        
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("搜索SN、箱号或69码")
        btn_search = QPushButton("查询")
        btn_search.clicked.connect(self.refresh_data)
        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(btn_search)
        layout.addLayout(search_layout)
        
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels(["箱号", "序号", "SN", "名称", "型号", "生产日期", "打印时间", "规格"])
        layout.addWidget(self.table)
        
    def refresh_data(self):
        k = f"%{self.txt_search.text()}%"
        sql = "SELECT box_no, box_sn_seq, sn, name, model, prod_date, print_date, spec FROM records WHERE sn LIKE ? OR box_no LIKE ? ORDER BY id DESC LIMIT 100"
        
        self.table.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute(sql, (k, k))
        for r_idx, row in enumerate(cursor.fetchall()):
            self.table.insertRow(r_idx)
            for c_idx, val in enumerate(row):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
