import win32com.client
import os
from src.database import Database

class BartenderPrinter:
    # 接收 Database 实例，虽然在 __init__ 中 db 没有用到，但为了遵循依赖注入原则，保持传入
    def __init__(self, db):
        self.db = db 
        self.bt_app = None # 启动时不再实例化 BarTender

    def _ensure_app_running(self):
        """确保 BarTender 实例已启动并可用，如果未启动则尝试启动。"""
        if self.bt_app is None:
            try:
                self.bt_app = win32com.client.Dispatch("BarTender.Application")
                self.bt_app.Visible = False
                return True
            except Exception as e:
                print(f"Bartender Init Error (Lazy): {e}")
                return False
        return True

    def print_label(self, template_path, data_map, printer_name=None):
        # --- 优化点：懒加载 BarTender 进程 ---
        # 只有在需要打印时才启动 BarTender
        if not self._ensure_app_running():
            return False, "Bartender未安装或无法启动"

        if not os.path.exists(template_path):
            return False, f"找不到模板文件: {template_path}"

        bt_format = None
        try:
            # --- 修复关键点 1: 保持以只读模式打开 ---
            # Open(FileName, ReadOnly, Password)
            # ReadOnly=True
            bt_format = self.bt_app.Formats.Open(template_path, True, "")
            
            # --- 设置默认打印机 ---
            # 由于 db 是从外部传入的，所以需要确保它有一个获取配置的方法
            target_printer = self.db.get_setting('default_printer')
            if target_printer and target_printer != "使用系统默认打印机":
                bt_format.Printer = target_printer

            # --- 设置数据源 ---
            # data_map 包含: name, spec, code69, 1, 2, 3...
            for key, value in data_map.items():
                try:
                    # 尝试设置命名数据源
                    bt_format.SetNamedSubStringValue(key, str(value))
                except:
                    pass 

            # 打印
            # PrintOut(ShowStatusWindow, ShowDialog)
            bt_format.PrintOut(False, False) 
            
            # --- 修复关键点 2: 强制不保存 ---
            # CloseOptions 枚举: 
            # 0 = btSaveChanges (保存)
            # 1 = btDoNotSaveChanges (不保存) <--- 修改为 1
            # 2 = btPromptSaveChanges (询问)
            bt_format.Close(1) 
            
            return True, "打印成功"
        except Exception as e:
            # 异常处理：尝试关闭模板防止锁死
            try:
                # 同样确保异常退出时也不保存
                if bt_format: bt_format.Close(1)
            except: pass
            return False, f"打印出错: {str(e)}"

    def quit(self):
        if self.bt_app:
            try:
                # --- 修复关键点 3: 退出程序时不保存 ---
                # SaveOptions: 1 = btDoNotSaveChanges
                self.bt_app.Quit(1) 
            except:
                pass
