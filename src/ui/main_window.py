import sys
import webbrowser
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QPushButton, QStackedWidget, QLabel, QFrame, QMessageBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer # 引入 QTimer
from PyQt5.QtGui import QIcon, QPainter, QColor
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

# 引入 Updater
try:
    from src.updater import AppUpdater
except ImportError:
    # 兼容路径
    try:
        from src.utils.updater import AppUpdater
    except:
        AppUpdater = None


# --- 新增：检查更新的后台线程 (从上一个回答复制) ---
class UpdateCheckWorker(QThread):
    # 信号：是否有更新，最新版本号，下载链接
    result_signal = pyqtSignal(bool, str, str)

    def run(self):
        if AppUpdater:
            has_update, tag, url = AppUpdater.get_latest_version_info()
            self.result_signal.emit(has_update, tag, url)
        else:
            self.result_signal.emit(False, "", "")

# --- 新增：自定义版本号按钮（支持红点）(从上一个回答复制)---
class VersionButton(QPushButton):
    def __init__(self, text, parent=None):
        super().__init__(text, parent)
        self.has_update = False
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                color: #7f8c8d;
                background-color: transparent;
                border: none;
                padding: 10px;
                font-size: 11px;
                text-align: center;
            }
            QPushButton:hover {
                color: #bdc3c7;
            }
        """)

    def set_update_status(self, has_update):
        self.has_update = has_update
        self.update() # 触发重绘

    def paintEvent(self, event):
        super().paintEvent(event)
        if self.has_update:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setBrush(QColor("#e74c3c")) # 红色
            painter.setPen(Qt.NoPen)
            
            w = self.width()
            painter.drawEllipse(w - 25, 5, 8, 8)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # --- 优化点：只实例化一次 Database ---
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
        nav_bar.setFixedWidth(160)
        
        nav_layout = QVBoxLayout(nav_bar)
        nav_layout.setContentsMargins(0, 30, 0, 20) 
        nav_layout.setSpacing(5)
        
        # LOGO
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
                padding-left: 30px;
                padding-top: 15px;
                padding-bottom: 15px;
                text-align: left;
                font-size: 16px;
                font-weight: 500;
                border-left: 5px solid transparent;
            }
            QPushButton:hover {
                background-color: #34495e;
                color: white;
            }
            QPushButton:checked {
                background-color: #2c3e50;
                color: #e67e22;
                border-left: 5px solid #e67e22;
                font-weight: bold;
            }
        """

        self.btn_product = QPushButton("📦  产品管理")
        self.btn_print = QPushButton("🔖  打印标签") 
        self.btn_history = QPushButton("📜  打印记录")
        self.btn_settings = QPushButton("⚙️  设    置")
        
        for btn in [self.btn_product, self.btn_print, self.btn_history, self.btn_settings]:
            btn.setCheckable(True)
            btn.setAutoExclusive(True)
            btn.setStyleSheet(btn_style)
            btn.setCursor(Qt.PointingHandCursor)
            nav_layout.addWidget(btn)

        nav_layout.addStretch()
        
        # 版本号按钮 (新增功能)
        self.btn_version = VersionButton(APP_VERSION)
        self.btn_version.clicked.connect(self.on_version_clicked)
        nav_layout.addWidget(self.btn_version)

        main_layout.addWidget(nav_bar)

        # ================= 右侧内容区 =================
        self.stack = QStackedWidget()
        main_layout.addWidget(self.stack)

        # --- 优化点：将 Database 实例传递给所有页面 ---
        self.product_page = ProductPage(self.db)
        self.print_page = PrintPage(self.db)
        self.history_page = HistoryPage(self.db) 
        self.settings_page = SettingsPage(self.db)

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

        # --- 优化点：延迟启动检查更新 ---
        self.update_url = None # 存储下载链接
        self.check_worker = UpdateCheckWorker()
        self.check_worker.result_signal.connect(self.on_update_result)
        # 延迟 1500 毫秒后启动更新检查，不影响主界面加载
        QTimer.singleShot(1500, self.check_worker.start) 

    def switch_page(self, index):
        self.stack.setCurrentIndex(index)
        # 切换页面时刷新数据
        current_widget = self.stack.widget(index)
        if hasattr(current_widget, 'refresh_data'):
            current_widget.refresh_data()

    def on_update_result(self, has_update, tag, url):
        """处理更新检查结果"""
        if has_update:
            self.btn_version.set_update_status(True)
            self.btn_version.setToolTip(f"发现新版本: v{tag}\n点击立即下载")
            self.update_url = url
            print(f"Update found: {tag}")

    def on_version_clicked(self):
        """点击版本号"""
        if self.btn_version.has_update and self.update_url:
            # 打开浏览器下载
            webbrowser.open(self.update_url)
        # else:
            # 可以选择手动检查更新，但此处保持静默

    def closeEvent(self, event):
        # 确保在程序关闭时 BarTender 进程被正确退出
        if hasattr(self, 'print_page') and hasattr(self.print_page, 'printer'):
            try:
                self.print_page.printer.quit()
            except:
                pass
        super().closeEvent(event)
