import sqlite3
import json
import os
from src.config import DEFAULT_MAPPING # 假设 DEFAULT_MAPPING 定义在 src/config.py

class Database:
    def __init__(self, db_name='db.sqlite3'):
        self.db_name = db_name
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.setup_db()

    def setup_db(self):
        # 1. 创建产品表 (确保 rule_id 存在)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY,
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
                rule_id INTEGER -- 箱号规则ID
            )
        ''')

        # 2. 创建箱号规则表 (确保 format 存在)
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_rules (
                id INTEGER PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                format TEXT NOT NULL,
                current_seq INTEGER DEFAULT 0,
                reset_date TEXT
            )
        ''')
        
        # 3. 【兼容性修复/数据库迁移】
        # 检查并添加缺失的 'format' 字段 (解决 'no such column: format' 错误)
        try:
            # 尝试访问 'format' 字段，如果失败则触发 except
            self.cursor.execute("SELECT format FROM box_rules LIMIT 1")
        except sqlite3.OperationalError:
            print("Database Migration: Adding 'format' column to box_rules table.")
            try:
                # 执行 ALTER TABLE 命令添加缺失的列
                self.cursor.execute("ALTER TABLE box_rules ADD COLUMN format TEXT")
                self.conn.commit()
            except sqlite3.OperationalError as e:
                # 如果还有其他旧版本遗留的缺失列，在此处处理 (例如 rule_id)
                if 'no such column: rule_id' in str(e):
                    self.cursor.execute("ALTER TABLE products ADD COLUMN rule_id INTEGER")
                    self.conn.commit()
                else:
                    raise e # 抛出其他意外错误
            
        # 4. 创建打印记录表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY,
                box_sn_seq INTEGER,
                name TEXT,
                spec TEXT,
                model TEXT,
                color TEXT,
                code69 TEXT,
                sn TEXT UNIQUE, -- SN必须唯一
                box_no TEXT,
                prod_date TEXT,
                print_date TEXT
            )
        ''')

        # 5. 创建设置表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # 6. 插入默认设置
        default_mapping_json = json.dumps(DEFAULT_MAPPING)
        self.cursor.execute(f'''
            INSERT OR IGNORE INTO settings (key, value) VALUES ('field_mapping', ?)
        ''', (default_mapping_json,))
        
        self.conn.commit()

    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = self.cursor.fetchone()
        if result:
            if key == 'field_mapping':
                try:
                    return json.loads(result[0])
                except json.JSONDecodeError:
                    # 如果JSON解析失败，返回默认值
                    return DEFAULT_MAPPING
            return result[0]
        return None

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def check_sn_exists(self, sn):
        self.cursor.execute("SELECT COUNT(*) FROM records WHERE sn=?", (sn,))
        return self.cursor.fetchone()[0] > 0

    def close(self):
        self.conn.close()
