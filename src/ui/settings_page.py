from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView)
from PyQt5.QtCore import Qt
from src.database import Database
import json

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # --- 规则管理 ---
        rule_group = QGroupBox("箱号规则管理")
        rule_layout = QVBoxLayout(rule_group)

        form_rule = QFormLayout()
        self.rule_name = QLineEdit()
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("例如: MZXH{SN4}{Y1}{M1}{SEQ5}")
        
        form_rule.addRow("规则名称:", self.rule_name)
        form_rule.addRow("规则格式:", self.rule_fmt)
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("添加规则")
        btn_add.clicked.connect(self.add_rule)
        btn_del = QPushButton("删除选中")
        btn_del.clicked.connect(self.delete_rule)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_del)
        form_rule.addRow(btn_layout)
        
        rule_layout.addLayout(form_rule)

        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(3)
        self.table_rules.setHorizontalHeaderLabels(["ID", "名称", "规则格式"])
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_rules.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_rules.setMaximumHeight(200)
        rule_layout.addWidget(self.table_rules)

        main_layout.addWidget(rule_group)

        # --- 映射管理 ---
        map_group = QGroupBox("字段映射")
        map_layout = QVBoxLayout(map_group)
        self.mapping_inputs = {}
        form_map = QFormLayout()
        
        fields = [("名称", "name"), ("规格", "spec"), ("型号", "model"), ("颜色", "color"),
                  ("SN前4", "sn4"), ("SKU", "sku"), ("69码", "code69"),
                  ("数量", "qty"), ("重量", "weight"), ("箱号", "box_no")]
        
        for lbl, key in fields:
            le = QLineEdit()
            self.mapping_inputs[key] = le
            form_map.addRow(lbl, le)
            
        btn_save_map = QPushButton("保存映射")
        btn_save_map.clicked.connect(self.save_mapping)
        map_layout.addLayout(form_map)
        map_layout.addWidget(btn_save_map)
        main_layout.addWidget(map_group)
        
        self.refresh_data()

    def refresh_data(self):
        self.load_rules()
        self.load_mapping()

    def load_rules(self):
        try:
            self.table_rules.setRowCount(0)
            cursor = self.db.conn.cursor()
            # 关键修复：这里统一使用 rule_string
            cursor.execute("SELECT id, name, rule_string FROM box_rules")
            for r, row in enumerate(cursor.fetchall()):
                self.table_rules.insertRow(r)
                for c, val in enumerate(row):
                    self.table_rules.setItem(r, c, QTableWidgetItem(str(val)))
        except Exception as e:
            print(f"Load rules error: {e}")

    def add_rule(self):
        name = self.rule_name.text()
        fmt = self.rule_fmt.text()
        if name and fmt:
            try:
                # 关键修复：插入 rule_string
                self.db.cursor.execute("INSERT INTO box_rules (name, rule_string) VALUES (?,?)", (name, fmt))
                self.db.conn.commit()
                self.rule_name.clear()
                self.rule_fmt.clear()
                self.load_rules()
                QMessageBox.information(self, "成功", "规则已添加")
            except Exception as e:
                QMessageBox.warning(self, "错误", str(e))

    def delete_rule(self):
        row = self.table_rules.currentRow()
        if row >= 0:
            rid = self.table_rules.item(row, 0).text()
            self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rid,))
            self.db.conn.commit()
            self.load_rules()

    def load_mapping(self):
        m = self.db.get_setting('field_mapping')
        for k, v in self.mapping_inputs.items():
            v.setText(m.get(k, ''))

    def save_mapping(self):
        m = {k: v.text() for k, v in self.mapping_inputs.items() if v.text()}
        self.db.set_setting('field_mapping', json.dumps(m))
        QMessageBox.information(self, "成功", "映射已保存")
