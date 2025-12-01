from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, 
                             QDialog, QFormLayout, QLineEdit, QSpinBox, 
                             QFileDialog, QMessageBox, QComboBox, QAbstractItemView)
from PyQt5.QtCore import Qt
from src.database import Database
import pandas as pd
import os

class ProductPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.layout = QVBoxLayout(self)
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("新增产品"); self.btn_add.clicked.connect(self.add_product)
        self.btn_edit = QPushButton("修改选中"); self.btn_edit.clicked.connect(self.edit_product)
        self.btn_del = QPushButton("删除选中"); self.btn_del.clicked.connect(self.delete_product)
        self.btn_imp = QPushButton("导入Excel"); self.btn_imp.clicked.connect(self.import_data)
        self.btn_exp = QPushButton("导出Excel"); self.btn_exp.clicked.connect(self.export_data)
        for b in [self.btn_add, self.btn_edit, self.btn_del, self.btn_imp, self.btn_exp]: toolbar.addWidget(b)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        # Table
        self.table = QTableWidget()
        # ID, Name, Spec, Model, Color, SN4, SKU, 69, Qty, Weight, Tmpl, BoxRule, SNRule
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "规格", "型号", "颜色", "SN前4", "SKU", "69码", "数量", "重量", "模板名称", "箱规ID", "SN规ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        self.table.doubleClicked.connect(self.edit_product)
        
        self.table.hideColumn(0); self.table.hideColumn(11); self.table.hideColumn(12)
        self.layout.addWidget(self.table)

        self.refresh_data()

    def refresh_data(self):
        self.table.setRowCount(0)
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT * FROM products ORDER BY id DESC")
            for r_idx, row in enumerate(cursor.fetchall()):
                self.table.insertRow(r_idx)
                for c_idx, val in enumerate(row):
                    disp = str(val)
                    if c_idx == 10 and val: disp = os.path.basename(val)
                    item = QTableWidgetItem(disp)
                    item.setData(Qt.UserRole, val)
                    self.table.setItem(r_idx, c_idx, item)
        except Exception as e: print(f"Refresh error: {e}")

    def add_product(self):
        dlg = ProductDialog(self)
        if dlg.exec_():
            d = dlg.get_data()
            try:
                sql = '''INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id, sn_rule_id) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?,?)'''
                self.db.cursor.execute(sql, d)
                self.db.conn.commit(); self.refresh_data()
                QMessageBox.information(self, "成功", "已添加")
            except Exception as e:
                msg = "SN前4位已存在" if "UNIQUE constraint" in str(e) else str(e)
                QMessageBox.critical(self, "错误", msg)

    def edit_product(self):
        r = self.table.currentRow()
        if r < 0: return
        pid = self.table.item(r, 0).text()
        cursor = self.db.conn.cursor(); cursor.execute("SELECT * FROM products WHERE id=?", (pid,))
        row = cursor.fetchone()
        if not row: return

        dlg = ProductDialog(self, row)
        if dlg.exec_():
            d = dlg.get_data() + (pid,)
            try:
                sql = '''UPDATE products SET name=?, spec=?, model=?, color=?, sn4=?, sku=?, code69=?, qty=?, weight=?, template_path=?, rule_id=?, sn_rule_id=?
                         WHERE id=?'''
                self.db.cursor.execute(sql, d)
                self.db.conn.commit(); self.refresh_data()
                QMessageBox.information(self, "成功", "已修改")
            except Exception as e: QMessageBox.critical(self, "错误", str(e))

    def delete_product(self):
        r = self.table.currentRow()
        if r >= 0:
            pid = self.table.item(r, 0).text()
            if QMessageBox.question(self,"确认","删除?",QMessageBox.Yes)==QMessageBox.Yes:
                self.db.cursor.execute("DELETE FROM products WHERE id=?", (pid,))
                self.db.conn.commit(); self.refresh_data()

    def import_data(self):
        p, _ = QFileDialog.getOpenFileName(self, "导入", "", "Excel (*.xlsx *.xls)")
        if not p: return
        try:
            df = pd.read_excel(p)
            if 'name' not in df.columns or 'sn4' not in df.columns: return QMessageBox.warning(self,"错","缺列")
            s, f = 0, 0
            for _, r in df.iterrows():
                try:
                    val = (
                        str(r['name']), str(r.get('spec','')), str(r.get('model','')), str(r.get('color','')), 
                        str(r['sn4']), str(r.get('sku','')), str(r.get('code69','')), int(r.get('qty',1)), 
                        str(r.get('weight','')), str(r.get('template_path','')), int(r.get('rule_id',0)), int(r.get('sn_rule_id',0))
                    )
                    self.db.cursor.execute('''INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id, sn_rule_id) 
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''', val)
                    s += 1
                except: f += 1
            self.db.conn.commit(); self.refresh_data()
            QMessageBox.information(self, "结果", f"成功: {s}, 失败: {f}")
        except Exception as e: QMessageBox.critical(self, "错", str(e))

    def export_data(self):
        p, _ = QFileDialog.getSaveFileName(self, "导出", "products.xlsx", "Excel (*.xlsx)")
        if p: pd.read_sql_query("SELECT * FROM products", self.db.conn).to_excel(p, index=False); QMessageBox.information(self,"好","成功")

class ProductDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("产品编辑")
        self.layout = QFormLayout(self)
        self.db = Database()
        self.inputs = {}
        
        # 字段定义 (Name, DB Index)
        f_map = [("名称",1), ("规格",2), ("型号",3), ("颜色",4), ("SN前4(唯一)",5), ("SKU",6), ("69码",7), ("重量",9)]
        for lbl, idx in f_map:
            le = QLineEdit()
            if data: le.setText(str(data[idx]) if data[idx] else "")
            self.layout.addRow(lbl, le)
            self.inputs[lbl] = le
            
        self.spin_qty = QSpinBox(); self.spin_qty.setRange(1,9999)
        if data: self.spin_qty.setValue(data[8])
        self.layout.addRow("每箱数量", self.spin_qty)

        self.tmpl_le = QLineEdit(); self.tmpl_le.setReadOnly(True)
        if data and data[10]: self.tmpl_le.setText(os.path.basename(data[10])); self.full_tmpl = data[10]
        else: self.full_tmpl = ""
        b_tmpl = QPushButton("选模板"); b_tmpl.clicked.connect(self.sel_tmpl)
        h = QHBoxLayout(); h.addWidget(self.tmpl_le); h.addWidget(b_tmpl)
        self.layout.addRow("打印模板", h)

        # Box Rule
        self.cb_box = QComboBox(); self.cb_box.addItem("无", 0)
        self.db.cursor.execute("SELECT id, name FROM box_rules")
        for r in self.db.cursor.fetchall(): self.cb_box.addItem(r[1], r[0])
        if data: idx = self.cb_box.findData(data[11]); self.cb_box.setCurrentIndex(idx if idx>=0 else 0)
        self.layout.addRow("箱号规则", self.cb_box)

        # SN Rule (New)
        self.cb_sn = QComboBox(); self.cb_sn.addItem("无", 0)
        self.db.cursor.execute("SELECT id, name FROM sn_rules")
        for r in self.db.cursor.fetchall(): self.cb_sn.addItem(r[1], r[0])
        if data: 
            # data[12] 是 sn_rule_id，如果数据库结构刚变，可能需要 try/except 处理旧数据
            try:
                idx = self.cb_sn.findData(data[12])
                self.cb_sn.setCurrentIndex(idx if idx>=0 else 0)
            except: pass
        self.layout.addRow("SN校验规则", self.cb_sn)

        btn = QPushButton("保存"); btn.clicked.connect(self.accept)
        self.layout.addRow(btn)

    def sel_tmpl(self):
        root = self.db.get_setting('template_root')
        p, _ = QFileDialog.getOpenFileName(self, "模板", root, "*.btw")
        if p: self.tmpl_le.setText(os.path.basename(p)); self.full_tmpl = os.path.basename(p)

    def get_data(self):
        return (
            self.inputs["名称"].text(), self.inputs["规格"].text(), self.inputs["型号"].text(), self.inputs["颜色"].text(),
            self.inputs["SN前4(唯一)"].text(), self.inputs["SKU"].text(), self.inputs["69码"].text(),
            self.spin_qty.value(), self.inputs["重量"].text(), self.full_tmpl,
            self.cb_box.currentData(), self.cb_sn.currentData()
      )
