from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QPushButton, QHBoxLayout, 
                             QTableWidgetItem, QLineEdit, QHeaderView, QAbstractItemView, 
                             QMessageBox, QDateEdit, QCheckBox, QFileDialog, QLabel, QProgressBar)
from PyQt5.QtCore import Qt, QDate, QThread, pyqtSignal
from src.database import Database
from src.bartender import BartenderPrinter
import pandas as pd
import datetime
import os
import traceback

# --- 核心修改：新增工作线程类 ---
# 将耗时的数据库查询操作放到这里执行，防止主界面卡死
class SearchWorker(QThread):
    # 定义信号：查询完成后，将结果列表传回主界面
    finished = pyqtSignal(list, str) # result_rows, error_msg

    def __init__(self, db_path, sql, params):
        super().__init__()
        self.db_path = db_path
        self.sql = sql
        self.params = params

    def run(self):
        try:
            # 在线程中建立独立的只读连接，避免干扰主线程
            import sqlite3
            # 使用 URI 模式打开只读连接，稍微更安全
            conn = sqlite3.connect(f"file:{self.db_path}?mode=ro", uri=True)
            cursor = conn.cursor()
            cursor.execute(self.sql, self.params)
            rows = cursor.fetchall()
            conn.close()
            self.finished.emit(rows, "")
        except Exception as e:
            self.finished.emit([], str(e))

