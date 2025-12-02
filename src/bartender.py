import win32com.client
import os
import pythoncom
from src.database import Database

class BartenderPrinter:
    def __init__(self):
        self.db = Database() # 初始化数据库连接
        self.bt_app = None
        # 注意：此处不再在初始化时启动 BarTender，改为“懒加载”
        # 从而极大地加快主程序的启动速度

    def _get_bt_app(self):
        """
        内部方法：获取或启动 Bartender 实例。
        仅在需要打印时调用，避免程序启动卡顿。
        """
        if self.bt_app:
            return self.bt_app

        try:
            # 必须在当前线程初始化 COM 环境
            pythoncom.CoInitialize()
            self.bt_app = win32com.client.Dispatch("BarTender.Application")
            self.bt_app.Visible = False
            return self.bt_app
        except Exception as e:
            print(f"Bartender Launch Error: {e}")
            return None

    def print_label(self, template_path, data_map, printer_name=None):
        # 1. 尝试获取 app 实例 (懒加载)
        app = self._get_bt_app()
        if not app:
            return False, "无法启动 Bartender，请确认已安装软件。"

        if not os.path.exists(template_path):
            return False, f"找不到模板文件: {template_path}"

        bt_format = None
        try:
            # 2. 打开模板 (ReadOnly=True)
            bt_format = app.Formats.Open(template_path, True, "")
            
            # 3. 设置默认打印机
            target_printer = self.db.get_setting('default_printer')
            if target_printer and target_printer != "使用系统默认打印机":
                bt_format.Printer = target_printer

            # 4. 设置数据源
            # data_map 包含: name, spec, code69, 1, 2, 3...
            for key, value in data_map.items():
                try:
                    # 尝试设置命名数据源
                    bt_format.SetNamedSubStringValue(key, str(value))
                except:
                    pass 

            # 5. 打印
            # PrintOut(ShowStatusWindow, ShowDialog)
            bt_format.PrintOut(False, False) 
            
            # 6. 关闭模板 (不保存)
            # CloseOptions: 1 = btDoNotSaveChanges
            bt_format.Close(1) 
            
            return True, "打印成功"
        except Exception as e:
            # 异常处理：尝试关闭模板防止锁死
            try:
                if bt_format: bt_format.Close(1)
            except: pass
            return False, f"打印出错: {str(e)}"

    def quit(self):
        """退出 Bartender 进程"""
        if self.bt_app:
            try:
                # SaveOptions: 1 = btDoNotSaveChanges
                self.bt_app.Quit(1) 
                self.bt_app = None
            except:
                pass
            finally:
                # 释放 COM 资源
                try: pythoncom.CoUninitialize()
                except: pass
