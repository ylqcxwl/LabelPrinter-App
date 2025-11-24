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
        # 0. 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. 内容区：水平布局
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        # ==================== 左侧：操作区 (占比 7) ====================
        v_left = QVBoxLayout()
        v_left.setSpacing(10) # 减小整体垂直间距，使其紧凑

        # 1.1 搜索框
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 搜索产品...")
        self.input_search.setStyleSheet("font-size: 14px; padding: 6px;")
        self.input_search.textChanged.connect(self.filter_products)
        v_left.addWidget(self.input_search)

        # 1.2 产品列表
        self.table_product = QTableWidget()
        self.table_product.setColumnCount(6)
        self.table_product.setHorizontalHeaderLabels(["名称", "规格", "颜色", "69码", "SN前4", "箱规"])
        self.table_product.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_product.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_product.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_product.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_product.setMaximumHeight(150) 
        self.table_product.itemClicked.connect(self.on_product_select)
        v_left.addWidget(self.table_product)

        # 1.3 产品详情 & 设置区域
        grp = QGroupBox("产品详情")
        grp.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; border: 1px solid #ccc; margin-top: 10px; } QGroupBox::title { subcontrol-origin: margin; left: 10px; padding: 0 5px; }")
        
        v_details = QVBoxLayout(grp)
        v_details.setSpacing(10)
        
        # --- 1.3.1 网格显示详情 (修改：均匀分布，填满宽度) ---
        gl = QGridLayout()
        gl.setContentsMargins(10, 20, 10, 10) 
        gl.setHorizontalSpacing(15) 
        gl.setVerticalSpacing(15)
        
        # 初始化标签
        self.lbl_name = QLabel("--"); self.lbl_sn4 = QLabel("--")
        self.lbl_sn_rule = QLabel("无"); self.lbl_spec = QLabel("--")
        self.lbl_code69 = QLabel("--"); self.lbl_box_rule_name = QLabel("无")
        self.lbl_model = QLabel("--"); self.lbl_qty = QLabel("--")
        self.lbl_tmpl_name = QLabel("无"); self.lbl_color = QLabel("--")

        style_lbl = "color: #666; font-size: 16px;"
        style_val = "color: #2980b9; font-weight: bold; font-size: 18px;"
        
        def add_item(r, c, label_text, widget):
            l = QLabel(label_text); l.setStyleSheet(style_lbl)
            widget.setStyleSheet(style_val)
            gl.addWidget(l, r, c, Qt.AlignLeft)
            gl.addWidget(widget, r, c+1, Qt.AlignLeft)

        # 布局排列 (3列块结构)
        # Row 0
        add_item(0, 0, "名称:", self.lbl_name)
        add_item(0, 2, "SN前4:", self.lbl_sn4)
        add_item(0, 4, "SN规则:", self.lbl_sn_rule)
        
        # Row 1
        add_item(1, 0, "规格:", self.lbl_spec)
        add_item(1, 2, "69码:", self.lbl_code69)
        add_item(1, 4, "箱号规则:", self.lbl_box_rule_name)
        
        # Row 2
        add_item(2, 0, "型号:", self.lbl_model)
        add_item(2, 2, "整箱数:", self.lbl_qty)
        add_item(2, 4, "模板:", self.lbl_tmpl_name)
        
        # Row 3
        add_item(3, 0, "颜色:", self.lbl_color)

        # 关键修改：设置列的伸展比例，让第1、3、5列（数值列）自动填充空白，解决右侧留空问题
        gl.setColumnStretch(1, 1)
        gl.setColumnStretch(3, 1)
        gl.setColumnStretch(5, 1)
        # 移除了之前的 gl.setColumnStretch(6, 1) 占位符

        v_details.addLayout(gl)

        # --- 1.3.2 日期与批次 ---
        h_ctrl = QHBoxLayout()
        self.date_prod = QDateEdit(QDate.currentDate()); self.date_prod.setCalendarPopup(True)
        self.date_prod.setStyleSheet("font-size: 16px; padding: 5px;")
        self.combo_repair = QComboBox(); self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.setStyleSheet("font-size: 16px; padding: 5px;")
        self.combo_repair.currentIndexChanged.connect(self.update_box_preview)
        
        l_date = QLabel("日期:"); l_date.setStyleSheet("font-size: 16px;")
        l_batch = QLabel("批次:"); l_batch.setStyleSheet("font-size: 16px;")
        
        h_ctrl.addWidget(l_date); h_ctrl.addWidget(self.date_prod)
        h_ctrl.addWidget(l_batch); h_ctrl.addWidget(self.combo_repair)
        h_ctrl.addStretch()
        v_details.addLayout(h_ctrl)

        v_left.addWidget(grp)

        # 修改：移除了之前的空 Label 占位符，实现整体上移

        # 1.4 当前箱号标题 (修改：字体继续加大)
        self.lbl_box_title = QLabel("当前箱号:")
        # 字体加大到 40px
        self.lbl_box_title.setStyleSheet("font-size: 40px; font-weight: bold; color: #333; margin-top: 5px;") 
        v_left.addWidget(self.lbl_box_title)

        # 1.5 当前箱号数值
        self.lbl_box_no = QLabel("--")
        self.lbl_box_no.setWordWrap(False)
        self.lbl_box_no.setStyleSheet("font-size: 50px; font-weight: bold; color: #c0392b; padding: 0px 0; font-family: Arial;")
        v_left.addWidget(self.lbl_box_no)

        # 1.6 SN 输入框
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("在此扫描SN...")
        self.input_sn.setMinimumHeight(80) 
        self.input_sn.setStyleSheet("font-size: 35px; padding: 10px; border: 3px solid #3498db; border-radius: 6px; color: #333;")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        v_left.addWidget(self.input_sn)
        
        content_layout.addLayout(v_left, 7) 

        # ==================== 右侧：SN列表区 (占比 3) ====================
        v_right = QVBoxLayout()
        
        # 2.1 顶部工具栏
        h_tools = QHBoxLayout()
        
        self.lbl_daily = QLabel("今日: 0")
        self.lbl_daily.setStyleSheet("color: green; font-weight: bold; font-size: 24px;")
        
        btn_all = QPushButton("全选"); btn_all.clicked.connect(lambda: self.list_sn.selectAll())
        btn_del = QPushButton("删除"); btn_del.clicked.connect(self.del_sn)
        btn_all.setFixedHeight(30); btn_del.setFixedHeight(30)
        
        h_tools.addStretch()
        h_tools.addWidget(self.lbl_daily)
        h_tools.addWidget(btn_all)
        h_tools.addWidget(btn_del)

        v_right.addLayout(h_tools)

        # 2.2 列表
        self.list_sn = QListWidget()
        self.list_sn.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_sn.setStyleSheet("font-size: 15px;")
        v_right.addWidget(self.list_sn)

        content_layout.addLayout(v_right, 3)
        main_layout.addLayout(content_layout)

        # 3. 底部打印按钮
        self.btn_print = QPushButton("打印 / 封箱")
        self.btn_print.setStyleSheet("background:#e67e22; color:white; padding:15px; font-size:20px; font-weight:bold; border-radius: 5px;")
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.clicked.connect(self.print_label)
        main_layout.addWidget(self.btn_print)

    # --- 逻辑功能 ---

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
        if not item: return
        p = self.table_product.item(item.row(),0).data(Qt.UserRole)
        if not p: return

        self.current_product = p
        self.lbl_name.setText(str(p.get('name','')))
        self.lbl_sn4.setText(str(p.get('sn4','')))
        self.lbl_spec.setText(str(p.get('spec','')))
        self.lbl_model.setText(str(p.get('model','')))
        self.lbl_color.setText(str(p.get('color',''))) 
        self.lbl_code69.setText(str(p.get('code69','')))
        self.lbl_qty.setText(str(p.get('qty','')))
        
        tmpl = p.get('template_path','')
        self.lbl_tmpl_name.setText(os.path.basename(tmpl) if tmpl else "未设置")
        
        rid = p.get('rule_id',0)
        rname = "无"
        if rid:
             c=self.db.conn.cursor(); c.execute("SELECT name FROM box_rules WHERE id=?",(rid,))
             res=c.fetchone(); rname=res[0] if res else "无"
        self.lbl_box_rule_name.setText(rname)
        
        self.current_sn_rule = None
        sn_rule_name = "无"
        if p.get('sn_rule_id'):
             c=self.db.conn.cursor(); c.execute("SELECT name, rule_string, length FROM sn_rules WHERE id=?",(p['sn_rule_id'],))
             res=c.fetchone()
             if res: 
                 sn_rule_name = res[0]
                 self.current_sn_rule={'fmt':res[1], 'len':res[2]}
        self.lbl_sn_rule.setText(sn_rule_name)

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
            self.lbl_box_no.setText("规则错误")

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
