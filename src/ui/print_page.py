# src/ui/print_page.py
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
                             QListWidget, QPushButton, QComboBox, QDateEdit, QGroupBox,
                             QMessageBox, QTableWidget, QTableWidgetItem, QHeaderView,
                             QAbstractItemView, QGridLayout)
from PyQt5.QtCore import QDate, Qt, QTimer # 修正：添加 QTimer
from src.database import Database
from src.box_rules import BoxRuleEngine
from src.bartender import BartenderPrinter
from src.config import DEFAULT_MAPPING
# 修正：添加 AppUpdater 引入
try:
    from src.utils.updater import AppUpdater
except ImportError:
    AppUpdater = None

import datetime
import os
import re
import traceback

class PrintPage(QWidget):
    def __init__(self):
        super().__init__()
        self.db = Database()
        self.rule_engine = BoxRuleEngine(self.db)
        # 【重要修改点】将 self.db 实例传递给 BartenderPrinter
        self.printer = BartenderPrinter(self.db) 
        self.current_product = None
        self.current_sn_list = [] 
        self.current_box_no = ""
        
        self.init_ui()
        self.refresh_data()
        
        # 修正：添加软件更新检查
        if AppUpdater:
            QTimer.singleShot(2000, lambda: AppUpdater.check_update(self))

    def init_ui(self):
        # 0. 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 1. 产品信息 & SN输入 (左侧部分)
        h_layout = QHBoxLayout()

        # 1.1 产品选择组
        product_group = QGroupBox("产品信息与选择")
        product_layout = QGridLayout()
        product_group.setLayout(product_layout)

        # 产品列表
        self.lbl_product = QLabel("选择产品:")
        self.cb_product = QComboBox()
        self.cb_product.currentIndexChanged.connect(self.select_product)
        product_layout.addWidget(self.lbl_product, 0, 0)
        product_layout.addWidget(self.cb_product, 0, 1)

        # 产品详情标签
        self.lbl_name = QLabel("名称: "); product_layout.addWidget(self.lbl_name, 1, 0)
        self.lbl_spec = QLabel("规格: "); product_layout.addWidget(self.lbl_spec, 2, 0)
        self.lbl_model = QLabel("型号: "); product_layout.addWidget(self.lbl_model, 3, 0)
        self.lbl_color = QLabel("颜色: "); product_layout.addWidget(self.lbl_color, 4, 0)
        
        self.val_name = QLabel(""); product_layout.addWidget(self.val_name, 1, 1)
        self.val_spec = QLabel(""); product_layout.addWidget(self.val_spec, 2, 1)
        self.val_model = QLabel(""); product_layout.addWidget(self.val_model, 3, 1)
        self.val_color = QLabel(""); product_layout.addWidget(self.val_color, 4, 1)

        # 数量、重量、69码
        self.lbl_qty = QLabel("箱容量: "); product_layout.addWidget(self.lbl_qty, 5, 0)
        self.lbl_weight = QLabel("重量: "); product_layout.addWidget(self.lbl_weight, 6, 0)
        self.lbl_code69 = QLabel("69码: "); product_layout.addWidget(self.lbl_code69, 7, 0)
        
        self.val_qty = QLabel(""); product_layout.addWidget(self.val_qty, 5, 1)
        self.val_weight = QLabel(""); product_layout.addWidget(self.val_weight, 6, 1)
        self.val_code69 = QLabel(""); product_layout.addWidget(self.val_code69, 7, 1)
        
        # 箱号规则
        self.lbl_box_rule = QLabel("箱号规则: "); product_layout.addWidget(self.lbl_box_rule, 8, 0)
        self.val_box_rule = QLabel(""); product_layout.addWidget(self.val_box_rule, 8, 1)
        
        # 补打级别（0-9）
        self.lbl_repair = QLabel("补打级别: "); product_layout.addWidget(self.lbl_repair, 9, 0)
        self.combo_repair = QComboBox()
        self.combo_repair.addItems([str(i) for i in range(10)])
        self.combo_repair.setCurrentIndex(0) # 默认 0
        self.combo_repair.currentIndexChanged.connect(self.update_preview)
        product_layout.addWidget(self.combo_repair, 9, 1)

        # 预览箱号
        self.lbl_preview = QLabel("预览箱号:"); 
        self.lbl_preview.setStyleSheet("font-weight: bold;")
        product_layout.addWidget(self.lbl_preview, 10, 0)
        self.val_preview = QLabel("N/A")
        self.val_preview.setStyleSheet("font-weight: bold; color: blue; border: 1px solid #ddd; padding: 5px;")
        product_layout.addWidget(self.val_preview, 10, 1)


        # 1.2 SN输入组
        sn_group = QGroupBox("SN/序列号信息")
        sn_layout = QVBoxLayout()
        sn_group.setLayout(sn_layout)

        self.lbl_sn_count = QLabel("已输入SN (0/0):")
        sn_layout.addWidget(self.lbl_sn_count)
        
        self.sn_list_widget = QListWidget()
        self.sn_list_widget.setContextMenuPolicy(Qt.CustomContextMenu)
        self.sn_list_widget.customContextMenuRequested.connect(self.show_context_menu)
        sn_layout.addWidget(self.sn_list_widget)

        self.sn_input = QLineEdit()
        self.sn_input.setPlaceholderText("扫描或输入SN (按回车添加)")
        self.sn_input.returnPressed.connect(self.add_sn)
        sn_layout.addWidget(self.sn_input)
        
        # 按钮区
        btn_layout = QHBoxLayout()
        self.btn_clear_sn = QPushButton("清空SN")
        self.btn_clear_sn.clicked.connect(self.clear_sn_list)
        self.btn_import_sn = QPushButton("导入SN列表")
        self.btn_import_sn.clicked.connect(self.import_sn_list)
        btn_layout.addWidget(self.btn_clear_sn)
        btn_layout.addWidget(self.btn_import_sn)
        sn_layout.addLayout(btn_layout)


        h_layout.addWidget(product_group, 2)
        h_layout.addWidget(sn_group, 3)
        main_layout.addLayout(h_layout, 1)

        # 2. 底部打印区
        bottom_layout = QHBoxLayout()
        self.lbl_print_status = QLabel("请扫描SN并点击打印")
        self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: #7f8c8d; border: 2px solid #ddd; border-radius: 8px; background-color: #ecf0f1; padding: 10px;")
        self.lbl_print_status.setAlignment(Qt.AlignCenter)

        self.btn_print = QPushButton("打印标签")
        self.btn_print.setFixedHeight(80)
        self.btn_print.setFixedWidth(200)
        self.btn_print.setStyleSheet("font-size: 30px; background-color: #3498db; color: white; border-radius: 10px;")
        self.btn_print.clicked.connect(self.start_print)
        
        bottom_layout.addWidget(self.lbl_print_status, 1)
        bottom_layout.addWidget(self.btn_print)
        
        main_layout.addLayout(bottom_layout)

    # --- 辅助方法 ---

    def refresh_data(self):
        """刷新产品列表，并加载第一个产品"""
        self.cb_product.clear()
        self.db.cursor.execute("SELECT id, name FROM products ORDER BY id DESC")
        products = self.db.cursor.fetchall()
        
        if not products:
            self.lbl_print_status.setText("请先在'产品管理'中添加产品")
        
        for p_id, p_name in products:
            self.cb_product.addItem(p_name, p_id)
        
        self.select_product(0)
        self.clear_sn_list()


    def select_product(self, index):
        """选择产品时的逻辑"""
        product_id = self.cb_product.itemData(index)
        
        if not product_id:
            self.current_product = None
            self.clear_product_info()
            return
            
        self.db.cursor.execute("SELECT * FROM products WHERE id=?", (product_id,))
        # id, name, spec, model, color, sn4, sku, code69, qty, weight, template_path, rule_id, sn_rule_id
        data = self.db.cursor.fetchone() 
        if not data: 
            self.clear_product_info()
            return

        # 转换为字典方便访问
        self.current_product = {
            'id': data[0], 'name': data[1], 'spec': data[2], 'model': data[3],
            'color': data[4], 'sn4': data[5], 'sku': data[6], 'code69': data[7],
            'qty': data[8], 'weight': data[9], 'template_path': data[10], 
            'rule_id': data[11], 'sn_rule_id': data[12]
        }
        
        # 更新显示
        p = self.current_product
        self.val_name.setText(p['name'])
        self.val_spec.setText(p['spec'] if p['spec'] else "N/A")
        self.val_model.setText(p['model'] if p['model'] else "N/A")
        self.val_color.setText(p['color'] if p['color'] else "N/A")
        self.val_qty.setText(str(p['qty']))
        self.val_weight.setText(p['weight'] if p['weight'] else "N/A")
        self.val_code69.setText(p['code69'] if p['code69'] else "N/A")
        
        # 箱号规则名称
        rule_name = self.db.get_rule_name(p['rule_id'])
        self.val_box_rule.setText(rule_name if rule_name else "默认")

        self.clear_sn_list()
        self.update_preview()
        

    def clear_product_info(self):
        """清空产品详情显示"""
        for label in [self.val_name, self.val_spec, self.val_model, self.val_color, 
                      self.val_qty, self.val_weight, self.val_code69, self.val_box_rule]:
            label.setText("N/A")
        self.val_preview.setText("N/A")


    def clear_sn_list(self):
        """清空SN列表"""
        self.sn_list_widget.clear()
        self.current_sn_list = []
        self._update_sn_count()
        self.lbl_print_status.setText("请扫描SN并点击打印")


    def _update_sn_count(self):
        """更新SN计数显示"""
        current_count = len(self.current_sn_list)
        max_count = self.current_product['qty'] if self.current_product and self.current_product['qty'] else 0
        self.lbl_sn_count.setText(f"已输入SN ({current_count}/{max_count}):")
        
        if max_count > 0 and current_count >= max_count:
            # 满箱时高亮显示
            self.lbl_sn_count.setStyleSheet("font-weight: bold; color: green;")
        else:
            self.lbl_sn_count.setStyleSheet("font-weight: normal; color: black;")


    def add_sn(self):
        """添加SN到列表"""
        if not self.current_product:
            self.lbl_print_status.setText("请先选择产品")
            return

        sn = self.sn_input.text().strip().upper() # 转换为大写
        self.sn_input.clear()
        
        if not sn: return
        
        max_qty = self.current_product.get('qty', 0)

        # 1. 检查数量限制
        if max_qty > 0 and len(self.current_sn_list) >= max_qty:
            self.lbl_print_status.setText(f"SN数量已满 ({max_qty}个)")
            QMessageBox.warning(self, "警告", f"SN数量已达到最大箱容量: {max_qty} 个。")
            return

        # 2. 检查SN重复
        if sn in [item[0] for item in self.current_sn_list]:
            self.lbl_print_status.setText(f"SN重复: {sn}")
            QMessageBox.warning(self, "警告", f"SN码 '{sn}' 已在列表中。")
            return

        # 3. 校验SN规则
        sn_rule_id = self.current_product.get('sn_rule_id', 0)
        if sn_rule_id != 0:
            ok, msg = self.rule_engine.validate_sn(sn_rule_id, sn)
            if not ok:
                self.lbl_print_status.setText(f"SN校验失败: {msg}")
                QMessageBox.critical(self, "校验失败", f"SN码 '{sn}' 不符合规则:\n{msg}")
                return

        # 4. 检查SN是否已被打印过
        if self.db.check_sn_exists(sn):
            self.lbl_print_status.setText(f"SN已打印: {sn}")
            QMessageBox.critical(self, "错误", f"SN码 '{sn}' 已被打印过，请检查！")
            return


        # 5. 添加SN
        # sn, rule_id (备用), date
        self.current_sn_list.append((sn, sn_rule_id, datetime.datetime.now()))
        self.sn_list_widget.addItem(sn)
        self.sn_list_widget.scrollToBottom()
        self._update_sn_count()
        self.lbl_print_status.setText(f"成功添加SN: {sn} (按打印标签完成)")

        # 自动触发打印 (如果满了)
        if max_qty > 0 and len(self.current_sn_list) == max_qty:
            self.lbl_print_status.setText(f"已满 ({max_qty}个)，准备打印...")
            self.start_print()


    def show_context_menu(self, pos):
        """SN列表右键菜单"""
        if not self.sn_list_widget.itemAt(pos): return

        from PyQt5.QtWidgets import QMenu
        menu = QMenu()
        delete_action = menu.addAction("删除选中SN")
        
        action = menu.exec_(self.sn_list_widget.mapToGlobal(pos))
        if action == delete_action:
            self.delete_selected_sn()


    def delete_selected_sn(self):
        """删除选中的SN"""
        selected_items = self.sn_list_widget.selectedItems()
        if not selected_items: return
        
        # 获取要删除的SN列表
        sn_to_remove = [item.text() for item in selected_items]
        
        # 从 internal list 中删除
        self.current_sn_list = [item for item in self.current_sn_list if item[0] not in sn_to_remove]
        
        # 从 QListWidget 中删除
        for item in selected_items:
            self.sn_list_widget.takeItem(self.sn_list_widget.row(item))
            
        self._update_sn_count()
        self.lbl_print_status.setText(f"已删除 {len(sn_to_remove)} 个SN")

    def import_sn_list(self):
        """从文件导入SN列表"""
        if not self.current_product:
            QMessageBox.warning(self, "警告", "请先选择产品")
            return
            
        path, _ = QFileDialog.getOpenFileName(self, "导入SN列表 (每行一个SN)", "", "Text Files (*.txt);;Excel Files (*.xlsx)")
        if not path: return

        try:
            sn_list = []
            # 检查文件类型
            if path.lower().endswith('.txt'):
                with open(path, 'r', encoding='utf-8') as f:
                    sn_list = [line.strip().upper() for line in f if line.strip()]
            elif path.lower().endswith('.xlsx'):
                # 假设 SN 在第一列
                df = pd.read_excel(path, header=None, sheet_name=0)
                sn_list = [str(sn).strip().upper() for sn in df.iloc[:, 0].tolist() if str(sn).strip()]
            
            if not sn_list:
                QMessageBox.warning(self, "警告", "文件内容为空或格式错误")
                return

            # 清空旧列表
            self.clear_sn_list()
            
            # 逐个校验并添加
            max_qty = self.current_product.get('qty', 0)
            sn_rule_id = self.current_product.get('sn_rule_id', 0)
            added_count = 0
            
            for sn in sn_list:
                # 数量限制
                if max_qty > 0 and added_count >= max_qty:
                    QMessageBox.warning(self, "警告", f"已导入 {max_qty} 个SN，超过最大箱容量，已忽略剩余SN。")
                    break

                # 校验规则
                if sn_rule_id != 0:
                    ok, msg = self.rule_engine.validate_sn(sn_rule_id, sn)
                    if not ok:
                        QMessageBox.warning(self, "校验失败", f"SN码 '{sn}' 不符合规则:\n{msg}\n已跳过此SN。")
                        continue
                
                # 检查SN是否已被打印过
                if self.db.check_sn_exists(sn):
                    QMessageBox.critical(self, "错误", f"SN码 '{sn}' 已被打印过，已跳过。")
                    continue
                
                # 添加SN
                self.current_sn_list.append((sn, sn_rule_id, datetime.datetime.now()))
                self.sn_list_widget.addItem(sn)
                added_count += 1
                
            self._update_sn_count()
            self.lbl_print_status.setText(f"导入成功: {added_count} 个SN")
            self.sn_list_widget.scrollToBottom()

        except Exception as e:
            QMessageBox.critical(self, "错误", f"导入文件失败: {e}")


    def update_preview(self):
        """更新箱号预览"""
        if not self.current_product:
            self.val_preview.setText("N/A")
            return

        rule_id = self.current_product.get('rule_id', 0)
        product_id = self.current_product.get('id', 0)
        repair_level = int(self.combo_repair.currentText())

        if rule_id == 0:
            self.val_preview.setText("无规则 (使用默认)")
            return

        # 调用规则引擎生成预览箱号 (不自增)
        # repair_level 传递给 engine
        box_no, _ = self.rule_engine.generate_box_no(rule_id, self.current_product, repair_level)
        self.val_preview.setText(box_no)


    def start_print(self):
        """开始打印流程"""
        if not self.current_product:
            self.lbl_print_status.setText("请先选择产品")
            QMessageBox.warning(self, "警告", "请先选择产品")
            return

        if len(self.current_sn_list) == 0:
            self.lbl_print_status.setText("SN列表为空")
            QMessageBox.warning(self, "警告", "SN列表为空，请扫描或导入SN")
            return
            
        # 0. 检查模板路径
        template_path = self.current_product.get('template_path')
        if not template_path:
            self.lbl_print_status.setText("模板路径缺失")
            QMessageBox.critical(self, "错误", "产品信息中缺少标签模板路径！")
            return

        # 1. 禁用按钮防止重复点击
        self.btn_print.setEnabled(False)
        self.lbl_print_status.setText("正在生成箱号...")

        try:
            p = self.current_product
            repair_level = int(self.combo_repair.currentText())

            # 2. 生成/获取箱号 (此处必须获取最终要提交的箱号)
            # generate_box_no(rule_id, product_info, repair_level, is_commit=False)
            # is_commit=False (默认) 会返回预览+下一个值。只有打印成功才调用 commit_sequence
            box_no, next_seq = self.rule_engine.generate_box_no(
                p['rule_id'], p, repair_level, is_commit=False
            )
            self.current_box_no = box_no
            self.lbl_print_status.setText(f"箱号: {box_no}，正在打印...")
            
            # 3. 构造打印数据字典
            dat = {
                # 基础信息
                'name': p['name'], 'spec': p['spec'], 'model': p['model'], 
                'color': p['color'], 'sn4': p['sn4'], 'sku': p['sku'], 
                'code69': p['code69'], 'qty': str(len(self.current_sn_list)), 
                'weight': p['weight'], 
                
                # 关键信息
                'box_no': box_no, 
                'date': datetime.datetime.now().strftime("%Y-%m-%d"),
                
                # SN 列表 (最多支持 10 个 SN 字段)
                **{f"SN{i+1}": sn for i, (sn,_,_) in enumerate(self.current_sn_list)},
            }
            # 清除未使用的 SN 占位符
            for i in range(len(self.current_sn_list), 10):
                dat[f"SN{i+1}"] = ""

            # ------------------------
            # 4. 调用打印机
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
                for i, (sn,_,_) in enumerate(self.current_sn_list):
                    self.db.cursor.execute("INSERT INTO records (box_no, box_sn_seq, name, spec, model, color, code69, sn, print_date) VALUES (?,?,?,?,?,?,?,?,?)",
                                           (self.current_box_no, i+1, p['name'], p['spec'], p['model'], p['color'], p['code69'], sn, now))
                self.db.conn.commit()
                # 提交计数器自增
                self.rule_engine.commit_sequence(p['rule_id'], p['id'], repair_level)
                
                # 2. 更新UI状态：显示“打印完成” (绿色)
                self.lbl_print_status.setText("打印完成")
                self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: green; border: 2px solid #ddd; border-radius: 8px; background-color: #e6ffe6; padding: 10px;")
                
                # 3. 清空SN列表并更新预览
                self.clear_sn_list()
                self.update_preview() # 获取下一个箱号
                
            else:
                # 打印失败
                self.lbl_print_status.setText(f"打印失败: {msg}")
                self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: red; border: 2px solid #ddd; border-radius: 8px; background-color: #ffe6e6; padding: 10px;")
                QMessageBox.critical(self, "打印失败", f"打印失败: {msg}\nSN列表未清空，请检查打印机。")


        except Exception as e:
            # 发生程序级异常
            err_msg = traceback.format_exc()
            self.lbl_print_status.setText("程序内部错误")
            self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: red; border: 2px solid #ddd; border-radius: 8px; background-color: #ffe6e6; padding: 10px;")
            QMessageBox.critical(self, "致命错误", f"打印过程中发生致命错误，SN未提交，请联系维护人员。\n错误信息:\n{err_msg}")

        finally:
            # 5. 重新启用按钮
            self.btn_print.setEnabled(True)
            # 确保状态标签恢复颜色
            if self.lbl_print_status.text() not in ["打印完成", "打印失败: "]:
                self.lbl_print_status.setStyleSheet("font-size: 40px; font-weight: bold; color: #7f8c8d; border: 2px solid #ddd; border-radius: 8px; background-color: #ecf0f1; padding: 10px;")
