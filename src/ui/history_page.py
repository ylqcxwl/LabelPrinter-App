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
    # --- 优化点：接收 Database 实例 ---
    def __init__(self, db: Database):
        super().__init__()
        try:
            self.db = db # 使用传入的共享实例
            # BartenderPrinter 需要 db 实例
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
        
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.dateChanged.connect(self.load)
        
        self.btn_search = QPushButton("搜索")
        self.btn_search.clicked.connect(self.load)

        self.btn_del = QPushButton("删除选中")
        self.btn_del.clicked.connect(self.delete_records)

        self.btn_exp = QPushButton("导出Excel")
        self.btn_exp.clicked.connect(self.export_data)

        h_layout.addWidget(QLabel("搜索:"))
        h_layout.addWidget(self.search_input)
        h_layout.addWidget(self.chk_date)
        h_layout.addWidget(self.date_start)
        h_layout.addWidget(QLabel("到"))
        h_layout.addWidget(self.date_end)
        h_layout.addWidget(self.btn_search)
        h_layout.addStretch()
        h_layout.addWidget(self.btn_del)
        h_layout.addWidget(self.btn_exp)
        
        layout.addLayout(h_layout)

        # --- 表格 ---
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["ID", "箱号", "箱内序号", "名称", "规格", "型号", "颜色", "69码", "SN", "打印时间"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)
        
        self.table.setColumnHidden(0, True) # 隐藏 ID 列

    def load(self):
        self.table.setRowCount(0)
        
        # 构造查询条件
        where_clauses = []
        params = []

        search_text = self.search_input.text().strip()
        if search_text:
            where_clauses.append("(sn LIKE ? OR box_no LIKE ?)")
            params.extend([f"%{search_text}%", f"%{search_text}%"])

        if self.chk_date.isChecked():
            start_date = self.date_start.date().toString("yyyy-MM-dd")
            end_date = self.date_end.date().toString("yyyy-MM-dd")
            where_clauses.append("print_date BETWEEN ? AND ?")
            # 结束日期包含当天，所以查询到下一天的开始
            params.extend([start_date, end_date + " 23:59:59"])

        where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""
        
        # 执行查询
        try:
            query = f"SELECT id, box_no, box_sn_seq, name, spec, model, color, code69, sn, print_date FROM records {where_sql} ORDER BY print_date DESC"
            self.db.cursor.execute(query, params)
            records = self.db.cursor.fetchall()

            self.table.setRowCount(len(records))
            for row_idx, data in enumerate(records):
                for col_idx, item in enumerate(data):
                    self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"查询数据失败: {e}")

    def refresh_data(self):
        self.load()

    def export_data(self):
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
            if QMessageBox.question(self, "确认", f"删 {len(ids)} 条?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                p = ",".join(["?"] * len(ids))
                self.db.cursor.execute(f"DELETE FROM records WHERE id IN ({p})", ids)
                self.db.conn.commit()
                QMessageBox.information(self, "成功", f"成功删除 {len(ids)} 条记录。")
                self.load()
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))
