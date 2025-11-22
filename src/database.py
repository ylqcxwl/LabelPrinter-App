import sqlite3
import json
import os
import shutil
from datetime import datetime
from functools import lru_cache

DB_FILE = "app_data.db"
BACKUP_DIR = "backup"  # 新增备份目录常量

DEFAULT_SETTINGS = {
    "field_mapping": {
        "name": "ProductName", "spec": "Spec", "model": "Model", 
        "color": "Color", "sn4": "SN4", "sku": "SKU", 
        "code69": "Code69", "qty": "Qty", "weight": "Weight",
        "box_no": "BoxNo", "prod_date": "ProdDate"
    },
    "template_root": "",
    "default_printer": ""
}

class Database:
    def __init__(self):
        self.conn = None
        self.cursor = None
        self.connect()
        self.setup_db()

    def connect(self):
        self.conn = sqlite3.connect(DB_FILE)
        self.cursor = self.conn.cursor()

    def setup_db(self):
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY, name TEXT UNIQUE, spec TEXT, model TEXT, color TEXT, 
                sn4 TEXT, sku TEXT, code69 TEXT, qty INTEGER, weight REAL, 
                rule_id INTEGER, sn_rule_id INTEGER, template_path TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS box_rules (
                id INTEGER PRIMARY KEY, name TEXT, rule_string TEXT, 
                current_seq INTEGER DEFAULT 0, daily_reset_date TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS sn_rules (
                id INTEGER PRIMARY KEY, name TEXT, rule_string TEXT, length INTEGER
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY, box_no TEXT, box_sn_seq INTEGER, 
                name TEXT, spec TEXT, model TEXT, color TEXT, code69 TEXT, 
                sn TEXT UNIQUE, print_date TEXT
            )
        """)
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        """)
        self.conn.commit()
        self._ensure_default_settings()

    def _ensure_default_settings(self):
        for key, default_value in DEFAULT_SETTINGS.items():
            self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
            if self.cursor.fetchone() is None:
                value_str = json.dumps(default_value)
                self.cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", (key, value_str))
        self.conn.commit()

    @lru_cache(maxsize=1)
    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = self.cursor.fetchone()
        if result:
            try:
                return json.loads(result[0])
            except (json.JSONDecodeError, TypeError):
                return result[0]
        return DEFAULT_SETTINGS.get(key)

    def set_setting(self, key, value):
        value_str = json.dumps(value)
        self.cursor.execute("REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value_str))
        self.conn.commit()
        self.get_setting.cache_clear() # 清除缓存

    def check_sn_exists(self, sn):
        self.cursor.execute("SELECT 1 FROM records WHERE sn=?", (sn,))
        return self.cursor.fetchone() is not None

    # --- 新增备份和清理功能 ---

    def backup_db(self, manual=False):
        """
        将主数据库文件复制到备份文件夹，并触发清理。
        manual=True 表示手动备份，用于文件名区分。
        """
        try:
            if not os.path.exists(BACKUP_DIR):
                os.makedirs(BACKUP_DIR)

            # 创建带时间戳和标识的文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            suffix = "_MANUAL" if manual else "_AUTO"
            backup_filename = f"{timestamp}{suffix}_{DB_FILE}"
            backup_path = os.path.join(BACKUP_DIR, backup_filename)

            # 暂时关闭连接，复制文件
            self.conn.close()
            shutil.copy2(DB_FILE, backup_path)
            
            # 重新建立连接
            self.connect()
            
            self.cleanup_backups() # 备份后立即执行清理
            
            return True, f"备份成功：{backup_filename}，旧文件已清理。"
        
        except Exception as e:
            # 尝试重新连接以确保应用能继续运行
            try:
                self.connect()
            except:
                pass 
            return False, f"备份失败：{e}"

    def cleanup_backups(self, retain_count=2):
        """删除备份目录中除最新的两个文件外的所有旧文件。"""
        try:
            if not os.path.exists(BACKUP_DIR):
                return
            
            # 筛选所有数据库备份文件
            backup_files = [f for f in os.listdir(BACKUP_DIR) 
                            if f.endswith(DB_FILE) and os.path.isfile(os.path.join(BACKUP_DIR, f))]
            
            # 获取文件修改时间 (mtime) 和路径
            file_details = []
            for filename in backup_files:
                file_path = os.path.join(BACKUP_DIR, filename)
                mtime = os.path.getmtime(file_path)
                file_details.append((mtime, file_path))
                
            # 按修改时间降序排序 (最新的在前)
            file_details.sort(key=lambda x: x[0], reverse=True)
            
            # 确定要删除的文件 (除了前 retain_count 个)
            files_to_delete = file_details[retain_count:]
            
            for mtime, file_path in files_to_delete:
                os.remove(file_path)
                
        except Exception as e:
            # 清理是非关键功能，仅打印错误
            print(f"备份文件清理错误: {e}")
            pass
