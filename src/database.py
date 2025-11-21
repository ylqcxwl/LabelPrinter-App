import sqlite3
import json
import os
from src.config import DEFAULT_MAPPING

class Database:
    def __init__(self, db_name='label_printer.db'):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_db()

    def setup_db(self):
        # 1. 创建表结构
        # 产品表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                spec TEXT,
                model TEXT,
                color TEXT,
                sn4 TEXT,
                sku TEXT,
                code69 TEXT,
                qty INTEGER,
                weight TEXT,
                template_path TEXT,
                rule_id INTEGER DEFAULT 0
            )
        ''')

        # 箱号规则表 (统一使用 rule_string)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                rule_string TEXT NOT NULL, 
                current_seq INTEGER DEFAULT 0
            )
        ''')
        
        # 打印记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_sn_seq INTEGER,
                name TEXT,
                spec TEXT,
                model TEXT,
                color TEXT,
                code69 TEXT,
                sn TEXT,
                box_no TEXT,
                prod_date TEXT,
                print_date TEXT
            )
        ''')

        # 设置表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')

        # 计数器表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_counters (
                key TEXT PRIMARY KEY,
                current_val INTEGER
            )
        ''')
        
        # 2. 智能修复：检查并补充缺失的字段
        self._check_and_add_column('products', 'rule_id', 'INTEGER DEFAULT 0')
        self._check_and_add_column('box_rules', 'rule_string', 'TEXT')
        
        # 3. 初始化默认设置
        default_mapping_json = json.dumps(DEFAULT_MAPPING)
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('field_mapping', ?)", (default_mapping_json,))
        
        self.conn.commit()

    def _check_and_add_column(self, table_name, column_name, column_type):
        """安全地检查并添加列"""
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in self.cursor.fetchall()]
            if column_name not in columns:
                print(f"Migrating: Adding {column_name} to {table_name}")
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        except Exception as e:
            print(f"Migration error for {table_name}.{column_name}: {e}")

    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = self.cursor.fetchone()
        if result:
            if key == 'field_mapping':
                try:
                    return json.loads(result[0])
                except:
                    return DEFAULT_MAPPING
            return result[0]
        return None

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def check_sn_exists(self, sn):
        # 检查记录表中是否存在 (防止重复打印)
        self.cursor.execute("SELECT id FROM records WHERE sn=?", (sn,))
        return self.cursor.fetchone() is not None

    def get_box_counter(self, rule_id, year, month, repair_level=0):
        key = f"{rule_id}_{year}_{month}_{repair_level}"
        self.cursor.execute("SELECT current_val FROM box_counters WHERE key=?", (key,))
        res = self.cursor.fetchone()
        if res:
            return res[0]
        return repair_level * 10000 # 默认初始值

    def increment_box_counter(self, rule_id, year, month, repair_level=0):
        key = f"{rule_id}_{year}_{month}_{repair_level}"
        current = self.get_box_counter(rule_id, year, month, repair_level)
        new_val = current + 1
        self.cursor.execute("INSERT OR REPLACE INTO box_counters (key, current_val) VALUES (?, ?)", (key, new_val))
        self.conn.commit()
        return new_val

    def close(self):
        self.conn.close()
