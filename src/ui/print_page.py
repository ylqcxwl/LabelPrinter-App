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
import traceback

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
        # 0. 主布局：垂直布局 (内容区 + 底部按钮)
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. 内容区：水平布局 (左侧产品选择 + 右侧操作区)
        content_layout = QHBoxLayout()
        content_layout.setSpacing(15)

        # ==================== 左侧：产品选择区 (占比 4) ====================
        v_selection = QVBoxLayout()
        v_selection.setSpacing(10)

        # 1.1 搜索框
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 搜索产品...")
        self.input_search.setStyleSheet("font-size: 14px; padding: 6px;")
        self.input_search.textChanged.connect(self.filter_products)
        v_selection.addWidget(self.input_search)

        # 1.2 产品列表
        self.table_product = QTableWidget()
        self.table_product.setColumnCount(6) # 名称, 规格, 颜色, 69码, SN前4, 箱规
        self.table_product.setHorizontalHeaderLabels(["名称", "规格", "颜色", "69码", "SN前4", "箱规"])
        self.table_product.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_product.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_product.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_product.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_product.itemClicked.connect(self.on_product_select)
        v_selection.addWidget(self.table_product) # 列表占据剩余垂直空间
        
        content_layout.addLayout(v_selection, 4) 

        # ==================== 右侧：操作仪表板 (占比 6) ====================
        v_operation = QVBoxLayout()
        v_operation.setSpacing(10)

        # 2.1 产品详情 Group Box (顶部)
        grp = QGroupBox("产品详情")
        grp.setStyleSheet("QGroupBox { font-weight: bold; font-size: 14px; border: 1px solid #ccc; margin-top: 6px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 3px; }")
        
        v_details_in_grp = QVBoxLayout(grp)
        
        # 2.1.1 网格显示具体信息
        gl = QGridLayout()
        gl.setContentsMargins(5, 10, 5, 5)
        gl.setHorizontalSpacing(20)
        
        # 标签初始化
        self.lbl_name = QLabel("--"); self.lbl_sn4 = QLabel("--")
        self.lbl_spec = QLabel("--"); self.lbl_model = QLabel("--")
        self.lbl_code69 = QLabel("--"); self.lbl_qty = QLabel("--")
        self.lbl_rule_name = QLabel("无"); self.lbl_tmpl_name = QLabel("无")
        self.lbl_color = QLabel("--")

        style_lbl = "color: #555;"
        style_val = "color: #2980b9; font-weight: bold; font-size: 13px;"
        
        def add_field(row, col, text, val_widget):
            l = QLabel(text); l.setStyleSheet(style_lbl)
            val_widget.setStyleSheet(style_val)
            gl.addWidget(l, row, col)
            gl.addWidget(val_widget, row, col+1)

        add_field(0, 0, "名称:", self.lbl_name); add_field(0, 2, "规格:", self.lbl_spec)
        add_field(0, 4, "型号:", self.lbl_model); add_field(0, 6, "颜色:", self.lbl_color)
        
        add_field(1, 0, "SN前4:", self.lbl_sn4); add_field(1, 2, "69码:", self.lbl_code69)
        add_field(1, 4, "整箱数:", self.lbl_qty)
        
        gl.addWidget(QLabel("箱号规则:"), 2, 0); gl.addWidget(self.lbl_rule_name, 2, 1)
        gl.addWidget(QLabel("打印模板:"), 2, 2); gl.addWidget(self.lbl_tmpl_name, 2, 3, 1, 3)
        v_details_in_grp.addLayout(gl)

        # 2.1.2 日期与批次控制
        h_ctrl = QHBoxLayout()
        self.date_prod = QDateEdit(QDate.currentDate()); self.date_prod.setCalendarPopup(True)
        self.combo_repair = QComboBox(); self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.currentIndexChanged.connect(self.update_box_preview)
        
        h_ctrl.addWidget(QLabel("日期:")); h_ctrl.addWidget(self.date_prod)
        h_ctrl.addWidget(QLabel("批次:")); h_ctrl.addWidget(self.combo_repair)
        h_ctrl.addStretch()
        v_details_in_grp.addLayout(h_ctrl)

        v_operation.addWidget(grp)

        # 2.2 当前箱号显示 (高亮)
        v_operation.addWidget(QLabel("当前箱号:"))
        self.lbl_box_no = QLabel("--")
        self.lbl_box_no.setWordWrap(False)
        self.lbl_box_no.setAlignment(Qt.AlignCenter)
        self.lbl_box_no.setStyleSheet("font-size: 26px; font-weight: bold; color: #c0392b; padding: 8px 5px; background: #ecf0f1; border: 1px solid #ccc; border-radius: 4px;")
        v_operation.addWidget(self.lbl_box_no)

        # 2.3 SN 扫描/列表区 (水平分栏)
        h_scan_area = QHBoxLayout()
        h_scan_area.setSpacing(10)

        # 2.3.1 扫描输入 (h_scan_area 左侧)
        v_scan = QVBoxLayout()
        v_scan.setSpacing(5)
        v_scan.addWidget(QLabel("扫描SN:"))
        
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("在此扫描SN...")
        self.input_sn.setStyleSheet("font-size: 22px; padding: 12px; border: 2px solid #3498db; border-radius: 4px; color: #333;")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        v_scan.addWidget(self.input_sn)
        v_scan.addStretch()
        h_scan_area.addLayout(v_scan, 4) 

        # 2.3.2 SN 列表 (h_scan_area 右侧)
        v_list = QVBoxLayout()
        v_list.setSpacing(5)
        
        # 列表顶部工具栏 (计数 + 按钮)
        h_list_tools = QHBoxLayout()
        self.lbl_daily = QLabel("今日: 0")
        self.lbl_daily.setStyleSheet("color: green; font-weight: bold; font-size: 16px;")
        
        btn_all = QPushButton("全选"); btn_all.clicked.connect(lambda: self.list_sn.selectAll())
        btn_del = QPushButton("删除"); btn_del.clicked.connect(self.del_sn)
        
        h_list_tools.addWidget(QLabel("SN列表"))
        h_list_tools.addStretch()
        h_list_tools.addWidget(self.lbl_daily)
        
        h_btns_row = QHBoxLayout()
        h_btns_row.addStretch()
        h_btns_row.addWidget(btn_all)
        h_btns_row.addWidget(btn_del)

        self.list_sn = QListWidget()
        self.list_sn.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_sn.setStyleSheet("font-size: 14px;")

        v_list.addLayout(h_list_tools)
        v_list.addLayout(h_btns_row)
        v_list.addWidget(self.list_sn)
        
        h_scan_area.addLayout(v_list, 6) # 给列表更多空间

        v_operation.addLayout(h_scan_area)
        v_operation.addStretch() # 撑开底部

        content_layout.addLayout(v_operation, 6)
        main_layout.addLayout(content_layout)

        # 3. 底部打印按钮
        self.btn_print = QPushButton("打印 / 封箱")
        self.btn_print.setStyleSheet("background:#e67e22; color:white; padding:15px; font-size:18px; font-weight:bold; border-radius: 5px;")
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.clicked.connect(self.print_label)
        main_layout.addWidget(self.btn_print)

    # --- 逻辑功能保持不变 ---

    def refresh_data(self):
        self.p_cache = []
        try:
            c = self.db.conn.cursor()
            c.execute("SELECT * FROM products ORDER BY name")
            cols = [d[0] for d in c.description]
            for r in c.fetchall(): self.p_cache.append(dict(zip(cols,r)))
            self.filter_products()
        except: pass

    def filter_products(self):
        k = self.input_search.text().lower()
        self.table_product.setRowCount(0)
        for p in self.p_cache:
            if k in p['name'].lower() or k in p['code69'].lower():
                r = self.table_product.rowCount(); self.table_product.insertRow(r)
                it = QTableWidgetItem(p['name']); it.setData(Qt.UserRole, p)
                self.table_product.setItem(r,0,it)
                self.table_product.setItem(r,1,QTableWidgetItem(p.get('spec','')))
                self.table_product.setItem(r,2,QTableWidgetItem(p.get('color','')))
                self.table_product.setItem(r,3,QTableWidgetItem(p['code69']))
                self.table_product.setItem(r,4,QTableWidgetItem(p['sn4']))
                rn = "无"
                if p.get('rule_id'):
                    c=self.db.conn.cursor(); c.execute("SELECT name FROM box_rules WHERE id=?",(p['rule_id'],))
                    res=c.fetchone(); rn=res[0] if res else "无"
                self.table_product.setItem(r,5,QTableWidgetItem(rn))

    def on_product_select(self, item):
        p = self.table_product.item(item.row(),0).data(Qt.UserRole)
        self.current_product = p
        self.lbl_name.setText(p.get('name',''))
        self.lbl_sn4.setText(p.get('sn4',''))
        self.lbl_spec.setText(p.get('spec',''))
        self.lbl_model.setText(p.get('model',''))
        self.lbl_color.setText(p.get('color','')) 
        self.lbl_code69.setText(p.get('code69',''))
        self.lbl_qty.setText(str(p.get('qty','')))
        
        tmpl = p.get('template_path','')
        self.lbl_tmpl_name.setText(os.path.basename(tmpl) if tmpl else "未设置")
        
        rid = p.get('rule_id',0)
        rname = "无"
        if rid:
             c=self.db.conn.cursor(); c.execute("SELECT name FROM box_rules WHERE id=?",(rid,))
             res=c.fetchone(); rname=res[0] if res else "无"
        self.lbl_rule_name.setText(rname)
        
        self.current_sn_rule = None
        if p.get('sn_rule_id'):
             c=self.db.conn.cursor(); c.execute("SELECT rule_string, length FROM sn_rules WHERE id=?",(p['sn_rule_id'],))
             res=c.fetchone()
             if res: self.current_sn_rule={'fmt':res[0], 'len':res[1]}

        self.current_sn_list=[]; 
        self.update_sn_list_ui() 
        self.update_box_preview(); self.update_daily(); self.input_sn.setFocus()

    def update_box_preview(self):
        if not self.current_product: return
        try:
            pid = self.current_product.get('id')
            rid = self.current_product.get('rule_id',0)
            rl = int(self.combo_repair.currentText())
            s, _ = self.rule_engine.generate_box_no(rid, self.current_product, rl)
            self.current_box_no = s
            self.lbl_box_no.setText(s)
        except Exception as e:
            self.lbl_box_no.setText("规则生成错")

    def update_daily(self):
        if not self.current_product: return
        d = datetime.datetime.now().strftime("%Y-%m-%d")+"%"
        try:
            c=self.db.conn.cursor()
            c.execute("SELECT COUNT(DISTINCT box_no) FROM records WHERE name=? AND print_date LIKE ?", (self.current_product['name'], d))
            self.lbl_daily.setText(f"今日: {c.fetchone()[0]}")
        except: pass

    def validate_sn(self, sn):
        sn = re.sub(r'[\s\W\u200b\ufeff]+$', '', sn); sn = sn.strip() 
        prefix = str(self.current_product.get('sn4', '')).strip()
        if not sn.startswith(prefix): return False, f"前缀不符！\n要求: {prefix}"
        
        if self.current_sn_rule:
            fmt = self.current_sn_rule['fmt']; mlen = self.current_sn_rule['len']
            if mlen > 0 and len(sn) != mlen: return False, f"长度错误！\n要求: {mlen}位"
            
            parts = re.split(r'(\{SN4\}|\{BATCH\}|\{SEQ\d+\})', fmt)
            regex_parts = []
            current_batch = self.combo_repair.currentText()
            
            for part in parts:
                if part == "{SN4}": regex_parts.append(re.escape(prefix))
                elif part == "{BATCH}": regex_parts.append(re.escape(current_batch))
                elif part.startswith("{SEQ") and part.endswith("}"):
                    match = re.search(r'\{SEQ(\d+)\}', part)
                    if match: regex_parts.append(f"\\d{{{int(match.group(1))}}}")
                    else: return False, "规则错误"
                else:
                    if part: regex_parts.append(re.escape(part))
            
            try:
                if not re.match("^" + "".join(regex_parts) + "$", sn): return False, f"格式不符！\nSN: {sn}"
            except: return False, "正则错误"
        return True, ""

    def update_sn_list_ui(self):
        self.list_sn.clear()
        for i, (sn, _) in enumerate(self.current_sn_list):
            self.list_sn.addItem(f"{i+1}. {sn}")
        self.list_sn.scrollToBottom()

    def on_sn_scan(self):
        if not self.current_product: return
        sn = self.input_sn.text().strip(); self.input_sn.clear() 
        if not sn: return
        sn = sn.upper()

        if sn in [x[0] for x in self.current_sn_list]: return QMessageBox.warning(self,"错","重复扫描")
        if self.db.check_sn_exists(sn): return QMessageBox.warning(self,"错","已打印过")
        
        ok, msg = self.validate_sn(sn)
        if not ok: return QMessageBox.warning(self,"校验失败", msg)
        
        self.current_sn_list.append((sn, datetime.datetime.now()))
        self.update_sn_list_ui()
        
        if len(self.current_sn_list) >= self.current_product['qty']: self.print_label()

    def del_sn(self):
        rows = sorted([item.row() for item in self.list_sn.selectedItems()], reverse=True)
        if not rows: return
        for row in rows: del self.current_sn_list[row]
        self.update_sn_list_ui()

    def print_label(self):
        if not self.current_product or not self.current_sn_list: return
        p = self.current_product
        m = self.db.get_setting('field_mapping')
        if not isinstance(m, dict): m = DEFAULT_MAPPING
        
        src = {"name":p.get('name'), "spec":p.get('spec'), "model":p.get('model'), "color":p.get('color'),
               "sn4":p.get('sn4'), "sku":p.get('sku'), "code69":p.get('code69'), "qty":len(self.current_sn_list),
               "weight":p.get('weight'), "box_no":self.current_box_no, "prod_date":self.date_prod.text()}
        
        dat = {}
        for k,v in m.items(): 
            if k in src: dat[v] = src[k]
        for i, (sn,_) in enumerate(self.current_sn_list): dat[str(i+1)] = sn
        
        root = self.db.get_setting('template_root')
        tp = p.get('template_path','')
        path = os.path.join(root, tp) if root and tp else tp
        
        ok, msg = self.printer.print_label(path, dat)
        if ok:
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            for sn,_ in self.current_sn_list:
                self.db.cursor.execute("INSERT INTO records (box_no, box_sn_seq, name, spec, model, color, code69, sn, print_date) VALUES (?,?,?,?,?,?,?,?,?)",
                                       (self.current_box_no, 0, p['name'], p['spec'], p['model'], p['color'], p['code69'], sn, now))
            self.db.conn.commit()
            self.rule_engine.commit_sequence(p['rule_id'], p['id'], int(self.combo_repair.currentText()))
            
            QMessageBox.information(self,"好","打印成功"); 
            self.current_sn_list=[]; self.update_sn_list_ui(); self.update_box_preview(); self.update_daily()
        else: QMessageBox.critical(self,"失败", msg)
