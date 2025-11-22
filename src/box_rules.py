import datetime
from src.database import Database

class BoxRuleEngine:
    def __init__(self, db: Database):
        self.db = db

    def parse_date_code(self, code, dt):
        if code == "Y1": return str(dt.year)[-1]
        if code == "Y2": return str(dt.year)[-2:]
        if code == "M1":
            m = dt.month
            if m <= 9: return str(m)
            return ['A', 'B', 'C'][m-10]
        if code == "MM": return f"{dt.month:02d}"
        if code == "DD": return f"{dt.day:02d}"
        return ""

    def generate_box_no(self, rule_id, product_info, repair_level=0):
        """
        product_info 必须包含 'id' 和 'sn4'
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT rule_string FROM box_rules WHERE id=?", (rule_id,))
        res = cursor.fetchone()
        if not res: return "DEFAULT_BOX", 0
        
        rule_fmt = res[0]
        now = datetime.datetime.now()
        
        # 获取当前产品、当前月的计数 (预览不自增，取当前值+1)
        pid = product_info.get('id', 0)
        current_seq = self.db.get_box_counter(pid, rule_id, now.year, now.month, repair_level)
        next_seq = current_seq + 1
        
        result = rule_fmt
        result = result.replace("{SN4}", str(product_info.get('sn4', '0000')))
        result = result.replace("{Y1}", self.parse_date_code("Y1", now))
        result = result.replace("{Y2}", self.parse_date_code("Y2", now))
        result = result.replace("{M1}", self.parse_date_code("M1", now))
        result = result.replace("{MM}", self.parse_date_code("MM", now))
        result = result.replace("{DD}", self.parse_date_code("DD", now))
        result = result.replace("{SEQ5}", f"{next_seq:05d}")

        return result, next_seq

    def commit_sequence(self, rule_id, product_id, repair_level=0):
        now = datetime.datetime.now()
        self.db.increment_box_counter(product_id, rule_id, now.year, now.month, repair_level)
