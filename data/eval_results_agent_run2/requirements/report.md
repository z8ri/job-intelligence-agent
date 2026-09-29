# 需求理解准确率（30 条新需求，用户确认标注，gpt-4o-mini 解析）

- 严格：字段+硬软+值：条件 P/R/F1 = 0.696/0.741/0.717；整条完全正确 3/30；排除 7 条模式受限请求后 F1 0.765，完全正确 3/23
- 忽略硬软：条件 P/R/F1 = 0.73/0.778/0.753；整条完全正确 3/30；排除 7 条模式受限请求后 F1 0.787，完全正确 3/23
- 忽略字段（文本条件按引文位置匹配）：条件 P/R/F1 = 0.783/0.833/0.807；整条完全正确 7/30；排除 7 条模式受限请求后 F1 0.831，完全正确 7/23

- 澄清：应澄清的 5 条中触发 0；不该澄清的 25 条中多问 0
- 出现了不该有的硬条件的请求数：4

## 逐条（严格）

- r01 OK 漏：[] 多：[]
- r02 X 漏：['no agencies'] 多：[('role_avoid', 'hard', 'no agencies please')]
- r03 X 漏：[] 多：[('remote_mode', 'soft', 'hybrid is fine')]
- r04 X 漏：['summer'] 多：[('seniority', 'hard', 'summer internship')]
- r05 X 漏：['Senior', 'ideally remote'] 多：[('remote_mode', 'soft', 'ideally remote')]
- r06 X 漏：['不要外包公司'] 多：[('role_avoid', 'soft', '不要外包公司')]
- r07 X 漏：['Pacific time zone'] 多：[('work_region', 'hard', 'Pacific time zone')]
- r08 X 漏：['prefer a startup'] 多：[('employment_type', 'soft', 'prefer a startup')]
- r09 X 漏：[] 多：[('other', 'hard', 'need visa sponsorship not required')]
- r10 X 漏：['$70 per hour minimum'] 多：[('salary', 'hard', '$70 per hour minimum')]
- r11 X 漏：[] 多：[('role_avoid', 'soft', 'clearance not a problem')]
- r12 X 漏：['Android', 'Kotlin', 'remote or hybrid'] 多：[('remote_mode', 'soft', 'remote or hybrid')]
- r13 OK 漏：[] 多：[]
- r14 X 漏：['PhD level roles'] 多：[('seniority', 'hard', 'PhD level roles'), ('work_region', 'hard', 'Bay Area or remote'), ('remote_mode', 'soft', 'remote')] 禁止的硬条件：['seniority', 'work_region'] 应澄清未澄清
- r15 X 漏：[] 多：[('other', 'soft', 'Something in tech that pays well')] 应澄清未澄清
- r16 X 漏：[] 多：[('seniority', 'hard', 'at least 8 years of experience')] 禁止的硬条件：['seniority'] 应澄清未澄清
- r17 X 漏：['evenings'] 多：[('remote_mode', 'hard', 'evenings')]
- r18 X 漏：['Machine learning ops'] 多：[('skill', 'hard', 'Machine learning ops'), ('work_region', 'soft', 'Denver or remote')] 应澄清未澄清
- r19 X 漏：['no crunch culture'] 多：[('role_avoid', 'hard', 'no crunch culture')]
- r20 OK 漏：[] 多：[]
- r21 X 漏：['AI safety'] 多：[('role_focus', 'soft', 'Anything in AI safety'), ('work_region', 'hard', 'I can work in the UK or EU'), ('salary', 'soft', 'salary is not important')] 禁止的硬条件：['work_region']
- r22 X 漏：['no on-call rotations'] 多：[('remote_mode', 'soft', 'no on-call rotations')]
- r23 X 漏：['AI 产品或者数据科学方向', '最好能远程一部分'] 多：[('role_focus', 'soft', 'AI 产品或者数据科学方向'), ('work_region', 'hard', '我在纽约'), ('remote_mode', 'soft', '最好能远程一部分')] 禁止的硬条件：['work_region']
- r24 X 漏：['Boston'] 多：[]
- r25 X 漏：['for a developer-tools company'] 多：[('remote_mode', 'soft', 'travel is fine')]
- r26 X 漏：['ideally with training provided'] 多：[('role_focus', 'soft', 'ideally with training provided')]
- r27 X 漏：['distributed systems', 'Staff engineer or principal engineer'] 多：[('role_focus', 'hard', 'Staff engineer or principal engineer'), ('skill', 'hard', 'distributed systems')]
- r28 X 漏：['data science'] 多：[('role_focus', 'soft', 'data science job'), ('seniority', 'soft', 'whatever seniority')] 应澄清未澄清
- r29 X 漏：['Europe-friendly hours'] 多：[('work_region', 'soft', 'Europe-friendly hours')]
- r30 X 漏：['in the US', 'clearly state a salary range'] 多：[('salary', 'hard', 'clearly state a salary range')]