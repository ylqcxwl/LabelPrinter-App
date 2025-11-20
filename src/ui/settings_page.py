from PyQt5.QtWidgets import QWidget, QVBoxLayout, QFormLayout, QLineEdit, QPushButton, QMessageBox, QInputDialog, QTextEdit
from src.database import Database
from src.config import PASSWORD

class SettingsPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        layout = QVBoxLayout(self)
        
        form = QFormLayout()
        
        self.rule_name = QLineEdit()
        self.rule_fmt = QLineEdit()
        self.rule_fmt.setPlaceholderText("例如: MZXH{SN4}{Y1}{M1}{SEQ5}2{DD}")
        
        form.addRow("规则名称", self.rule_name)
        form.addRow("规则格式", self.rule_fmt)
        
        btn_add_rule = QPushButton("添加箱号规则")
        btn_add_rule.clicked.connect(self.add_rule)
        form.addRow(btn_add_rule)
        
        layout.addLayout(form)
        
        # 说明
        help_txt = QTextEdit()
        help_txt.setReadOnly(True)
        help_txt.setHtml("""
        <b>箱号规则说明:</b><br>
        {SN4}: SN前四位<br>
        {Y1}: 年份最后1位 (9)<br>
        {M1}: 月份1位 (1-9, A, B, C)<br>
        {MM}: 月份2位 (01-12)<br>
        {DD}: 日期 (01-31)<br>
        {SEQ5}: 5位流水号 (00001) - 每月重置
        """)
        layout.addWidget(help_txt)

    def check_auth(self):
        text, ok = QInputDialog.getText(self, '验证', '请输入管理员密码:', QLineEdit.Password)
        if ok and text == PASSWORD:
            return True
        QMessageBox.warning(self, "错误", "密码错误")
        return False

    def add_rule(self):
        if not self.check_auth(): return
        name = self.rule_name.text()
        fmt = self.rule_fmt.text()
        if name and fmt:
            self.db.cursor.execute("INSERT INTO box_rules (name, rule_string) VALUES (?,?)", (name, fmt))
            self.db.conn.commit()
            QMessageBox.information(self, "成功", "规则已添加")
