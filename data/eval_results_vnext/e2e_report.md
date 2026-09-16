# 端到端回答质量评估报告 (§7.6)

- 查询数：**20** 条（从 40 条 test_queries 中挑选，覆盖 7 类别 + 多字段组合 + 硬过滤）
- 数据源：HN + Greenhouse 双源 2311 条 (2026-04-23)
- 打分者：**gpt-4o-mini (single)** 单评分员自动评分（选项 B，成本 $0.02）
- 三维定义：Relevance（职位是否匹配查询核心约束）/ Completeness（答案是否覆盖查询涉及字段且解释每个 pick）/ Readability（结构与可读性）

## 三维总评（单评分员 macro mean）

| 维度 | Macro mean (1-5) | 分布 |
|---|---|---|
| relevance | 3.55 | 2:3, 3:3, 4:14 |
| completeness | 4.1 | 3:3, 4:12, 5:5 |
| readability | 4.3 | 3:2, 4:10, 5:8 |

> 本节采用单评分员（gpt-4o-mini）自动评分，不计算 ICC / Cronbach α。

## 每条 query 明细

| query_id | query | relevance | completeness | readability | 平均 |
|---|---|---|---|---|---|
| q01 | Remote Python backend jobs above 150k | 4 | 5 | 5 | 4.67 |
| q05 | Data science positions around 130k to 16... | 4 | 4 | 5 | 4.33 |
| q07 | Positions near Boston for backend develo... | 2 | 3 | 4 | 3.0 |
| q11 | Fully remote senior engineering roles | 4 | 4 | 4 | 4.0 |
| q14 | 100% remote data engineering jobs | 4 | 4 | 4 | 4.0 |
| q15 | React and TypeScript frontend developer ... | 4 | 5 | 5 | 4.67 |
| q16 | Kubernetes and Terraform DevOps engineer | 4 | 4 | 4 | 4.0 |
| q20 | Mobile development jobs with Flutter or ... | 4 | 4 | 4 | 4.0 |
| q22 | Engineering manager or tech lead opening... | 4 | 4 | 4 | 4.0 |
| q25 | Site reliability engineer SRE jobs | 4 | 5 | 5 | 4.67 |
| q26 | Remote ML jobs in New York above 130k | 4 | 4 | 5 | 4.33 |
| q27 | Backend Go developer, hybrid, 160k or mo... | 3 | 4 | 4 | 3.67 |
| q28 | Full stack JavaScript developer in San F... | 4 | 5 | 5 | 4.67 |
| q29 | Senior data engineer with Spark and Kafk... | 2 | 3 | 3 | 2.67 |
| q30 | React frontend roles in Chicago or nearb... | 3 | 4 | 3 | 3.33 |
| q31 | DevOps with AWS and Docker in Austin, hy... | 2 | 3 | 4 | 3.0 |
| q32 | Remote Python or Java backend, good sala... | 4 | 5 | 5 | 4.67 |
| q33 | Management positions in Denver or Boulde... | 3 | 4 | 4 | 3.67 |
| q34 | Companies with good culture for junior d... | 4 | 4 | 4 | 4.0 |
| q35 | Fast-paced startup environment with equi... | 4 | 4 | 5 | 4.33 |
