from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,\
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,\
                             QAbstractItemView, QGridLayout)
from PyQt5.QtCore import QDate, Qt, QTimer # 修正：添加 QTimer
from src.database import Database
from src.box_rules import BoxRuleEngine
from src.bartender import BartenderPrinter
from src.config import DEFAULT_MAPPING
# 修正：添加 AppUpdater 引入
try:
    # 假设 AppUpdater 在 src 根目录
    from src.updater import AppUpdater 
except ImportError:
    # 兼容 utils 路径
    try:
        from src.utils.updater import AppUpdater
    except:
        AppUpdater = None

import datetime
import os
import re
import traceback

class PrintPage(QWidget):
    # --- 优化点：接收 Database 实例 ---
    def __init__(self, db: Database): 
        super().__init__()
        self.db = db # 使用传入的共享实例
        # BoxRuleEngine 也需要 db 实例
        self.rule_engine = BoxRuleEngine(self.db)
        # BartenderPrinter 需要 db 实例
        self.printer = BartenderPrinter(self.db) 
        self.current_product = None
        self.current_sn_list = [] 
        self.current_box_no = ""
        
        self.init_ui()
        self.refresh_data()
        
        # 移除原有的 QTimer.singleShot，由 main_window 统一处理或保持静默
        # if AppUpdater:
        #     QTimer.singleShot(2000, lambda: AppUpdater.check_update(self))

    def init_ui(self):
        # 0. 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)
        
        # 1. 顶部控制区
        top_group = QGroupBox("打印控制")
        top_layout = QHBoxLayout(top_group)
        
        # 产品选择
        self.combo_product = QComboBox()
        self.combo_product.setMinimumWidth(300)
        self.combo_product.currentIndexChanged.connect(self.select_product)
        
        self.lbl_sn4 = QLabel("SN4: N/A")
        self.lbl_sn4.setStyleSheet("font-weight: bold;")
        
        self.lbl_spec = QLabel("规格: N/A")
        
        self.lbl_qty = QLabel("数量: 0")
        
        self.combo_repair = QComboBox()
        self.combo_repair.addItems(["0", "1", "2", "3"]) # 维修等级/计数器分区
        self.combo_repair.currentIndexChanged.connect(self.generate_box_no)

        self.btn_print = QPushButton("📦 打印箱号标签")
        self.btn_print.setFixedHeight(40)
        self.btn_print.setStyleSheet("font-size: 18px; font-weight: bold; background-color: #3498db; color: white;")
        self.btn_print.clicked.connect(self.do_print)

        top_layout.addWidget(QLabel("选择产品:"))
        top_layout.addWidget(self.combo_product)
        top_layout.addWidget(QLabel("维修级别:"))
        top_layout.addWidget(self.combo_repair)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_print)
        
        main_layout.addWidget(top_group)

        # 2. 中间信息区 (Grid)
        info_group = QGroupBox("信息总览")
        info_layout = QGridLayout(info_group)
        
        self.lbl_box_no = QLabel("箱号: N/A")
        self.lbl_box_no.setStyleSheet("font-size: 20px; font-weight: bold; color: #e67e22;")
        
        self.lbl_next_seq = QLabel("下一序号: 0")
        
        self.lbl_tmpl = QLabel("模板: N/A")
        
        self.lbl_print_status = QLabel("待输入SN")
        self.lbl_print_status.setAlignment(Qt.AlignCenter)
        self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: #34495e; border: 2px solid #ddd; border-radius: 8px; background-color: #f0f0f0;")
        self.lbl_print_status.setMinimumSize(200, 100)
        
        info_layout.addWidget(self.lbl_sn4, 0, 0)
        info_layout.addWidget(self.lbl_spec, 0, 1)
        info_layout.addWidget(self.lbl_qty, 0, 2)
        info_layout.addWidget(self.lbl_box_no, 1, 0)
        info_layout.addWidget(self.lbl_next_seq, 1, 1)
        info_layout.addWidget(self.lbl_tmpl, 1, 2)
        info_layout.addWidget(self.lbl_print_status, 0, 3, 2, 1) # 跨两行

        main_layout.addWidget(info_group)

        # 3. 底部SN输入与列表
        bottom_layout = QHBoxLayout()
        
        # SN输入
        sn_input_group = QGroupBox("SN录入")
        sn_input_layout = QVBoxLayout(sn_input_group)
        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("扫码输入SN")
        self.sn_input.returnPressed.connect(self.add_sn)
        self.sn_input_status = QLabel("等待输入...")
        self.sn_input_status.setStyleSheet("color: blue;")
        
        sn_input_layout.addWidget(self.sn_input)
        sn_input_layout.addWidget(self.sn_input_status)
        sn_input_layout.addStretch()
        
        bottom_layout.addWidget(sn_input_group, 1) # 比例 1
        
        # SN列表
        sn_list_group = QGroupBox("本箱SN列表 (0 / 0)")
        self.sn_list = QListWidget()
        self.sn_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        
        sn_list_layout = QVBoxLayout(sn_list_group)
        sn_list_layout.addWidget(self.sn_list)
        
        sn_btns_layout = QHBoxLayout()
        self.btn_del_sn = QPushButton("删除选中SN")
        self.btn_clear_sn = QPushButton("清空所有SN")
        self.btn_del_sn.clicked.connect(self.delete_selected_sn)
        self.btn_clear_sn.clicked.connect(self.clear_all_sn)
        sn_btns_layout.addWidget(self.btn_del_sn)
        sn_btns_layout.addWidget(self.btn_clear_sn)
        sn_list_layout.addLayout(sn_btns_layout)
        
        bottom_layout.addWidget(sn_list_group, 2) # 比例 2

        main_layout.addLayout(bottom_layout)
        
        # 定时器，用于清除状态栏信息
        self.status_timer = QTimer(self)
        self.status_timer.setSingleShot(True)
        self.status_timer.timeout.connect(lambda: self.lbl_print_status.setText("待输入SN"))

    def refresh_data(self):
        # 加载产品列表
        self.combo_product.clear()
        self.combo_product.addItem("--- 请选择产品 ---", None)
        self.db.cursor.execute("SELECT id, name, sn4, spec, qty, template_path, rule_id, model, color, code69, sku, sn_rule_id FROM products ORDER BY name")
        products = self.db.cursor.fetchall()
        
        # ID, Name, SN4, Spec, Qty, TmplPath, RuleID, Model, Color, Code69, SKU, SNRuleID
        keys = ["id", "name", "sn4", "spec", "qty", "template_path", "rule_id", "model", "color", "code69", "sku", "sn_rule_id"]
        
        for p_data in products:
            product_info = dict(zip(keys, p_data))
            self.combo_product.addItem(product_info['name'], product_info)
        
        if self.combo_product.count() > 1:
            self.combo_product.setCurrentIndex(1) # 默认选中第一个产品
        
        self.select_product(self.combo_product.currentIndex())


    def select_product(self, index):
        self.current_product = self.combo_product.itemData(index)
        
        if self.current_product:
            p = self.current_product
            self.lbl_sn4.setText(f"SN4: {p.get('sn4', 'N/A')}")
            self.lbl_spec.setText(f"规格: {p.get('spec', 'N/A')}")
            self.lbl_qty.setText(f"数量: {p.get('qty', 0)}")
            
            root = self.db.get_setting('template_root')
            tp = p.get('template_path','')
            path = os.path.join(root, tp) if root and tp else tp
            self.lbl_tmpl.setText(f"模板: {os.path.basename(path)}")

            self.clear_all_sn()
            self.generate_box_no()
        else:
            self.lbl_sn4.setText("SN4: N/A")
            self.lbl_spec.setText("规格: N/A")
            self.lbl_qty.setText("数量: 0")
            self.lbl_box_no.setText("箱号: N/A")
            self.lbl_next_seq.setText("下一序号: 0")
            self.lbl_tmpl.setText("模板: N/A")
            self.current_box_no = ""
            self.current_sn_list = []
            self.update_sn_list_count()
            self.lbl_print_status.setText("待输入SN")


    def generate_box_no(self):
        if not self.current_product:
            self.lbl_box_no.setText("箱号: N/A")
            self.lbl_next_seq.setText("下一序号: 0")
            return

        p = self.current_product
        rule_id = p.get('rule_id', 0)
        repair_level = int(self.combo_repair.currentText())

        if rule_id == 0:
            self.current_box_no = "NO_RULE"
            self.lbl_box_no.setText("箱号: NO_RULE")
            self.lbl_next_seq.setText("下一序号: 0")
            return

        try:
            box_no, next_seq = self.rule_engine.generate_box_no(rule_id, p, repair_level)
            self.current_box_no = box_no
            self.lbl_box_no.setText(f"箱号: {box_no}")
            self.lbl_next_seq.setText(f"下一序号: {next_seq}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"箱号规则生成失败: {e}")
            self.current_box_no = "ERROR"
            self.lbl_box_no.setText("箱号: ERROR")
            self.lbl_next_seq.setText("下一序号: 0")


    def add_sn(self):
        sn = self.sn_input.text().strip()
        if not sn:
            self.sn_input_status.setText("SN不能为空！"); self.sn_input_status.setStyleSheet("color: red;");
            self.sn_input.clear(); QTimer.singleShot(1500, self.reset_sn_status)
            return

        # 检查是否重复
        if sn in [item[0] for item in self.current_sn_list]:
            self.sn_input_status.setText("SN已在本箱中！"); self.sn_input_status.setStyleSheet("color: orange;");
            self.sn_input.clear(); QTimer.singleShot(1500, self.reset_sn_status)
            return

        # 检查是否已打印
        if self.db.check_sn_exists(sn):
            self.sn_input_status.setText("SN已被打印过！"); self.sn_input_status.setStyleSheet("color: red;");
            self.sn_input.clear(); QTimer.singleShot(1500, self.reset_sn_status)
            return

        # SN规则校验 (如果有)
        if self.current_product and self.current_product.get('sn_rule_id', 0) != 0:
            rule_id = self.current_product.get('sn_rule_id')
            ok, msg = self.rule_engine.validate_sn(rule_id, sn)
            if not ok:
                self.sn_input_status.setText(f"SN校验失败: {msg}"); self.sn_input_status.setStyleSheet("color: red;");
                self.sn_input.clear(); QTimer.singleShot(2500, self.reset_sn_status)
                return

        # 添加SN
        self.current_sn_list.append((sn, datetime.datetime.now().strftime("%H:%M:%S")))
        self.sn_list.addItem(f"{sn} ({self.current_sn_list[-1][1]})")
        
        self.sn_input_status.setText("添加成功"); self.sn_input_status.setStyleSheet("color: green;")
        self.sn_input.clear()
        
        self.update_sn_list_count()
        
        # 如果数量达到要求，自动准备打印
        if self.current_product and len(self.current_sn_list) == self.current_product['qty']:
            self.lbl_print_status.setText("数量已满，可打印")
            self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: green; border: 2px solid #3498db; border-radius: 8px; background-color: #ecf0f1;")
            self.status_timer.stop()
        else:
            QTimer.singleShot(1000, self.reset_sn_status)


    def reset_sn_status(self):
        self.sn_input_status.setText("等待输入...")
        self.sn_input_status.setStyleSheet("color: blue;")

    def update_sn_list_count(self):
        total_qty = self.current_product['qty'] if self.current_product else 0
        current_count = len(self.current_sn_list)
        self.sn_list_group.setTitle(f"本箱SN列表 ({current_count} / {total_qty})")

    def delete_selected_sn(self):
        selected_items = self.sn_list.selectedItems()
        if not selected_items: return
        
        # 记录要删除的SN，以便从 self.current_sn_list 中移除
        sns_to_remove = []
        for item in selected_items:
            # 列表项格式为 "SN (时间)"，需要解析出 SN
            text = item.text().split(' ')[0]
            sns_to_remove.append(text)
            self.sn_list.takeItem(self.sn_list.row(item))
            
        # 从核心列表中删除
        self.current_sn_list = [sn_time for sn_time in self.current_sn_list if sn_time[0] not in sns_to_remove]
        
        self.update_sn_list_count()
        self.lbl_print_status.setText("待输入SN")
        self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: #34495e; border: 2px solid #ddd; border-radius: 8px; background-color: #f0f0f0;")
        self.status_timer.stop()

    def clear_all_sn(self):
        self.current_sn_list = []
        self.sn_list.clear()
        self.update_sn_list_count()
        self.lbl_print_status.setText("待输入SN")
        self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: #34495e; border: 2px solid #ddd; border-radius: 8px; background-color: #f0f0f0;")
        self.status_timer.stop()

    def do_print(self):
        if not self.current_product:
            return QMessageBox.warning(self, "警告", "请先选择一个产品。")

        p = self.current_product
        required_qty = p['qty']
        
        if len(self.current_sn_list) != required_qty:
            return QMessageBox.warning(self, "警告", f"SN数量不足或过多，要求 {required_qty} 个，当前 {len(self.current_sn_list)} 个。")

        if not self.current_box_no or self.current_box_no in ["N/A", "ERROR", "NO_RULE"]:
            return QMessageBox.critical(self, "错误", "箱号生成失败或规则无效，无法打印。")

        # 1. 准备打印数据 (Data Map)
        dat = {}
        # 基础产品信息
        for key in ['name', 'spec', 'model', 'color', 'sn4', 'sku', 'code69', 'qty', 'weight']:
            dat[key] = p.get(key, '')
        
        # 箱号和SN列表 (BarTender通常通过SetNamedSubStringValue设置单个字段)
        dat['box_no'] = self.current_box_no
        
        # 将 SN 列表转为可用于 BarTender 的数据 (SN1, SN2, SN3...)
        for i, (sn, _) in enumerate(self.current_sn_list):
            dat[f'SN{i+1}'] = sn
        
        # ------------------------
        
        root = self.db.get_setting('template_root')
        tp = p.get('template_path','')
        path = os.path.join(root, tp) if root and tp else tp
        
        # 调用底层打印
        ok, msg = self.printer.print_label(path, dat)
        
        if ok:
            # 1. 更新数据库记录
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            # 修正：记录正确的 box_sn_seq (序号从 1 开始)
            for i, (sn,_) in enumerate(self.current_sn_list):
                self.db.cursor.execute("INSERT INTO records (box_no, box_sn_seq, name, spec, model, color, code69, sn, print_date) VALUES (?,?,?,?,?,?,?,?,?)",
                                       (self.current_box_no, i+1, p['name'], p['spec'], p['model'], p['color'], p['code69'], sn, now))
            self.db.conn.commit()
            self.rule_engine.commit_sequence(p['rule_id'], p['id'], int(self.combo_repair.currentText()))
            
            # 2. 更新UI状态：显示“打印完成” (绿色)
            self.lbl_print_status.setText("打印完成")
            self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: green; border: 2px solid #ddd; border-radius: 8px; background-color: #ecf0f1;")
            self.status_timer.start(3000) # 3秒后清除状态
            
            # 3. 清空SN列表并生成新箱号
            self.clear_all_sn()
            self.generate_box_no()
            
        else:
            # 打印失败
            self.lbl_print_status.setText("打印失败")
            self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: red; border: 2px solid #ddd; border-radius: 8px; background-color: #ffe0e0;")
            self.status_timer.start(5000)
            QMessageBox.critical(self, "打印失败", f"BarTender打印错误: {msg}")
