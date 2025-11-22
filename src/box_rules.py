import datetime
import re # 引入正则模块
from src.database import Database

class BoxRuleEngine:
    def __init__(self, db: Database):
        self.db = db

    def parse_date_code(self, code, dt):
        """处理自定义日期编码"""
        # 年份
        if code == "Y1": return str(dt.year)[-1]
        if code == "Y2": return str(dt.year)[-2:]
        if code == "YYYY": return str(dt.year)
        
        # 月份
        if code == "M1": # 1-9, A, B, C
            m = dt.month
            if m <= 9: return str(m)
            return ['A', 'B', 'C'][m-10]
        if code == "MM": return f"{dt.month:02d}"
        
        # 日期
        if code == "DD": return f"{dt.day:02d}"
        
        return ""

    def generate_box_no(self, rule_id, product_info, repair_level=0):
        """
        product_info: dict (must contain 'id', 'sn4')
        """
        cursor = self.db.conn.cursor()
        cursor.execute("SELECT rule_string FROM box_rules WHERE id=?", (rule_id,))
        res = cursor.fetchone()
        
        # 如果没有规则，返回默认
        if not res: return "NO_RULE", 0
        
        rule_fmt = res[0]
        now = datetime.datetime.now()
        
        # 1. 获取计数
        # 预览时不自增，取 (当前值 + 1)
        pid = product_info.get('id', 0)
        current_seq = self.db.get_box_counter(pid, rule_id, now.year, now.month, repair_level)
        next_seq = current_seq + 1
        
        # 2. 解析规则
        result = rule_fmt
        
        # 替换基础变量
        result = result.replace("{SN4}", str(product_info.get('sn4', '0000')))
        
        # 替换时间变量
        for code in ["YYYY", "Y2", "Y1", "MM", "M1", "DD"]:
            placeholder = f"{{{code}}}"
            if placeholder in result:
                result = result.replace(placeholder, self.parse_date_code(code, now))

        # 3. 替换动态流水号 {SEQn}
        # 使用正则查找所有 {SEQ数字} 的模式
        def seq_replacer(match):
            # 获取括号内的数字，例如 {SEQ3} -> 3
            width = int(match.group(1))
            # 格式化数字，例如 1 -> 001
            return f"{next_seq:0{width}d}"

        # 正则替换：匹配 {SEQ + 数字 + }
        result = re.sub(r"\{SEQ(\d+)\}", seq_replacer, result)

        return result, next_seq

    def commit_sequence(self, rule_id, product_id, repair_level=0):
        """打印成功后提交计数"""
        now = datetime.datetime.now()
        self.db.increment_box_counter(product_id, rule_id, now.year, now.month, repair_level)
