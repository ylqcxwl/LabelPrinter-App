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
        # --- 表结构定义 ---
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL, 
                spec TEXT, model TEXT, color TEXT,
                sn4 TEXT NOT NULL UNIQUE, 
                sku TEXT, code69 TEXT,
                qty INTEGER, weight TEXT,
                template_path TEXT,
                rule_id INTEGER DEFAULT 0,
                sn_rule_id INTEGER DEFAULT 0
            )
        ''')
        
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS box_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                rule_string TEXT NOT NULL, 
                current_seq INTEGER DEFAULT 0
            )
        ''')
        
        # 新增：SN规则表
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS sn_rules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                rule_string TEXT NOT NULL,
                length INTEGER DEFAULT 0
            )
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                box_sn_seq INTEGER, name TEXT, spec TEXT, model TEXT, color TEXT,
                code69 TEXT, sn TEXT, box_no TEXT, prod_date TEXT, print_date TEXT
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
        
        # 补充字段检查
        self._check_and_add_column('products', 'rule_id', 'INTEGER DEFAULT 0')
        self._check_and_add_column('products', 'sn_rule_id', 'INTEGER DEFAULT 0') # 新增
        self._check_and_add_column('box_rules', 'rule_string', 'TEXT')
        
        # 初始化设置
        default_mapping_json = json.dumps(DEFAULT_MAPPING)
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('field_mapping', ?)", (default_mapping_json,))
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('backup_path', ?)", (os.path.abspath("./backups"),))
        
        default_tmpl_root = os.path.abspath("./templates")
        if not os.path.exists(default_tmpl_root): os.makedirs(default_tmpl_root, exist_ok=True)
        self.cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('template_root', ?)", (default_tmpl_root,))
        
        self.conn.commit()

    def _check_and_add_column(self, table_name, column_name, column_type):
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [info[1] for info in self.cursor.fetchall()]
            if column_name not in columns:
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        except: pass

    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        result = self.cursor.fetchone()
        if result:
            if key == 'field_mapping':
                try: return json.loads(result[0])
                except: return DEFAULT_MAPPING
            return result[0]
        return None

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    # --- 备份恢复 ---
    def backup_db(self, custom_path=None):
        try:
            target_dir = custom_path if custom_path else self.get_setting('backup_path')
            if not os.path.exists(target_dir):
                os.makedirs(target_dir)
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(target_dir, f"backup_{timestamp}.db")
            self.conn.commit()
            shutil.copy2(self.db_name, backup_file)
            return True, f"备份成功: {backup_file}"
        except Exception as e:
            return False, str(e)

    def restore_db(self, backup_file_path):
        try:
            if not os.path.exists(backup_file_path):
                return False, "备份文件不存在"
            self.conn.close()
            try: shutil.move(self.db_name, self.db_name + ".old")
            except: pass 
            shutil.copy2(backup_file_path, self.db_name)
            self.conn = sqlite3.connect(self.db_name)
            self.cursor = self.conn.cursor()
            return True, "数据恢复成功，请重启软件。"
        except Exception as e:
            return False, f"恢复失败: {e}"

    # --- 辅助 ---
    def check_sn_exists(self, sn):
        self.cursor.execute("SELECT id FROM records WHERE sn=?", (sn,))
        return self.cursor.fetchone() is not None

    def get_box_counter(self, rule_id, year, month, repair_level=0):
        key = f"{rule_id}_{year}_{month}_{repair_level}"
        self.cursor.execute("SELECT current_val FROM box_counters WHERE key=?", (key,))
        res = self.cursor.fetchone()
        return res[0] if res else repair_level * 10000

    def increment_box_counter(self, rule_id, year, month, repair_level=0):
        key = f"{rule_id}_{year}_{month}_{repair_level}"
        current = self.get_box_counter(rule_id, year, month, repair_level)
        new_val = current + 1
        self.cursor.execute("INSERT OR REPLACE INTO box_counters (key, current_val) VALUES (?, ?)", (key, new_val))
        self.conn.commit()
        return new_val

    def close(self):
        self.conn.close()
