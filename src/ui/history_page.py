from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, 
                             QMessageBox, QDateEdit, QCheckBox, QFileDialog, QLabel)
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
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- 顶部工具栏 ---
        h_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜SN / 箱号...")
        self.search_input.returnPressed.connect(self.load)
        
        self.chk_date = QCheckBox("日期筛选:")
        self.chk_date.stateChanged.connect(self.load)
        
        self.date_start = QDateEdit(QDate.currentDate())
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.dateChanged.connect(self.load)
        
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.dateChanged.connect(self.load)
        
        btn_search = QPushButton("查询")
        btn_search.clicked.connect(self.load)
        
        btn_exp = QPushButton("导出Excel")
        btn_exp.clicked.connect(self.export_data)
        
        btn_del = QPushButton("删除选中")
        btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(self.delete_records)
        
        h_layout.addWidget(self.search_input, 2)
        h_layout.addWidget(self.chk_date)
        h_layout.addWidget(self.date_start)
        h_layout.addWidget(QLabel("至"))
        h_layout.addWidget(self.date_end)
        h_layout.addWidget(btn_search)
        h_layout.addWidget(btn_exp)
        h_layout.addWidget(btn_del)
        
        layout.addLayout(h_layout)
        
        # --- 表格区域 (修改：列宽优化) ---
        self.table = QTableWidget()
        cols = ["ID", "箱号", "名称", "规格", "型号", "颜色", "SN", "69码", "时间"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        
        # 关键修改：箱号(索引1)自适应，SN(索引6)自适应，其他伸展或默认
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Stretch) # 默认伸展
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) # 箱号自适应内容
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents) # SN自适应内容
        
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
            
            sql = """
                SELECT id, box_no, name, spec, model, color, sn, code69, print_date 
                FROM records 
                WHERE (sn LIKE ? OR box_no LIKE ?)
            """
            params = [keyword, keyword]
            
            if self.chk_date.isChecked():
                s_date = self.date_start.date().toString("yyyy-MM-dd")
                e_date = self.date_end.date().toString("yyyy-MM-dd")
                sql += " AND print_date >= ? AND print_date <= ?"
                params.append(f"{s_date} 00:00:00")
                params.append(f"{e_date} 23:59:59")
            
            sql += " ORDER BY id DESC LIMIT 1000"
            
            cursor.execute(sql, params)
            for r_idx, row in enumerate(cursor.fetchall()):
                self.table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    text = str(val) if val is not None else ""
                    if c_idx == 8 and len(text) >= 10:
                        try: text = text[:10].replace("-", "")
                        except: pass
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(text))
                    
        except Exception as e:
            print(f"Load History Error: {e}")

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出", "print_history.xlsx", "Excel (*.xlsx)")
        if not path: return
        
        try:
            rows = []
            headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
            for r in range(self.table.rowCount()):
                row_data = []
                for c in range(self.table.columnCount()):
                    item = self.table.item(r, c)
                    row_data.append(item.text() if item else "")
                rows.append(row_data)
            
            if not rows: return QMessageBox.warning(self, "提示", "无数据")
            
            df = pd.DataFrame(rows, columns=headers)
            if "ID" in df.columns: df = df.drop(columns=["ID"])
            df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", "导出成功")
            
        except Exception as e: QMessageBox.critical(self, "错误", str(e))

    def delete_records(self):
        try:
            rows = set(i.row() for i in self.table.selectedIndexes())
            if not rows: return QMessageBox.warning(self, "提示", "未选中")
            
            ids = [self.table.item(r, 0).text() for r in rows]
            if QMessageBox.question(self, "确认", f"删 {len(ids)} 条?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                p = ",".join("?" * len(ids))
                self.db.cursor.execute(f"DELETE FROM records WHERE id IN ({p})", ids)
                self.db.conn.commit()
                self.load()
        except Exception as e: QMessageBox.critical(self, "错误", str(e))
