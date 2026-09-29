# 需求理解准确率（30 条新需求，用户确认标注，gpt-4o-mini 解析）

- 严格：字段+硬软+值：条件 P/R/F1 = 0.805/0.835/0.82；整条完全正确 11/30；排除 6 条模式受限请求后 F1 0.862，完全正确 11/24
- 忽略硬软：条件 P/R/F1 = 0.858/0.89/0.874；整条完全正确 16/30；排除 6 条模式受限请求后 F1 0.915，完全正确 15/24
- 忽略字段（文本条件按引文位置匹配）：条件 P/R/F1 = 0.885/0.917/0.901；整条完全正确 16/30；排除 6 条模式受限请求后 F1 0.926，完全正确 15/24

- 澄清：应澄清的 5 条中触发 2；不该澄清的 25 条中多问 0
- 出现了不该有的硬条件的请求数：4

## 逐条（严格）

- r01 OK 漏：[] 多：[]
- r02 OK 漏：[] 多：[]
- r03 OK 漏：[] 多：[]
- r04 X 漏：['summer'] 多：[('seniority', 'hard', 'internship')]
- r05 X 漏：['Senior'] 多：[]
- r06 X 漏：['产品经理', '不要外包公司'] 多：[('role_avoid', 'hard', '不要外包公司')]
- r07 OK 漏：[] 多：[]
- r08 X 漏：['prefer a startup'] 多：[('employment_type', 'soft', 'prefer a startup')]
- r09 X 漏：[] 多：[('other', 'hard', 'need visa sponsorship not required')]
- r10 OK 漏：[] 多：[]
- r11 OK 漏：[] 多：[]
- r12 X 漏：['remote or hybrid'] 多：[('remote_mode', 'soft', 'remote or hybrid')]
- r13 OK 漏：[] 多：[]
- r14 X 漏：['PhD level roles'] 多：[('seniority', 'hard', 'PhD level roles'), ('work_region', 'hard', 'Bay Area or remote'), ('remote_mode', 'hard', 'Bay Area or remote')] 禁止的硬条件：['seniority', 'work_region', 'remote_mode']
- r15 X 漏：[] 多：[] 应澄清未澄清
- r16 X 漏：[] 多：[('seniority', 'hard', 'at least 8 years of experience')] 禁止的硬条件：['seniority'] 应澄清未澄清
- r17 X 漏：['evenings'] 多：[('other', 'soft', 'evenings')]
- r18 X 漏：['Machine learning ops'] 多：[('skill', 'hard', 'Machine learning ops'), ('work_region', 'hard', 'Denver or remote')] 禁止的硬条件：['work_region'] 应澄清未澄清
- r19 OK 漏：[] 多：[]
- r20 OK 漏：[] 多：[]
- r21 X 漏：['AI safety'] 多：[('role_focus', 'soft', 'Anything in AI safety')]
- r22 OK 漏：[] 多：[]
- r23 X 漏：['AI 产品或者数据科学方向', '最好能远程一部分'] 多：[('role_focus', 'soft', 'AI 产品或者数据科学方向'), ('work_region', 'hard', '我在纽约'), ('remote_mode', 'soft', '最好能远程一部分')] 禁止的硬条件：['work_region']
- r24 X 漏：['on-site'] 多：[('skill', 'hard', 'Go or Python')]
- r25 X 漏：[] 多：[('remote_mode', 'soft', 'travel is fine')]
- r26 OK 漏：[] 多：[]
- r27 X 漏：['distributed systems', 'Staff engineer or principal engineer'] 多：[('role_focus', 'hard', 'Staff engineer or principal engineer'), ('skill', 'hard', 'distributed systems')]
- r28 X 漏：['data science'] 多：[('role_focus', 'soft', 'data science job')]
- r29 X 漏：['Europe-friendly hours'] 多：[('other', 'soft', 'Europe-friendly hours')]
- r30 X 漏：['in the US'] 多：[]