import sqlite3
import json
import shutil
import os
import datetime
from src.config import DEFAULT_MAPPING

class Database:
    def __init__(self, db_name='label_printer.db'):
        self.db_name = os.path.abspath(db_name)
        self.conn = sqlite3.connect(self.db_name)
        self.cursor = self.conn.cursor()
        self.setup_db()

    def setup_db(self):
        # 表结构定义 (保持现有结构，只做检查)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, spec TEXT, model TEXT, color TEXT,
                sn4 TEXT NOT NULL UNIQUE, sku TEXT, code69 TEXT,
                qty INTEGER, weight TEXT, template_path TEXT,
                rule_id INTEGER DEFAULT 0, sn_rule_id INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, rule_string TEXT NOT NULL, current_seq INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sn_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE, rule_string TEXT NOT NULL, length INTEGER DEFAULT 0
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_no TEXT NOT NULL, box_sn_seq INTEGER,
                name TEXT, spec TEXT, model TEXT, color TEXT,
                code69 TEXT, sn TEXT NOT NULL, print_date TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY, value TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_counters (
                key TEXT PRIMARY KEY, current_val INTEGER
            )
        ''')
        self.conn.commit()

        # 检查并初始化默认设置
        self.init_default_settings()
        self.init_field_mapping()

    def init_default_settings(self):
        # 检查并插入默认设置
        if not self.get_setting('template_root'):
            self.set_setting('template_root', os.path.abspath("templates"))
        if not self.get_setting('backup_path'):
            self.set_setting('backup_path', os.path.abspath("backup"))
        if not self.get_setting('default_printer'):
            self.set_setting('default_printer', '使用系统默认打印机')
        self.conn.commit()

    def get_setting(self, key, default=None):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = self.cursor.fetchone()
        return json.loads(res[0]) if res else default

    def set_setting(self, key, value):
        val = json.dumps(value)
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, val))

    def init_field_mapping(self):
        current_map = self.get_setting('field_mapping')
        if not current_map:
            self.set_setting('field_mapping', DEFAULT_MAPPING)
            self.conn.commit()

    def get_field_mapping(self):
        return self.get_setting('field_mapping', DEFAULT_MAPPING)
    
    def set_field_mapping(self, mapping):
        self.set_setting('field_mapping', mapping)
        self.conn.commit()

    def backup_db(self, manual=True):
        try:
            backup_path = self.get_setting('backup_path')
            if not backup_path: return False, "未设置备份目录"
            
            os.makedirs(backup_path, exist_ok=True)
            
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_path, f"label_printer_{timestamp}.db")
            
            # 关闭当前连接，以确保备份文件是最新的
            self.conn.close() 
            shutil.copy2(self.db_name, backup_file)
            # 重新连接
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            
            return True, f"备份成功: {os.path.basename(backup_file)}"
        except Exception as e:
            return False, f"备份失败: {e}"

    def restore_db(self, path):
        try:
            if not os.path.exists(path): return False, "文件不存在"
            self.conn.close()
            try: shutil.move(self.db_name, self.db_name+".old")
            except: pass
            shutil.copy2(path, self.db_name)
            self.conn = sqlite3.connect(self.db_name); self.cursor = self.conn.cursor()
            return True, "恢复成功，请重启"
        except Exception as e: return False, str(e)

    def check_sn_exists(self, sn):
        self.cursor.execute("SELECT id FROM records WHERE sn=?", (sn,))
        return self.cursor.fetchone() is not None

    # --- 核心修改：计数器增加 product_id 参数 ---
    def get_box_counter(self, product_id, rule_id, year, month, repair_level=0):
        # Key格式: P{prod_id}_R{rule_id}_{YYYY}_{MM}_{Repair}
        # 确保每个产品单独计数
        key = f"P{product_id}_R{rule_id}_{year}_{month}_{repair_level}"
        self.cursor.execute("SELECT current_val FROM box_counters WHERE key=?", (key,))
        res = self.cursor.fetchone()
        return res[0] if res else repair_level * 10000 # 初始值

    def increment_box_counter(self, product_id, rule_id, year, month, repair_level=0):
        key = f"P{product_id}_R{rule_id}_{year}_{month}_{repair_level}"
        self.cursor.execute("INSERT OR REPLACE INTO box_counters (key, current_val) VALUES (?, COALESCE((SELECT current_val FROM box_counters WHERE key=?), 0) + 1)", (key, key))
        self.conn.commit()
