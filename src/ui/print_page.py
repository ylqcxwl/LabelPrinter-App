from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,
                             QMessageBox, QRadioButton, QButtonGroup)
from PyQt5.QtCore import QDate, Qt
from src.database import Database
from src.box_rules import BoxRuleEngine
from src.bartender import BartenderPrinter
from src.config import DEFAULT_MAPPING
import datetime

class PrintPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.rule_engine = BoxRuleEngine(self.db)
        self.printer = BartenderPrinter()
        
        self.current_product = None
        self.current_sn_list = [] # [(sn, timestamp)]
        self.current_box_no = ""
        
        self.init_ui()

    def init_ui(self):
        main_layout = QVBoxLayout(self)

        # 1. 顶部：产品选择区
        top_group = QGroupBox("作业设置")
        top_layout = QHBoxLayout()
        
        self.combo_product = QComboBox()
        self.combo_product.currentIndexChanged.connect(self.on_product_select)
        
        self.date_prod = QDateEdit()
        self.date_prod.setDate(QDate.currentDate())
        
        # 返修/补箱选项 (0-9)
        self.combo_repair = QComboBox()
        self.combo_repair.addItems([str(i) for i in range(10)])
        
        top_layout.addWidget(QLabel("选择产品:"))
        top_layout.addWidget(self.combo_product)
        top_layout.addWidget(QLabel("生产日期:"))
        top_layout.addWidget(self.date_prod)
        top_layout.addWidget(QLabel("批次/返修等级:"))
        top_layout.addWidget(self.combo_repair)
        
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # 2. 中部：扫描与显示
        mid_layout = QHBoxLayout()
        
        # 左侧：当前箱信息
        left_panel = QVBoxLayout()
        self.lbl_info = QLabel("请选择产品")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9;")
        
        self.lbl_box_no = QLabel("当前箱号: 待生成")
        self.lbl_box_no.setStyleSheet("font-size: 18px; color: #c0392b; font-weight: bold;")
        
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("在此扫描SN...")
        self.input_sn.setStyleSheet("font-size: 16px; padding: 10px;")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        
        left_panel.addWidget(self.lbl_info)
        left_panel.addWidget(self.lbl_box_no)
        left_panel.addWidget(self.input_sn)
        left_panel.addStretch()
        
        # 右侧：列表
        self.list_sn = QListWidget()
        
        mid_layout.addLayout(left_panel, 1)
        mid_layout.addWidget(self.list_sn, 1)
        main_layout.addLayout(mid_layout)

        # 3. 底部：操作
        btn_layout = QHBoxLayout()
        self.btn_print = QPushButton("手动打印/强制封箱")
        self.btn_print.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 10px;")
        self.btn_print.clicked.connect(self.execute_print)
        
        self.btn_del_sn = QPushButton("删除选中SN")
        self.btn_del_sn.clicked.connect(self.delete_selected_sn)
        
        btn_layout.addWidget(self.btn_del_sn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_print)
        main_layout.addLayout(btn_layout)

    def refresh_data(self):
        self.combo_product.clear()
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, sn4, qty FROM products")
        self.products = cursor.fetchall()
        for p in self.products:
            # data: (id, sn4, qty)
            self.combo_product.addItem(p[1], (p[0], p[2], p[3])) 

    def on_product_select(self):
        idx = self.combo_product.currentIndex()
        if idx < 0: return
        
        p_name = self.combo_product.currentText()
        p_data = self.combo_product.currentData() # (id, sn4, qty)
        
        self.current_product = {
            "id": p_data[0],
            "name": p_name,
            "sn4": p_data[1],
            "qty": p_data[2]
        }
        
        self.lbl_info.setText(f"产品: {p_name}\nSN前四位: {p_data[1]}\n整箱数量: {p_data[2]}")
        self.current_sn_list = []
        self.list_sn.clear()
        self.update_box_number_preview()
        self.input_sn.setFocus()

    def update_box_number_preview(self):
        if not self.current_product: return
        
        # 获取产品关联的规则ID
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT rule_id FROM products WHERE id=?", (self.current_product['id'],))
        res = cursor.fetchone()
        rule_id = res[0] if res else 0
        
        repair_lvl = int(self.combo_repair.currentText())
        
        preview_str, _ = self.rule_engine.generate_box_no(rule_id, self.current_product, repair_lvl)
        self.current_box_no = preview_str
        self.lbl_box_no.setText(f"当前箱号: {preview_str}")

    def on_sn_scan(self):
        sn = self.input_sn.text().strip()
        self.input_sn.clear()
        if not sn: return
        
        # 1. 校验SN前四位
        target_prefix = self.current_product['sn4']
        if not sn.startswith(target_prefix):
            QMessageBox.warning(self, "错误", f"SN前缀不匹配! \n需: {target_prefix}\n实: {sn[:4]}")
            return

        # 2. 校验重复 (内存 + 数据库)
        if sn in [x[0] for x in self.current_sn_list]:
            QMessageBox.warning(self, "错误", "该SN已在当前箱中")
            return
            
        if self.db.check_sn_exists(sn):
            QMessageBox.warning(self, "错误", "该SN历史记录已存在 (已打印过)")
            return

        # 3. 添加到列表
        self.current_sn_list.append((sn, datetime.datetime.now()))
        row = self.list_sn.count() + 1
        self.list_sn.addItem(f"{row}. {sn}")

        # 4. 检查是否满箱
        if len(self.current_sn_list) >= self.current_product['qty']:
            self.execute_print()

    def delete_selected_sn(self):
        rows = self.list_sn.selectedItems()
        if not rows: return
        for item in rows:
            # item text format: "1. XXXXX"
            sn_txt = item.text().split(". ")[1]
            # Remove from list
            self.current_sn_list = [x for x in self.current_sn_list if x[0] != sn_txt]
            self.list_sn.takeItem(self.list_sn.row(item))
        
        # Refresh indices
        self.list_sn.clear()
        for i, (sn, _) in enumerate(self.current_sn_list):
             self.list_sn.addItem(f"{i+1}. {sn}")

    def execute_print(self):
        if not self.current_product: return
        if len(self.current_sn_list) == 0: return

        # 1. 获取完整产品详情
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (self.current_product['id'],))
        # columns: id, name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id
        p_row = cursor.fetchone()
        
        # 2. 准备数据源 Map
        # 从设置中读取映射关系
        mapping = self.db.get_setting('field_mapping') or DEFAULT_MAPPING
        
        data_map = {}
        # 静态数据
        data_map[mapping.get('name')] = p_row[1]
        data_map[mapping.get('spec')] = p_row[2]
        data_map[mapping.get('model')] = p_row[3]
        data_map[mapping.get('color')] = p_row[4]
        data_map[mapping.get('sn4')] = p_row[5]
        data_map[mapping.get('sku')] = p_row[6]
        data_map[mapping.get('code69')] = p_row[7]
        data_map[mapping.get('weight')] = p_row[9]
        
        # 动态数据
        real_qty = len(self.current_sn_list)
        data_map[mapping.get('qty')] = real_qty
        data_map[mapping.get('box_no')] = self.current_box_no
        
        # SN 列表数据源 (1, 2, 3...)
        for i, (sn, _) in enumerate(self.current_sn_list):
            data_map[str(i+1)] = sn

        # 3. 调用打印机
        template_path = p_row[10]
        success, msg = self.printer.print_label(template_path, data_map)

        if success:
            # 4. 存档并清空
            self.save_records(p_row, self.current_box_no)
            
            # 提交计数器
            rule_id = p_row[11]
            self.rule_engine.commit_sequence(rule_id, int(self.combo_repair.currentText()))
            
            QMessageBox.information(self, "成功", "打印成功")
            self.current_sn_list = []
            self.list_sn.clear()
            self.update_box_number_preview() # 生成新箱号
        else:
            QMessageBox.critical(self, "打印失败", msg)

    def save_records(self, p_row, box_no):
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        prod_date = self.date_prod.text()
        
        for i, (sn, _) in enumerate(self.current_sn_list):
            try:
                self.db.cursor.execute('''
                    INSERT INTO records (box_sn_seq, name, spec, model, color, code69, sn, box_no, prod_date, print_date)
                    VALUES (?,?,?,?,?,?,?,?,?,?)
                ''', (
                    i+1, p_row[1], p_row[2], p_row[3], p_row[4], p_row[7], sn, box_no, prod_date, now_str
                ))
            except:
                pass # 忽略重复 (理论上前面校验过)
        self.db.conn.commit()
