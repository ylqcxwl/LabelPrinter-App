import win32com.client
import os

class BartenderPrinter:
    def __init__(self):
        self.bt_app = None
        try:
            self.bt_app = win32com.client.Dispatch("BarTender.Application")
            self.bt_app.Visible = False
        except Exception as e:
            print(f"Bartender Init Error: {e}")

    def print_label(self, template_path, data_map, printer_name=None):
        if not self.bt_app:
            return False, "Bartender未安装或无法启动"

        if not os.path.exists(template_path):
            return False, "找不到模板文件"

        try:
            # 打开格式文件
            bt_format = self.bt_app.Formats.Open(template_path, False, "")
            
            # 设置数据源
            # data_map: {"mingcheng": "Product A", "SN4": "1234", "1": "SN001", "2": "SN002"...}
            for key, value in data_map.items():
                try:
                    bt_format.SetNamedSubStringValue(key, str(value))
                except:
                    pass # 忽略模板中不存在的字段

            # 打印
            # Use default printer if not specified
            result = bt_format.PrintOut(False, False) # ShowStatusWindow, ShowDialog
            
            # 不保存模板修改
            bt_format.Close(2) # 2 = btDoNotSaveChanges
            
            return True, "打印成功"
        except Exception as e:
            return False, str(e)

    def quit(self):
        if self.bt_app:
            self.bt_app.Quit(2)
