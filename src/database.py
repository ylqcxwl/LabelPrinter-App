import sqlite3
import json
import shutil
import os
import datetime
from src.config import DEFAULT_MAPPING

class Database:
    def __init__(self, db_name='label_printer.db'):
        self.db_name = os.path.abspath(db_name)
        self.conn = sqlite3.connect(self.db_name, check_same_thread=False) # 允许跨线程使用连接（需谨慎）
        
        # --- 性能优化：开启 WAL 模式 ---
        # Write-Ahead Logging 模式，极大提高并发读写速度，防止UI卡顿
        try:
            self.conn.execute("PRAGMA journal_mode=WAL;")
            self.conn.execute("PRAGMA synchronous=NORMAL;")
        except:
            pass
            
        self.cursor = self.conn.cursor()
        self.setup_db()

    def setup_db(self):
        # 表结构定义
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
                box_sn_seq INTEGER, name TEXT, spec TEXT, model TEXT, color TEXT,
                code69 TEXT, sn TEXT, box_no TEXT, prod_date TEXT, print_date TEXT
            )
        ''')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)')
        self.cursor.execute('CREATE TABLE IF NOT EXISTS box_counters (key TEXT PRIMARY KEY, current_val INTEGER)')
        
        # --- 性能优化：创建索引 ---
        # 为常用查询字段创建索引，防止数据量大时查询变慢
        index_queries = [
            "CREATE INDEX IF NOT EXISTS idx_records_sn ON records (sn)",
            "CREATE INDEX IF NOT EXISTS idx_records_box_no ON records (box_no)",
            "CREATE INDEX IF NOT EXISTS idx_records_print_date ON records (print_date)",
            "CREATE INDEX IF NOT EXISTS idx_records_name ON records (name)",
            "CREATE INDEX IF NOT EXISTS idx_products_name ON products (name)",
            "CREATE INDEX IF NOT EXISTS idx_products_code69 ON products (code69)"
        ]
        for q in index_queries:
            self.cursor.execute(q)

        # 字段检查补全
        self._check_and_add_column('products', 'rule_id', 'INTEGER DEFAULT 0')
        self._check_and_add_column('products', 'sn_rule_id', 'INTEGER DEFAULT 0')
        self._check_and_add_column('box_rules', 'rule_string', 'TEXT')
        
        # 初始化默认设置
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
            if column_name not in [i[1] for i in self.cursor.fetchall()]:
                self.cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}")
        except: pass

    def get_setting(self, key):
        self.cursor.execute("SELECT value FROM settings WHERE key=?", (key,))
        r = self.cursor.fetchone()
        if r and key == 'field_mapping':
            try: return json.loads(r[0])
            except: return DEFAULT_MAPPING
        return r[0] if r else None

    def set_setting(self, key, value):
        self.cursor.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
        self.conn.commit()

    def backup_db(self, custom_path=None, manual=True):
        try:
            td = custom_path if custom_path else self.get_setting('backup_path')
            if not os.path.exists(td): os.makedirs(td)
            
            # 自动备份时，如果今天已经备份过，可以跳过（可选逻辑，这里暂保留每次启动备份）
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            f = os.path.join(td, f"backup_{ts}.db")
            
            # 必须先 commit 确保 WAL 数据写入文件
            self.conn.commit()
            
            # 使用 SQLite 专用的备份 API，比 shutil.copy 更安全
            bck = sqlite3.connect(f)
            self.conn.backup(bck)
            bck.close()
            
            return True, f"备份成功: {f}"
        except Exception as e: return False, str(e)

    def restore_db(self, path):
        try:
            if not os.path.exists(path): return False, "文件不存在"
            self.conn.close()
            try: shutil.move(self.db_name, self.db_name+".old")
            except: pass
            shutil.copy2(path, self.db_name)
            self.conn = sqlite3.connect(self.db_name)
            
            # 恢复后重新设置 WAL
            try: self.conn.execute("PRAGMA journal_mode=WAL;")
            except: pass
            
            self.cursor = self.conn.cursor()
            return True, "恢复成功，请重启"
        except Exception as e: return False, str(e)

    def check_sn_exists(self, sn):
        # 优化查询：利用索引并限制返回1条
        self.cursor.execute("SELECT 1 FROM records WHERE sn=? LIMIT 1", (sn,))
        return self.cursor.fetchone() is not None

    def get_box_counter(self, product_id, rule_id, year, month, repair_level=0):
        key = f"P{product_id}_R{rule_id}_{year}_{month}_{repair_level}"
        self.cursor.execute("SELECT current_val FROM box_counters WHERE key=?", (key,))
        res = self.cursor.fetchone()
        return res[0] if res else repair_level * 10000 

    def increment_box_counter(self, product_id, rule_id, year, month, repair_level=0):
        key = f"P{product_id}_R{rule_id}_{year}_{month}_{repair_level}"
        current = self.get_box_counter(product_id, rule_id, year, month, repair_level)
        new_val = current + 1
        self.cursor.execute("INSERT OR REPLACE INTO box_counters (key, current_val) VALUES (?, ?)", (key, new_val))
        self.conn.commit()
        return new_val

    def close(self):
        self.conn.close()
