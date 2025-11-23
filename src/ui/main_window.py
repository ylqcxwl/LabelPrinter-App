import sys
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from src.config import get_resource_path
from src.version import APP_VERSION
from src.database import Database

# 导入各个页面
from src.ui.product_page import ProductPage
from src.ui.print_page import PrintPage
# 兼容导入 RecordPage/HistoryPage
try:
    from src.ui.record_page import RecordPage as HistoryPage
except ImportError:
    from src.ui.history_page import HistoryPage
# 兼容导入 SettingsPage
try:
    from src.ui.settings_page import SettingsPage
except ImportError:
    from src.ui.setting_page import SettingsPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        
        # 尝试自动备份 (不阻塞界面)
        try:
            if hasattr(self.db, 'backup_db'):
                self.db.backup_db(manual=False)
        except:
            pass

        self.setWindowTitle(f"外箱标签打印程序 {APP_VERSION}")
        self.resize(1280, 850)
        
        # 设置窗口图标
        try:
            icon_path = get_resource_path("assets/icon.ico")
            if icon_path: self.setWindowIcon(QIcon(icon_path))
        except: pass

        # 主容器
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # ================= 左侧导航栏 =================
        nav_bar = QFrame()
        nav_bar.setStyleSheet("background-color: #2c3e50;")
        nav_bar.setFixedWidth(160) # 固定宽度
        
        nav_layout = QVBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 30, 0, 20) 
        nav_layout.setSpacing(5)
        
        # LOGO区域
        logo_label = QLabel("标签打印")
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet("color: white; font-size: 24px; font-weight: bold; margin-bottom: 40px;")
        nav_layout.addWidget(logo_label)

        # 按钮样式
        btn_style = """
            QPushButton {
                color: #ecf0f1;
                background-color: transparent;
                border: none;
                padding-left: 30px; /* 左侧留出空间给图标 */
                padding-top: 15px;
                padding-bottom: 15px;
                text-align: left;   /* 文字左对齐 */
                font-size: 16px;
                font-weight: 500;
                border-left: 5px solid transparent;
            }
            QPushButton:hover {
                background-color: #34495e;
                color: white;
            }
            QPushButton:checked {
                background-color: #2c3e50; /* 选中背景色 */
                color: #e67e22;            /* 选中文字变橙色 */
                border-left: 5px solid #e67e22; /* 左侧橙色指示条 */
                font-weight: bold;
            }
        """

        # 定义按钮 
        # 修改：使用 '🔖' (书签/吊牌)，这是 Unicode 6.0 标准，在 Win7 上兼容性极好，且形似标签
        self.btn_product = QPushButton("📦  产品管理")
        self.btn_print = QPushButton("🔖  打印标签") 
        self.btn_history = QPushButton("📜  打印记录")
        self.btn_settings = QPushButton("⚙️  设    置")
        
        # 应用样式并添加到布局
        for btn in [self.btn_product, self.btn_print, self.btn_history, self.btn_settings]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        
        # 版本号
        ver_label = QLabel(APP_VERSION)
        ver_label.setAlignment(Qt.AlignCenter)
        ver_label.setStyleSheet("color: #7f8c8d; padding: 10px; font-size: 11px;")
        nav_layout.addWidget(ver_label)

        main_layout.addWidget(nav_bar)

        # ================= 右侧内容区 =================
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # 初始化各个页面
        self.product_page = ProductPage()
        self.print_page = PrintPage()
        self.history_page = HistoryPage() 
        self.settings_page = SettingsPage()

        self.stack.addWidget(self.product_page)
        self.stack.addWidget(self.print_page)
        self.stack.addWidget(self.history_page)
        self.stack.addWidget(self.settings_page)

        # 绑定点击事件
        self.btn_product.clicked.connect(lambda: self.switch_page(0))
        self.btn_print.clicked.connect(lambda: self.switch_page(1))
        self.btn_history.clicked.connect(lambda: self.switch_page(2))
        self.btn_settings.clicked.connect(lambda: self.switch_page(3))

        # 默认选中“打印标签”
        self.btn_print.click()

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        # 切换页面时刷新数据
        current_widget = self.stack.widget(index)
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    def closeEvent(self, event):
        # 关闭时释放打印机资源
        if hasattr(self, 'print_page') and hasattr(self.print_page, 'printer'):
            try:
                self.print_page.printer.quit()
            except:
                pass
        super().closeEvent(event)
