import datetime
from src.database import Database

class BoxRuleEngine:
    def __init__(self, db: Database):
        self.db = db

    def parse_date_code(self, code, dt):
        """处理自定义日期编码"""
        # 年份最后一位
        if code == "Y1": return str(dt.year)[-1]
        # 月份 1-9, A, B, C
        if code == "M1":
            m = dt.month
            if m <= 9: return str(m)
            return ['A', 'B', 'C'][m-10]
        # 日期
        if code == "DD": return f"{dt.day:02d}"
        return ""

    def generate_box_no(self, rule_id, product_info, repair_level=0):
        """
        product_info: dict containing 'sn4', etc.
        rule_string example: "MZXH{SN4}{Y1}{M1}{SEQ5}2{DD}"
        """
        # 获取规则字符串
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT rule_string FROM box_rules WHERE id=?", (rule_id,))
        res = cursor.fetchone()
        if not res:
            return "DEFAULT001" # Fallback
        
        rule_fmt = res[0]
        now = datetime.datetime.now()
        
        # 1. 获取流水号
        # 逻辑：每月清零。如果repair_level=0, 从00001开始; =1, 从10001开始
        # 这里我们先不自增，只预览，真正打印时才自增。
        # 但为了简化逻辑，我们在生成时获取当前值+1作为预览
        
        current_seq = self.db.get_box_counter(rule_id, now.year, now.month, repair_level)
        next_seq = current_seq + 1
        
        # 2. 解析规则
        # 简单解析器，替换 {} 内容
        
        result = rule_fmt
        
        # 替换 SN4
        if "{SN4}" in result:
            result = result.replace("{SN4}", str(product_info.get('sn4', '0000')))
            
        # 替换 Y1 (年份最后一位)
        if "{Y1}" in result:
            result = result.replace("{Y1}", self.parse_date_code("Y1", now))

        # 替换 Y2 (年份后两位)
        if "{Y2}" in result:
            result = result.replace("{Y2}", str(now.year)[-2:])
            
        # 替换 M1 (月份代码)
        if "{M1}" in result:
            result = result.replace("{M1}", self.parse_date_code("M1", now))
            
        # 替换 MM (月份两位)
        if "{MM}" in result:
            result = result.replace("{MM}", f"{now.month:02d}")
            
        # 替换 DD (日期)
        if "{DD}" in result:
            result = result.replace("{DD}", f"{now.day:02d}")

        # 替换 SEQ5 (5位流水号)
        if "{SEQ5}" in result:
            result = result.replace("{SEQ5}", f"{next_seq:05d}")

        return result, next_seq

    def commit_sequence(self, rule_id, repair_level=0):
        now = datetime.datetime.now()
        self.db.increment_box_counter(rule_id, now.year, now.month, repair_level)
