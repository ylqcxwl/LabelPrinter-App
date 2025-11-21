from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,
                             QMessageBox, QRadioButton, QButtonGroup, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QFont
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
        self.refresh_data() # 初始加载数据

    def init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20) # 增加边距
        main_layout.setSpacing(15) # 增加组件间距

        # 1. 顶部：产品选择区
        top_group = QGroupBox("作业设置")
        top_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 16px; margin-top: 10px; border: 1px solid #ccc; border-radius: 5px; } QGroupBox::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0 5px; }")
        top_layout = QHBoxLayout()
        
        self.combo_product = QComboBox()
        self.combo_product.setMinimumHeight(30)
        self.combo_product.currentIndexChanged.connect(self.on_product_select)
        
        self.date_prod = QDateEdit()
        self.date_prod.setDate(QDate.currentDate())
        self.date_prod.setCalendarPopup(True) # 显示日历选择
        self.date_prod.setMinimumHeight(30)
        
        # 返修/补箱选项 (0-9)
        self.combo_repair = QComboBox()
        self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.setMinimumHeight(30)
        self.combo_repair.currentIndexChanged.connect(self.update_box_number_preview) # 修复：改变批次时更新箱号预览
        
        top_layout.addWidget(QLabel("选择产品:"))
        top_layout.addWidget(self.combo_product, 2)
        top_layout.addWidget(QLabel("生产日期:"))
        top_layout.addWidget(self.date_prod, 1)
        top_layout.addWidget(QLabel("批次/返修等级:"))
        top_layout.addWidget(self.combo_repair, 1)
        
        top_group.setLayout(top_layout)
        main_layout.addWidget(top_group)

        # 2. 中部：扫描与显示
        mid_layout = QHBoxLayout()
        
        # 左侧：当前箱信息
        left_panel = QVBoxLayout()
        self.lbl_info = QLabel("请选择产品")
        self.lbl_info.setStyleSheet("font-size: 14px; font-weight: bold; color: #2980b9; padding: 5px;")
        
        self.lbl_box_no = QLabel("当前箱号: 待生成")
        self.lbl_box_no.setStyleSheet("font-size: 18px; color: #c0392b; font-weight: bold; padding: 5px;")
        
        self.input_sn = QLineEdit()
        self.input_sn.setPlaceholderText("在此扫描SN...")
        self.input_sn.setStyleSheet("font-size: 16px; padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px;")
        self.input_sn.returnPressed.connect(self.on_sn_scan)
        
        left_panel.addWidget(self.lbl_info)
        left_panel.addWidget(self.lbl_box_no)
        left_panel.addWidget(self.input_sn)
        left_panel.addStretch() # 增加弹性空间，将内容顶到上方
        
        # 右侧：列表
        self.list_sn = QListWidget()
        self.list_sn.setStyleSheet("font-size: 14px; border: 1px solid #bdc3c7; border-radius: 5px;")
        
        mid_layout.addLayout(left_panel, 1)
        mid_layout.addWidget(self.list_sn, 1)
        main_layout.addLayout(mid_layout)

        # 3. 底部：操作
        btn_layout = QHBoxLayout()
        self.btn_print = QPushButton("手动打印/强制封箱")
        self.btn_print.setStyleSheet("background-color: #e67e22; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_print.setMinimumHeight(40)
        self.btn_print.setCursor(Qt.PointingHandCursor)
        self.btn_print.clicked.connect(self.execute_print)
        
        self.btn_del_sn = QPushButton("删除选中SN")
        self.btn_del_sn.setStyleSheet("background-color: #95a5a6; color: white; font-weight: bold; padding: 10px; border-radius: 5px;")
        self.btn_del_sn.setMinimumHeight(40)
        self.btn_del_sn.setCursor(Qt.PointingHandCursor)
        self.btn_del_sn.clicked.connect(self.delete_selected_sn)
        
        btn_layout.addWidget(self.btn_del_sn)
        btn_layout.addStretch()
        btn_layout.addWidget(self.btn_print)
        main_layout.addLayout(btn_layout)

    def refresh_data(self):
        """刷新产品列表并尝试选中第一个产品"""
        self.combo_product.clear()
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT id, name, sn4, qty, rule_id FROM products ORDER BY name ASC") # 增加 rule_id 获取
        self.products_data = cursor.fetchall() # 存储所有产品数据
        
        if not self.products_data:
            self.lbl_info.setText("请先在'产品管理'页面添加产品。")
            self.lbl_box_no.setText("当前箱号: 无产品")
            self.current_product = None
            self.current_sn_list = []
            self.list_sn.clear()
            return

        for p in self.products_data:
            # p: (id, name, sn4, qty, rule_id)
            self.combo_product.addItem(p[1], (p[0], p[2], p[3], p[4])) 
        
        # 默认选中第一个产品
        if self.combo_product.count() > 0:
            self.combo_product.setCurrentIndex(0)
            self.on_product_select() # 强制触发一次选择事件

    def on_product_select(self):
        """处理产品选择事件"""
        idx = self.combo_product.currentIndex()
        if idx < 0: # 没有产品被选中
            self.current_product = None
            self.lbl_info.setText("请选择产品")
            self.lbl_box_no.setText("当前箱号: 待生成")
            self.current_sn_list = []
            self.list_sn.clear()
            return
        
        p_name = self.combo_product.currentText()
        p_data = self.combo_product.currentData() # (id, sn4, qty, rule_id)
        
        if not p_data: # 防止数据为空
            QMessageBox.warning(self, "错误", "产品数据加载失败，请检查产品管理页面。")
            return

        self.current_product = {
            "id": p_data[0],
            "name": p_name,
            "sn4": p_data[1],
            "qty": p_data[2],
            "rule_id": p_data[3] # 添加 rule_id 到 current_product
        }
        
        self.lbl_info.setText(f"产品: {p_name}\nSN前四位: {p_data[1]}\n整箱数量: {p_data[2]}")
        self.current_sn_list = []
        self.list_sn.clear()
        self.update_box_number_preview() # 修复：确保在选择产品后更新箱号预览
        self.input_sn.setFocus()

    def update_box_number_preview(self):
        """更新当前箱号的预览"""
        if not self.current_product:
            self.lbl_box_no.setText("当前箱号: 无产品信息")
            return
        
        rule_id = self.current_product.get('rule_id')
        if not rule_id:
            self.lbl_box_no.setText("当前箱号: 无箱号规则")
            return
        
        repair_lvl = int(self.combo_repair.currentText())
        
        preview_str, _ = self.rule_engine.generate_box_no(rule_id, self.current_product, repair_lvl)
        self.current_box_no = preview_str
        self.lbl_box_no.setText(f"当前箱号: {preview_str}")

    def on_sn_scan(self):
        """处理SN扫描或手动输入"""
        if not self.current_product:
            QMessageBox.warning(self, "警告", "请先选择一个产品。")
            self.input_sn.clear()
            return

        sn = self.input_sn.text().strip().upper() # 统一转大写
        self.input_sn.clear()
        if not sn: return
        
        # 1. 校验SN前四位
        target_prefix = self.current_product['sn4'].upper() # 统一转大写
        if not sn.startswith(target_prefix):
            QMessageBox.warning(self, "错误", f"SN前缀不匹配! \n需: {target_prefix}\n实: {sn[:len(target_prefix)] if len(sn) >= len(target_prefix) else sn}")
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
        self.list_sn.scrollToBottom() # 自动滚动到底部

        # 4. 检查是否满箱
        if len(self.current_sn_list) >= self.current_product['qty']:
            self.execute_print()

    def delete_selected_sn(self):
        """删除选中SN"""
        selected_items = self.list_sn.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "提示", "请选择要删除的SN。")
            return
        
        if QMessageBox.question(self, "确认删除", f"确定删除选中的 {len(selected_items)} 个SN吗？") == QMessageBox.Yes:
            sns_to_remove = []
            for item in selected_items:
                sn_txt = item.text().split(". ")[1]
                sns_to_remove.append(sn_txt)
            
            # 从 self.current_sn_list 中移除
            self.current_sn_list = [x for x in self.current_sn_list if x[0] not in sns_to_remove]
            
            # 更新列表显示
            self.list_sn.clear()
            for i, (sn, _) in enumerate(self.current_sn_list):
                 self.list_sn.addItem(f"{i+1}. {sn}")

    def execute_print(self):
        """执行打印操作"""
        if not self.current_product:
            QMessageBox.warning(self, "警告", "请先选择一个产品。")
            return
        if len(self.current_sn_list) == 0:
            QMessageBox.warning(self, "警告", "当前箱中没有SN，无法打印。")
            return
        if not self.current_box_no or self.current_box_no == "待生成" or self.current_box_no == "无箱号规则":
            QMessageBox.warning(self, "警告", "箱号未生成或规则无效，请检查设置。")
            return

        # 1. 获取完整产品详情
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT * FROM products WHERE id=?", (self.current_product['id'],))
        # columns: id, name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id
        p_row = cursor.fetchone()
        
        if not p_row:
            QMessageBox.critical(self, "错误", "未找到产品详细信息，无法打印。")
            return

        template_path = p_row[10]
        if not template_path or not os.path.exists(template_path): # 确保模板路径有效
            QMessageBox.critical(self, "错误", f"Bartender模板路径无效或文件不存在: {template_path}")
            return

        # 2. 准备数据源 Map
        mapping = self.db.get_setting('field_mapping') or DEFAULT_MAPPING
        
        data_map = {}
        # 静态数据映射
        data_map[mapping.get('name', 'mingcheng')] = p_row[1]
        data_map[mapping.get('spec', 'guige')] = p_row[2]
        data_map[mapping.get('model', 'xinghao')] = p_row[3]
        data_map[mapping.get('color', 'yanse')] = p_row[4]
        data_map[mapping.get('sn4', 'SN4')] = p_row[5]
        data_map[mapping.get('sku', 'SKU')] = p_row[6]
        data_map[mapping.get('code69', '69')] = p_row[7]
        data_map[mapping.get('weight', 'zhongliang')] = p_row[9]
        
        # 动态数据
        real_qty = len(self.current_sn_list)
        data_map[mapping.get('qty', 'shuliang')] = real_qty
        data_map[mapping.get('box_no', 'xianghao')] = self.current_box_no
        
        # SN 列表数据源 (1, 2, 3...)
        for i, (sn, _) in enumerate(self.current_sn_list):
            data_map[str(i+1)] = sn

        # 3. 调用打印机
        success, msg = self.printer.print_label(template_path, data_map)

        if success:
            # 4. 存档并清空
            self.save_records(p_row, self.current_box_no)
            
            # 提交箱号计数器 (只有打印成功才自增)
            rule_id = p_row[11]
            repair_lvl = int(self.combo_repair.currentText())
            self.rule_engine.commit_sequence(rule_id, repair_lvl)
            
            QMessageBox.information(self, "成功", "打印成功")
            self.current_sn_list = []
            self.list_sn.clear()
            self.update_box_number_preview() # 重新生成新箱号预览
            self.input_sn.setFocus()
        else:
            QMessageBox.critical(self, "打印失败", msg)

    def save_records(self, p_row, box_no):
        """保存打印记录"""
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
            except sqlite3.IntegrityError:
                # 理论上前面已校验SN唯一性，这里作为二次防护
                print(f"Warning: SN {sn} already exists in records, skipping save.")
            except Exception as e:
                print(f"Error saving record for SN {sn}: {e}")
        self.db.conn.commit()
