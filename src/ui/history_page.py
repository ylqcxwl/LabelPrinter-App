# src/ui/history_page.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, 
                             QMessageBox, QDateEdit, QCheckBox, QFileDialog, QLabel)
from PyQt5.QtCore import Qt, QDate
from src.database import Database
from src.bartender import BartenderPrinter # 引入打印机
import pandas as pd
import datetime
import os

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.db = Database()
            # 【重要修改点】将 self.db 实例传递给 BartenderPrinter
            self.printer = BartenderPrinter(self.db) 
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
        
        self.date_end = QDateEdit(QDate.currentDate().addDays(1)) # 默认包含今天
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.dateChanged.connect(self.load)
        
        self.btn_search = QPushButton("搜索 / 刷新")
        self.btn_search.clicked.connect(self.load)

        self.btn_export = QPushButton("导出 Excel")
        self.btn_export.clicked.connect(self.export_records)

        self.btn_delete = QPushButton("删除选中")
        self.btn_delete.clicked.connect(self.delete_records)
        
        h_layout.addWidget(self.search_input)
        h_layout.addWidget(self.chk_date)
        h_layout.addWidget(self.date_start)
        h_layout.addWidget(QLabel("到"))
        h_layout.addWidget(self.date_end)
        h_layout.addWidget(self.btn_search)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_export)
        h_layout.addWidget(self.btn_delete)
        
        layout.addLayout(h_layout)

        # --- 表格 ---
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "ID", "箱号", "箱内序号", "产品名称", "规格", "型号", "69码", "SN码", "打印时间"
        ])
        
        # 隐藏 ID 列
        self.table.setColumnHidden(0, True)
        
        # 自动调整列宽
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.Stretch) # SN码列拉伸
        
        # 整行选择
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        # 只读
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        
        layout.addWidget(self.table)
        
    def load(self):
        try:
            self.table.setRowCount(0)
            
            query = "SELECT id, box_no, box_sn_seq, name, spec, model, code69, sn, print_date FROM records WHERE 1=1"
            params = []
            
            # 搜索框筛选
            search_text = self.search_input.text().strip()
            if search_text:
                query += " AND (sn LIKE ? OR box_no LIKE ?)"
                params.append(f"%{search_text}%")
                params.append(f"%{search_text}%")
            
            # 日期筛选
            if self.chk_date.isChecked():
                start_date = self.date_start.date().toString("yyyy-MM-dd") + " 00:00:00"
                # 结束日期包含当天，所以加一天，然后查询 < next_day
                end_date_dt = self.date_end.date().toPyDate() + datetime.timedelta(days=1)
                end_date = end_date_dt.strftime("'%Y-%m-%d %H:%M:%S'") # SQL格式

                query += f" AND print_date >= ? AND print_date < {end_date}"
                params.append(start_date)
            
            query += " ORDER BY id DESC"
            
            self.db.cursor.execute(query, params)
            rows = self.db.cursor.fetchall()
            
            self.table.setRowCount(len(rows))
            
            for row_idx, row_data in enumerate(rows):
                for col_idx, item in enumerate(row_data):
                    self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))
                    
        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载数据失败: {e}")

    def export_records(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出", "print_history.xlsx", "Excel (*.xlsx)")
        if not path: return
        try:
            rows = []; headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
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
            if QMessageBox.question(self, "确认", f"删 {len(ids)} 条? (不可恢复)", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                p = ",".join("?" * len(ids))
                self.db.cursor.execute(f"DELETE FROM records WHERE id IN ({p})", ids)
                self.db.conn.commit()
                QMessageBox.information(self, "成功", f"成功删除 {len(ids)} 条记录")
                self.load() # 重新加载数据
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
