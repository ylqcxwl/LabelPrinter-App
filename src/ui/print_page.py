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
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5,5,5,5)

        # 1. 搜索栏与列表
        h_search = QHBoxLayout()
        self.input_search = QLineEdit()
        self.input_search.setPlaceholderText("🔍 搜索产品...")
        self.input_search.textChanged.connect(self.filter_products)
        
        self.table_product = QTableWidget()
        self.table_product.setColumnCount(6)
        self.table_product.setHorizontalHeaderLabels(["名称", "规格", "颜色", "69码", "SN前4", "箱规"])
        self.table_product.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table_product.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_product.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_product.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_product.setMaximumHeight(150)
        self.table_product.itemClicked.connect(self.on_product_select)
        
        main_layout.addLayout(h_search)
        main_layout.addWidget(self.input_search)
        main_layout.addWidget(self.table_product)

        # 2. 详细信息
        grp = QGroupBox("产品详情")
        gl = QGridLayout(grp)
        gl.setContentsMargins(5,5,5,5)
        
        self.lbl_name = QLabel("--"); self.lbl_sn4 = QLabel("--")
        self.lbl_spec = QLabel("--"); self.lbl_model = QLabel("--")
        self.lbl_code69 = QLabel("--"); self.lbl_qty = QLabel("--")
        self.lbl_rule_name = QLabel("无"); self.lbl_tmpl_name = QLabel("无")

        style = "color: #2980b9; font-weight: bold;"
        for l in [self.lbl_name, self.lbl_sn4, self.lbl_spec, self.lbl_model, self.lbl_code69, self.lbl_qty, self.lbl_rule_name, self.lbl_tmpl_name]:
            l.setStyleSheet(style)

        gl.addWidget(QLabel("名称:"),0,0); gl.addWidget(self.lbl_name,0,1)
        gl.addWidget(QLabel("规格:"),0,2); gl.addWidget(self.lbl_spec,0,3)
        gl.addWidget(QLabel("型号:"),0,4); gl.addWidget(self.lbl_model,0,5)
        gl.addWidget(QLabel("SN前4:"),1,0); gl.addWidget(self.lbl_sn4,1,1)
        gl.addWidget(QLabel("69码:"),1,2); gl.addWidget(self.lbl_code69,1,3)
        gl.addWidget(QLabel("整箱数:"),1,4); gl.addWidget(self.lbl_qty,1,5)
        gl.addWidget(QLabel("箱号规则:"),2,0); gl.addWidget(self.lbl_rule_name,2,1)
        gl.addWidget(QLabel("打印模板:"),2,2); gl.addWidget(self.lbl_tmpl_name,2,3,1,3)

        main_layout.addWidget(grp)

        # 3. 控制
        h_ctrl = QHBoxLayout()
        self.date_prod = QDateEdit(QDate.currentDate()); self.date_prod.setCalendarPopup(True)
        self.combo_repair = QComboBox(); self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.currentIndexChanged.connect(self.update_box_preview)
        self.lbl_daily = QLabel("今日: 0")
        self.lbl_daily.setStyleSheet("color:green; font-weight:bold")
        h_ctrl.addWidget(QLabel("日期:")); h_ctrl.addWidget(self.date_prod)
        h_ctrl.addWidget(QLabel("批次:")); h_ctrl.addWidget(self.combo_repair)
        h_ctrl.addStretch(); h_ctrl.addWidget(self.lbl_daily)
        main_layout.addLayout(h_ctrl)

        # 4. 扫描区
        h_work = QHBoxLayout()
        v_scan = QVBoxLayout()
        self.lbl_box_no = QLabel("--")
        self.lbl_box_no.setWordWrap(False)
        self.lbl_box_no.setStyleSheet("font-size: 22px; font-weight: bold; color: #c0392b; padding: 5px;")
        
        self.input_sn = QLineEdit(); self.input_sn.setPlaceholderText("扫描SN...")
        self.input_sn.setStyleSheet("font-size:18px; padding:8px; border:2px solid #3498db")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        
        v_scan.addWidget(QLabel("当前箱号:")); v_scan.addWidget(self.lbl_box_no)
        v_scan.addWidget(self.input_sn); v_scan.addStretch()
        
        v_list = QVBoxLayout()
        h_btns = QHBoxLayout()
        b_all = QPushButton("全选"); b_all.clicked.connect(lambda: self.list_sn.selectAll())
        b_del = QPushButton("删除"); b_del.clicked.connect(self.del_sn)
        h_btns.addWidget(QLabel("SN列表")); h_btns.addStretch(); h_btns.addWidget(b_all); h_btns.addWidget(b_del)
        self.list_sn = QListWidget(); self.list_sn.setSelectionMode(QAbstractItemView.ExtendedSelection)
        v_list.addLayout(h_btns); v_list.addWidget(self.list_sn)
        
        h_work.addLayout(v_scan, 4); h_work.addLayout(v_list, 6)
        main_layout.addLayout(h_work)

        b_print = QPushButton("打印 / 封箱"); b_print.setStyleSheet("background:#e67e22;color:white;padding:10px;font-size:16px;font-weight:bold")
        b_print.clicked.connect(self.print_label)
        main_layout.addWidget(b_print)

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

        self.current_sn_list=[]; self.list_sn.clear()
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
        # 1. 基础前缀校验
        prefix = str(self.current_product.get('sn4', '')).strip().upper()
        if not sn.startswith(prefix): return False, f"SN前4位不符 (需以 {prefix} 开头)"
        
        # 2. 规则校验
        if self.current_sn_rule:
            fmt = self.current_sn_rule['fmt']
            mlen = self.current_sn_rule['len']
            
            # 长度校验
            if mlen > 0 and len(sn) != mlen: return False, f"长度错误 (需{mlen}位, 实{len(sn)}位)"
            
            # --- 核心修复：安全正则生成 ---
            # 步骤1：先用占位符保护变量
            temp_pat = fmt.replace("{SN4}", "___SN4___") \
                          .replace("{BATCH}", "___BATCH___")
            # 保护 {SEQn}
            temp_pat = re.sub(r"\{SEQ(\d+)\}", r"___SEQ\1___", temp_pat)
            
            # 步骤2：转义所有字符（处理 / + . 等特殊字符）
            safe_pat = re.escape(temp_pat)
            
            # 步骤3：还原变量为正则代码
            # 还原SN4 (也要转义实际值，防止SN本身含特殊字符)
            safe_pat = safe_pat.replace("___SN4___", re.escape(prefix))
            # 还原批次
            safe_pat = safe_pat.replace("___BATCH___", re.escape(self.combo_repair.currentText()))
            # 还原SEQ (\d{n})
            safe_pat = re.sub(r"___SEQ(\d+)___", lambda m: f"\\d{{{m.group(1)}}}", safe_pat)
            
            try:
                if not re.match(f"^{safe_pat}$", sn): return False, "格式校验不通过"
            except: 
                return False, "规则解析错误"
                
        return True, ""

    def on_sn_scan(self):
        if not self.current_product: return
        sn = self.input_sn.text().strip().upper(); self.input_sn.clear()
        if not sn: return
        
        if sn in [x[0] for x in self.current_sn_list]: return QMessageBox.warning(self,"错","重复扫描")
        if self.db.check_sn_exists(sn): return QMessageBox.warning(self,"错","已打印过")
        
        ok, msg = self.validate_sn(sn)
        if not ok: return QMessageBox.warning(self,"校验失败", msg)
        
        self.current_sn_list.append((sn, datetime.datetime.now()))
        self.list_sn.addItem(sn); self.list_sn.scrollToBottom()
        if len(self.current_sn_list) >= self.current_product['qty']: self.print_label()

    def del_sn(self):
        for i in self.list_sn.selectedItems():
            v=i.text()
            self.current_sn_list=[x for x in self.current_sn_list if x[0]!=v]
            self.list_sn.takeItem(self.list_sn.row(i))

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
            self.current_sn_list=[]; self.list_sn.clear(); self.update_box_preview(); self.update_daily()
        else: QMessageBox.critical(self,"失败", msg)
