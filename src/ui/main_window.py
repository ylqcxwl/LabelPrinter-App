from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from src.config import get_resource_path
from src.version import APP_VERSION
from src.ui.product_page import ProductPage
from src.ui.print_page import PrintPage
from src.ui.history_page import HistoryPage
from src.ui.settings_page import SettingsPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"外箱标签打印程序 {APP_VERSION}")
        self.resize(1280, 850)
        
        try:
            icon_path = get_resource_path("assets/icon.ico")
            if icon_path: self.setWindowIcon(QIcon(icon_path))
        except: pass

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # --- 左侧导航栏 ---
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #2c3e50;")
        nav_bar.setFixedWidth(150) # 固定宽度
        
        nav_layout = QVBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 20, 0, 20) 
        nav_layout.setSpacing(0) # 按钮紧挨着
        
        logo_label = QLabel("标签打印")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 22px; font-weight: bold; margin-bottom: 30px;")
        nav_layout.addWidget(logo_label)

        # 按钮样式 - 修复UI显示问题
        btn_style = """
            QPushButton {
                color: #bdc3c7;
                background-color: transparent;
                border: none;
                padding: 20px 0px;
                text-align: center;
                font-size: 15px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #34495e;
                color: white;
            }
            QPushButton:checked {
                background-color: #e67e22; /* 整个背景变橙色，避免边框渲染问题 */
                color: white;
            }
        """

        self.btn_product = QPushButton("📦 产品管理")
        self.btn_print = QPushButton("🖨️打印标签")
        self.btn_history = QPushButton("📜 打印记录")
        self.btn_settings = QPushButton("⚙️ 设    置")
        
        for btn in [self.btn_product, self.btn_print, self.btn_history, self.btn_settings]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        
        ver_label = QLabel(APP_VERSION)
        ver_label.setAlignment(Qt.AlignCenter)
        ver_label.setStyleSheet("color: #7f8c8d; padding: 10px; font-size: 10px;")
        nav_layout.addWidget(ver_label)

        main_layout.addWidget(nav_bar)

        # 右侧内容
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        self.product_page = ProductPage()
        self.print_page = PrintPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.product_page)
        self.stack.addWidget(self.print_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)

        self.btn_product.clicked.connect(lambda: self.switch_page(0))
        self.btn_print.clicked.connect(lambda: self.switch_page(1))
        self.btn_history.clicked.connect(lambda: self.switch_page(2))
        self.btn_settings.clicked.connect(lambda: self.switch_page(3))

        self.btn_product.click()

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        if index == 0: self.product_page.refresh_data()
        elif index == 1: self.print_page.refresh_data()
        elif index == 2: self.history_page.refresh_data()
        elif index == 3: self.settings_page.refresh_data()

    def closeEvent(self, event):
        if hasattr(self, 'print_page') and self.print_page.printer:
            self.print_page.printer.quit()
        super().closeEvent(event)
