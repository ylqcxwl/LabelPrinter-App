import os
import sys

def get_resource_path(relative_path):
    """获取资源绝对路径，兼容开发环境和PyInstaller打包后的环境"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

DB_NAME = "label_printer.db"
PASSWORD = "123456"

# 默认字段映射
DEFAULT_MAPPING = {
    "name": "mingcheng",
    "spec": "guige",
    "model": "xinghao",
    "color": "yanse",
    "sn4": "SN4",
    "sku": "SKU",
    "code69": "69",
    "box_no": "xianghao",
    "qty": "shuliang",
    "weight": "zhongliang"
}
