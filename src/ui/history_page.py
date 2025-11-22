from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, 
                             QMessageBox, QDateEdit, QCheckBox, QFileDialog)
from PyQt5.QtCore import Qt, QDate
from src.database import Database
import pandas as pd
import datetime

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
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
        
        # 搜索框
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜SN / 箱号...")
        self.search_input.returnPressed.connect(self.load)
        
        # 日期筛选
        self.chk_date = QCheckBox("按日期:")
        self.chk_date.stateChanged.connect(self.load)
        self.date_edit = QDateEdit(QDate.currentDate())
        self.date_edit.setCalendarPopup(True)
        self.date_edit.dateChanged.connect(self.load)
        
        btn_search = QPushButton("查询")
        btn_search.clicked.connect(self.load)
        
        btn_exp = QPushButton("导出Excel")
        btn_exp.clicked.connect(self.export_data)
        
        btn_del = QPushButton("删除选中")
        btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(self.delete_records)
        
        h_layout.addWidget(self.search_input)
        h_layout.addWidget(self.chk_date)
        h_layout.addWidget(self.date_edit)
        h_layout.addWidget(btn_search)
        h_layout.addWidget(btn_exp)
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
        self.table.hideColumn(0) 
        layout.addWidget(self.table)

    def refresh_data(self):
        self.load()

    def load(self):
        try:
            keyword = f"%{self.search_input.text().strip()}%"
            self.table.setRowCount(0)
            
            cursor = self.db.conn.cursor()
            
            # 构建查询
            sql = """
                SELECT id, box_no, name, spec, model, color, sn, code69, print_date 
                FROM records 
                WHERE (sn LIKE ? OR box_no LIKE ?)
            """
            params = [keyword, keyword]
            
            # 日期筛选
            if self.chk_date.isChecked():
                target_date = self.date_edit.date().toString("yyyy-MM-dd")
                sql += " AND print_date LIKE ?"
                params.append(f"{target_date}%")
            
            sql += " ORDER BY id DESC LIMIT 200"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for r_idx, row in enumerate(rows):
                self.table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    text = str(val) if val is not None else ""
                    
                    # 格式化时间: 2025-11-22 12:00:00 -> 20251122
                    # 时间是最后一列 (索引 8)
                    if c_idx == 8 and len(text) >= 10:
                        try:
                            text = text[:10].replace("-", "")
                        except: pass
                        
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(text))
                    
        except Exception as e:
            print(f"Load History Error: {e}")

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出", "print_history.xlsx", "Excel (*.xlsx)")
        if not path: return
        
        try:
            # 获取当前表格中所有数据
            rows = []
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            
            # 只导出可见的行
            for r in range(self.table.rowCount()):
                row_data = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    row_data.append(item.text() if item else "")
                rows.append(row_data)
            
            if not rows:
                return QMessageBox.warning(self, "提示", "无数据可导出")
            
            df = pd.DataFrame(rows, columns=headers)
            # 移除ID列导出 (第一列)
            if "ID" in df.columns:
                df = df.drop(columns=["ID"])
                
            df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", "导出成功")
            
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))

    def delete_records(self):
        try:
            selected_rows = self.table.selectedIndexes()
            if not selected_rows:
                return QMessageBox.warning(self, "提示", "未选中任何记录")
            
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
