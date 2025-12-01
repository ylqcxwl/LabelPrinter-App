from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, 
                             QMessageBox, QTextEdit, QGroupBox, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,\
                             QTabWidget, QLabel, QFileDialog, QComboBox, QSpinBox)
from PyQt5.QtCore import Qt
# --- 新增导入：用于获取打印机信息 ---
from PyQt5.QtPrintSupport import QPrinterInfo 
# -----------------------------------
from src.database import Database
from src.config import DEFAULT_MAPPING
import json
import os

class SettingsPage(QWidget):
    # --- 优化点：接收 Database 实例 ---
    def __init__(self, db: Database): 
        super().__init__()
        self.db = db # 使用传入的共享实例
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)

        self.tabs = QTabWidget()
        
        # 1. 箱号规则
        self.tab_rules = QWidget()
        self.init_rules_tab()
        self.tabs.addTab(self.tab_rules, "1. 箱号规则")

        # 2. SN规则
        self.tab_sn = QWidget()
        self.init_sn_tab()
        self.tabs.addTab(self.tab_sn, "2. SN规则")

        # 3. 字段映射
        self.tab_map = QWidget()
        self.init_map_tab()
        self.tabs.addTab(self.tab_map, "3. 字段映射")
        
        # 4. 系统维护
        self.tab_sys = QWidget()
        self.init_sys_tab()
        self.tabs.addTab(self.tab_sys, "4. 系统维护")

        main_layout.addWidget(self.tabs)

        self.refresh_data()

    def refresh_data(self):
        # 刷新箱号规则
        self.table_rules.setRowCount(0)
        self.db.cursor.execute("SELECT id, name, rule_string FROM box_rules")
        for row_idx, data in enumerate(self.db.cursor.fetchall()):
            self.table_rules.insertRow(row_idx)
            for col_idx, item in enumerate(data):
                self.table_rules.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))

        # 刷新 SN 规则
        self.table_sn.setRowCount(0)
        self.db.cursor.execute("SELECT id, name, rule_string, length FROM sn_rules")
        for row_idx, data in enumerate(self.db.cursor.fetchall()):
            self.table_sn.insertRow(row_idx)
            for col_idx, item in enumerate(data):
                self.table_sn.setItem(row_idx, col_idx, QTableWidgetItem(str(item)))

        # 刷新字段映射
        self.load_field_mapping()

        # 刷新系统设置
        self.path_tmpl_edit.setText(self.db.get_setting('template_root', ''))
        self.path_bk_edit.setText(self.db.get_setting('backup_path', ''))
        self.combo_printer.setCurrentText(self.db.get_setting('default_printer', '使用系统默认打印机'))


    # --- (init_rules_tab, init_sn_tab, init_map_tab, init_sys_tab, load_field_mapping, save_field_mapping, etc. 保持不变) ---
    def init_rules_tab(self):
        layout = QVBoxLayout(self.tab_rules)
        toolbar = QHBoxLayout()
        self.btn_add_rule = QPushButton("新增规则"); self.btn_add_rule.clicked.connect(self.add_rule)
        self.btn_edit_rule = QPushButton("修改选中"); self.btn_edit_rule.clicked.connect(self.edit_rule)
        self.btn_del_rule = QPushButton("删除选中"); self.btn_del_rule.clicked.connect(self.delete_rule)
        for b in [self.btn_add_rule, self.btn_edit_rule, self.btn_del_rule]: toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table_rules = QTableWidget()
        self.table_rules.setColumnCount(3)
        self.table_rules.setHorizontalHeaderLabels(["ID", "名称", "规则表达式"])
        self.table_rules.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_rules.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_rules.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_rules.horizontalHeader().setStretchLastSection(True)
        self.table_rules.setColumnHidden(0, True)
        layout.addWidget(self.table_rules)

    def init_sn_tab(self):
        layout = QVBoxLayout(self.tab_sn)
        toolbar = QHBoxLayout()
        self.btn_add_sn_rule = QPushButton("新增规则"); self.btn_add_sn_rule.clicked.connect(self.add_sn_rule)
        self.btn_edit_sn_rule = QPushButton("修改选中"); self.btn_edit_sn_rule.clicked.connect(self.edit_sn_rule)
        self.btn_del_sn_rule = QPushButton("删除选中"); self.btn_del_sn_rule.clicked.connect(self.delete_sn_rule)
        for b in [self.btn_add_sn_rule, self.btn_edit_sn_rule, self.btn_del_sn_rule]: toolbar.addWidget(b)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        self.table_sn = QTableWidget()
        self.table_sn.setColumnCount(4)
        self.table_sn.setHorizontalHeaderLabels(["ID", "名称", "正则表达式", "长度"])
        self.table_sn.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_sn.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_sn.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_sn.horizontalHeader().setStretchLastSection(True)
        self.table_sn.setColumnHidden(0, True)
        layout.addWidget(self.table_sn)

    def init_map_tab(self):
        layout = QVBoxLayout(self.tab_map)
        self.map_form = QFormLayout()
        
        self.map_editors = {}
        mapping = self.db.get_field_mapping()
        
        for key, default_value in DEFAULT_MAPPING.items():
            le = QLineEdit(mapping.get(key, default_value))
            self.map_editors[key] = le
            self.map_form.addRow(f"产品字段 '{key}' 映射到 BarTender 字段名:", le)
            
        btn_save = QPushButton("保存字段映射")
        btn_save.clicked.connect(self.save_field_mapping)
        self.map_form.addRow(btn_save)
        
        layout.addLayout(self.map_form)
        layout.addStretch()

    def load_field_mapping(self):
        mapping = self.db.get_field_mapping()
        for key, editor in self.map_editors.items():
            editor.setText(mapping.get(key, DEFAULT_MAPPING.get(key, "")))

    def save_field_mapping(self):
        new_mapping = {}
        for key, editor in self.map_editors.items():
            new_mapping[key] = editor.text().strip()
        
        self.db.set_field_mapping(new_mapping)
        QMessageBox.information(self, "成功", "字段映射保存成功！")

    def init_sys_tab(self):
        layout = QVBoxLayout(self.tab_sys)
        form = QFormLayout()
        
        # 1. 模板根目录
        tmpl_layout = QHBoxLayout()
        self.path_tmpl_edit = QLineEdit(self.db.get_setting('template_root', ''))
        self.path_tmpl_edit.setReadOnly(True)
        btn_tmpl = QPushButton("选择"); btn_tmpl.clicked.connect(self.sel_tmpl_path)
        tmpl_layout.addWidget(self.path_tmpl_edit); tmpl_layout.addWidget(btn_tmpl)
        form.addRow("模板根目录", tmpl_layout)

        # 2. 备份目录
        bk_layout = QHBoxLayout()
        self.path_bk_edit = QLineEdit(self.db.get_setting('backup_path', ''))
        self.path_bk_edit.setReadOnly(True)
        btn_bk = QPushButton("选择"); btn_bk.clicked.connect(self.sel_bk_path)
        bk_layout.addWidget(self.path_bk_edit); bk_layout.addWidget(btn_bk)
        form.addRow("数据库备份目录", bk_layout)

        # 3. 默认打印机
        self.combo_printer = QComboBox()
        self.combo_printer.addItem('使用系统默认打印机')
        for printer in QPrinterInfo.availablePrinters():
            self.combo_printer.addItem(printer.printerName())
        
        default_printer = self.db.get_setting('default_printer', '使用系统默认打印机')
        idx = self.combo_printer.findText(default_printer)
        self.combo_printer.setCurrentIndex(idx if idx >= 0 else 0)

        btn_save_printer = QPushButton("保存默认打印机"); btn_save_printer.clicked.connect(self.sel_default_printer)
        printer_layout = QHBoxLayout(); printer_layout.addWidget(self.combo_printer); printer_layout.addWidget(btn_save_printer)
        form.addRow("默认打印机", printer_layout)
        
        # 4. 维护操作
        maintenance_group = QGroupBox("数据库维护")
        m_layout = QHBoxLayout(maintenance_group)
        btn_backup = QPushButton("立即备份"); btn_backup.clicked.connect(self.do_backup)
        btn_restore = QPushButton("从文件恢复"); btn_restore.clicked.connect(self.do_restore)
        m_layout.addWidget(btn_backup); m_layout.addWidget(btn_restore)
        
        layout.addLayout(form)
        layout.addWidget(maintenance_group)
        layout.addStretch()

    def sel_tmpl_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择模板根目录")
        if p:
            self.db.set_setting('template_root', p)
            self.db.conn.commit()
            self.path_tmpl_edit.setText(p)
            QMessageBox.information(self, "成功", "模板根目录设置成功！")

    def sel_bk_path(self):
        p = QFileDialog.getExistingDirectory(self, "选择备份目录")
        if p:
            self.db.set_setting('backup_path', p)
            self.db.conn.commit()
            self.path_bk_edit.setText(p)
            QMessageBox.information(self, "成功", "备份目录设置成功！")

    def sel_default_printer(self):
        """保存用户选择的默认打印机。"""
        selected_printer = self.combo_printer.currentText()
        self.db.set_setting('default_printer', selected_printer)
        self.db.conn.commit()
        QMessageBox.information(self, "成功", f"默认打印机已设置为: {selected_printer}")

    def do_backup(self):
        # 确保路径已保存并提交
        self.db.conn.commit() 
        ok, msg = self.db.backup_db(manual=True)
        QMessageBox.information(self, "结果", msg)

    def do_restore(self):
        p, _ = QFileDialog.getOpenFileName(self, "选择数据库", "", "DB (*.db)")
        if p:
            if QMessageBox.warning(self, "警告", "恢复将覆盖当前数据，确定？", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
                ok, msg = self.db.restore_db(p)
                QMessageBox.information(self, "结果", msg + "\n请重启程序以完成恢复。")

    # --- (add_rule, edit_rule, delete_rule, add_sn_rule, edit_sn_rule, delete_sn_rule 保持不变) ---
    def add_rule(self):
        dialog = RuleDialog(self.db, rule_type='box')
        if dialog.exec_(): self.refresh_data()
    
    def edit_rule(self):
        selected = self.table_rules.selectedIndexes()
        if not selected: return QMessageBox.warning(self, "提示", "请选择要修改的规则。")
        rule_id = self.table_rules.item(selected[0].row(), 0).text()
        self.db.cursor.execute("SELECT id, name, rule_string FROM box_rules WHERE id=?", (rule_id,))
        data = self.db.cursor.fetchone()
        dialog = RuleDialog(self.db, data=data, rule_type='box')
        if dialog.exec_(): self.refresh_data()

    def delete_rule(self):
        selected = self.table_rules.selectedIndexes()
        if not selected: return QMessageBox.warning(self, "提示", "请选择要删除的规则。")
        rows = set(i.row() for i in selected)
        ids = [self.table_rules.item(r, 0).text() for r in rows]
        if QMessageBox.question(self, "确认", f"删 {len(ids)} 条箱号规则?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            p = ",".join(["?"] * len(ids))
            self.db.cursor.execute(f"DELETE FROM box_rules WHERE id IN ({p})", ids)
            self.db.conn.commit()
            self.refresh_data()

    def add_sn_rule(self):
        dialog = RuleDialog(self.db, rule_type='sn')
        if dialog.exec_(): self.refresh_data()

    def edit_sn_rule(self):
        selected = self.table_sn.selectedIndexes()
        if not selected: return QMessageBox.warning(self, "提示", "请选择要修改的SN规则。")
        rule_id = self.table_sn.item(selected[0].row(), 0).text()
        self.db.cursor.execute("SELECT id, name, rule_string, length FROM sn_rules WHERE id=?", (rule_id,))
        data = self.db.cursor.fetchone()
        dialog = RuleDialog(self.db, data=data, rule_type='sn')
        if dialog.exec_(): self.refresh_data()

    def delete_sn_rule(self):
        selected = self.table_sn.selectedIndexes()
        if not selected: return QMessageBox.warning(self, "提示", "请选择要删除的SN规则。")
        rows = set(i.row() for i in selected)
        ids = [self.table_sn.item(r, 0).text() for r in rows]
        if QMessageBox.question(self, "确认", f"删 {len(ids)} 条SN规则?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            p = ",".join(["?"] * len(ids))
            self.db.cursor.execute(f"DELETE FROM sn_rules WHERE id IN ({p})", ids)
            self.db.conn.commit()
            self.refresh_data()


# 规则对话框 (ProductDialog中也有这个，但这里也要定义，因为它在SettingsPage中使用)
class RuleDialog(QDialog):
    # --- 优化点：接收 Database 实例 ---
    def __init__(self, db: Database, data=None, rule_type='box'):
        super().__init__()
        self.db = db # 使用传入的共享实例
        self.data = data
        self.rule_type = rule_type # 'box' or 'sn'
        
        title = "箱号规则" if rule_type == 'box' else "SN规则"
        self.setWindowTitle(title + ("修改" if data else "新增"))
        self.setFixedWidth(500)

        self.layout = QFormLayout(self)
        
        self.name_le = QLineEdit(data[1] if data else "")
        self.rule_te = QTextEdit(data[2] if data else "")
        self.rule_te.setFixedHeight(100)
        
        self.layout.addRow("规则名称*", self.name_le)
        self.layout.addRow("规则表达式*", self.rule_te)
        
        self.length_sb = None
        if rule_type == 'sn':
            # SN 规则额外有长度限制
            self.length_sb = QSpinBox()
            self.length_sb.setRange(0, 100)
            self.length_sb.setValue(data[3] if data else 0)
            self.layout.addRow("SN长度限制 (0为不限制)", self.length_sb)

        btn = QPushButton("保存"); btn.clicked.connect(self.accept)
        self.layout.addRow(btn)

    def accept(self):
        name = self.name_le.text().strip()
        rule = self.rule_te.toPlainText().strip()
        
        if not all([name, rule]):
            QMessageBox.warning(self, "警告", "名称和表达式不能为空。")
            return
        
        length = self.length_sb.value() if self.rule_type == 'sn' else 0

        try:
            if self.rule_type == 'box':
                table = 'box_rules'
                fields = 'name, rule_string'
                values = (name, rule)
            else: # 'sn'
                table = 'sn_rules'
                fields = 'name, rule_string, length'
                values = (name, rule, length)
            
            if self.data:
                # Update
                rule_id = self.data[0]
                self.db.cursor.execute(f"UPDATE {table} SET {fields.replace(',', '=?, ')=?} WHERE id=?", values + (rule_id,))
            else:
                # Insert
                placeholders = ','.join(['?'] * len(values))
                self.db.cursor.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", values)
            
            self.db.conn.commit()
            super().accept()
        except sqlite3.IntegrityError:
            QMessageBox.critical(self, "错误", f"规则名称 '{name}' 已存在。")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据库操作失败: {e}")
