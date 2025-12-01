# src/bartender.py
import win32com.client
import os
from src.database import Database

class BartenderPrinter:
    # 修复点：接受一个可选的 db_instance 参数
    def __init__(self, db_instance=None): 
        # 如果传入了 db 实例，则使用它；否则，自行初始化一个
        # 这样确保了在 MainWindow 或 Page 中创建的 db 实例能够被复用
        self.db = db_instance if db_instance else Database() 
        self.bt_app = None
        try:
            self.bt_app = win32com.client.Dispatch("BarTender.Application")
            self.bt_app.Visible = False
        except Exception as e:
            print(f"Bartender Init Error: {e}")

    def print_label(self, template_path, data_map, printer_name=None):
        # 检查 Bartender 实例
        if not self.bt_app:
            try:
                self.bt_app = win32com.client.Dispatch("BarTender.Application")
                self.bt_app.Visible = False
            except:
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
                self.bt_app.Quit()
            except:
                pass
