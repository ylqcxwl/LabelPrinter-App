from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, 
                             QDialog, QFormLayout, QLineEdit, QSpinBox, 
                             QFileDialog, QMessageBox, QComboBox)
from src.database import Database
import pandas as pd

class ProductPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.layout = QVBoxLayout(self)
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("新增产品")
        self.btn_del = QPushButton("删除选中")
        self.btn_add.clicked.connect(self.add_product)
        self.btn_del.clicked.connect(self.delete_product)
        
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_del)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "规格", "型号", "颜色", "SN前4", "SKU", "69码", "数量", "重量", "模板"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        self.refresh_data()

    def refresh_data(self):
        self.table.setRowCount(0)
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT * FROM products")
            rows = cursor.fetchall()
            for r_idx, row in enumerate(rows):
                self.table.insertRow(r_idx)
                # 只显示前11列，不显示 rule_id
                for c_idx in range(11):
                    val = row[c_idx] if c_idx < len(row) else ""
                    self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(val)))
        except Exception as e:
            print(f"Refresh products error: {e}")

    def add_product(self):
        dialog = ProductDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            try:
                sql = '''INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id) 
                         VALUES (?,?,?,?,?,?,?,?,?,?,?)'''
                self.db.cursor.execute(sql, data)
                self.db.conn.commit()
                self.refresh_data()
                QMessageBox.information(self, "成功", "产品已添加")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def delete_product(self):
        curr_row = self.table.currentRow()
        if curr_row >= 0:
            pid = self.table.item(curr_row, 0).text()
            if QMessageBox.question(self, "确认", "确定删除?") == QMessageBox.Yes:
                self.db.cursor.execute("DELETE FROM products WHERE id=?", (pid,))
                self.db.conn.commit()
                self.refresh_data()

class ProductDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("产品信息")
        self.layout = QFormLayout(self)
        self.resize(400, 500)
        
        self.inputs = {}
        fields = ["名称", "规格", "型号", "颜色", "SN前四位", "SKU", "69码", "重量", "模板路径"]
        for f in fields:
            le = QLineEdit()
            self.layout.addRow(f, le)
            self.inputs[f] = le
            
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        self.layout.addRow("每箱数量", self.spin_qty)

        # 箱号规则下拉
        self.combo_rule = QComboBox()
        self.db = Database()
        try:
            # 获取规则列表
            self.db.cursor.execute("SELECT id, name FROM box_rules")
            rules = self.db.cursor.fetchall()
            if not rules:
                self.combo_rule.addItem("无规则 (请先去设置页添加)", 0)
            else:
                for r in rules:
                    self.combo_rule.addItem(r[1], r[0])
        except:
             self.combo_rule.addItem("读取规则失败", 0)
             
        self.layout.addRow("箱号规则", self.combo_rule)

        btn_tmpl = QPushButton("选择模板文件")
        btn_tmpl.clicked.connect(self.sel_tmpl)
        self.layout.addRow("", btn_tmpl)

        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self.accept)
        self.layout.addRow(btn_save)

    def sel_tmpl(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模板", "", "Bartender (*.btw)")
        if path:
            self.inputs["模板路径"].setText(path)

    def get_data(self):
        rule_id = self.combo_rule.currentData()
        if rule_id is None: rule_id = 0
        
        return (
            self.inputs["名称"].text(),
            self.inputs["规格"].text(),
            self.inputs["型号"].text(),
            self.inputs["颜色"].text(),
            self.inputs["SN前四位"].text(),
            self.inputs["SKU"].text(),
            self.inputs["69码"].text(),
            self.spin_qty.value(),
            self.inputs["重量"].text(),
            self.inputs["模板路径"].text(),
            rule_id
              )
