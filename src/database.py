import sqlite3
import json
from datetime import datetime
from src.config import DB_NAME, DEFAULT_MAPPING

class Database:
    def __init__(self):
        self.conn = sqlite3.connect(DB_NAME)
        self.cursor = self.conn.cursor()
        self.init_tables()

    def init_tables(self):
        # 产品表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT, spec TEXT, model TEXT, color TEXT,
                sn4 TEXT, sku TEXT, code69 TEXT,
                qty INTEGER, weight TEXT,
                template_path TEXT, rule_id INTEGER
            )
        ''')
        
        # 打印记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_sn_seq INTEGER, -- 箱内序号 1-12
                name TEXT, spec TEXT, model TEXT, color TEXT,
                code69 TEXT, sn TEXT UNIQUE,
                box_no TEXT,
                prod_date TEXT,
                print_date TEXT
            )
        ''')

        # 箱号计数器 (用于生成规则)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_counters (
                key TEXT PRIMARY KEY, -- 格式 rule_id_YYYY_MM
                current_val INTEGER
            )
        ''')

        # 设置表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # 箱号规则表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                rule_string TEXT
            )
        ''')

        # 初始化默认设置
        self._init_default_settings()
        self.conn.commit()

    def _init_default_settings(self):
        # 检查并插入字段映射
        self.cursor.execute("SELECT value FROM settings WHERE key='field_mapping'")
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?)", 
                                ('field_mapping', json.dumps(DEFAULT_MAPPING)))

    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        res = self.cursor.fetchone()
        return json.loads(res[0]) if res else None

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", 
                            (key, json.dumps(value)))
        self.conn.commit()

    def get_box_counter(self, rule_id, year, month, repair_level=0):
        # repair_level: 0=正常, 1=一修, 2=二修
        key = f"{rule_id}_{year}_{month}_{repair_level}"
        self.cursor.execute("SELECT current_val FROM box_counters WHERE key=?", (key,))
        res = self.cursor.fetchone()
        if res:
            return res[0]
        else:
            # 初始值 logic based on repair level
            start_val = repair_level * 10000
            return start_val

    def increment_box_counter(self, rule_id, year, month, repair_level=0):
        key = f"{rule_id}_{year}_{month}_{repair_level}"
        current = self.get_box_counter(rule_id, year, month, repair_level)
        new_val = current + 1
        self.cursor.execute("INSERT OR REPLACE INTO box_counters (key, current_val) VALUES (?, ?)", (key, new_val))
        self.conn.commit()
        return new_val

    def check_sn_exists(self, sn):
        self.cursor.execute("SELECT id FROM records WHERE sn=?", (sn,))
        return self.cursor.fetchone() is not None

    def close(self):
        self.conn.close()
