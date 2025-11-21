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
        
        # 工具栏
        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("新增产品")
        self.btn_edit = QPushButton("修改选中") # 新增修改按钮
        self.btn_del = QPushButton("删除选中")
        self.btn_import = QPushButton("导入Excel")
        self.btn_export = QPushButton("导出Excel")
        
        for btn in [self.btn_add, self.btn_edit, self.btn_del, self.btn_import, self.btn_export]:
            toolbar.addWidget(btn)
            
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(12) # 增加一列隐藏ID
        # 这里的表头只是显示用
        self.table.setHorizontalHeaderLabels(["ID", "名称", "规格", "型号", "颜色", "SN前4", "SKU", "69码", "数量", "重量", "模板名称", "规则ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) # 禁止直接编辑表格
        self.table.doubleClicked.connect(self.edit_product) # 双击编辑
        
        # 隐藏不需要显示的列 (ID, 规则ID)
        self.table.hideColumn(0) 
        self.table.hideColumn(11) 
        
        self.layout.addWidget(self.table)

        # 信号
        self.btn_add.clicked.connect(self.add_product)
        self.btn_edit.clicked.connect(self.edit_product)
        self.btn_del.clicked.connect(self.delete_product)
        self.btn_import.clicked.connect(self.import_data)
        self.btn_export.clicked.connect(self.export_data)

        self.refresh_data()

    def refresh_data(self):
        self.table.setRowCount(0)
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT * FROM products ORDER BY id DESC")
            rows = cursor.fetchall()
            for r_idx, row in enumerate(rows):
                self.table.insertRow(r_idx)
                # row结构: id, name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id
                
                # 填充数据
                for c_idx, val in enumerate(row):
                    display_val = str(val)
                    
                    # 特殊处理：模板列 (索引10) 只显示文件名
                    if c_idx == 10 and val:
                        display_val = os.path.basename(val)
                    
                    item = QTableWidgetItem(display_val)
                    # 将真实数据存入UserRole (特别是模板路径，显示的是文件名，但我们需要存路径)
                    item.setData(Qt.UserRole, val) 
                    self.table.setItem(r_idx, c_idx, item)
                    
        except Exception as e:
            print(f"Refresh error: {e}")

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

    def edit_product(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个产品")
            return
            
        # 获取当前行数据
        pid = self.table.item(row, 0).text()
        
        # 从数据库获取完整最新信息
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (pid,))
        product_data = cursor.fetchone()
        
        if not product_data: return

        dialog = ProductDialog(self, product_data)
        if dialog.exec_():
            new_data = dialog.get_data() # tuple (name, spec...)
            # 加上ID用于更新
            update_data = new_data + (pid,) 
            
            try:
                sql = '''UPDATE products SET name=?, spec=?, model=?, color=?, sn4=?, sku=?, code69=?, qty=?, weight=?, template_path=?, rule_id=? 
                         WHERE id=?'''
                self.db.cursor.execute(sql, update_data)
                self.db.conn.commit()
                self.refresh_data()
                QMessageBox.information(self, "成功", "产品已修改")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"更新失败: {e}")

    def delete_product(self):
        row = self.table.currentRow()
        if row >= 0:
            pid = self.table.item(row, 0).text()
            name = self.table.item(row, 1).text()
            if QMessageBox.question(self, "确认", f"确定删除产品: {name}?") == QMessageBox.Yes:
                self.db.cursor.execute("DELETE FROM products WHERE id=?", (pid,))
                self.db.conn.commit()
                self.refresh_data()

    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出", "products_export.xlsx", "Excel Files (*.xlsx)")
        if path:
            try:
                df = pd.read_sql_query("SELECT * FROM products", self.db.conn)
                df.to_excel(path, index=False)
                QMessageBox.information(self, "成功", "导出成功")
            except Exception as e:
                QMessageBox.critical(self, "错误", str(e))

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入", "", "Excel Files (*.xlsx *.xls)")
        if path:
            try:
                df = pd.read_excel(path)
                # 简单的列检查
                required_cols = ['name', 'sn4']
                if not all(col in df.columns for col in required_cols):
                    QMessageBox.warning(self, "格式错误", "Excel缺少必要的列 (name, sn4)")
                    return
                
                count = 0
                for _, row in df.iterrows():
                    # 使用 .get() 防止列缺失报错
                    try:
                        self.db.cursor.execute('''
                            INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        ''', (
                            row.get('name'), row.get('spec', ''), row.get('model', ''), row.get('color', ''),
                            str(row.get('sn4', '')), str(row.get('sku', '')), str(row.get('code69', '')),
                            int(row.get('qty', 1)), str(row.get('weight', '')), 
                            row.get('template_path', ''), int(row.get('rule_id', 0))
                        ))
                        count += 1
                    except Exception as e:
                        print(f"Skipping row: {e}")
                        
                self.db.conn.commit()
                self.refresh_data()
                QMessageBox.information(self, "成功", f"成功导入 {count} 条数据")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导入失败: {e}")

class ProductDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("产品信息编辑")
        self.layout = QFormLayout(self)
        self.resize(450, 550)
        
        self.inputs = {}
        # 字段名映射到DB顺序: name=1, spec=2, model=3, color=4, sn4=5, sku=6, code69=7, weight=9, tmpl=10
        fields_map = [
            ("名称", 1), ("规格", 2), ("型号", 3), ("颜色", 4), 
            ("SN前四位", 5), ("SKU", 6), ("69码", 7), ("重量", 9), ("模板路径", 10)
        ]
        
        for label, idx in fields_map:
            le = QLineEdit()
            if data: le.setText(str(data[idx]) if data[idx] else "")
            self.layout.addRow(label, le)
            self.inputs[label] = le
            
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 9999)
        if data: self.spin_qty.setValue(data[8])
        self.layout.addRow("每箱数量", self.spin_qty)

        # 箱号规则
        self.combo_rule = QComboBox()
        self.db = Database()
        self.db.cursor.execute("SELECT id, name FROM box_rules")
        rules = self.db.cursor.fetchall()
        self.combo_rule.addItem("无规则", 0)
        for r in rules:
            self.combo_rule.addItem(r[1], r[0])
            
        if data:
            idx = self.combo_rule.findData(data[11])
            if idx >= 0: self.combo_rule.setCurrentIndex(idx)
            
        self.layout.addRow("箱号规则", self.combo_rule)

        btn_tmpl = QPushButton("选择模板文件")
        btn_tmpl.clicked.connect(self.sel_tmpl)
        self.layout.addRow("", btn_tmpl)

        btn_save = QPushButton("保存提交")
        btn_save.clicked.connect(self.accept)
        self.layout.addRow(btn_save)

    def sel_tmpl(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择模板", "", "Bartender (*.btw)")
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
