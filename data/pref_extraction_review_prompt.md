# Job Query Preference Extraction Task (Evaluation Set)

You are helping to evaluate a job-search system's query understanding module. For each user query below, independently extract a structured preference JSON following the schema and examples below. Do NOT look at or refer to any system-provided answer — your job is to produce your own best-effort extraction.

## Schema


You are a job search query understanding assistant. Extract structured preferences from the user's natural language query.

Output a JSON object with these fields (set to null if not mentioned):

- description_keywords: list of keywords describing the desired role/responsibilities (e.g. ["machine learning", "distributed systems"])
- target_salary: target annual salary as integer in USD (e.g. 150000)
- preferred_location: preferred work location as a city/region string (e.g. "New York")
- remote_preference: one of "remote", "hybrid", "onsite", or null
- desired_tags: list of desired technology/skill tags (e.g. ["Python", "AWS", "React"])
- preferred_category: one of "backend", "frontend", "data", "devops", "fullstack", "mobile", "management", or null
- weight_adjustments: dict mapping field names to importance level ("high", "medium", "low") for fields the user emphasizes. Only include fields the user explicitly cares about more or less than usual.
- hard_filters: list of absolute constraints that MUST be met (e.g. [{"field": "degree_req", "exclude": ["phd", "master"]}]). Use sparingly — only for deal-breakers like degree requirements.

Output ONLY valid JSON. No explanation, no markdown fences.


## Examples

**Example 1**
- Query: `Remote Python jobs above 150k`
- Output:
```json
{"description_keywords": null, "target_salary": 150000, "preferred_location": null, "remote_preference": "remote", "desired_tags": ["Python"], "preferred_category": null, "weight_adjustments": {"salary": "high", "remote": "high"}, "hard_filters": []}
```

**Example 2**
- Query: `ML roles near New York, ideally over 120k`
- Output:
```json
{"description_keywords": ["machine learning"], "target_salary": 120000, "preferred_location": "New York", "remote_preference": null, "desired_tags": ["Machine Learning"], "preferred_category": "data", "weight_adjustments": {"location": "high", "salary": "medium"}, "hard_filters": []}
```

**Example 3**
- Query: `Junior dev positions, no PhD required`
- Output:
```json
{"description_keywords": ["junior", "entry level"], "target_salary": null, "preferred_location": null, "remote_preference": null, "desired_tags": null, "preferred_category": null, "weight_adjustments": {}, "hard_filters": [{"field": "degree_req", "exclude": ["phd"]}]}
```

**Example 4**
- Query: `Senior backend engineer in San Francisco, React and Node.js, hybrid preferred, around 180k`
- Output:
```json
{"description_keywords": ["senior", "backend engineer"], "target_salary": 180000, "preferred_location": "San Francisco", "remote_preference": "hybrid", "desired_tags": ["React", "Node.js"], "preferred_category": "backend", "weight_adjustments": {}, "hard_filters": []}
```

**Example 5**
- Query: `Data engineering jobs with Spark and Kafka, salary doesn't matter much but must be remote`
- Output:
```json
{"description_keywords": ["data engineering"], "target_salary": null, "preferred_location": null, "remote_preference": "remote", "desired_tags": ["Spark", "Kafka"], "preferred_category": "data", "weight_adjustments": {"remote": "high", "salary": "low"}, "hard_filters": []}
```

**Example 6**
- Query: `Frontend developer roles, React or Vue, anywhere in Texas`
- Output:
```json
{"description_keywords": ["frontend developer"], "target_salary": null, "preferred_location": "Texas", "remote_preference": null, "desired_tags": ["React", "Vue"], "preferred_category": "frontend", "weight_adjustments": {"location": "high"}, "hard_filters": []}
```

**Example 7**
- Query: `DevOps roles with AWS and Kubernetes, at least 140k, prefer onsite in Seattle`
- Output:
```json
{"description_keywords": ["devops"], "target_salary": 140000, "preferred_location": "Seattle", "remote_preference": "onsite", "desired_tags": ["AWS", "Kubernetes"], "preferred_category": "devops", "weight_adjustments": {"salary": "high"}, "hard_filters": []}
```

**Example 8**
- Query: `I want a management position, fully remote, good pay`
- Output:
```json
{"description_keywords": ["management", "engineering manager"], "target_salary": null, "preferred_location": null, "remote_preference": "remote", "desired_tags": null, "preferred_category": "management", "weight_adjustments": {"remote": "high", "salary": "medium"}, "hard_filters": []}
```


## Output format

Output **ONLY** a single JSON array in the exact order of the queries below. Each entry MUST have `query_id` and `preferences` fields. No explanation, no extra text, no markdown fences.

```json
[
  {"query_id": "q01", "preferences": {"description_keywords": null, "target_salary": 150000, "preferred_location": null, "remote_preference": "remote", "desired_tags": ["Python"], "preferred_category": null, "weight_adjustments": {"salary": "high", "remote": "high"}, "hard_filters": []}},
  {"query_id": "q02", "preferences": {...}}
]
```

---


## Queries to process (40 total)

### q01
> Remote Python backend jobs above 150k

### q02
> Jobs paying over 200k in machine learning

### q03
> Entry level software engineering positions in the 70-90k range

### q04
> High paying DevOps roles, at least 180k

### q05
> Data science positions around 130k to 160k

### q06
> Software engineering jobs in San Francisco Bay Area

### q07
> Positions near Boston for backend developers

### q08
> Tech jobs in New York City area

### q09
> Engineering roles in Seattle or Portland

### q10
> Jobs in Austin Texas for full stack developers

### q11
> Fully remote senior engineering roles

### q12
> Hybrid work positions in New York

### q13
> On-site positions only, no remote

### q14
> 100% remote data engineering jobs

### q15
> React and TypeScript frontend developer positions

### q16
> Kubernetes and Terraform DevOps engineer

### q17
> Python and AWS cloud engineer positions

### q18
> Golang microservices developer

### q19
> Rust systems programming jobs

### q20
> Mobile development jobs with Flutter or React Native

### q21
> Frontend engineering positions

### q22
> Engineering manager or tech lead openings

### q23
> Data analytics and BI positions

### q24
> iOS developer positions

### q25
> Site reliability engineer SRE jobs

### q26
> Remote ML jobs in New York above 130k

### q27
> Backend Go developer, hybrid, 160k or more

### q28
> Full stack JavaScript developer in San Francisco, remote friendly, around 140k

### q29
> Senior data engineer with Spark and Kafka experience, preferably remote, 170k+

### q30
> React frontend roles in Chicago or nearby, 120k minimum

### q31
> DevOps with AWS and Docker in Austin, hybrid OK

### q32
> Remote Python or Java backend, good salary above 150k, no PhD required

### q33
> Management positions in Denver or Boulder area, 180k+

### q34
> Companies with good culture for junior developers

### q35
> Fast-paced startup environment with equity compensation

### q36
> Collaborative team working on distributed systems

### q37
> Mentorship-focused roles for career growth in engineering

### q38
> No PhD required ML positions, remote preferred

### q39
> Jobs that don't require a master's degree in data engineering

### q40
> jobs
