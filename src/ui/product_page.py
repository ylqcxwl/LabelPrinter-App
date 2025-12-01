from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, 
                             QDialog, QFormLayout, QLineEdit, QSpinBox, 
                             QFileDialog, QMessageBox, QComboBox, QAbstractItemView)
from PyQt5.QtCore import Qt
from src.database import Database
import pandas as pd
import os

class ProductPage(QWidget):
    # --- 优化点：接收 Database 实例 ---
    def __init__(self, db: Database): 
        super().__init__()
        self.db = db # 使用传入的共享实例
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
        # ID, Name, Spec, Model, Color, SN4, SKU, 69, Qty, Weight, TemplatePath, RuleID, SNRuleID
        self.table.setColumnCount(13)
        self.table.setHorizontalHeaderLabels(["ID", "名称", "规格", "型号", "颜色", "SN4", "SKU", "69码", "数量", "重量", "模板路径", "箱号规则", "SN规则"])
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.layout.addWidget(self.table)
        
        self.refresh_data()

    def refresh_data(self):
        self.table.setRowCount(0)
        self.db.cursor.execute("SELECT p.*, r.name FROM products p LEFT JOIN box_rules r ON p.rule_id=r.id")
        products = self.db.cursor.fetchall()

        self.table.setRowCount(len(products))
        for row_idx, data in enumerate(products):
            # 将 RuleID 替换为 RuleName
            display_data = list(data)
            self.db.cursor.execute("SELECT name FROM sn_rules WHERE id=?", (data[12],))
            sn_rule_name = self.db.cursor.fetchone()
            display_data[11] = data[13] if data[13] else '无' # RuleName (来自 LEFT JOIN)
            display_data.append(sn_rule_name[0] if sn_rule_name else '无') # SNRuleName

            for col_idx, item in enumerate(display_data[:13]): # 只显示前13列（包含新的SN规则名）
                self.table.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))
            
            # 隐藏 ID 列
            self.table.setColumnHidden(0, True)

    def add_product(self):
        dialog = ProductDialog(self.db)
        if dialog.exec_():
            self.refresh_data()

    def edit_product(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择要修改的产品。")
            return
        
        row = selected_rows[0].row()
        product_id = self.table.item(row, 0).text()
        
        self.db.cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
        data = self.db.cursor.fetchone()
        
        if data:
            dialog = ProductDialog(self.db, data)
            if dialog.exec_():
                self.refresh_data()

    def delete_product(self):
        selected_rows = self.table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "提示", "请选择要删除的产品。")
            return

        rows_to_delete = set(index.row() for index in selected_rows)
        ids_to_delete = [self.table.item(row, 0).text() for row in rows_to_delete]

        if QMessageBox.question(self, "确认删除", f"确定删除选中的 {len(ids_to_delete)} 个产品吗？", 
                                QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                self.db.cursor.execute(f"DELETE FROM products WHERE id IN ({','.join(['?'] * len(ids_to_delete))})", ids_to_delete)
                self.db.conn.commit()
                QMessageBox.information(self, "成功", "删除成功。")
                self.refresh_data()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {e}")

    def import_data(self):
        path, _ = QFileDialog.getOpenFileName(self, "选择Excel", "", "Excel (*.xlsx *.xls)")
        if not path: return
        try:
            df = pd.read_excel(path).fillna('')
            # 确保列名匹配数据库字段 (忽略 ID 和 RuleID)
            required_cols = ["名称", "规格", "型号", "颜色", "SN4", "SKU", "69码", "数量", "重量", "模板路径"]
            for col in required_cols:
                if col not in df.columns:
                    QMessageBox.critical(self, "错误", f"Excel中缺少必要的列: {col}")
                    return

            count = 0
            for index, row in df.iterrows():
                # 检查 SN4 是否重复
                self.db.cursor.execute("SELECT id FROM products WHERE sn4=?", (str(row['SN4']),))
                if self.db.cursor.fetchone():
                    print(f"SKIPPED: SN4 {row['SN4']} already exists.")
                    continue

                # 尝试获取规则ID (简化逻辑：假设规则名称在数据库中唯一)
                rule_id = 0
                if '箱号规则' in row and row['箱号规则']:
                    self.db.cursor.execute("SELECT id FROM box_rules WHERE name=?", (str(row['箱号规则']),))
                    res = self.db.cursor.fetchone()
                    if res: rule_id = res[0]
                
                sn_rule_id = 0
                if 'SN校验规则' in row and row['SN校验规则']:
                    self.db.cursor.execute("SELECT id FROM sn_rules WHERE name=?", (str(row['SN校验规则']),))
                    res = self.db.cursor.fetchone()
                    if res: sn_rule_id = res[0]

                self.db.cursor.execute("""
                    INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id, sn_rule_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    row['名称'], row['规格'], row['型号'], row['颜色'], str(row['SN4']), 
                    str(row['SKU']), str(row['69码']), int(row['数量']), str(row['重量']), 
                    str(row['模板路径']), rule_id, sn_rule_id
                ))
                count += 1
            
            self.db.conn.commit()
            QMessageBox.information(self, "成功", f"成功导入 {count} 条新产品数据。")
            self.refresh_data()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入失败: {e}")


    def export_data(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出Excel", "product_data.xlsx", "Excel (*.xlsx)")
        if not path: return
        try:
            self.db.cursor.execute("SELECT p.name, p.spec, p.model, p.color, p.sn4, p.sku, p.code69, p.qty, p.weight, p.template_path, r.name, sr.name FROM products p LEFT JOIN box_rules r ON p.rule_id=r.id LEFT JOIN sn_rules sr ON p.sn_rule_id=sr.id")
            data = self.db.cursor.fetchall()
            
            columns = ["名称", "规格", "型号", "颜色", "SN4", "SKU", "69码", "数量", "重量", "模板路径", "箱号规则", "SN校验规则"]
            df = pd.DataFrame(data, columns=columns)
            df.to_excel(path, index=False)
            QMessageBox.information(self, "成功", "导出成功")
        except Exception as e:
            QMessageBox.critical(self, "错误", str(e))


class ProductDialog(QDialog):
    # --- 优化点：接收 Database 实例 ---
    def __init__(self, db: Database, data=None):
        super().__init__()
        self.db = db # 使用传入的共享实例
        self.data = data
        self.setWindowTitle("产品信息" + ("修改" if data else "新增"))
        self.setFixedWidth(400)

        self.full_tmpl = ""
        
        self.layout = QFormLayout(self)
        
        # ... (其余 UI 代码保持不变) ...

        # Fields
        self.name_le = QLineEdit(data[1] if data else "")
        self.spec_le = QLineEdit(data[2] if data else "")
        self.model_le = QLineEdit(data[3] if data else "")
        self.color_le = QLineEdit(data[4] if data else "")
        self.sn4_le = QLineEdit(data[5] if data else "")
        self.sku_le = QLineEdit(data[6] if data else "")
        self.code69_le = QLineEdit(data[7] if data else "")
        
        self.qty_sb = QSpinBox(); self.qty_sb.setRange(1, 9999); self.qty_sb.setValue(data[8] if data else 1)
        self.weight_le = QLineEdit(data[9] if data else "")
        
        # Template Path
        tmpl_h_layout = QHBoxLayout()
        self.tmpl_le = QLineEdit(os.path.basename(data[10]) if data else "")
        self.tmpl_le.setReadOnly(True)
        self.full_tmpl = data[10] if data else ""
        tmpl_btn = QPushButton("选择"); tmpl_btn.clicked.connect(self.sel_tmpl)
        tmpl_h_layout.addWidget(self.tmpl_le); tmpl_h_layout.addWidget(tmpl_btn)

        self.layout.addRow("名称*", self.name_le)
        self.layout.addRow("规格", self.spec_le)
        self.layout.addRow("型号", self.model_le)
        self.layout.addRow("颜色", self.color_le)
        self.layout.addRow("SN4*", self.sn4_le)
        self.layout.addRow("SKU", self.sku_le)
        self.layout.addRow("69码", self.code69_le)
        self.layout.addRow("数量*", self.qty_sb)
        self.layout.addRow("重量", self.weight_le)
        self.layout.addRow("模板文件*", tmpl_h_layout)

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

    def accept(self):
        name = self.name_le.text().strip()
        sn4 = self.sn4_le.text().strip()
        tmpl = self.full_tmpl.strip()
        
        if not all([name, sn4, tmpl]):
            QMessageBox.warning(self, "警告", "带*号的字段不能为空。")
            return

        spec = self.spec_le.text().strip()
        model = self.model_le.text().strip()
        color = self.color_le.text().strip()
        sku = self.sku_le.text().strip()
        code69 = self.code69_le.text().strip()
        qty = self.qty_sb.value()
        weight = self.weight_le.text().strip()
        rule_id = self.cb_box.currentData()
        sn_rule_id = self.cb_sn.currentData()
        
        try:
            if self.data:
                # Update
                product_id = self.data[0]
                self.db.cursor.execute("""
                    UPDATE products SET 
                    name=?, spec=?, model=?, color=?, sn4=?, sku=?, code69=?, qty=?, weight=?, template_path=?, rule_id=?, sn_rule_id=?
                    WHERE id=?
                """, (name, spec, model, color, sn4, sku, code69, qty, weight, tmpl, rule_id, sn_rule_id, product_id))
            else:
                # Insert
                self.db.cursor.execute("""
                    INSERT INTO products (name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id, sn_rule_id) 
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (name, spec, model, color, sn4, sku, code69, qty, weight, tmpl, rule_id, sn_rule_id))
            
            self.db.conn.commit()
            super().accept()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "错误", "SN4值已存在，请修改。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据库操作失败: {e}")
