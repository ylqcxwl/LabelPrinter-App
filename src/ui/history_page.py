from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, QMessageBox)
from PyQt5.QtCore import Qt
from src.database import Database

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # 搜索栏
        search_layout = QHBoxLayout()
        self.txt_search = QLineEdit()
        self.txt_search.setPlaceholderText("搜索SN、箱号或69码")
        self.txt_search.returnPressed.connect(self.refresh_data)
        
        btn_search = QPushButton("查询")
        btn_search.clicked.connect(self.refresh_data)
        
        # 删除按钮
        btn_del = QPushButton("删除选中记录")
        btn_del.setStyleSheet("background-color: #dc3545; color: white; font-weight: bold;")
        btn_del.clicked.connect(self.delete_records)
        
        search_layout.addWidget(self.txt_search)
        search_layout.addWidget(btn_search)
        search_layout.addWidget(btn_del)
        layout.addLayout(search_layout)
        
        # 表格 - 按要求排序
        self.table = QTableWidget()
        # 顺序：箱号，序号，名称、规格、型号、颜色、SN、69码、生产日期、打印日期
        headers = ["ID", "箱号", "序号", "名称", "规格", "型号", "颜色", "SN", "69码", "生产日期", "打印时间"]
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection) # 允许按Ctrl/Shift多选
        self.table.hideColumn(0) # 隐藏ID列，用于删除
        layout.addWidget(self.table)
        
        self.refresh_data()
        
    def refresh_data(self):
        k = f"%{self.txt_search.text().strip()}%"
        # 调整SQL查询顺序以匹配表头
        sql = """
            SELECT id, box_no, box_sn_seq, name, spec, model, color, sn, code69, prod_date, print_date 
            FROM records 
            WHERE sn LIKE ? OR box_no LIKE ? OR code69 LIKE ?
            ORDER BY id DESC LIMIT 200
        """
        
        self.table.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute(sql, (k, k, k))
        for r_idx, row in enumerate(cursor.fetchall()):
            self.table.insertRow(r_idx)
            for c_idx, val in enumerate(row):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))

    def delete_records(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请先选择要删除的记录")
            return
            
        # 获取去重后的行号
        rows = set(index.row() for index in selected_rows)
        ids_to_delete = []
        for r in rows:
            item = self.table.item(r, 0) # ID在第0列
            if item: ids_to_delete.append(item.text())
            
        if not ids_to_delete: return
        
        if QMessageBox.question(self, "确认", f"确定删除选中的 {len(ids_to_delete)} 条记录吗？") == QMessageBox.Yes:
            try:
                # 批量删除
                placeholders = ', '.join(['?'] * len(ids_to_delete))
                sql = f"DELETE FROM records WHERE id IN ({placeholders})"
                self.db.cursor.execute(sql, ids_to_delete)
                self.db.conn.commit()
                QMessageBox.information(self, "成功", "删除成功")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))
