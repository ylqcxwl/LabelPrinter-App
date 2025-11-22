import sys
from PyQt5.QtWidgets import QMainWindow, QTabWidget, QApplication
from src.database import Database
from src.ui.print_page import PrintPage
from src.ui.product_page import ProductPage
from src.ui.setting_page import SettingPage
from src.ui.rule_page import RulePage
from src.ui.sn_rule_page import SnRulePage
from src.ui.record_page import RecordPage

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.db = Database()
        
        # --- 新增：应用启动时自动备份 ---
        ok, msg = self.db.backup_db(manual=False)
        if not ok:
             # 如果自动备份失败，仅在控制台打印警告
             print(f"启动时自动备份失败: {msg}") 
        # --- 自动备份结束 ---
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("标签打印管理工具")
        self.setGeometry(100, 100, 1200, 800)
        
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)
        
        # 创建页面实例
        self.print_page = PrintPage()
        self.product_page = ProductPage()
        self.setting_page = SettingPage(self.db)
        self.rule_page = RulePage()
        self.sn_rule_page = SnRulePage()
        self.record_page = RecordPage()
        
        # 添加标签页
        self.tabs.addTab(self.print_page, "打印标签")
        self.tabs.addTab(self.product_page, "产品管理")
        self.tabs.addTab(self.rule_page, "箱号规则")
        self.tabs.addTab(self.sn_rule_page, "SN规则")
        self.tabs.addTab(self.record_page, "打印记录")
        self.tabs.addTab(self.setting_page, "系统设置")
        
        # 绑定页面刷新事件
        self.tabs.currentChanged.connect(self.tab_changed)

    def tab_changed(self, index):
        current_widget = self.tabs.widget(index)
        # 仅刷新需要数据的页面，避免不必要的数据库操作
        if isinstance(current_widget, PrintPage):
            current_widget.refresh_data()
        elif isinstance(current_widget, ProductPage):
            current_widget.refresh_data()
        elif isinstance(current_widget, RulePage):
            current_widget.refresh_data()
        elif isinstance(current_widget, SnRulePage):
            current_widget.refresh_data()
        elif isinstance(current_widget, RecordPage):
            current_widget.refresh_data()

def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
