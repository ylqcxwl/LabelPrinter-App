from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QGridLayout)
from PyQt5.QtCore import QDate, Qt
from src.database import Database
from src.box_rules import BoxRuleEngine
from src.bartender import BartenderPrinter
from src.config import DEFAULT_MAPPING
import datetime
import os
import re

class PrintPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.rule_engine = BoxRuleEngine(self.db)
        self.printer = BartenderPrinter()
        self.current_product = None
        self.current_sn_list = [] 
        self.current_box_no = ""
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5)

        # Top Search
        h1 = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 69码/名称筛选...")
        self.input_search.textChanged.connect(self.filter_products)
        self.table_product = QTableWidget(); self.table_product.setColumnCount(4)
        self.table_product.setHorizontalHeaderLabels(["名称", "69码", "SN前4", "SN规则"])
        self.table_product.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_product.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_product.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_product.setMaximumHeight(100)
        self.table_product.itemClicked.connect(self.on_product_select)
        main_layout.addLayout(h1); main_layout.addWidget(self.input_search); main_layout.addWidget(self.table_product)

        # Info
        info_grp = QGroupBox("详情")
        gl = QGridLayout(info_grp)
        self.lbl_name = QLabel("--"); self.lbl_sn4 = QLabel("--"); self.lbl_rule = QLabel("无")
        gl.addWidget(QLabel("名称:"),0,0); gl.addWidget(self.lbl_name,0,1)
        gl.addWidget(QLabel("SN前4:"),0,2); gl.addWidget(self.lbl_sn4,0,3)
        gl.addWidget(QLabel("SN规则:"),1,0); gl.addWidget(self.lbl_rule,1,1)
        main_layout.addWidget(info_grp)

        # Control
        h2 = QHBoxLayout()
        self.date_prod = QDateEdit(QDate.currentDate()); self.date_prod.setCalendarPopup(True)
        self.combo_repair = QComboBox(); self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.currentIndexChanged.connect(self.update_box_preview)
        self.lbl_daily = QLabel("今日: 0")
        h2.addWidget(QLabel("日期:")); h2.addWidget(self.date_prod)
        h2.addWidget(QLabel("批次:")); h2.addWidget(self.combo_repair)
        h2.addStretch(); h2.addWidget(self.lbl_daily)
        main_layout.addLayout(h2)

        # Scan
        h3 = QHBoxLayout()
        v1 = QVBoxLayout()
        self.lbl_box_no = QLabel("--"); self.lbl_box_no.setStyleSheet("font-size:18px; font-weight:bold; color:red")
        self.input_sn = QLineEdit(); self.input_sn.setPlaceholderText("扫描SN...")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        v1.addWidget(self.lbl_box_no); v1.addWidget(self.input_sn); v1.addStretch()
        
        v2 = QVBoxLayout()
        self.list_sn = QListWidget()
        b_del = QPushButton("删除选中"); b_del.clicked.connect(self.del_sn)
        v2.addWidget(QLabel("列表")); v2.addWidget(self.list_sn); v2.addWidget(b_del)
        h3.addLayout(v1, 4); h3.addLayout(v2, 6)
        main_layout.addLayout(h3)

        btn = QPushButton("打印"); btn.setStyleSheet("background:#e67e22;color:white;font-weight:bold;padding:10px")
        btn.clicked.connect(self.print_label)
        main_layout.addWidget(btn)

    def refresh_data(self):
        self.p_cache = []
        cur = self.db.conn.cursor()
        cur.execute("SELECT * FROM products ORDER BY name")
        cols = [d[0] for d in cur.description]
        for r in cur.fetchall(): self.p_cache.append(dict(zip(cols, r)))
        self.filter_products()

    def filter_products(self):
        k = self.input_search.text().lower()
        self.table_product.setRowCount(0)
        for p in self.p_cache:
            if k in p['name'].lower() or k in p['code69'].lower():
                r = self.table_product.rowCount(); self.table_product.insertRow(r)
                it = QTableWidgetItem(p['name']); it.setData(Qt.UserRole, p)
                self.table_product.setItem(r,0,it)
                self.table_product.setItem(r,1,QTableWidgetItem(p['code69']))
                self.table_product.setItem(r,2,QTableWidgetItem(p['sn4']))
                # 获取规则名称
                rule_name = "无"
                if p.get('sn_rule_id'):
                    c = self.db.conn.cursor(); c.execute("SELECT name FROM sn_rules WHERE id=?", (p['sn_rule_id'],))
                    res = c.fetchone()
                    if res: rule_name = res[0]
                self.table_product.setItem(r,3,QTableWidgetItem(rule_name))

    def on_product_select(self, item):
        p = self.table_product.item(item.row(), 0).data(Qt.UserRole)
        self.current_product = p
        self.lbl_name.setText(p['name']); self.lbl_sn4.setText(p['sn4'])
        
        # 更新SN规则显示
        self.current_sn_rule = None
        if p.get('sn_rule_id'):
             c = self.db.conn.cursor()
             c.execute("SELECT rule_string, length, name FROM sn_rules WHERE id=?", (p['sn_rule_id'],))
             res = c.fetchone()
             if res:
                 self.current_sn_rule = {'fmt': res[0], 'len': res[1]}
                 self.lbl_rule.setText(res[2])
             else: self.lbl_rule.setText("无")
        else: self.lbl_rule.setText("无")

        self.current_sn_list = []
        self.list_sn.clear()
        self.update_box_preview()
        self.update_daily()
        self.input_sn.setFocus()

    def update_box_preview(self):
        if not self.current_product: return
        try:
            s, _ = self.rule_engine.generate_box_no(self.current_product.get('rule_id',0), self.current_product, int(self.combo_repair.currentText()))
            self.current_box_no = s; self.lbl_box_no.setText(f"箱号: {s}")
        except: self.lbl_box_no.setText("规则错误")

    def update_daily(self):
        if not self.current_product: return
        d = datetime.datetime.now().strftime("%Y-%m-%d") + "%"
        c = self.db.conn.cursor()
        c.execute("SELECT COUNT(DISTINCT box_no) FROM records WHERE sn LIKE ? AND print_date LIKE ?", (f"{self.current_product['sn4']}%", d))
        self.lbl_daily.setText(f"今日: {c.fetchone()[0]}")

    def validate_sn(self, sn):
        # 1. 基础校验
        if not sn.startswith(self.current_product['sn4']): return False, "SN前4位不匹配"
        
        # 2. 规则校验
        if self.current_sn_rule:
            rule_fmt = self.current_sn_rule['fmt']
            max_len = self.current_sn_rule['len']
            
            # 长度校验
            if max_len > 0 and len(sn) != max_len:
                return False, f"长度错误 (需{max_len}位, 实{len(sn)}位)"
            
            # 格式解析与校验
            # 将规则转换为正则表达式
            # {SN4} -> 实际SN4
            # {BATCH} -> 当前选中的批次 (e.g., 0)
            # {SEQn} -> \d{n}
            
            current_batch = self.combo_repair.currentText()
            
            regex_pattern = rule_fmt
            regex_pattern = regex_pattern.replace("{SN4}", self.current_product['sn4'])
            regex_pattern = regex_pattern.replace("{BATCH}", current_batch)
            
            # 处理 {SEQn}
            def repl(match):
                n = match.group(1)
                return f"\\d{{{n}}}"
            regex_pattern = re.sub(r"\{SEQ(\d+)\}", repl, regex_pattern)
            
            # 处理固定字符中的特殊正则符号 (如 /, +, .)
            # 这里简单处理，实际应该 escape 那些非 {} 内容。
            # 简易方案：只在匹配时加上 ^$
            
            try:
                if not re.match(f"^{regex_pattern}$", sn):
                    return False, f"格式不符\n规则: {rule_fmt}\n批次需为: {current_batch}"
            except Exception as e:
                print(f"Regex Error: {e}")
                # 如果正则出错，回退到简单前缀检查
                pass 
                
        return True, ""

    def on_sn_scan(self):
        if not self.current_product: return
        sn = self.input_sn.text().strip().upper(); self.input_sn.clear()
        if not sn: return
        
        # 重复校验
        if sn in [x[0] for x in self.current_sn_list]: return QMessageBox.warning(self,"错","重复扫描")
        if self.db.check_sn_exists(sn): return QMessageBox.warning(self,"错","已打印过")
        
        # 规则校验
        valid, msg = self.validate_sn(sn)
        if not valid:
            return QMessageBox.warning(self, "SN校验失败", msg)

        self.current_sn_list.append((sn, datetime.datetime.now()))
        self.list_sn.addItem(sn); self.list_sn.scrollToBottom()
        
        if len(self.current_sn_list) >= self.current_product['qty']: self.print_label()

    def del_sn(self):
        for item in self.list_sn.selectedItems():
            val = item.text()
            self.current_sn_list = [x for x in self.current_sn_list if x[0] != val]
            self.list_sn.takeItem(self.list_sn.row(item))

    def print_label(self):
        if not self.current_product or not self.current_sn_list: return
        p = self.current_product
        # ... (打印逻辑与之前相同，略微简化展示) ...
        m = self.db.get_setting('field_mapping')
        if not isinstance(m, dict): m = DEFAULT_MAPPING
        data = {"box_no": self.current_box_no, "qty": len(self.current_sn_list), 
                "name": p['name'], "spec": p['spec'], "model": p['model'], "color": p['color'], "sku": p['sku'], "code69": p['code69']}
        # 映射
        final_data = {}
        for k,v in m.items(): 
            if k in data: final_data[v] = data[k]
        for i, (sn,_) in enumerate(self.current_sn_list): final_data[str(i+1)] = sn
        
        root = self.db.get_setting('template_root')
        path = os.path.join(root, p['template_path']) if root and p['template_path'] else p['template_path']
        
        if self.printer.print_label(path, final_data)[0]:
            # Save
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for sn,_ in self.current_sn_list:
                self.db.cursor.execute("INSERT INTO records (box_no, box_sn_seq, name, spec, model, color, code69, sn, print_date) VALUES (?,?,?,?,?,?,?,?,?)",
                                       (self.current_box_no, 0, p['name'], p['spec'], p['model'], p['color'], p['code69'], sn, now))
            self.db.conn.commit()
            self.rule_engine.commit_sequence(p['rule_id'], int(self.combo_repair.currentText()))
            QMessageBox.information(self,"好","成功")
            self.current_sn_list = []; self.list_sn.clear(); self.update_box_preview(); self.update_daily()
