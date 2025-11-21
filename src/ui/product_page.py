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
        self.btn_edit = QPushButton("修改选中")
        self.btn_del = QPushButton("删除选中")
        self.btn_import = QPushButton("导入Excel")
        self.btn_export = QPushButton("导出Excel")
        
        for btn in [self.btn_add, self.btn_edit, self.btn_del, self.btn_import, self.btn_export]:
            toolbar.addWidget(btn)
            
        toolbar.addStretch()
        self.layout.addLayout(toolbar)

        # 表格
        self.table = QTableWidget()
        self.table.setColumnCount(12)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "规格", "型号", "颜色", "SN前4", "SKU", "69码", "数量", "重量", "模板名称", "规则ID"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers) 
        self.table.doubleClicked.connect(self.edit_product)
        
        self.table.hideColumn(0) 
        self.table.hideColumn(11) 
        
        self.layout.addWidget(self.table)

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
                for c_idx, val in enumerate(row):
                    display_val = str(val)
                    if c_idx == 10 and val:
                        display_val = os.path.basename(val)
                    item = QTableWidgetItem(display_val)
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
                err_msg = str(e)
                if "UNIQUE constraint failed: products.sn4" in err_msg:
                    QMessageBox.critical(self, "错误", f"保存失败：SN前四位 '{data[4]}' 已存在！\nSN前4位必须唯一。")
                else:
                    QMessageBox.critical(self, "错误", f"保存失败: {e}")

    def edit_product(self):
        row = self.table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "提示", "请先选择一个产品")
            return
        pid = self.table.item(row, 0).text()
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (pid,))
        product_data = cursor.fetchone()
        
        if not product_data: return

        dialog = ProductDialog(self, product_data)
        if dialog.exec_():
            new_data = dialog.get_data() 
            update_data = new_data + (pid,) 
            try:
                sql = '''UPDATE products SET name=?, spec=?, model=?, color=?, sn4=?, sku=?, code69=?, qty=?, weight=?, template_path=?, rule_id=? 
                         WHERE id=?'''
                self.db.cursor.execute(sql, update_data)
                self.db.conn.commit()
                self.refresh_data()
                QMessageBox.information(self, "成功", "产品已修改")
            except Exception as e:
                err_msg = str(e)
                if "UNIQUE constraint failed: products.sn4" in err_msg:
                    QMessageBox.critical(self, "错误", f"修改失败：SN前四位已存在！")
                else:
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
                if 'name' not in df.columns or 'sn4' not in df.columns:
                    QMessageBox.warning(self, "格式错误", "Excel必须包含 'name' 和 'sn4' 列")
                    return
                
                success_count = 0
                error_count = 0
                
                for _, row in df.iterrows():
                    try:
                        name = str(row['name']) if pd.notna(row['name']) else ""
                        sn4 = str(row.get('sn4', '')) if pd.notna(row.get('sn4')) else ""
                        
                        if not sn4: continue # SN4不能为空

                        spec = str(row.get('spec', '')) if pd.notna(row.get('spec')) else ""
                        model = str(row.get('model', '')) if pd.notna(row.get('model')) else ""
                        color = str(row.get('color', '')) if pd.notna(row.get('color')) else ""
                        sku = str(row.get('sku', '')) if pd.notna(row.get('sku')) else ""
                        code69 = str(row.get('code69', '')) if pd.notna(row.get('code69')) else ""
                        qty = int(row.get('qty', 1)) if pd.notna(row.get('qty')) else 1
                        weight = str(row.get('weight', '')) if pd.notna(row.get('weight')) else ""
                        tmpl = str(row.get('template_path', '')) if pd.notna(row.get('template_path')) else ""
                        rule_id = int(row.get('rule_id', 0)) if pd.notna(row.get('rule_id')) else 0
                        
                        self.db.cursor.execute('''
                            INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id) 
                            VALUES (?,?,?,?,?,?,?,?,?,?,?)
                        ''', (name, spec, model, color, sn4, sku, code69, qty, weight, tmpl, rule_id))
                        
                        success_count += 1
                    except Exception as row_err:
                        print(f"Row Error: {row_err}")
                        error_count += 1
                        
                self.db.conn.commit()
                self.refresh_data()
                
                msg = f"导入完成。\n成功: {success_count} 条"
                if error_count > 0:
                    msg += f"\n失败: {error_count} 条 (SN前4位重复)"
                QMessageBox.information(self, "结果", msg)
                
            except Exception as e:
                QMessageBox.critical(self, "错误", f"文件读取失败: {e}")

class ProductDialog(QDialog):
    def __init__(self, parent=None, data=None):
        super().__init__(parent)
        self.setWindowTitle("产品信息编辑")
        self.layout = QFormLayout(self)
        self.resize(450, 400)
        
        self.db = Database()
        self.template_root = self.db.get_setting('template_root')
        
        self.inputs = {}
        fields_map = [
            ("名称", 1), ("规格", 2), ("型号", 3), ("颜色", 4), 
            ("SN前四位 (唯一)", 5), ("SKU", 6), ("69码", 7), ("重量", 9)
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

        self.tmpl_le = QLineEdit()
        self.tmpl_le.setPlaceholderText("请选择模板文件")
        self.tmpl_le.setReadOnly(True)
        if data and data[10]:
            self.tmpl_le.setText(os.path.basename(data[10]))
            self.full_tmpl_path = data[10]
        else:
            self.full_tmpl_path = ""
            
        btn_tmpl = QPushButton("选择模板")
        btn_tmpl.clicked.connect(self.sel_tmpl)
        
        tmpl_layout = QHBoxLayout()
        tmpl_layout.addWidget(self.tmpl_le)
        tmpl_layout.addWidget(btn_tmpl)
        self.layout.addRow("打印模板", tmpl_layout)

        self.combo_rule = QComboBox()
        self.db.cursor.execute("SELECT id, name FROM box_rules")
        rules = self.db.cursor.fetchall()
        self.combo_rule.addItem("无规则", 0)
        for r in rules:
            self.combo_rule.addItem(r[1], r[0])
            
        if data:
            idx = self.combo_rule.findData(data[11])
            if idx >= 0: self.combo_rule.setCurrentIndex(idx)
            
        self.layout.addRow("箱号规则", self.combo_rule)

        btn_save = QPushButton("保存提交")
        btn_save.clicked.connect(self.accept)
        self.layout.addRow(btn_save)

    def sel_tmpl(self):
        start_dir = self.template_root if self.template_root and os.path.exists(self.template_root) else ""
        path, _ = QFileDialog.getOpenFileName(self, "选择模板", start_dir, "Bartender (*.btw)")
        if path:
            filename = os.path.basename(path)
            self.tmpl_le.setText(filename)
            self.full_tmpl_path = filename

    def get_data(self):
        return (
            self.inputs["名称"].text(),
            self.inputs["规格"].text(),
            self.inputs["型号"].text(),
            self.inputs["颜色"].text(),
            self.inputs["SN前四位 (唯一)"].text(),
            self.inputs["SKU"].text(),
            self.inputs["69码"].text(),
            self.spin_qty.value(),
            self.inputs["重量"].text(),
            self.full_tmpl_path,
            self.combo_rule.currentData()
      )
