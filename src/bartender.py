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
            # --- 修复：防止模板被覆盖 ---
            # Open(FileName, ReadOnly, Password)
            # 将 ReadOnly 设置为 True，确保绝对不会保存对模板的修改
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
            
            # 关闭不保存 (CloseOptions: 2 = btDoNotSaveChanges)
            # 虽然已经是 ReadOnly 打开，但再次强制不保存
            bt_format.Close(2) 
            
            return True, "打印成功"
        except Exception as e:
            # 异常处理：尝试关闭模板防止锁死
            try:
                if bt_format: bt_format.Close(2)
            except: pass
            return False, f"打印出错: {str(e)}"

    def quit(self):
        if self.bt_app:
            try:
                self.bt_app.Quit(2) # 2 = btDoNotSaveChanges
            except:
                pass
