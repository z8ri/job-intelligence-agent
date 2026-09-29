# 需求理解准确率（24 条需求，标注文件 requirements_heldout.json，gpt-4o-mini 解析）

- 严格：字段+硬软+值：条件 P/R/F1 = 0.767/0.805/0.786；整条完全正确 6/24；排除 7 条模式受限请求后 F1 0.803，完全正确 5/17
- 忽略硬软：条件 P/R/F1 = 0.791/0.829/0.81；整条完全正确 6/24；排除 7 条模式受限请求后 F1 0.833，完全正确 5/17
- 忽略字段（文本条件按引文位置匹配）：条件 P/R/F1 = 0.814/0.854/0.833；整条完全正确 7/24；排除 7 条模式受限请求后 F1 0.864，完全正确 6/17

- 澄清：应澄清的 5 条中触发 2；不该澄清的 19 条中多问 1
- 出现了不该有的硬条件的请求数：2

## 逐条（严格）

- h01 OK 漏：[] 多：[]
- h02 OK 漏：[] 多：[]
- h03 X 漏：[] 多：[('role_focus', 'hard', '推荐系统')]
- h04 X 漏：['Senior'] 多：[('work_region', 'hard', 'Austin or fully remote'), ('remote_mode', 'hard', 'fully remote')] 禁止的硬条件：['work_region', 'remote_mode']
- h05 X 漏：['B2B SaaS company'] 多：[]
- h06 X 漏：['Junior', 'work from home most days'] 多：[('remote_mode', 'soft', 'I would like to work from home most days')]
- h07 X 漏：['PhD preferred'] 多：[('skill', 'hard', 'reinforcement learning'), ('seniority', 'soft', 'PhD preferred')]
- h08 X 漏：['technical recruiter'] 多：[]
- h09 OK 漏：[] 多：[]
- h10 X 漏：['not the west coast'] 多：[('work_region', 'hard', 'not the west coast')]
- h11 X 漏：['Rust'] 多：[]
- h12 OK 漏：[] 多：[]
- h13 OK 漏：[] 多：[]
- h14 X 漏：[] 多：[('role_focus', 'hard', 'pre-sales'), ('remote_mode', 'soft', 'Boston or New York')]
- h15 X 漏：['hybrid'] 多：[('employment_type', 'hard', 'hybrid'), ('remote_mode', 'soft', 'hybrid')]
- h16 X 漏：['Staff', 'in the US', 'not interested in consulting firms'] 多：[('other', 'hard', 'not interested in consulting firms')]
- h17 X 漏：[] 多：[] 应澄清未澄清
- h18 OK 漏：[] 多：[]
- h19 X 漏：[] 多：[('remote_mode', 'soft', 'willing to relocate from Toronto')]
- h20 X 漏：['only speak English and Spanish'] 多：[('skill', 'hard', 'I only speak English and Spanish')]
- h21 X 漏：['Kubernetes'] 多：[]
- h22 X 漏：[] 多：[('work_region', 'hard', 'London, anything above $200k, or Zurich'), ('salary', 'hard', 'anything above $200k, or Zurich at 250k'), ('salary', 'hard', 'Zurich at 250k')] 禁止的硬条件：['work_region', 'salary', 'salary'] 应澄清未澄清
- h23 X 漏：[] 多：[('skill', 'hard', 'Selenium or Cypress')] 应澄清未澄清
- h24 X 漏：['generalist full-stack', 'Startup'] 多：[('role_focus', 'hard', 'Startup engineer'), ('employment_type', 'hard', 'full-stack')]