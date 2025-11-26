import win32com.client
import os
from src.database import Database

class BartenderPrinter:
    def __init__(self):
        self.db = Database() # 初始化数据库连接
        self.bt_app = None
        try:
            self.bt_app = win32com.client.Dispatch("BarTender.Application")
            self.bt_app.Visible = False
        except Exception as e:
            print(f"Bartender Init Error: {e}")

    def print_label(self, template_path, data_map, printer_name=None):
        # 检查 Bartender 实例，如果丢失尝试重连
        if not self.bt_app:
            try:
                self.bt_app = win32com.client.Dispatch("BarTender.Application")
                self.bt_app.Visible = False
            except:
                return False, "Bartender未安装或无法启动"

        if not os.path.exists(template_path):
            return False, "找不到模板文件"

        try:
            # 打开格式文件
            # Open(FileName, CloseAfterPrint, Password)
            bt_format = self.bt_app.Formats.Open(template_path, False, "")
            
            # --- 新增：设置默认打印机逻辑 ---
            # 1. 从数据库获取设置
            target_printer = self.db.get_setting('default_printer')
            
            # 2. 如果设置了具体打印机（且不是占位符），则应用设置
            if target_printer and target_printer != "使用系统默认打印机":
                bt_format.Printer = target_printer
            # -----------------------------

            # 设置数据源
            # data_map: {"mingcheng": "Product A", "SN4": "1234", "1": "SN001", "2": "SN002"...}
            for key, value in data_map.items():
                try:
                    bt_format.SetNamedSubStringValue(key, str(value))
                except:
                    pass # 忽略模板中不存在的字段

            # 打印
            # PrintOut(ShowStatusWindow, ShowDialog)
            # 返回值通常为 0 (成功) 或其他错误码，但在 win32com 中可能表现不同，这里主要捕获异常
            bt_format.PrintOut(False, False) 
            
            # 不保存模板修改并关闭
            # Close(SaveOptions): 2 = btDoNotSaveChanges
            bt_format.Close(2) 
            
            return True, "打印成功"
        except Exception as e:
            # 尝试关闭模板以防锁死，忽略错误
            try:
                if 'bt_format' in locals():
                    bt_format.Close(2)
            except:
                pass
            return False, f"打印出错: {str(e)}"

    def quit(self):
        if self.bt_app:
            try:
                self.bt_app.Quit(2) # 2 = btDoNotSaveChanges
            except:
                pass
