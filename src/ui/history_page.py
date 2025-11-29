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
            self.printer = BartenderPrinter() # 实例化打印机
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
        
        lbl_to = QLabel("至")
        
        self.date_end = QDateEdit(QDate.currentDate())
        self.date_end.setCalendarPopup(True)
        self.date_end.setDisplayFormat("yyyy-MM-dd")
        self.date_end.dateChanged.connect(self.load)
        
        btn_search = QPushButton("查询")
        btn_search.clicked.connect(self.load)
        
        btn_exp = QPushButton("导出Excel")
        btn_exp.clicked.connect(self.export_data)
        
        # --- 新增：重打按钮 ---
        btn_reprint = QPushButton("重打此箱")
        btn_reprint.setStyleSheet("background-color: #2980b9; color: white; font-weight: bold;")
        btn_reprint.clicked.connect(self.reprint_box)
        # -------------------

        btn_del = QPushButton("删除选中")
        btn_del.setStyleSheet("color: red;")
        btn_del.clicked.connect(self.delete_records)
        
        h_layout.addWidget(self.search_input, 2)
        h_layout.addWidget(self.chk_date)
        h_layout.addWidget(self.date_start)
        h_layout.addWidget(lbl_to)
        h_layout.addWidget(self.date_end)
        h_layout.addWidget(btn_search)
        h_layout.addWidget(btn_exp)
        h_layout.addWidget(btn_reprint) # 添加重打按钮
        h_layout.addWidget(btn_del)
        
        layout.addLayout(h_layout)
        
        # --- 表格区域 ---
        self.table = QTableWidget()
        # 修改：新增 "序号" 列 (Box SN Seq)
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

    def refresh_data(self):
        self.load()

    def load(self):
        try:
            keyword = f"%{self.search_input.text().strip()}%"
            self.table.setRowCount(0)
            
            cursor = self.db.conn.cursor()
            
            # 修改查询：增加 box_sn_seq
            sql = """
                SELECT id, box_no, box_sn_seq, name, spec, model, color, sn, code69, print_date 
                FROM records 
                WHERE (sn LIKE ? OR box_no LIKE ?)
            """
            params = [keyword, keyword]
            
            if self.chk_date.isChecked():
                s_date = self.date_start.date().toString("yyyy-MM-dd")
                e_date = self.date_end.date().toString("yyyy-MM-dd")
                start_time = f"{s_date} 00:00:00"
                end_time = f"{e_date} 23:59:59"
                sql += " AND print_date >= ? AND print_date <= ?"
                params.append(start_time)
                params.append(end_time)
            
            sql += " ORDER BY id DESC LIMIT 1000"
            
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            
            for r_idx, row in enumerate(rows):
                self.table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    text = str(val) if val is not None else ""
                    # 时间列是最后一列 (索引9)
                    if c_idx == 9 and len(text) >= 10:
                        try: text = text[:10].replace("-", "")
                        except: pass
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(text))
                    
            self.table.resizeColumnToContents(1)
            
        except Exception as e:
            print(f"Load History Error: {e}")

    def reprint_box(self):
        """重打选中记录所属的整箱标签"""
        row = self.table.currentRow()
        if row < 0:
            return QMessageBox.warning(self, "提示", "请先选择一条打印记录")
        
        # 获取选中行的箱号和产品名称
        box_no = self.table.item(row, 1).text()
        prod_name = self.table.item(row, 3).text()
        
        if QMessageBox.question(self, "确认", f"确定要重新打印箱号 [{box_no}] 吗？", 
                                QMessageBox.Yes|QMessageBox.No) != QMessageBox.Yes:
            return

        try:
            c = self.db.conn.cursor()
            
            # 1. 查找产品信息以获取模板路径和箱规
            c.execute("SELECT template_path, qty, weight, sku FROM products WHERE name=?", (prod_name,))
            prod_info = c.fetchone()
            if not prod_info:
                return QMessageBox.critical(self, "错误", f"找不到产品 [{prod_name}] 的信息，无法获取模板。")
            
            tmpl_path, qty, weight, sku = prod_info
            
            # 2. 查找该箱号下的所有记录
            c.execute("SELECT sn, box_sn_seq, spec, model, color, code69, print_date FROM records WHERE box_no=? ORDER BY box_sn_seq", (box_no,))
            records = c.fetchall()
            
            if not records:
                return QMessageBox.warning(self, "错误", "未找到该箱号的记录")

            # 3. 构建打印数据
            # 取第一条记录的信息作为公共信息
            first_rec = records[0]
            # records struct: 0:sn, 1:seq, 2:spec, 3:model, 4:color, 5:code69, 6:date
            
            data_map = {
                "name": prod_name,
                "spec": first_rec[2],
                "model": first_rec[3],
                "color": first_rec[4],
                "code69": first_rec[5],
                "sn4": first_rec[0][:4] if len(first_rec[0])>=4 else "", # 简单提取前4
                "sku": sku,
                "qty": len(records), # 实际记录数
                "weight": weight,
                "box_no": box_no,
                "prod_date": first_rec[6][:10] if len(first_rec[6])>=10 else ""
            }
            
            # 填充 SN 列表 (1, 2, 3...)
            # 创建一个临时的 SN 列表，索引对应 box_sn_seq
            # 假设 box_sn_seq 是 1-based (1,2,3...)
            # 我们需要按照装箱序号正确填入位置
            
            # 初始化所有位置为空
            full_box_qty = int(qty) if qty else len(records)
            for i in range(1, full_box_qty + 1):
                data_map[str(i)] = ""
            
            # 填入实际 SN
            for rec in records:
                sn = rec[0]
                # 尝试用 box_sn_seq 作为位置，如果记录中没有序号(旧数据)，则按顺序填充
                seq = rec[1]
                if seq and int(seq) > 0:
                    data_map[str(seq)] = sn
                else:
                    # 如果没有序号，按列表顺序找一个空位填充 (简单容错)
                    pass 
            
            # 如果上面 seq 逻辑复杂，这里简化：直接按列表顺序填入 1..N
            for i, rec in enumerate(records):
                data_map[str(i+1)] = rec[0]

            # 4. 获取映射配置
            mapping = self.db.get_setting('field_mapping')
            from src.config import DEFAULT_MAPPING
            if not isinstance(mapping, dict): mapping = DEFAULT_MAPPING
            
            # 转换键名
            final_dat = {}
            for k, v in mapping.items():
                if k in data_map: final_dat[v] = data_map[k]
            # 复制 SN 键 (1, 2, 3...)
            for k, v in data_map.items():
                if k.isdigit(): final_dat[k] = v

            # 5. 打印
            root = self.db.get_setting('template_root')
            full_path = os.path.join(root, tmpl_path) if root and tmpl_path else tmpl_path
            
            ok, msg = self.printer.print_label(full_path, final_dat)
            if ok:
                QMessageBox.information(self, "成功", "补打指令已发送")
            else:
                QMessageBox.critical(self, "打印失败", msg)

        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "系统错误", str(e))
    
    # ... export_data 和 delete_records 保持不变 ...
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
                p = ",".join("?" * len(ids))
                self.db.cursor.execute(f"DELETE FROM records WHERE id IN ({p})", ids)
                self.db.conn.commit()
                self.load()
        except Exception as e: QMessageBox.critical(self, "错误", str(e))
