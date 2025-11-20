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
        self.btn_import = QPushButton("导入Excel")
        self.btn_export = QPushButton("导出Excel")
        self.btn_del = QPushButton("删除选中")
        
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_import)
        toolbar.addWidget(self.btn_export)
        toolbar.addWidget(self.btn_del)
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "规格", "型号", "颜色", "SN前4", "SKU", "69码", "数量", "重量", "模板"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.layout.addWidget(self.table)

        # 事件
        self.btn_add.clicked.connect(self.add_product)
        self.btn_del.clicked.connect(self.delete_product)
        self.btn_export.clicked.connect(self.export_data)
        self.btn_import.clicked.connect(self.import_data)

        self.refresh_data()

    def refresh_data(self):
        self.table.setRowCount(0)
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM products")
        rows = cursor.fetchall()
        for r_idx, row in enumerate(rows):
            self.table.insertRow(r_idx)
            for c_idx, col in enumerate(row):
                self.table.setItem(r_idx, c_idx, QTableWidgetItem(str(col)))

    def add_product(self):
        dialog = ProductDialog(self)
        if dialog.exec_():
            data = dialog.get_data()
            sql = '''INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id) 
                     VALUES (?,?,?,?,?,?,?,?,?,?,?)'''
            self.db.cursor.execute(sql, data)
            self.db.conn.commit()
            self.refresh_data()

    def delete_product(self):
        curr_row = self.table.currentRow()
        if curr_row >= 0:
            pid = self.table.item(curr_row, 0).text()
            if QMessageBox.question(self, "确认", "确定删除?") == QMessageBox.Yes:
                self.db.cursor.execute("DELETE FROM products WHERE id=?", (pid,))
                self.db.conn.commit()
                self.refresh_data()

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出", "", "Excel Files (*.xlsx)")
        if path:
            df = pd.read_sql_query("SELECT * FROM products", self.db.conn)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", "导出成功")

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入", "", "Excel Files (*.xlsx)")
        if path:
            try:
                df = pd.read_excel(path)
                # 简化处理：假设列名对应
                for _, row in df.iterrows():
                    sql = '''INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id) 
                             VALUES (?,?,?,?,?,?,?,?,?,?,?)'''
                    # 需要确保Excel列顺序或使用命名映射，此处略作简化
                    # 实际生产建议做严格列名校验
                    pass 
                QMessageBox.information(self, "提示", "导入功能需严格匹配列名，演示代码仅做框架")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

class ProductDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("产品信息")
        self.layout = QFormLayout(self)
        
        self.inputs = {}
        fields = ["名称", "规格", "型号", "颜色", "SN前四位", "SKU", "69码", "重量", "模板路径"]
        for f in fields:
            le = QLineEdit()
            self.layout.addRow(f, le)
            self.inputs[f] = le
            
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 999)
        self.layout.addRow("每箱数量", self.spin_qty)

        # 箱号规则下拉
        self.combo_rule = QComboBox()
        self.db = Database()
        self.db.cursor.execute("SELECT id, name FROM box_rules")
        rules = self.db.cursor.fetchall()
        for r in rules:
            self.combo_rule.addItem(r[1], r[0])
        self.layout.addRow("箱号规则", self.combo_rule)

        # 模板选择按钮
        btn_tmpl = QPushButton("选择模板")
        btn_tmpl.clicked.connect(self.sel_tmpl)
        self.layout.addRow("", btn_tmpl)

        btn_save = QPushButton("保存")
        btn_save.clicked.connect(self.accept)
        self.layout.addRow(btn_save)

    def sel_tmpl(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择Bartender模板", "", "Bartender Files (*.btw)")
        if path:
            self.inputs["模板路径"].setText(path)

    def get_data(self):
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
            self.combo_rule.currentData()
                                                                 )
