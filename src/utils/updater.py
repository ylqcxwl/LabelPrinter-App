import requests
import webbrowser
from PyQt5.QtWidgets import QMessageBox
from src.version import APP_VERSION

class AppUpdater:
    # 替换为您的实际仓库API地址
    GITHUB_API_URL = "https://api.github.com/repos/ylqcxwl/LabelPrinterApp/releases/latest"

    @staticmethod
    def check_update(parent_widget, manual=False):
        """
        检查更新
        :param parent_widget: 父窗口，用于弹窗
        :param manual: 是否为手动检查（手动检查时，无更新也会提示）
        """
        try:
            # 设置超时，避免卡顿
            response = requests.get(AppUpdater.GITHUB_API_URL, timeout=5)
            if response.status_code == 200:
                data = response.json()
                latest_tag = data.get("tag_name", "").replace("v", "")
                current_ver = APP_VERSION.replace("v", "")
                
                # 简单的版本号比较逻辑
                if latest_tag > current_ver:
                    msg = f"发现新版本: {latest_tag}\n当前版本: {APP_VERSION}\n\n更新内容:\n{data.get('body', '')}"
                    reply = QMessageBox.question(parent_widget, "发现新版本", 
                                                 msg + "\n\n是否前往下载页面？", 
                                                 QMessageBox.Yes | QMessageBox.No)
                    if reply == QMessageBox.Yes:
                        webbrowser.open(data.get("html_url"))
                elif manual:
                    QMessageBox.information(parent_widget, "检查更新", "当前已是最新版本。")
            else:
                if manual:
                    QMessageBox.warning(parent_widget, "检查失败", f"无法获取版本信息 (Code {response.status_code})")
        except Exception as e:
            print(f"Update check failed: {e}")
            if manual:
                QMessageBox.warning(parent_widget, "检查失败", f"网络错误: {e}")
