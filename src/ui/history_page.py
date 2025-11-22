from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, QMessageBox)
from src.database import Database
import traceback

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        # 使用 try-catch 保护初始化，防止DB连接失败导致闪退
        try:
            self.db = Database()
            self.init_ui()
            self.load()
        except Exception as e:
            print(f"History Init Error: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # 搜索栏
        h_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜SN / 箱号...")
        self.search_input.returnPressed.connect(self.load)
        
        btn_search = QPushButton("查询")
        btn_search.clicked.connect(self.load)
        
        btn_del = QPushButton("删除选中")
        btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(self.delete_records)
        
        h_layout.addWidget(self.search_input)
        h_layout.addWidget(btn_search)
        h_layout.addWidget(btn_del)
        layout.addLayout(h_layout)
        
        # 表格
        self.table = QTableWidget()
        cols = ["ID", "箱号", "名称", "规格", "型号", "颜色", "SN", "69码", "时间"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.hideColumn(0) # 隐藏ID
        layout.addWidget(self.table)

    def refresh_data(self):
        # 主界面调用此方法
        self.load()

    def load(self):
        try:
            keyword = f"%{self.search_input.text().strip()}%"
            self.table.setRowCount(0)
            
            cursor = self.db.conn.cursor()
            # 确保SQL列数与表格列数一致
            sql = """
                SELECT id, box_no, name, spec, model, color, sn, code69, print_date 
                FROM records 
                WHERE sn LIKE ? OR box_no LIKE ? 
                ORDER BY id DESC LIMIT 100
            """
            cursor.execute(sql, (keyword, keyword))
            
            rows = cursor.fetchall()
            for r_idx, row in enumerate(rows):
                self.table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    # 安全转换，防止 None 报错
                    text = str(val) if val is not None else ""
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(text))
                    
        except Exception as e:
            print(f"Load History Error: {e}")
            # 不弹窗，避免循环闪退

    def delete_records(self):
        try:
            selected_rows = self.table.selectedIndexes()
            if not selected_rows:
                return QMessageBox.warning(self, "提示", "未选中任何记录")
            
            # 获取选中的ID (第0列)
            # 使用 set 去重行号
            rows = set(index.row() for index in selected_rows)
            ids = [self.table.item(r, 0).text() for r in rows]
            
            if QMessageBox.question(self, "确认", f"确定删除 {len(ids)} 条记录?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                placeholders = ",".join("?" * len(ids))
                sql = f"DELETE FROM records WHERE id IN ({placeholders})"
                self.db.cursor.execute(sql, ids)
                self.db.conn.commit()
                self.load()
                
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
