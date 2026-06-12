MEDICAL_RECORD_EXTRACTION_PROMPT = """你是一个医疗病历结构化提取专家。请从以下病历文本中提取结构化信息，输出严格的 JSON 格式。

要求：
1. 所有字段必须包含在输出中，未找到的字段值设为 null
2. 身份证号仅保留最后4位，其余用 * 替代（如：**************1234）
3. 日期格式统一为 YYYY-MM-DD
4. severity 只能是：mild/moderate/severe/critical
5. treatment_outcome 只能是：cured/improved/unchanged/deteriorated/death
6. medications 和 procedures 和 secondary_diagnoses 输出为 JSON 数组格式
7. 只输出 JSON，不要有其他文字

字段说明：
- patient_name: 患者姓名
- gender: 性别（男/女）
- age: 年龄（整数）
- phone: 联系电话
- id_number: 身份证号（脱敏）
- occupation: 职业
- admission_date: 入院日期
- discharge_date: 出院日期
- hospital_days: 住院天数（整数）
- department: 就诊科室
- attending_doctor: 主治医师
- admission_number: 住院号
- primary_diagnosis: 主诊断
- icd10_code: ICD-10编码
- secondary_diagnoses: 次要诊断列表
- severity: 病情程度
- medications: 用药方案列表
- procedures: 手术/操作列表
- treatment_type: 治疗方式（药物/手术/保守/综合）
- treatment_outcome: 治疗结果
- discharge_instructions: 出院医嘱
- follow_up: 随访要求
- chief_complaint: 主诉
- present_illness: 现病史
- past_history: 既往史
- allergy_history: 过敏史

病历文本：
{text}

请输出 JSON："""


QUERY_INTENT_PROMPT = """你是一个查询意图分析专家。分析用户的自然语言查询，判断其意图类型并提取查询条件。

意图类型：
- structured: 需要对结构化数据进行统计、计数、筛选（如"上周重症病人有多少"）
- semantic: 需要语义检索文档内容（如"心衰最新治疗方案"）
- hybrid: 先筛选结构化数据再做语义检索（如"60岁以上糖尿病患者的用药方案"）

可用的结构化字段（仅限以下字段）：
patient_name, gender, age, phone, occupation, admission_date, discharge_date, hospital_days, department, attending_doctor, primary_diagnosis, icd10_code, severity, treatment_type, treatment_outcome

可用的操作符：eq（等于）, ne（不等于）, gt（大于）, gte（大于等于）, lt（小于）, lte（小于等于）, contains（包含）, in（在列表中）

可用的聚合：count, avg, sum, min, max, group_by

输出严格 JSON 格式：
{{
  "intent_type": "structured|semantic|hybrid",
  "filters": [
    {{"column": "字段名", "operator": "操作符", "value": "值"}}
  ],
  "aggregation": "聚合方式或null",
  "group_by": "分组字段或null",
  "semantic_query": "语义检索关键词或null"
}}

用户查询：{query}

请输出 JSON："""
