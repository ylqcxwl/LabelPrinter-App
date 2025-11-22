from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QFileDialog, 
                             QLineEdit, QCheckBox, QMessageBox, QComboBox, QLabel, 
                             QGroupBox, QGridLayout)
from PyQt5.QtCore import Qt
from src.config import DEFAULT_MAPPING, PRINTERS
import json

class SettingPage(QWidget):
    def __init__(self, db):
        super().__init__()
        self.db = db
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- 模板设置 ---
        grp_tmpl = QGroupBox("模板路径设置")
        h_tmpl = QHBoxLayout(grp_tmpl)
        self.input_tmpl_root = QLineEdit()
        self.btn_browse_tmpl = QPushButton("浏览...")
        self.btn_browse_tmpl.clicked.connect(self.browse_template_root)
        h_tmpl.addWidget(QLabel("根目录:"))
        h_tmpl.addWidget(self.input_tmpl_root)
        h_tmpl.addWidget(self.btn_browse_tmpl)
        main_layout.addWidget(grp_tmpl)

        # --- 打印机设置 ---
        grp_printer = QGroupBox("默认打印机设置")
        h_printer = QHBoxLayout(grp_printer)
        self.combo_printer = QComboBox()
        self.combo_printer.addItems(PRINTERS)
        h_printer.addWidget(QLabel("打印机:"))
        h_printer.addWidget(self.combo_printer)
        h_printer.addStretch(1)
        main_layout.addWidget(grp_printer)

        # --- 字段映射设置 ---
        grp_map = QGroupBox("字段映射设置 (Bartender 变量名)")
        g_map = QGridLayout(grp_map)
        self.map_inputs = {}
        row = 0
        for k, default_v in DEFAULT_MAPPING.items():
            input_field = QLineEdit()
            self.map_inputs[k] = input_field
            g_map.addWidget(QLabel(f"产品字段 '{k}':"), row, 0)
            g_map.addWidget(input_field, row, 1)
            row += 1
        g_map.setColumnStretch(1, 1)
        main_layout.addWidget(grp_map)

        # --- 备份与恢复 ---
        grp_backup = QGroupBox("数据备份")
        h_backup = QHBoxLayout(grp_backup)
        self.btn_backup = QPushButton("手动备份数据库")
        self.btn_restore = QPushButton("恢复数据库 (开发用)")
        
        # 修改按钮槽函数，调用新的备份逻辑
        self.btn_backup.clicked.connect(self.on_backup_db) 
        # self.btn_restore.clicked.connect(self.on_restore_db) # 恢复功能未实现，保持现有状态

        h_backup.addWidget(self.btn_backup)
        h_backup.addWidget(self.btn_restore)
        h_backup.addStretch(1)
        main_layout.addWidget(grp_backup)

        # --- 保存按钮 ---
        self.btn_save = QPushButton("保存设置")
        self.btn_save.setStyleSheet("padding: 8px; background-color: #27ae60; color: white; font-weight: bold;")
        self.btn_save.clicked.connect(self.save_settings)
        main_layout.addWidget(self.btn_save)

        main_layout.addStretch(1)

    def load_settings(self):
        # 加载模板根目录
        root = self.db.get_setting('template_root')
        self.input_tmpl_root.setText(root if root else "")
        
        # 加载默认打印机
        printer = self.db.get_setting('default_printer')
        index = self.combo_printer.findText(printer)
        if index >= 0:
            self.combo_printer.setCurrentIndex(index)
            
        # 加载字段映射
        mapping = self.db.get_setting('field_mapping')
        for k, input_field in self.map_inputs.items():
            input_field.setText(mapping.get(k, DEFAULT_MAPPING.get(k, "")))

    def save_settings(self):
        # 1. 保存模板根目录
        self.db.set_setting('template_root', self.input_tmpl_root.text().strip())
        
        # 2. 保存默认打印机
        self.db.set_setting('default_printer', self.combo_printer.currentText())
        
        # 3. 保存字段映射
        new_mapping = {k: v.text().strip() for k, v in self.map_inputs.items()}
        self.db.set_setting('field_mapping', new_mapping)
        
        QMessageBox.information(self, "成功", "系统设置已保存！")

    def browse_template_root(self):
        directory = QFileDialog.getExistingDirectory(self, "选择模板根目录", self.input_tmpl_root.text())
        if directory:
            self.input_tmpl_root.setText(directory)

    # --- 修复后的手动备份槽函数 ---
    def on_backup_db(self):
        """手动备份数据库并清理旧文件。"""
        # 调用 Database 中的新备份方法，并设置 manual=True
        ok, msg = self.db.backup_db(manual=True)
        if ok:
            QMessageBox.information(self, "备份成功", msg)
        else:
            QMessageBox.critical(self, "备份失败", msg)

    # ... (如果 restore 函数存在，请保留)
