from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QInputDialog, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
                             QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt
from src.database import Database
from src.config import PASSWORD
import json

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(15)

        # ------------------- 箱号规则管理 -------------------
        rule_group = QGroupBox("箱号规则管理")
        rule_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; margin-top: 10px; border: 1px solid #ccc; border-radius: 5px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        rule_layout = QVBoxLayout(rule_group)

        form_rule = QFormLayout()
        self.rule_name = QLineEdit()
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("例如: MZXH{SN4}{Y1}{M1}{SEQ5}2{DD}")
        
        form_rule.addRow("规则名称:", self.rule_name)
        form_rule.addRow("规则格式:", self.rule_fmt)
        
        btn_layout_rule = QHBoxLayout()
        btn_add_rule = QPushButton("添加新规则")
        btn_add_rule.setStyleSheet("background-color: #28a745; color: white; padding: 8px; border-radius: 4px;")
        btn_add_rule.clicked.connect(self.add_rule)
        btn_del_rule = QPushButton("删除选中规则")
        btn_del_rule.setStyleSheet("background-color: #dc3545; color: white; padding: 8px; border-radius: 4px;")
        btn_del_rule.clicked.connect(self.delete_rule)
        
        btn_layout_rule.addWidget(btn_add_rule)
        btn_layout_rule.addWidget(btn_del_rule)
        form_rule.addRow(btn_layout_rule)
        
        rule_layout.addLayout(form_rule)

        # 规则列表显示
        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(3)
        self.table_rules.setHorizontalHeaderLabels(["ID", "名称", "规则格式"])
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_rules.setSelectionBehavior(QAbstractItemView.SelectRows) # 整行选中
        self.table_rules.setSelectionMode(QAbstractItemView.SingleSelection) # 单选
        self.table_rules.setMaximumHeight(200) # 限制高度
        rule_layout.addWidget(self.table_rules)
        
        # 规则说明
        rule_help = QTextEdit()
        rule_help.setReadOnly(True)
        rule_help.setStyleSheet("background-color: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 10px;")
        rule_help.setHtml("""
        <b>箱号规则说明:</b><br>
        <b>{SN4}</b>: SN前四位<br>
        <b>{Y1}</b>: 年份最后1位 (例: 2023 -> 3)<br>
        <b>{Y2}</b>: 年份后两位 (例: 2023 -> 23)<br>
        <b>{MM}</b>: 月份两位 (例: 1月 -> 01)<br>
        <b>{M1}</b>: 月份代码 (1-9, 10=A, 11=B, 12=C)<br>
        <b>{DD}</b>: 日期两位 (例: 1日 -> 01)<br>
        <b>{SEQ5}</b>: 5位流水号 (00001) - 每月重置，不同批次单独计数
        """)
        rule_help.setMaximumHeight(200) # 限制高度
        rule_layout.addWidget(rule_help)

        main_layout.addWidget(rule_group)

        # ------------------- 字段映射管理 -------------------
        mapping_group = QGroupBox("打印字段映射管理")
        mapping_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; margin-top: 10px; border: 1px solid #ccc; border-radius: 5px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        mapping_layout = QVBoxLayout(mapping_group)

        self.mapping_inputs = {}
        form_mapping = QFormLayout()
        
        # 预设的映射字段
        fields_to_map = [
            ("名称", "name"), ("规格", "spec"), ("型号", "model"), ("颜色", "color"),
            ("SN前四位", "sn4"), ("SKU", "sku"), ("69码", "code69"),
            ("数量", "qty"), ("重量", "weight"), ("箱号", "box_no")
        ]
        
        for display_name, key_name in fields_to_map:
            le = QLineEdit()
            le.setPlaceholderText("输入模板中的字段名称...")
            self.mapping_inputs[key_name] = le
            form_mapping.addRow(f"{display_name} (数据库字段) -> ", le)

        btn_save_mapping = QPushButton("保存字段映射")
        btn_save_mapping.setStyleSheet("background-color: #007bff; color: white; padding: 8px; border-radius: 4px;")
        btn_save_mapping.clicked.connect(self.save_mapping)
        form_mapping.addRow(btn_save_mapping)

        mapping_layout.addLayout(form_mapping)
        main_layout.addWidget(mapping_group)

        # ------------------- 备份与恢复 (占位) -------------------
        backup_group = QGroupBox("数据备份与恢复")
        backup_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; margin-top: 10px; border: 1px solid #ccc; border-radius: 5px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        backup_layout = QVBoxLayout(backup_group)
        
        btn_backup = QPushButton("备份数据")
        btn_backup.setStyleSheet("background-color: #6c757d; color: white; padding: 8px; border-radius: 4px;")
        btn_backup.clicked.connect(lambda: QMessageBox.information(self, "提示", "备份功能待实现。"))
        
        btn_restore = QPushButton("恢复数据") # 补全的按钮
        btn_restore.setStyleSheet("background-color: #6c757d; color: white; padding: 8px; border-radius: 4px;")
        btn_restore.clicked.connect(lambda: QMessageBox.information(self, "提示", "恢复功能待实现。"))
        
        backup_h_layout = QHBoxLayout()
        backup_h_layout.addWidget(btn_backup)
        backup_h_layout.addWidget(btn_restore)

        backup_layout.addLayout(backup_h_layout)
        main_layout.addWidget(backup_group)
        
        main_layout.addStretch() # 将所有内容顶到上方
        
        # 初始化加载数据
        self.refresh_data() 

    def refresh_data(self):
        """刷新箱号规则列表和字段映射显示"""
        self.load_rules()
        self.load_mapping()
        
    def load_rules(self):
        """加载箱号规则到表格"""
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, format FROM box_rules")
        rules = cursor.fetchall()
        
        self.table_rules.setRowCount(0)
        for row_num, row_data in enumerate(rules):
            self.table_rules.insertRow(row_num)
            for col_num, data in enumerate(row_data):
                item = QTableWidgetItem(str(data))
                item.setTextAlignment(Qt.AlignCenter)
                self.table_rules.setItem(row_num, col_num, item)

    def add_rule(self):
        """添加新箱号规则"""
        name = self.rule_name.text().strip()
        fmt = self.rule_fmt.text().strip()
        
        if not name or not fmt:
            QMessageBox.warning(self, "警告", "规则名称和规则格式不能为空。")
            return
            
        try:
            self.db.cursor.execute("INSERT INTO box_rules (name, format, current_seq) VALUES (?, ?, ?)", (name, fmt, 0))
            self.db.conn.commit()
            QMessageBox.information(self, "成功", f"箱号规则 '{name}' 添加成功。")
            self.rule_name.clear()
            self.rule_fmt.clear()
            self.load_rules()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"添加规则失败: {e}")

    def delete_rule(self):
        """删除选中的箱号规则"""
        selected_rows = self.table_rules.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "警告", "请选择要删除的规则行。")
            return
            
        rule_id = self.table_rules.item(selected_rows[0].row(), 0).text()
        rule_name = self.table_rules.item(selected_rows[0].row(), 1).text()
        
        if QMessageBox.question(self, "确认删除", f"确定删除规则 ID: {rule_id} ({rule_name}) 吗？\n\n注意：如果产品正在使用该规则，可能会导致打印失败。", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            try:
                self.db.cursor.execute("DELETE FROM box_rules WHERE id=?", (rule_id,))
                self.db.conn.commit()
                QMessageBox.information(self, "成功", "规则删除成功。")
                self.load_rules()
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除规则失败: {e}")

    def load_mapping(self):
        """加载当前字段映射到输入框"""
        mapping = self.db.get_setting('field_mapping')
        
        for key, input_widget in self.mapping_inputs.items():
            # 使用 .get() 安全获取值，如果键不存在则返回空字符串
            input_widget.setText(mapping.get(key, '')) 

    def save_mapping(self):
        """保存字段映射"""
        new_mapping = {}
        for key, input_widget in self.mapping_inputs.items():
            value = input_widget.text().strip()
            if value: # 只保存非空字段
                new_mapping[key] = value
                
        try:
            self.db.set_setting('field_mapping', json.dumps(new_mapping))
            QMessageBox.information(self, "成功", "字段映射保存成功。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存映射失败: {e}")