class HistoryPage(QWidget):
    def __init__(self):
        super().__init__()
        try:
            self.db = Database()
            self.printer = BartenderPrinter()
            self.init_ui()
            # 默认加载今天的数据，避免启动时全表扫描
            self.load()
        except Exception as e:
            print(f"History Init Error: {e}")

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # --- 顶部工具栏 ---
        h_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜SN / 箱号 (支持模糊搜索)")
        self.search_input.returnPressed.connect(self.load)
        
        # 默认勾选日期筛选，这是性能优化的关键！
        # 如果不限制日期，百万级数据的 LIKE 查询会极慢
        self.chk_date = QCheckBox("日期筛选:")
        self.chk_date.setChecked(True) 
        self.chk_date.stateChanged.connect(self.load)
        
        # 默认只查最近 30 天
        self.date_start = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_start.setCalendarPopup(True)
        self.date_start.setDisplayFormat("yyyy-MM-dd")
        self.date_start.dateChanged.connect(self.load)
        
        lbl_to = QLabel("至")
        
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.dateChanged.connect(self.load)
        
        self.btn_search = QPushButton("查询")
        self.btn_search.clicked.connect(self.load)
        
        self.btn_exp = QPushButton("导出Excel")
        self.btn_exp.clicked.connect(self.export_data)
        
        self.btn_reprint = QPushButton("重打此箱")
        self.btn_reprint.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        self.btn_reprint.clicked.connect(self.reprint_box)

        btn_del = QPushButton("删除选中")
        btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(self.delete_records)
        
        h_layout.addWidget(self.search_input, 2)
        h_layout.addWidget(self.chk_date)
        h_layout.addWidget(self.date_start)
        h_layout.addWidget(lbl_to)
        h_layout.addWidget(self.date_end)
        h_layout.addWidget(self.btn_search)
        h_layout.addWidget(self.btn_exp)
        h_layout.addWidget(self.btn_reprint)
        h_layout.addWidget(btn_del)
        
        layout.addLayout(h_layout)

        # --- 进度条 (默认隐藏) ---
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0) # 忙碌模式
        self.progress_bar.setFixedHeight(5)
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)
        
        # --- 表格区域 ---
        self.table = QTableWidget()
        cols = ["ID", "箱号", "序号", "名称", "规格", "型号", "颜色", "SN", "69码", "时间"]
        self.table.setColumnCount(len(cols))
        self.table.setHorizontalHeaderLabels(cols)
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch) 
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents) 
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents) 
        
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.hideColumn(0) 
        layout.addWidget(self.table)
        
        # 状态标签
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: gray;")
        layout.addWidget(self.lbl_status)

    def refresh_data(self):
        # 页面切换时不需要自动加载，防止卡顿，由用户点击查询即可
        pass

    def load(self):
        # 1. 禁用按钮，显示进度条，防止重复点击
        self.btn_search.setEnabled(False)
        self.progress_bar.show()
        self.lbl_status.setText("正在查询数据库，请稍候...")
        self.table.setRowCount(0)

        # 2. 构建 SQL
        keyword = self.search_input.text().strip()
        sql = """
            SELECT id, box_no, box_sn_seq, name, spec, model, color, sn, code69, print_date 
            FROM records 
            WHERE 1=1
        """
        params = []

        # 优化策略：
        # 如果勾选了日期，强制先用索引过滤日期。
        # SQLite 查询优化器会优先使用 print_date 索引，
        # 将扫描范围从 100万条 缩小到 几千条，然后再在这个小范围内匹配 SN。
        if self.chk_date.isChecked():
            s_date = self.date_start.date().toString("yyyy-MM-dd")
            e_date = self.date_end.date().toString("yyyy-MM-dd")
            start_time = f"{s_date} 00:00:00"
            end_time = f"{e_date} 23:59:59"
            sql += " AND print_date >= ? AND print_date <= ?"
            params.append(start_time)
            params.append(end_time)

        if keyword:
            # 模糊查询放在最后
            sql += " AND (sn LIKE ? OR box_no LIKE ?)"
            params.append(f"%{keyword}%")
            params.append(f"%{keyword}%")
        
        sql += " ORDER BY id DESC LIMIT 1000"

        # 3. 启动后台线程
        self.worker = SearchWorker(self.db.db_name, sql, params)
        self.worker.finished.connect(self.on_search_finished)
        self.worker.start()

    def on_search_finished(self, rows, error):
        # 线程回调：数据查完后更新 UI
        self.btn_search.setEnabled(True)
        self.progress_bar.hide()
        
        if error:
            self.lbl_status.setText(f"查询出错: {error}")
            QMessageBox.critical(self, "错误", error)
            return

        self.table.setRowCount(0)
        # 关闭排序功能以提高大批量插入速度
        self.table.setSortingEnabled(False) 
        
        for r_idx, row in enumerate(rows):
            self.table.insertRow(r_idx)
            for c_idx, val in enumerate(row):
                text = str(val) if val is not None else ""
                if c_idx == 9 and len(text) >= 10: # 时间格式化
                    try: text = text[:10]
                    except: pass
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(text))
        
        self.table.setSortingEnabled(True)
        self.lbl_status.setText(f"查询完成，共找到 {len(rows)} 条记录 (仅显示前 1000 条)")

    def reprint_box(self):
        row = self.table.currentRow()
        if row < 0:
            return QMessageBox.warning(self, "提示", "请先选择一条打印记录")
        
        box_no = self.table.item(row, 1).text()
        prod_name = self.table.item(row, 3).text()
        
        if QMessageBox.question(self, "确认", f"确定要重新打印箱号 [{box_no}] 吗？", 
                                QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            c = self.db.conn.cursor()
            c.execute("SELECT template_path, qty, weight, sku FROM products WHERE name=?", (prod_name,))
            prod_info = c.fetchone()
            if not prod_info:
                return QMessageBox.critical(self, "错误", f"找不到产品 [{prod_name}] 的信息")
            
            tmpl_path, qty, weight, sku = prod_info
            
            c.execute("SELECT sn, box_sn_seq, spec, model, color, code69, print_date FROM records WHERE box_no=? ORDER BY box_sn_seq", (box_no,))
            records = c.fetchall()
            
            if not records:
                return QMessageBox.warning(self, "错误", "未找到该箱号的记录")

            first_rec = records[0]
            data_map = {
                "name": prod_name,
                "spec": first_rec[2],
                "model": first_rec[3],
                "color": first_rec[4],
                "code69": first_rec[5],
                "sn4": first_rec[0][:4] if len(first_rec[0])>=4 else "", 
                "sku": sku,
                "qty": len(records), 
                "weight": weight,
                "box_no": box_no,
                "prod_date": first_rec[6][:10] if len(first_rec[6])>=10 else ""
            }
            
            full_box_qty = int(qty) if qty else len(records)
            for i in range(1, full_box_qty + 1):
                data_map[str(i)] = ""
            
            for i, rec in enumerate(records):
                data_map[str(i+1)] = rec[0]

            mapping = self.db.get_setting('field_mapping')
            from src.config import DEFAULT_MAPPING
            if not isinstance(mapping, dict): mapping = DEFAULT_MAPPING
            
            final_dat = {}
            for k, v in mapping.items():
                if k in data_map: final_dat[v] = data_map[k]
            for k, v in data_map.items():
                if k.isdigit(): final_dat[k] = v

            root = self.db.get_setting('template_root')
            full_path = os.path.join(root, tmpl_path) if root and tmpl_path else tmpl_path
            
            # 使用 Bartender 打印
            # 注意：此处直接调用打印是主线程阻塞的，但Bartender本身处理很快
            # 如果需要，这里也可以改为线程调用
            ok, msg = self.printer.print_label(full_path, final_dat)
            if ok:
                QMessageBox.information(self, "成功", "补打指令已发送")
            else:
                QMessageBox.critical(self, "打印失败", msg)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "系统错误", str(e))

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
            
            self.lbl_status.setText("正在导出 Excel，请稍候...")
            # 简单的导出可以在主线程，如果数据量特别大建议也移到线程
            df = pd.DataFrame(rows, columns=headers)
            if "ID" in df.columns: df = df.drop(columns=["ID"])
            df.to_excel(path, index=False)
            self.lbl_status.setText("导出成功")
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
                self.load() # 重新触发查询线程刷新
        except Exception as e: QMessageBox.critical(self, "错误", str(e))
