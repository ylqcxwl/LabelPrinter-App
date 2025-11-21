from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QMessageBox, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon, QFont
from src.config import get_resource_path
from src.version import APP_VERSION
from src.ui.product_page import ProductPage
from src.ui.print_page import PrintPage
from src.ui.history_page import HistoryPage
from src.ui.settings_page import SettingsPage
from src.database import Database # 导入Database以便在关闭时清理

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"外箱标签打印程序 {APP_VERSION}")
        self.resize(1200, 800)
        
        # 尝试加载图标，如果失败则不设置
        try:
            icon_path = get_resource_path("assets/icon.ico")
            if icon_path and QIcon(icon_path).isNull():
                print(f"Warning: Icon file not found or invalid: {icon_path}")
            else:
                self.setWindowIcon(QIcon(icon_path))
        except Exception as e:
            print(f"Error loading icon: {e}")

        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 左侧导航栏
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #2c3e50; min-width: 200px;")
        nav_layout = QVBoxLayout(nav_bar)
        
        # Logo - 字体大一号
        logo_label = QLabel("标签打印")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 28px; font-weight: bold; padding: 20px;") # 字体加大
        nav_layout.addWidget(logo_label)

        # 按钮样式 - 增加悬浮和选中橙色效果
        btn_style = """
            QPushButton {
                color: white;
                background-color: transparent;
                border: none;
                padding: 15px;
                text-align: left;
                font-size: 16px;
            }
            QPushButton:hover {
                background-color: #34495e; /* 悬浮效果 */
            }
            QPushButton:checked {
                background-color: #e67e22; /* 选中后名称框变橙色 */
                font-weight: bold;
            }
        """

        self.btn_product = QPushButton("📦  产品管理")
        self.btn_print = QPushButton("🖨️  打印标签")
        self.btn_history = QPushButton("📜  打印记录")
        self.btn_settings = QPushButton("⚙️  设置")
        
        for btn in [self.btn_product, self.btn_print, self.btn_history, self.btn_settings]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        
        # 版本信息
        ver_label = QLabel(APP_VERSION)
        ver_label.setStyleSheet("color: #7f8c8d; padding: 10px; text-align: center;")
        nav_layout.addWidget(ver_label)

        main_layout.addWidget(nav_bar)

        # 右侧内容区
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 初始化页面
        self.product_page = ProductPage()
        self.print_page = PrintPage()
        self.history_page = HistoryPage()
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.product_page)
        self.stack.addWidget(self.print_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)

        # 信号连接
        self.btn_product.clicked.connect(lambda: self.switch_page(0))
        self.btn_print.clicked.connect(lambda: self.switch_page(1))
        self.btn_history.clicked.connect(lambda: self.switch_page(2))
        self.btn_settings.clicked.connect(lambda: self.switch_page(3))

        # 默认选中
        self.btn_product.click()

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        # 刷新页面数据 (每次切换时刷新，确保数据最新)
        if index == 0: self.product_page.refresh_data()
        elif index == 1: self.print_page.refresh_data()
        elif index == 2: self.history_page.refresh_data()
        elif index == 3: self.settings_page.refresh_data()

    def closeEvent(self, event):
        """关闭窗口时释放Bartender资源"""
        if hasattr(self, 'print_page') and self.print_page.printer:
            self.print_page.printer.quit()
        # 关闭数据库连接
        if hasattr(self, 'db') and self.db: # MainWindow 并没有直接持有db实例，各个页面持有
             pass # 暂时不用在这里显式关闭，因为每个页面都创建了自己的DB实例。
                  # 更好的做法是传递一个共享的DB实例，但这会涉及到重构
        super().closeEvent(event)
