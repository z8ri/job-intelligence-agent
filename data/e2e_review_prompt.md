# Job Search End-to-End Answer Quality Evaluation

You are an independent evaluator for a job-search system. For each of the 20 queries below, you will see:
- the user's natural language query
- the structured preferences the system extracted
- the top-10 jobs the ranker chose
- the system's final natural language answer

Your job is to rate the **final answer** on three dimensions using a 1-5 integer scale. Be a strict but fair reviewer — do NOT be lenient. Use the full 1-5 range.

## Scoring dimensions

### 1. Relevance
Do the jobs in the answer actually match the user's core constraints (salary, location, remote mode, tech stack, category)?
- **5** = Every highlighted job matches all hard constraints from the query.
- **4** = Most jobs match; one or two minor mismatches.
- **3** = Roughly half match; notable misses on salary/location/remote/stack.
- **2** = Most jobs violate one or more explicit constraints.
- **1** = Answer appears unrelated to the query.

### 2. Completeness
Does the answer cover the aspects the user asked about? Does it explain WHY each job matches (citing salary fit, location, tech stack, remote mode, etc.)?
- **5** = Addresses every mentioned field; clearly justifies each pick against query constraints.
- **4** = Covers most fields; justifications are mostly present.
- **3** = Covers the main ask but skips one or two query dimensions.
- **2** = Superficial — listing jobs without tying back to query constraints.
- **1** = Does not engage with the query's dimensions at all.

### 3. Readability
Is the answer well-structured, concise, and easy to scan?
- **5** = Clean numbered list, consistent structure, no filler, easy to scan.
- **4** = Well-structured with minor wordiness or inconsistency.
- **3** = Understandable but wall-of-text or uneven formatting.
- **2** = Rambling, repetitive, or poorly organized.
- **1** = Confusing or incoherent.

For each dimension, first write one short comment (≤30 words) explaining your rating, then give the integer 1-5.

## Output format

Output **ONLY** a single JSON array in the exact order of the queries below. No explanation, no extra text, no markdown fences.

```json
[
  {
    "query_id": "q01",
    "relevance": {"comment": "All top-3 are remote Python backend above 150k; strong match.", "score": 5},
    "completeness": {"comment": "Explains salary/remote/stack per job, but omits explicit category label.", "score": 4},
    "readability": {"comment": "Clean numbered list; slightly verbose summary paragraph.", "score": 4}
  },
  {"query_id": "q05", "relevance": {...}, "completeness": {...}, "readability": {...}}
]
```

---


## 20 queries to rate

### q01
**User query:** Remote Python backend jobs above 150k

**Extracted preferences:**
```json
{
  "description_keywords": [
    "Python",
    "backend"
  ],
  "target_salary": 150000,
  "preferred_location": null,
  "remote_preference": "remote",
  "desired_tags": [
    "Python"
  ],
  "preferred_category": "backend",
  "weight_adjustments": {
    "salary": "high",
    "remote": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Software Engineer, Growth & Monetization @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $153,000+
  - Tags: AI, C++, Go, ML, PostgreSQL, Python, React, TypeScript
  - Category: backend
  - Final score: 0.699
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#2** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.722
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#3** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.722
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#4** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.722
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#5** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.722
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#6** Software Engineer, AI Platforms @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $153,000+
  - Tags: AI, Go, ML, Python, TypeScript
  - Category: backend
  - Final score: 0.698
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#7** Full Stack Software Engineer @ Piq Energy
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000 – $250,000
  - Tags: AI, Python, TypeScript
  - Category: backend
  - Final score: 0.713
  - Snippet: Piq Energy | Full Stack Software Engineer | SF, Athens, or US REMOTE | Full-time | $150k-$250k + equity (SF; location-adjusted) https://jobs.gem.com/piqenergy/am9icG9zdDp5j21vRWEpgIUq005H6... Piq Energy builds software that helps renewable …
- **#8** Full Stack Software Engineer @ Piq Energy
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000 – $250,000
  - Tags: AI, Python, TypeScript
  - Category: backend
  - Final score: 0.713
  - Snippet: Piq Energy | Full Stack Software Engineer | SF, Athens, or US REMOTE | Full-time | $150k-$250k + equity (SF; location-adjusted) https://jobs.gem.com/piqenergy/am9icG9zdDp5j21vRWEpgIUq005H6... Piq Energy builds software that helps renewable …
- **#9** Software Engineer @ MachineSP
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000+
  - Tags: AI, AWS, Python
  - Category: backend
  - Final score: 0.711
  - Snippet: MachineSP | Software Engineer | NYC or SF (Hybrid → Remote) | Full-time | $150K–$200K+ MachineSP ( https://www.machinesp.com/ ) is a fast growing mortgage-backed securities (MBS) fintech company with a client list that includes most of the …
- **#10** Senior + Staff Engineers (Elixir, React, ML/AI) @ River
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000 – $250,000
  - Tags: AI, Go, ML, Python, React
  - Category: backend
  - Final score: 0.701
  - Snippet: River | Senior + Staff Engineers (Elixir, React, ML/AI) | SF or NYC or REMOTE (US, Europe, South America) | Full-Time | $150K-$250K + equity | https://jobs.ashbyhq.com/river I'm Alex, founder and CEO of River. I also wrote the first line of…

**System answer to rate:**

Here are the top remote Python backend job opportunities that meet your salary criteria of above $150,000:

1. **Company:** FIGMA  
   **Title:** Software Engineer, Growth & Monetization  
   **Salary:** $153,000+  
   **Key Matching Details:** This position is fully remote and offers a competitive salary above your target. It involves working with Python and is categorized under backend development, aligning perfectly with your skills.  
   **Tradeoffs:** The tech stack includes additional languages like C++ and Go, which may require some adjustment if you're primarily focused on Python.  

2. **Company:** Enveritas (YC S18, non-profit)  
   **Title:** Backend Software Engineer  
   **Salary:** $135,000 - $155,000  
   **Key Matching Details:** This role is remote and offers a salary that meets your target at the upper end. It emphasizes Python and backend development, making it a strong fit for your expertise.  
   **Tradeoffs:** The salary is slightly below your target but is still within your range, and the company is a non-profit, which may influence the work culture and mission.  

3. **Company:** Piq Energy  
   **Title:** Full Stack Software Engineer  
   **Salary:** $150,000 - $250,000  
   **Key Matching Details:** This position is remote and offers a salary range that exceeds your target. It involves Python and backend work, aligning well with your preferences.  
   **Tradeoffs:** As a full stack role, it may require you to work with frontend technologies as well, which could diversify your responsibilities.  

4. **Company:** MachineSP  
   **Title:** Software Engineer  
   **Salary:** $150,000+  
   **Key Matching Details:** This remote position offers a salary that meets your criteria and involves Python in a backend context.  
   **Tradeoffs:** The company operates in the fintech sector, which may require specific industry knowledge or adaptability to new domain challenges.  

5. **Company:** River  
   **Title:** Senior + Staff Engineers (Elixir, React, ML/AI)  
   **Salary:** $150,000 - $250,000  
   **Key Matching Details:** This remote role offers a competitive salary and involves Python along with other technologies.  
   **Tradeoffs:** The inclusion of Elixir and React in the tech stack may require you to expand your skill set beyond Python.  

### Summary
The top pick is **FIGMA** for its strong salary and direct alignment with your Python backend focus. **Enveritas** offers a solid option at a non-profit, while **Piq Energy** provides a higher salary range but includes full stack responsibilities. **MachineSP** and **River** also present good opportunities, though they may require familiarity with additional technologies. Overall, FIGMA and Piq Energy stand out as the best matches for your criteria.

---

### q05
**User query:** Data science positions around 130k to 160k

**Extracted preferences:**
```json
{
  "description_keywords": [
    "data science"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": "data",
  "weight_adjustments": {
    "salary": "medium"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Data Engineer, Payments @ AIRBNB
  - Location: Bangalore, India | Remote: onsite
  - Salary: not specified
  - Tags: AI, AWS, Go, ML, PostgreSQL, Python
  - Category: data
  - Final score: 0.449
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Unknown @ John Carroll University Faculty of Practice in Dat
  - Location: Cleveland | Remote: onsite
  - Salary: not specified
  - Tags: AI, Go
  - Category: data
  - Final score: 0.583
  - Snippet: John Carroll University Faculty of Practice in Data Science Cleveland OH | Onsite To view the complete job description and apply, please visit: https://jcu.peopleadmin.com/postings/3954 * Only applications and inquiries through this website…
- **#3** Staff Software Engineer, Data Engineering @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $191,000+
  - Tags: AI, Go, Java, ML, PostgreSQL, Python, Rust
  - Category: data
  - Final score: 0.446
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Staff Data Engineer, Ads @ DISCORD
  - Location: Remote (U.S.) | Remote: remote
  - Salary: $248,000+
  - Tags: AI, ML, Python
  - Category: data
  - Final score: 0.417
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#5** Data Platform Engineer @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $235,000+
  - Tags: AI, AWS, Go, ML, Python
  - Category: data
  - Final score: 0.399
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#6** Senior Data Engineer, Analytics @ DISCORD
  - Location: San Francisco Bay Area | Remote: onsite
  - Salary: $196,000+
  - Tags: AI, Go, Python, Rust
  - Category: data
  - Final score: 0.382
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#7** Senior Data Scientist, Causal Inference @ AIRBNB
  - Location: Remote | Remote: remote
  - Salary: $179,000+
  - Tags: AI, Python
  - Category: data
  - Final score: 0.378
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#8** Senior Staff Data Engineer, Marketplaces DNA @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $244,000+
  - Tags: AI, Go, Java, ML
  - Category: data
  - Final score: 0.369
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#9** Data Scientist, Core Data -  PhD (2026) @ FIGMA
  - Location: New York, NY • United States; San Francisco, CA • New York, NY | Remote: remote
  - Salary: $170,000+
  - Tags: AI, Go, ML, Python
  - Category: data
  - Final score: 0.362
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#10** Data Scientist, Analytics @ DISCORD
  - Location: San Francisco Bay Area | Remote: onsite
  - Salary: $160,000+
  - Tags: AI
  - Category: data
  - Final score: 0.360
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…

**System answer to rate:**

Here are the top data science positions that align with your salary range of $130k to $160k:

1. **Company:** AIRBNB  
   **Title:** Senior Data Scientist, Causal Inference  
   **Location:** Remote  
   **Salary:** $179,000+  
   **Matching Details:** This position offers a salary above your target range and is fully remote, which provides flexibility. The tech stack includes AI and Python, aligning well with data science roles.  
   **Tradeoff:** Slightly above your target salary but a strong match for remote work and relevant skills.

2. **Company:** DISCORD  
   **Title:** Data Scientist, Analytics  
   **Location:** San Francisco Bay Area  
   **Salary:** $160,000+  
   **Matching Details:** This role meets your salary target exactly and is in the data science category. It requires onsite presence, which may be a consideration if you're looking for remote options.  
   **Tradeoff:** Onsite requirement may limit flexibility, but it fits your salary expectations perfectly.

3. **Company:** FIGMA  
   **Title:** Data Scientist, Core Data - PhD (2026)  
   **Location:** New York, NY / San Francisco, CA  
   **Salary:** $170,000+  
   **Matching Details:** This position is remote and offers a salary above your target. It involves AI and Python, which are essential in data science.  
   **Tradeoff:** The salary is above your range, but the remote option and tech stack are strong positives.

4. **Company:** AIRBNB  
   **Title:** Senior Staff Data Engineer, Marketplaces DNA  
   **Location:** United States  
   **Salary:** $244,000+  
   **Matching Details:** While this role is significantly above your salary range, it is remote and includes a robust tech stack (AI, Go, Java, ML).  
   **Tradeoff:** The salary is much higher than your target, but it may be worth considering for the tech stack and remote work.

5. **Company:** DISCORD  
   **Title:** Senior Data Engineer, Analytics  
   **Location:** San Francisco Bay Area  
   **Salary:** $196,000+  
   **Matching Details:** This role is also above your salary range but offers onsite work in a dynamic environment. It involves AI and Python, relevant to data science.  
   **Tradeoff:** Onsite requirement and higher salary, but the tech stack is a strong match.

### Summary
The best fit for your salary range is the **Senior Data Scientist at AIRBNB** for $179,000, which offers remote work and aligns well with your skills. The **Data Scientist at DISCORD** meets your salary expectation exactly at $160,000 but requires onsite presence. If you're open to roles slightly above your target, the positions at **FIGMA** and **DISCORD** offer excellent tech stacks and remote flexibility. Consider your priorities regarding salary versus remote work when making a decision.

---

### q07
**User query:** Positions near Boston for backend developers

**Extracted preferences:**
```json
{
  "description_keywords": [
    "backend developer"
  ],
  "target_salary": null,
  "preferred_location": "Boston",
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": "backend",
  "weight_adjustments": {
    "location": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Staff GenAI Backend Engineer, Automation Foundation @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.571
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Java Developer / Web & React Native Developer @ TantumPay
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: Java, React
  - Category: frontend
  - Final score: 0.647
  - Snippet: TantumPay | Java Developer / Web & React Native Developer | Europe (CET) | Remote | Full Time We're a FinTech company reinventing high-risk-market payments with an integrated digital identity layer. Our team is expanding, and we are looking…
- **#3** Senior Software Engineer, Quality Engineering @ AIRBNB
  - Location: Brazil - Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.553
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Senior iOS Software Engineer, Quality Platform @ AIRBNB
  - Location: Brazil - Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.553
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Android Software Engineer, Quality Platform @ AIRBNB
  - Location: Remote, Brazil | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.553
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#6** Staff Backend Engineer - Hosting Services @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.553
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#7** Staff Backend Engineer, Core Entities Data Foundation @ AIRBNB
  - Location: Remote - US | Remote: remote
  - Salary: $212,000+
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.547
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#8** Senior Software Engineer, Backend GraphQL @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $191,000+
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.547
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#9** Staff Software Engineer, Build @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, Go
  - Category: backend
  - Final score: 0.542
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#10** Senior Python Backend Developer @ SKYCATCHFIRE
  - Location: Remote or OH | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, Python
  - Category: backend
  - Final score: 0.601
  - Snippet: SKYCATCHFIRE| Senior Python Backend Developer | US Remote (OH-based preferred) | Full-time Our team transforms complex business operations into elegant, reliable systems. We prioritize "Email > Meetings" and protected focus time to ensure w…

**System answer to rate:**

Here are the top job positions for backend developers near Boston:

1. **Company:** AIRBNB  
   **Title:** Staff GenAI Backend Engineer, Automation Foundation  
   **Location:** Remote - USA  
   **Key Matching Details:** This position offers a high salary of $204,000+ and aligns with your backend development focus. It also emphasizes AI and Go, which may be relevant if you have experience in these areas.  
   **Tradeoffs:** Fully remote, so not Boston-specific, but salary and tech stack are strong.

2. **Company:** TantumPay  
   **Title:** Java Developer / Web & React Native Developer  
   **Location:** Remote  
   **Key Matching Details:** This role is also remote and focuses on Java, which is a common backend technology. While the salary is not specified, the position is full-time and aligns well with backend development.  
   **Tradeoffs:** Remote nature means no direct location benefit for Boston.

3. **Company:** AIRBNB  
   **Title:** Staff Backend Engineer - Hosting Services  
   **Location:** Remote - USA  
   **Key Matching Details:** Another strong offering from Airbnb with a salary of $204,000+. This position focuses on backend services and is fully remote, providing a good salary and tech stack match.  
   **Tradeoffs:** Remote position, so it does not provide local Boston opportunities.

4. **Company:** AIRBNB  
   **Title:** Staff Backend Engineer, Core Entities Data Foundation  
   **Location:** Remote - US  
   **Key Matching Details:** This role offers a salary of $212,000+ and focuses on backend engineering. It is fully remote, which may be appealing if you prefer flexibility.  
   **Tradeoffs:** Again, remote means no Boston-specific benefits.

5. **Company:** AIRBNB  
   **Title:** Senior Software Engineer, Backend GraphQL  
   **Location:** Remote - USA  
   **Key Matching Details:** This position offers a salary of $191,000+ and focuses on backend development with GraphQL, which is a popular technology in the field.  
   **Tradeoffs:** Fully remote, so it lacks local Boston engagement.

### Summary
While there are several strong remote backend developer positions available, they do not offer direct opportunities in Boston. The roles from Airbnb stand out due to their high salaries and relevant tech stacks, but all are remote. If you are specifically looking for in-office roles in Boston, consider broadening your search criteria or including hybrid options.

---

### q11
**User query:** Fully remote senior engineering roles

**Extracted preferences:**
```json
{
  "description_keywords": [
    "senior engineering"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": "remote",
  "desired_tags": null,
  "preferred_category": null,
  "weight_adjustments": {
    "remote": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Staff Software Engineer, Payments @ AIRBNB
  - Location: Bangalore, India | Remote: remote
  - Salary: not specified
  - Tags: AI, Go
  - Category: management
  - Final score: 0.439
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer @ Prompt Health
  - Location: Remote | Remote: remote
  - Salary: $100,000+
  - Tags: AI, AWS, Docker, Kubernetes, ML, Python
  - Category: devops
  - Final score: 0.564
  - Snippet: Prompt Health| Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer | REMOTE (US) Prompt Health is a fast-growing Healthcare SaaS company with over $100M in ARR, growing 100%+ YoY. We build software used by large healthcare …
- **#3** Senior Software Engineer, Community Support Engineering @ AIRBNB
  - Location: China | Remote: remote
  - Salary: not specified
  - Tags: AI, Java, ML
  - Category: management
  - Final score: 0.435
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer @ Prompt Health
  - Location: Remote | Remote: remote
  - Salary: $100,000+
  - Tags: AI, AWS, Docker, Kubernetes, ML, Python
  - Category: devops
  - Final score: 0.558
  - Snippet: Prompt Health| Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer | REMOTE (US) Prompt Health is a fast-growing Healthcare SaaS company with over $100M in ARR, growing 100%+ YoY. We build software used by large healthcare …
- **#5** Senior Fullstack Engineer, Senior DevOps Engineer @ Sequent Tech
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: Kubernetes, React, Rust, TypeScript
  - Category: devops
  - Final score: 0.548
  - Snippet: Sequent Tech | Senior Fullstack Engineer, Senior DevOps Engineer | REMOTE (Global) | Full-time | sequentech.io Sequent builds cryptographically secure online voting infrastructure used in 200+ real elections across multiple countries. We're…
- **#6** Senior Frontend Engineer, Reliability Experience @ AIRBNB
  - Location: Brazil - Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Java, ML, React, TypeScript
  - Category: management
  - Final score: 0.426
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#7** AI Engineer @ Rootly
  - Location: Remote or San Francisco | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, Rust
  - Category: devops
  - Final score: 0.542
  - Snippet: Rootly | AI-native on-call & incident response (Slack/Teams) | REMOTE (US/Canada/Europe); optional hubs SF & Toronto We build the end-to-end platform that helps SRE/eng teams detect, manage, and learn from incidents faster—trusted by 1000+ …
- **#8** Senior iOS Engineer, Global Markets  @ AIRBNB
  - Location: China | Remote: remote
  - Salary: not specified
  - Tags: AI
  - Category: management
  - Final score: 0.422
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#9** Senior Software Engineer, Community Support Engineering  @ AIRBNB
  - Location: Remote, USA | Remote: remote
  - Salary: $195,000+
  - Tags: AI, C++, Java
  - Category: management
  - Final score: 0.419
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#10** Senior Staff Software Engineer, Trust @ AIRBNB
  - Location: Remote - US | Remote: remote
  - Salary: $248,000+
  - Tags: AI, Java, ML, Rust
  - Category: management
  - Final score: 0.419
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…

**System answer to rate:**

Here are the top fully remote senior engineering roles that match your query:

1. **Company:** Prompt Health  
   **Title:** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer  
   **Key Matching Details:** This position is fully remote, offers a salary of $100,000+, and involves technologies like AI, AWS, Docker, Kubernetes, ML, and Python, which are highly relevant for senior engineering roles.  
   **Tradeoffs:** While the salary is competitive, it may be lower than some other senior roles in the market.

2. **Company:** Sequent Tech  
   **Title:** Senior Fullstack Engineer, Senior DevOps Engineer  
   **Key Matching Details:** This role is also fully remote and involves working with Kubernetes, React, Rust, and TypeScript, making it a strong match for tech stack overlap.  
   **Tradeoffs:** Salary details are not specified, which may be a concern for some candidates.

3. **Company:** AIRBNB  
   **Title:** Senior Staff Software Engineer, Payments  
   **Key Matching Details:** This position is remote and aligns with senior engineering responsibilities, although the salary is not specified. The company is well-known, which could be a significant advantage for career growth.  
   **Tradeoffs:** The lack of salary information may make it difficult to assess overall compensation.

4. **Company:** AIRBNB  
   **Title:** Senior Software Engineer, Community Support Engineering  
   **Key Matching Details:** Fully remote and involves AI and Java, which are relevant technologies for senior roles.  
   **Tradeoffs:** Salary is not specified, which could be a drawback for some candidates.

5. **Company:** Rootly  
   **Title:** AI Engineer  
   **Key Matching Details:** This role is remote and involves AI technologies, with the option to work from San Francisco or other locations.  
   **Tradeoffs:** Salary details are not provided, which may affect decision-making.

### Summary
The top picks emphasize fully remote opportunities with strong tech stack overlaps, particularly in AI and cloud technologies. Prompt Health stands out for its competitive salary, while Sequent Tech and AIRBNB offer reputable companies but lack salary transparency. If salary is a critical factor for you, consider focusing on roles with specified compensation.

---

### q14
**User query:** 100% remote data engineering jobs

**Extracted preferences:**
```json
{
  "description_keywords": [
    "data engineering"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": "remote",
  "desired_tags": null,
  "preferred_category": "data",
  "weight_adjustments": {
    "remote": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Staff Software Engineer, Data Engineering @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $191,000+
  - Tags: AI, Go, Java, ML, PostgreSQL, Python, Rust
  - Category: data
  - Final score: 0.566
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Unknown @ We’re looking for an exceptional Staff Data Engine
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go
  - Category: data
  - Final score: 0.551
  - Snippet: We’re looking for an exceptional Staff Data Engineer to help us take our data platform to the next level. This is a high-impact role where you’ll architect and build scalable data infrastructure, empower data-driven decision-making, and hel…
- **#3** Lead Data & AI Engineer @ Milestone Systems
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, ML, Python
  - Category: data
  - Final score: 0.547
  - Snippet: Milestone Systems | Lead Data & AI Engineer | Remote (USA) The Arcules team at Milestone is looking for a Lead Data & AI Engineer to design and evolve the intelligent analytics portion of our security cloud platform. This spans from squeezi…
- **#4** Unknown @ Zipline.ai
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, AWS, ML
  - Category: data
  - Final score: 0.538
  - Snippet: Zipline.ai | REMOTE - Europe, LATAM | Contract work We’re rethinking the data platform for the modern age of AI/ML workflows. Our founding team built the Chronon open source project that powers all major AI/ML workflows at companies like Ai…
- **#5** Staff Data Engineer, Ads @ DISCORD
  - Location: Remote (U.S.) | Remote: remote
  - Salary: $248,000+
  - Tags: AI, ML, Python
  - Category: data
  - Final score: 0.547
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#6** Software Engineer, Data Infrastructure @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $153,000+
  - Tags: AI, Go, ML, Python
  - Category: data
  - Final score: 0.546
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#7** Senior Staff Data Engineer, Marketplaces DNA @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $244,000+
  - Tags: AI, Go, Java, ML
  - Category: data
  - Final score: 0.541
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#8** Unknown @ Data Analyst
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: Go, Python
  - Category: data
  - Final score: 0.520
  - Snippet: Data Analyst | Redistricting Data Hub | Remote (US) The nonpartisan Redistricting Data Hub provides individuals, good government organizations, and community groups the data, resources, and knowledge to participate effectively in the redist…
- **#9** Data Engineer @ Foxglove
  - Location: Remote or San Francisco | Remote: remote
  - Salary: not specified
  - Tags: AI, Rust
  - Category: data
  - Final score: 0.513
  - Snippet: Foxglove | Onsite (San Francisco) & Remote | Full Time | https://foxglove.dev/ Foxglove is the leading observability & data platform for robotics and physical AI. Our software supports the full data lifecycle, from collection, upload, and s…
- **#10** Data Engineer @ IPinfo.io
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Category: data
  - Final score: 0.513
  - Snippet: IPinfo.io | Various Roles | Remote (Anywhere) | Fulltime / Partime / Contract | https://ipinfo.io IPinfo is a leading provider of IP address data, including geolocation, VPN and residential proxy detection, mobile carrier data, and over 20 …

**System answer to rate:**

Here are the top remote data engineering job opportunities that match your query:

1. **Company:** AIRBNB  
   **Title:** Staff Software Engineer, Data Engineering  
   **Key Matching Details:** This position is fully remote and offers a competitive salary starting at $191,000+. The role involves working with a strong tech stack including AI, Go, Java, ML, PostgreSQL, Python, and Rust.  
   **Tradeoffs:** None noted; strong alignment with your remote preference and tech stack.

2. **Company:** Unknown  
   **Title:** Staff Data Engineer  
   **Key Matching Details:** This role is fully remote, focusing on architecting and building scalable data infrastructure. While the salary is not specified, it aligns well with your data engineering focus.  
   **Tradeoffs:** Salary details are missing, which may be a consideration.

3. **Company:** Milestone Systems  
   **Title:** Lead Data & AI Engineer  
   **Key Matching Details:** Fully remote position with a focus on intelligent analytics and data engineering. The tech stack includes AI, Go, ML, and Python, which may overlap with your experience.  
   **Tradeoffs:** Salary not specified, which could be a drawback.

4. **Company:** Zipline.ai  
   **Title:** Unknown  
   **Key Matching Details:** Remote position focusing on modern AI/ML workflows. The role is contract-based, which may offer flexibility.  
   **Tradeoffs:** Salary not specified and the contract nature may not suit everyone.

5. **Company:** DISCORD  
   **Title:** Staff Data Engineer, Ads  
   **Key Matching Details:** This fully remote role offers a high salary starting at $248,000+, focusing on data engineering within a popular platform. The tech stack includes AI, ML, and Python.  
   **Tradeoffs:** None noted; strong salary and tech stack match.

6. **Company:** FIGMA  
   **Title:** Software Engineer, Data Infrastructure  
   **Key Matching Details:** Remote role with a salary starting at $153,000+. The position involves working with AI, Go, ML, and Python, aligning well with your interests.  
   **Tradeoffs:** Salary is lower compared to others on this list.

7. **Company:** AIRBNB  
   **Title:** Senior Staff Data Engineer, Marketplaces DNA  
   **Key Matching Details:** Fully remote with a salary of $244,000+. This role also involves a strong tech stack including AI, Go, Java, and ML.  
   **Tradeoffs:** None noted; excellent salary and tech stack match.

8. **Company:** Unknown  
   **Title:** Data Analyst  
   **Key Matching Details:** Remote position focusing on data analysis. The role is less technical compared to others but still within the data category.  
   **Tradeoffs:** Salary not specified and may not be as aligned with data engineering.

9. **Company:** Foxglove  
   **Title:** Data Engineer  
   **Key Matching Details:** Remote or onsite in San Francisco. The role involves working with AI and Rust, which may be relevant to your skills.  
   **Tradeoffs:** Salary not specified, and there is an onsite option which may not suit your preference.

10. **Company:** IPinfo.io  
    **Title:** Data Engineer  
    **Key Matching Details:** Fully remote position with various roles available. The company specializes in IP address data.  
    **Tradeoffs:** Salary not specified, which could be a consideration.

### Summary
The top picks include high-salary positions at Airbnb and Discord, both offering strong tech stack matches and fully remote options. While some roles lack salary transparency, they still align with your data engineering focus. If salary is a key factor for you, consider prioritizing the roles at Discord and Airbnb.

---

### q15
**User query:** React and TypeScript frontend developer positions

**Extracted preferences:**
```json
{
  "description_keywords": [
    "frontend developer"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": [
    "React",
    "TypeScript"
  ],
  "preferred_category": "frontend",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Software Engineer - Web Platform @ DISCORD
  - Location: San Francisco Bay Area | Remote: onsite
  - Salary: $196,000+
  - Tags: AI, Go, Java, Python, React, Rust, TypeScript
  - Category: frontend
  - Final score: 0.502
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#2** Senior Frontend Engineer (fullstack Typescript nice to have) @ Document Crunch
  - Location: Remote or Austin | Remote: remote
  - Salary: $40,000+
  - Tags: AI, ML, Python, React, TypeScript
  - Category: fullstack
  - Final score: 0.503
  - Snippet: Document Crunch | REMOTE(US) / HYBRID Company description: We do construction compliance AI. We're in series B, about $40m raised. Growing a lot! Feel free to reply or DM me if you want some more info. Tech Stack: Typescript full stack exce…
- **#3** Senior Frontend Engineer @ Level
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, React, TypeScript
  - Category: frontend
  - Final score: 0.498
  - Snippet: Level | Senior Frontend Engineer | REMOTE (US + international with US-ET overlap) | https://level.io Level builds a modern Remote Monitoring & Management (RMM) platform for IT teams and Managed Service Providers. We help IT professionals mo…
- **#4** Senior Full Stack Developer @ Pelairo Inc.
  - Location: Remote | Remote: remote
  - Salary: $100,000 – $150,000
  - Tags: AI, AWS, Go, React, TypeScript
  - Category: frontend
  - Final score: 0.494
  - Snippet: Pelairo Inc. | Senior Full Stack Developer | REMOTE (US Only) | Full-time | $100-150k At Pelairo we're building the most intuitive and flexible Laboratory Information Management System (LIMS) on the market. "Manage the lab, not the LIMS!" A…
- **#5** Senior Software Engineers (Frontend, Mobile) @ Noise
  - Location: New York City | Remote: onsite
  - Salary: $160,000 – $210,000
  - Tags: AI, React, TypeScript
  - Category: frontend
  - Final score: 0.490
  - Snippet: Noise | Senior Software Engineers (Frontend, Mobile) | NYC | ONSITE | Full-time | $160k-$210k + equity Noise is building a way to measure and trade attention — something the internet produces endlessly but no one has been able to objectivel…
- **#6** Frontend Developer (React/Next.js) @ Modall
  - Location: Remote or Onsite | Remote: remote
  - Salary: $60,000 – $80,000
  - Tags: AI, Go, React, TypeScript
  - Category: frontend
  - Final score: 0.471
  - Snippet: Modall | Frontend Developer (React/Next.js) | Uxbridge, ON (Greater Toronto) | On-Site | C$60-80k We're a 5-person dev agency building AI, Web3, and SaaS products for startups, NFL players, and enterprises. Stack: TypeScript, React, Next.js…
- **#7** Senior Software Engineer II @ Carta
  - Location: OK | Remote: hybrid
  - Salary: not specified
  - Tags: React, TypeScript
  - Category: frontend
  - Final score: 0.465
  - Snippet: Carta | Senior Software Engineer II | Waterloo / Toronto | ONSITE (Hybrid OK) Apply Here: - https://job-boards.greenhouse.io/carta/jobs/7544237003 - https://job-boards.greenhouse.io/carta/jobs/7504452003 ⎯ Carta connects founders, investors…
- **#8** Unknown @ any2any
  - Location: Unknown | Remote: onsite
  - Salary: not specified
  - Tags: React, TypeScript
  - Category: frontend
  - Final score: 0.460
  - Snippet: any2any | On-site (Munich, Germany) | Full-time About us: We provide access and visitor management platforms integrating a wide range of technologies. Backed by a large Swiss AG. Hiring: Multiple roles; backend developer (Kotlin, PHP), fron…
- **#9** engineer... Fullstack Engineer @ Waypoint AI
  - Location: Remote | Remote: remote
  - Salary: $3,000+
  - Tags: AI, Go, React, TypeScript
  - Category: frontend
  - Final score: 0.457
  - Snippet: Waypoint AI | Senior Backend, Fullstack, Frontend | Prague + REMOTE (CZ) | Full-time | Equity We're building Chip — an AI support engineer that autonomously triages, routes, and resolves complex technical support cases. Think: a teammate th…
- **#10** Founding Design & Frontend Engineer @ Spiich Labs (Stockholm)
  - Location: Unknown | Remote: onsite
  - Salary: not specified
  - Tags: AI, React, TypeScript
  - Category: frontend
  - Final score: 0.448
  - Snippet: Spiich Labs (Stockholm) | Founding Design & Frontend Engineer | Full-time | On-site | Visa Sponsorship We're building Cursor for sales - an AI assistant doubling sales productivity by handling prospecting, CRM updates, meeting prep, and fol…

**System answer to rate:**

Here are the top React and TypeScript frontend developer positions that match your query:

1. **Company:** DISCORD  
   **Title:** Senior Software Engineer - Web Platform  
   **Location:** San Francisco Bay Area (onsite)  
   **Salary:** $196,000+  
   **Key Matching Details:** Strong tech stack overlap with React and TypeScript, high salary potential.  
   **Tradeoffs:** Onsite position may not fit remote preferences.

2. **Company:** Document Crunch  
   **Title:** Senior Frontend Engineer (fullstack Typescript nice to have)  
   **Location:** Remote or Austin  
   **Salary:** $40,000+  
   **Key Matching Details:** Fully remote option, strong alignment with desired tech stack (React, TypeScript).  
   **Tradeoffs:** Salary is significantly lower than typical for senior roles.

3. **Company:** Level  
   **Title:** Senior Frontend Engineer  
   **Location:** Remote  
   **Salary:** Not specified  
   **Key Matching Details:** Fully remote position with a focus on React and TypeScript.  
   **Tradeoffs:** Salary information not provided, which may affect decision-making.

4. **Company:** Pelairo Inc.  
   **Title:** Senior Full Stack Developer  
   **Location:** Remote  
   **Salary:** $100,000 - $150,000  
   **Key Matching Details:** Remote work, solid salary range, and relevant tech stack (React, TypeScript).  
   **Tradeoffs:** Full stack role may involve additional responsibilities beyond frontend development.

5. **Company:** Noise  
   **Title:** Senior Software Engineers (Frontend, Mobile)  
   **Location:** New York City (onsite)  
   **Salary:** $160,000 - $210,000  
   **Key Matching Details:** High salary range and strong tech stack match with React and TypeScript.  
   **Tradeoffs:** Onsite requirement may not suit remote work preferences.

### Summary
The top positions offer a mix of remote and onsite opportunities, with varying salary ranges. Discord and Noise provide high salaries but require onsite work, while Document Crunch offers a fully remote role at a lower salary. Pelairo Inc. balances a good salary with remote work, though it is a full stack position. Level presents a remote option but lacks salary details. Consider your priorities between salary, remote work, and job responsibilities when making a choice.

---

### q16
**User query:** Kubernetes and Terraform DevOps engineer

**Extracted preferences:**
```json
{
  "description_keywords": [
    "devops engineer"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": [
    "Kubernetes",
    "Terraform"
  ],
  "preferred_category": "devops",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Software Engineer, Platform as a Service @ DISCORD
  - Location: San Francisco Bay Area | Remote: onsite
  - Salary: $196,000+
  - Tags: AI, Docker, Go, Kubernetes, Rust
  - Category: devops
  - Final score: 0.359
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#2** Senior Fullstack Engineer, Senior DevOps Engineer @ Sequent Tech
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: Kubernetes, React, Rust, TypeScript
  - Category: devops
  - Final score: 0.444
  - Snippet: Sequent Tech | Senior Fullstack Engineer, Senior DevOps Engineer | REMOTE (Global) | Full-time | sequentech.io Sequent builds cryptographically secure online voting infrastructure used in 200+ real elections across multiple countries. We're…
- **#3** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer @ Prompt Health
  - Location: Remote | Remote: remote
  - Salary: $100,000+
  - Tags: AI, AWS, Docker, Kubernetes, ML, Python
  - Category: devops
  - Final score: 0.431
  - Snippet: Prompt Health| Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer | REMOTE (US) Prompt Health is a fast-growing Healthcare SaaS company with over $100M in ARR, growing 100%+ YoY. We build software used by large healthcare …
- **#4** Senior Software Engineer, Reliability Engineering @ AIRBNB
  - Location: São Paulo, Brazil | Remote: onsite
  - Salary: not specified
  - Tags: AI, AWS, Docker, Go, Java, Kubernetes, Python
  - Category: devops
  - Final score: 0.349
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Software Engineer & Senior DevOps Engineer @ Blackshark AI
  - Location: Remote | Remote: remote
  - Salary: $35,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes, Python
  - Category: devops
  - Final score: 0.424
  - Snippet: Blackshark AI | Software Engineer & Senior DevOps Engineer | Full-time | Austria or Remote EU | VISA sponsorship available Vo to satellite and drone imagery is on the rise, while traditional image processing methods struggle to keep up. Our…
- **#6** Software Engineer & Senior DevOps Engineer @ Blackshark AI
  - Location: Remote | Remote: remote
  - Salary: $35,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes, Python
  - Category: devops
  - Final score: 0.422
  - Snippet: Blackshark AI | Software Engineer & Senior DevOps Engineer | Full-time | Austria or Remote EU | VISA sponsorship available Satellite and drone imagery access is on the rise, and traditional image processing methods are struggling to keep up…
- **#7** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer @ Prompt Health
  - Location: Remote | Remote: remote
  - Salary: $100,000+
  - Tags: AI, AWS, Docker, Kubernetes, ML, Python
  - Category: devops
  - Final score: 0.417
  - Snippet: Prompt Health| Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer | REMOTE (US) Prompt Health is a fast-growing Healthcare SaaS company with over $100M in ARR, growing 100%+ YoY. We build software used by large healthcare …
- **#8** Senior Security Software Engineer, Detection and Response @ DISCORD
  - Location: San Francisco Bay Area or Remote | Remote: remote
  - Salary: $196,000+
  - Tags: AI, Kubernetes, Python, React, Rust
  - Category: devops
  - Final score: 0.338
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#9** Staff Software Engineer, Platform Security @ DISCORD
  - Location: San Francisco Bay Area or Remote | Remote: remote
  - Salary: $248,000+
  - Tags: AI, AWS, Docker, Kubernetes, Python, Rust
  - Category: devops
  - Final score: 0.335
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#10** Engineering Manager, Cloud Networking (Brazil) @ AIRBNB
  - Location: Brazil | Remote: onsite
  - Salary: not specified
  - Tags: AI, AWS, Go, Kubernetes, ML
  - Category: devops
  - Final score: 0.332
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…

**System answer to rate:**

Here are the top job matches for a Kubernetes and Terraform DevOps engineer:

1. **Sequent Tech**
   - **Title:** Senior Fullstack Engineer, Senior DevOps Engineer
   - **Location:** Remote
   - **Remote:** Yes
   - **Salary:** Not specified
   - **Tags:** Kubernetes, React, Rust, TypeScript
   - **Key Match:** Strong alignment with your desired tags, particularly Kubernetes. The remote option provides flexibility.
   - **Tradeoff:** Salary details are not available, which may be a concern.

2. **Prompt Health**
   - **Title:** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer
   - **Location:** Remote
   - **Remote:** Yes
   - **Salary:** $100,000+
   - **Tags:** AI, AWS, Docker, Kubernetes, ML, Python
   - **Key Match:** Excellent tech stack match with Kubernetes and a solid salary. Remote work is also available.
   - **Tradeoff:** The salary is slightly below what might be expected for a senior role, but the company is rapidly growing.

3. **Blackshark AI**
   - **Title:** Software Engineer & Senior DevOps Engineer
   - **Location:** Remote
   - **Remote:** Yes
   - **Salary:** $35,000+
   - **Tags:** AI, AWS, Docker, Go, Kubernetes, Python
   - **Key Match:** Good match with Kubernetes in the tech stack and fully remote work.
   - **Tradeoff:** The salary is significantly lower than typical for senior roles, which could be a major drawback.

4. **Discord**
   - **Title:** Senior Software Engineer, Platform as a Service
   - **Location:** San Francisco Bay Area
   - **Remote:** Onsite
   - **Salary:** $196,000+
   - **Tags:** AI, Docker, Go, Kubernetes, Rust
   - **Key Match:** High salary and strong Kubernetes experience required, but this position is not remote.
   - **Tradeoff:** The onsite requirement limits flexibility, especially for those seeking remote work.

5. **Airbnb**
   - **Title:** Senior Software Engineer, Reliability Engineering
   - **Location:** São Paulo, Brazil
   - **Remote:** Onsite
   - **Salary:** Not specified
   - **Tags:** AI, AWS, Docker, Go, Java, Kubernetes, Python
   - **Key Match:** Good tech stack overlap with Kubernetes, but the salary is unspecified and the role is onsite.
   - **Tradeoff:** Lack of salary information and onsite requirement may be less appealing.

### Summary
The best options for a Kubernetes and Terraform DevOps engineer are Sequent Tech and Prompt Health, both offering remote work and relevant tech stacks. Sequent Tech has the advantage of being fully remote, while Prompt Health offers a solid salary. Blackshark AI is also remote but has a significantly lower salary. Discord offers a high salary but requires onsite work, which may not suit your preferences.

---

### q20
**User query:** Mobile development jobs with Flutter or React Native

**Extracted preferences:**
```json
{
  "description_keywords": [
    "mobile development"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": [
    "Flutter",
    "React Native"
  ],
  "preferred_category": "mobile",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Staff Software Engineer, Mobile Architecture @ DISCORD
  - Location: San Francisco Bay Area  | Remote: onsite
  - Salary: $248,000+
  - Tags: AI, Go, Java, React, TypeScript
  - Category: frontend
  - Final score: 0.259
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#2** Founding Engineer, Mobile App Developer & More @ Songscription
  - Location: San Francisco | Remote: onsite
  - Salary: not specified
  - Tags: AI
  - Category: mobile
  - Final score: 0.355
  - Snippet: Songscription | Founding Engineer, Mobile App Developer & More | San Francisco, CA At Songscription, we are building state-of-the-art AI models to automate music transcription, with the vision of enabling any musician to learn any song, on …
- **#3** Mobile Engineer (React Native/Typescript) @ EnsoData
  - Location: Remote or Milwaukee | Remote: remote
  - Salary: not specified
  - Tags: AI, React, TypeScript
  - Category: mobile
  - Final score: 0.330
  - Snippet: EnsoData | Mobile Engineer (React Native/Typescript) | Full-time | Hybrid (Madison, WI) or Remote (US) EnsoData strives to make healthcare more accurate, efficient, and affordable through waveform artificial intelligence (AI) technology. Us…
- **#4** Unknown @ Revelare Networks / Mobile Software Engineer/ Full
  - Location: Remote | Remote: remote
  - Salary: $110,000 – $155,000
  - Category: mobile
  - Final score: 0.321
  - Snippet: Revelare Networks / Mobile Software Engineer/ Fully Remote/ Full-Time/ US Citizen We are hiring a Mobile Software Engineer with extensive experience in Android (Kotlin/Jetpack Compose) and iOS (Swift/SwiftUI). The salary range for this posi…
- **#5** Mobile Engineer (iOS/Android) @ Musa
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI
  - Category: mobile
  - Final score: 0.319
  - Snippet: Musa — Mobile Engineer (iOS/Android) — Remote (Americas) Musa is a mobile app helping women understand their hormonal health through a cycle tracker with personalization and a small companion character. Thousands use it daily. We’re a small…
- **#6** Senior Software Engineer, Mobile Architecture @ DISCORD
  - Location: San Francisco Bay Area | Remote: onsite
  - Salary: $196,000+
  - Tags: AI, Go, Java, React, TypeScript
  - Category: frontend
  - Final score: 0.232
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#7** Senior Mobile Engineer @ Attendi
  - Location: Hybrid | Remote: hybrid
  - Salary: not specified
  - Tags: AI, ML
  - Category: devops
  - Final score: 0.298
  - Snippet: Attendi | Senior Mobile Engineer | Amsterdam, Netherlands | ON-SITE hybrid | Full-time (80–100%) Healthcare professionals have to spend too much time on administrative tasks when they should be spending that time delivering great care. Atte…
- **#8** React Native Developer @ Chatwoot
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, ML, React
  - Category: mobile
  - Final score: 0.287
  - Snippet: Chatwoot | React Native Developer | Remote (India) https://chatwoot.com Chatwoot is a modern customer support tool for your business with an integrated AI assistant, omnichannel support desk, and knowledge base. We aim to provide everything…
- **#9** Software Engineer (Mobile + Frontend Focus) @ Uniplay
  - Location: Remote or Onsite | Remote: remote
  - Salary: not specified
  - Tags: AI
  - Category: mobile
  - Final score: 0.280
  - Snippet: Uniplay | Software Engineer (Mobile + Frontend Focus) | STOCKHOLM ONSITE/REMOTE HYBRID 3/5 | https://uniplay.io & Uniplay Business on App Store We’re looking for a Software Engineer (Mobile + Frontend Focus) who can make Uniplay feel amazin…
- **#10** Stack Mobile Engineer (KMP) @ Pushscroll
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go
  - Category: mobile
  - Final score: 0.274
  - Snippet: Pushscroll | Full-Stack Mobile Engineer (KMP) | REMOTE (GMT-3 to GMT+4) We make people do push-ups before opening addictive apps - verified through camera pose detection. Our goal is to replace doomscrolling with exercise. 500k+ downloads, …

**System answer to rate:**

Here are the top mobile development job opportunities that align with your interest in Flutter or React Native:

1. **Company**: Songscription  
   **Title**: Founding Engineer, Mobile App Developer & More  
   **Location**: San Francisco  
   **Remote**: Onsite  
   **Salary**: Not specified  
   **Key Matching Details**: This role is categorized under mobile development and offers a strong focus on building innovative applications. While the salary isn't specified, the position is in a tech-forward environment.  
   **Tradeoff**: Onsite requirement may limit flexibility.

2. **Company**: EnsoData  
   **Title**: Mobile Engineer (React Native/Typescript)  
   **Location**: Remote or Milwaukee  
   **Remote**: Remote  
   **Salary**: Not specified  
   **Key Matching Details**: This position specifically mentions React Native and TypeScript, making it a strong match for your desired tech stack. The remote option adds flexibility.  
   **Tradeoff**: Salary details are not provided.

3. **Company**: Revelare Networks  
   **Title**: Mobile Software Engineer  
   **Location**: Remote  
   **Remote**: Remote  
   **Salary**: $110,000 - $155,000  
   **Key Matching Details**: This role is fully remote and focuses on mobile software engineering, although it primarily emphasizes Android and iOS development rather than Flutter or React Native specifically.  
   **Tradeoff**: Salary range may be lower than some expectations.

4. **Company**: Musa  
   **Title**: Mobile Engineer (iOS/Android)  
   **Location**: Remote  
   **Remote**: Remote  
   **Salary**: Not specified  
   **Key Matching Details**: This position involves mobile development with a focus on iOS and Android, providing a broad scope of mobile engineering experience.  
   **Tradeoff**: Salary details are not available.

5. **Company**: Chatwoot  
   **Title**: React Native Developer  
   **Location**: Remote  
   **Remote**: Remote  
   **Salary**: Not specified  
   **Key Matching Details**: This role is specifically for a React Native Developer, making it a direct match for your skills and interests.  
   **Tradeoff**: Salary information is not provided.

### Summary
The top picks include a mix of onsite and remote opportunities, with a strong emphasis on mobile development roles that align with your interests in Flutter and React Native. Songscription and EnsoData stand out for their direct relevance to your tech stack, while Revelare Networks offers a solid salary range but with a broader mobile focus. If remote flexibility is a priority, EnsoData and Chatwoot are excellent choices.

---

### q22
**User query:** Engineering manager or tech lead openings

**Extracted preferences:**
```json
{
  "description_keywords": [
    "engineering manager",
    "tech lead"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": "management",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Engineering Manager, Community Support Engineering (Routing and Data Services) @ AIRBNB
  - Location: China | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, Rust
  - Category: management
  - Final score: 0.376
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Unknown @ Looking for a CTO / Tech Lead A startup producing 
  - Location: Unknown | Remote: onsite
  - Salary: not specified
  - Category: management
  - Final score: 0.431
  - Snippet: Looking for a CTO / Tech Lead A startup producing short-form vertical video series for mobile platforms is looking for a CTO / Tech Lead to lead the technical side of the company. Looking for someone who: - Is based in the US (mandatory, no…
- **#3** Engineering Manager, Quality Platform @ AIRBNB
  - Location: São Paulo, Brazil | Remote: onsite
  - Salary: not specified
  - Tags: AI, ML, Rust
  - Category: management
  - Final score: 0.372
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Senior Staff Software Engineer, Payments @ AIRBNB
  - Location: Bangalore, India | Remote: remote
  - Salary: not specified
  - Tags: AI, Go
  - Category: management
  - Final score: 0.347
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Engineering Manager, Experimentation Infrastructure @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $204,000+
  - Tags: AI, Go
  - Category: management
  - Final score: 0.341
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#6** Engineering Manager (Data Platform) @ Apple
  - Location: San Francisco | Remote: onsite
  - Salary: not specified
  - Tags: AI, Go, ML, Rust
  - Category: management
  - Final score: 0.384
  - Snippet: Apple | Engineering Manager (Data Platform) | Cupertino, CA | Full-time Apple’s Data Platform team is hiring an Engineering Manager to lead a small, high-impact team building distributed data infrastructure at Apple scale. This team owns a …
- **#7** Staff Software Engineer, Community Support Engineering @ AIRBNB
  - Location: China | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, Java, Python, React
  - Category: management
  - Final score: 0.338
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#8** Engineering Manager, Network Infrastructure (Cloud) @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, AWS, Go
  - Category: management
  - Final score: 0.336
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#9** Engineering Manager, Listings Products @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, ML, Rust
  - Category: management
  - Final score: 0.334
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#10** Engineering Manager (Analytics Product) @ Greenhouse Software
  - Location: Remote | Remote: remote
  - Salary: $142,700 – $214,100
  - Tags: AI, Go, Java, React, TypeScript
  - Category: management
  - Final score: 0.372
  - Snippet: Greenhouse Software | Engineering Manager (Analytics Product) | REMOTE (Ontario or BC, Canada) | Full-time | We're unable to support sponsorship at this time. Greenhouse is the company dedicated to making hiring work for everyone. We help o…

**System answer to rate:**

Here are the top job openings for Engineering Manager or Tech Lead positions that match your query:

1. **Company:** AIRBNB  
   **Title:** Engineering Manager, Community Support Engineering (Routing and Data Services)  
   **Location:** China  
   **Remote:** Yes  
   **Salary:** Not specified  
   **Key Match:** Strong alignment with your management category preference and relevant tech stack (AI, Go, Rust).  
   **Tradeoff:** Location may be a consideration as it's based in China.

2. **Company:** Startup (CTO / Tech Lead)  
   **Title:** Unknown  
   **Location:** Unknown  
   **Remote:** Onsite  
   **Salary:** Not specified  
   **Key Match:** High relevance in the tech lead role with a focus on mobile platforms, although details are limited.  
   **Tradeoff:** Lack of specific location and salary information could be a drawback.

3. **Company:** AIRBNB  
   **Title:** Engineering Manager, Quality Platform  
   **Location:** São Paulo, Brazil  
   **Remote:** Onsite  
   **Salary:** Not specified  
   **Key Match:** Matches management category and involves AI, ML, and Rust technologies.  
   **Tradeoff:** Onsite requirement may not suit all candidates.

4. **Company:** AIRBNB  
   **Title:** Senior Staff Software Engineer, Payments  
   **Location:** Bangalore, India  
   **Remote:** Yes  
   **Salary:** Not specified  
   **Key Match:** Relevant management role with a focus on AI and Go technologies.  
   **Tradeoff:** Location may be a barrier for some candidates.

5. **Company:** AIRBNB  
   **Title:** Engineering Manager, Experimentation Infrastructure  
   **Location:** United States  
   **Remote:** Yes  
   **Salary:** $204,000+  
   **Key Match:** Strong salary fit and relevant tech stack (AI, Go).  
   **Tradeoff:** Competitive environment typical of large companies.

6. **Company:** Apple  
   **Title:** Engineering Manager (Data Platform)  
   **Location:** San Francisco  
   **Remote:** Onsite  
   **Salary:** Not specified  
   **Key Match:** High relevance in management with a strong tech stack (AI, Go, ML, Rust).  
   **Tradeoff:** Onsite requirement may limit flexibility.

7. **Company:** AIRBNB  
   **Title:** Staff Software Engineer, Community Support Engineering  
   **Location:** China  
   **Remote:** Yes  
   **Salary:** Not specified  
   **Key Match:** Relevant management category and tech stack (AI, Go, Java, Python, React).  
   **Tradeoff:** Location may be a consideration as it's based in China.

8. **Company:** AIRBNB  
   **Title:** Engineering Manager, Network Infrastructure (Cloud)  
   **Location:** Remote - USA  
   **Remote:** Yes  
   **Salary:** $204,000+  
   **Key Match:** Strong salary and relevant tech stack (AI, AWS, Go).  
   **Tradeoff:** Competitive nature of the role.

9. **Company:** AIRBNB  
   **Title:** Engineering Manager, Listings Products  
   **Location:** Remote - USA  
   **Remote:** Yes  
   **Salary:** $204,000+  
   **Key Match:** Strong salary fit and relevant tech stack (AI, ML, Rust).  
   **Tradeoff:** High competition for roles at Airbnb.

10. **Company:** Greenhouse Software  
    **Title:** Engineering Manager (Analytics Product)  
    **Location:** Remote  
    **Remote:** Yes  
    **Salary:** $142,700 - $214,100  
    **Key Match:** Competitive salary range and relevant tech stack (AI, Go, Java, React, TypeScript).  
    **Tradeoff:** Company may not support sponsorship.

### Summary
The top picks predominantly feature positions at Airbnb, offering strong salary prospects and relevant tech stacks, particularly in AI and Go. However, many roles are onsite, which may limit options for remote work. The startup opportunity is intriguing but lacks specific details. If remote flexibility is a priority, consider the roles at Airbnb and Greenhouse Software.

---

### q25
**User query:** Site reliability engineer SRE jobs

**Extracted preferences:**
```json
{
  "description_keywords": [
    "site reliability engineer",
    "SRE"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": "devops",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Software Engineer, Reliability Engineering @ AIRBNB
  - Location: São Paulo, Brazil | Remote: onsite
  - Salary: not specified
  - Tags: AI, AWS, Docker, Go, Java, Kubernetes, Python
  - Category: devops
  - Final score: 0.460
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Cloud Site Reliability Engineer @ Ford Motor Company
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go, Kubernetes, Python
  - Category: devops
  - Final score: 0.517
  - Snippet: Ford Motor Company | Cloud Site Reliability Engineer | Full-Time | Remote (US) | 113k-190k USD Visa Sponsorship Is not provided. Ford is seeking an experienced and passionate Site Reliability Engineer (SRE) to join our team. You will play a…
- **#3** Staff/Senior Security Software Engineer or SRE @ MongoDB
  - Location: Remote or New York City | Remote: remote
  - Salary: not specified
  - Tags: AI, AWS, Go, Kubernetes, Python, Rust
  - Category: devops
  - Final score: 0.478
  - Snippet: MongoDB | Staff/Senior Security Software Engineer or SRE - Infrastructure Security | REMOTE (US) or HYBRID (NYC) | Full-Time We are looking for experienced Software and Site Reliability Engineers to help secure the foundation of MongoDB Atl…
- **#4** Lead DevOps / SRE @ Jurisphere.ai
  - Location: Hybrid | Remote: hybrid
  - Salary: not specified
  - Tags: AI, AWS, Go, Kubernetes, ML
  - Category: devops
  - Final score: 0.441
  - Snippet: Jurisphere.ai | Lead DevOps / SRE | Bangalore (Hybrid) | Full-time Comp: ₹40–60L + ESOPs (flexible) Exp: 6–12+ yrs Jurisphere builds an enterprise Legal AI platform used by top law firms in India & the US. We’re hiring our first SRE / Platf…
- **#5** Senior SRE + Full Stack Engineer @ Parabola
  - Location: San Francisco | Remote: hybrid
  - Salary: not specified
  - Tags: AI, Go
  - Category: devops
  - Final score: 0.431
  - Snippet: Parabola | Senior SRE + Full Stack Engineer | NYC/SF Hybrid | Full-time We're building the AI-powered workflow automation platform that ops and finance teams at Lyft, Flexport, WHOOP, 1000+ other companies use to escape spreadsheet hell. Th…
- **#6** Senior Site Reliability Engineer @ Lumin Digital
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Go
  - Category: devops
  - Final score: 0.425
  - Snippet: Lumin Digital | Senior Site Reliability Engineer | Full-Time | Remote (US) | 170k-200k USD base, plus bonus+equity Visa Sponsorship is not provided. At Lumin Digital, we serve digital banking needs for financial institutions of all types an…
- **#7** Senior SRE + Full Stack Engineer @ Parabola
  - Location: San Francisco | Remote: hybrid
  - Salary: not specified
  - Tags: AI
  - Category: devops
  - Final score: 0.420
  - Snippet: Parabola | Senior SRE + Full Stack Engineer | NYC/SF ONSITE-Hybrid | Full-time We're building the AI-powered workflow automation platform that ops and finance teams at Lyft, Flexport, WHOOP, 1000+ other companies use to turn their business …
- **#8** Unknown @ Hiring Tech Lead and SRE – REMOTE LATAM
  - Location: Remote or OK | Remote: remote
  - Salary: not specified
  - Tags: AI, Kubernetes, Python, TypeScript
  - Category: devops
  - Final score: 0.414
  - Snippet: Hiring Tech Lead and SRE – REMOTE LATAM - We build AI tools that help high-volume law firms manage their caseloads more efficiently. Our first product—an AI assistant that transcribes and classifies inbound calls—is in production. We’re now…
- **#9** scale pipelines, backend Python engineers for our platform. Story:  https://venturebeat.com/ai/alembic @ Alembic
  - Location: San Francisco | Remote: onsite
  - Salary: $145,000+
  - Tags: AI, Python
  - Category: devops
  - Final score: 0.410
  - Snippet: Alembic | SF (5 days onsite) | SRE • C++ AI • Backend Python • Data Engineering Causal AI at scale for Fortune 500. We melted GPUs building this—now running one of the world's fastest private supercomputers. The only non-Fortune 500 company…
- **#10** Unknown @ EnigmoFi
  - Location: Remote | Remote: remote
  - Salary: $192,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes
  - Category: devops
  - Final score: 0.396
  - Snippet: EnigmoFi | DevOps / SRE (Cloud & Infrastructure) | Remote | $192k + bonus EnigmoFi is a crypto financial infrastructure startup building secure, scalable digital finance systems. We’re hiring a senior DevOps / SRE to own and scale productio…

**System answer to rate:**

Here are the top site reliability engineer (SRE) job matches for you:

1. **Company:** Ford Motor Company  
   **Title:** Cloud Site Reliability Engineer  
   **Location:** Remote  
   **Remote:** Yes  
   **Key Matching Details:** This position offers a fully remote setup, aligning well with potential remote work preferences. The role involves a tech stack that includes AI, Go, Kubernetes, and Python, which is relevant for SRE roles.  
   **Tradeoffs:** Salary is not specified, but the company is known for competitive compensation.  

2. **Company:** MongoDB  
   **Title:** Staff/Senior Security Software Engineer or SRE  
   **Location:** Remote or New York City  
   **Remote:** Yes  
   **Key Matching Details:** This role is flexible with remote or hybrid options, making it suitable for various work preferences. The tech stack includes AI, AWS, Go, Kubernetes, and Python, which are highly relevant for SRE positions.  
   **Tradeoffs:** Salary is not specified, but MongoDB typically offers competitive packages.  

3. **Company:** Lumin Digital  
   **Title:** Senior Site Reliability Engineer  
   **Location:** Remote  
   **Remote:** Yes  
   **Key Matching Details:** This position is fully remote and offers a salary range of $170k-$200k, which is appealing for SRE roles. The tech stack includes AI and Go, relevant for the position.  
   **Tradeoffs:** Visa sponsorship is not provided, which may limit some candidates.  

4. **Company:** AIRBNB  
   **Title:** Senior Software Engineer, Reliability Engineering  
   **Location:** São Paulo, Brazil  
   **Remote:** Onsite  
   **Key Matching Details:** This role is focused on reliability engineering, fitting well within the SRE scope. The tech stack includes AWS, Docker, Go, Java, Kubernetes, and Python, which are highly relevant.  
   **Tradeoffs:** Onsite requirement may not suit those looking for remote work. Salary is not specified.  

5. **Company:** Jurisphere.ai  
   **Title:** Lead DevOps / SRE  
   **Location:** Hybrid (Bangalore)  
   **Remote:** Hybrid  
   **Key Matching Details:** This position allows for hybrid work and involves a tech stack relevant to SRE roles, including AI and Kubernetes.  
   **Tradeoffs:** Salary is not specified, and the location may not be ideal for all candidates.  

### Summary
The top picks highlight a strong preference for remote work opportunities, particularly with Ford and MongoDB leading the way. Lumin Digital offers a competitive salary range, while Airbnb and Jurisphere.ai provide strong tech stack matches but have onsite or hybrid requirements. Consider your preferences for remote work and salary when making a decision.

---

### q26
**User query:** Remote ML jobs in New York above 130k

**Extracted preferences:**
```json
{
  "description_keywords": [
    "machine learning"
  ],
  "target_salary": 130000,
  "preferred_location": "New York",
  "remote_preference": "remote",
  "desired_tags": [
    "Machine Learning"
  ],
  "preferred_category": "data",
  "weight_adjustments": {
    "location": "high",
    "salary": "medium"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Data Scientist, Causal Inference @ AIRBNB
  - Location: Remote | Remote: remote
  - Salary: $179,000+
  - Tags: AI, Python
  - Category: data
  - Final score: 0.494
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Founding ML Engineer, Growth Engineer @ Lucia
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $240,000
  - Tags: AI, ML
  - Category: data
  - Final score: 0.601
  - Snippet: Lucia | Founding ML Engineer, Growth Engineer | Remote | Luciaprotocol.com Lucia is changing how data can be used for growth and revenue generation. With our open source SDK you can collect 10x the amount of data from your visitors whether …
- **#3** Product Manager @ EnsoData
  - Location: Remote or Milwaukee | Remote: remote
  - Salary: $110,000 – $130,000
  - Tags: AI
  - Category: data
  - Final score: 0.596
  - Snippet: EnsoData | healthcare, sleep, machine learning | Hybrid or Remote (Madison, WI) | Product Manager - Software Medical Devices SaaS | Full Time | $110k-$130k + bonus, stock options | https://apply.workable.com/ensodata/j/5FD6175FEB/ Sleep is …
- **#4** Staff Machine Learning Engineer, Listings and Host Tools Data and AI @ AIRBNB
  - Location: Remote-USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, C++, Go, Java, Kubernetes, ML, Python
  - Category: data
  - Final score: 0.487
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Principal AI Engineer @ PhysicsX
  - Location: Remote or NY | Remote: remote
  - Salary: $135,000+
  - Tags: AI, Go
  - Category: data
  - Final score: 0.590
  - Snippet: PhysicsX | Principal AI Engineer | London / NY / Remote | Full time | physicsx.ai We're building an AI-native platform that turns physics simulations from days-long jobs into millisecond inference. Think: training deep learning surrogates o…
- **#6** iOS Software Engineer, Host Pricing @ AIRBNB
  - Location: Remote, USA | Remote: remote
  - Salary: $157,000+
  - Tags: AI
  - Category: management
  - Final score: 0.483
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#7** Unknown @ Confluence
  - Location: Remote | Remote: remote
  - Salary: $100,000 – $300,000
  - Category: data
  - Final score: 0.583
  - Snippet: Confluence | hourly consultant | remote Research analyst (non-technical) looking for someone to help bridge the gap on some of the more technical aspects on neoclouds. Interested in views from a customer perspective as well as operators. Pa…
- **#8** opening insights. Atlanta, US engineering roles (semi @ Fullstory
  - Location: Remote or Atlanta | Remote: remote
  - Salary: $145,000+
  - Tags: AI, Go, Java, Kubernetes, React, TypeScript
  - Category: data
  - Final score: 0.582
  - Snippet: Fullstory | Atlanta, USA & Bogotá, Colombia | https://www.fullstory.com/ Fullstory offers privacy-preserving session replay and analytics for websites and mobile apps. Our session replays are nothing short of magical, and the combination wi…
- **#9** Senior Machine Learning Engineer @ Nomi.ai
  - Location: Remote | Remote: remote
  - Salary: $150,000+
  - Tags: AI, ML
  - Category: data
  - Final score: 0.580
  - Snippet: Nomi.ai | https://nomi.ai | Senior Machine Learning Engineer | Remote (Global) | Full-time | $150k–$250k + equity At Nomi, we're building AI companions that form deeply meaningful, humanlike relationships and immersive roleplaying experienc…
- **#10** Software Engineer, Guest & Host  @ AIRBNB
  - Location: Remote, USA  | Remote: remote
  - Salary: $160,000+
  - Tags: AI, Go, Java, ML, React
  - Category: management
  - Final score: 0.473
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…

**System answer to rate:**

Here are the top remote machine learning jobs that match your criteria of being based in New York and offering a salary above $130,000:

1. **Company:** AIRBNB  
   **Title:** Senior Data Scientist, Causal Inference  
   **Salary:** $179,000+  
   **Key Matching Details:** This position is fully remote and offers a strong salary that exceeds your target. It also aligns well with your interest in data and machine learning.  
   **Tradeoffs:** None significant, as it meets all your criteria well.  

2. **Company:** Lucia  
   **Title:** Founding ML Engineer, Growth Engineer  
   **Salary:** $135,000 - $240,000  
   **Key Matching Details:** This role is remote and starts at your salary target, with potential for higher earnings. It focuses on machine learning and data, fitting your desired category perfectly.  
   **Tradeoffs:** The job is relatively new and may involve more startup-related risks.  

3. **Company:** PhysicsX  
   **Title:** Principal AI Engineer  
   **Salary:** $135,000+  
   **Key Matching Details:** This position is remote and offers a salary that meets your target. It also emphasizes AI, which is relevant to your interests.  
   **Tradeoffs:** The description is less detailed, which may require further inquiry into the role's specifics.  

4. **Company:** Nomi.ai  
   **Title:** Senior Machine Learning Engineer  
   **Salary:** $150,000+  
   **Key Matching Details:** Fully remote and offers a competitive salary. The role is focused on AI and machine learning, aligning well with your preferences.  
   **Tradeoffs:** The salary range is broad, so the final offer may vary significantly based on experience.  

5. **Company:** EnsoData  
   **Title:** Product Manager  
   **Salary:** $110,000 - $130,000  
   **Key Matching Details:** This role is remote and offers a salary close to your target, with a focus on machine learning in healthcare.  
   **Tradeoffs:** The salary is slightly below your target, which may not fully meet your expectations.  

### Summary
The top picks are led by AIRBNB's Senior Data Scientist role, which offers a high salary and a solid match for your interests. Lucia's Founding ML Engineer position also stands out with a flexible salary range and a focus on growth. PhysicsX and Nomi.ai provide competitive salaries and relevant roles, while EnsoData is a close match but slightly below your salary target. Consider your priorities regarding salary versus role specifics when making a decision.

---

### q27
**User query:** Backend Go developer, hybrid, 160k or more

**Extracted preferences:**
```json
{
  "description_keywords": [
    "backend",
    "Go developer"
  ],
  "target_salary": 160000,
  "preferred_location": null,
  "remote_preference": "hybrid",
  "desired_tags": [
    "Go"
  ],
  "preferred_category": "backend",
  "weight_adjustments": {
    "salary": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Software Engineer- Database Infrastructure @ DISCORD
  - Location: San Francisco Bay Area  | Remote: onsite
  - Salary: $160,000+
  - Tags: AI, C++, Go, Java, Kubernetes, PostgreSQL, Rust
  - Category: backend
  - Final score: 0.623
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#2** Senior Software Engineer @ Vestwell
  - Location: New York City | Remote: hybrid
  - Salary: $145,000 – $160,000
  - Tags: AI, Go, TypeScript
  - Category: backend
  - Final score: 0.685
  - Snippet: Vestwell | Senior Software Engineer | HYBRID - NYC; Austin; King of Prussia, PA | https://www.vestwell.com/careers/7510610003 | $145K - $160K base + bonus & equity I'm the hiring manager for this role. Please see the job description for det…
- **#3** Product Manager, AI Platform @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $169,000+
  - Tags: AI, Go, ML, Rust
  - Category: backend
  - Final score: 0.623
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#4** Senior Software Engineer @ Bloomberg
  - Location: New York City | Remote: hybrid
  - Salary: $160,000 – $240,000
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.677
  - Snippet: Bloomberg | Senior Software Engineer | Hybrid (NYC) | Full-time | $160k - $240k USD + bonus Every day, Bloomberg’s clients rely on secure and seamless access to our products. Our team makes that possible by building infrastructure that veri…
- **#5** Senior Software Engineer @ Bloomberg
  - Location: New York City | Remote: hybrid
  - Salary: $160,000 – $240,000
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.677
  - Snippet: Bloomberg | Senior Software Engineer | Hybrid (NYC) | Full-time | $160k - $240k USD + bonus Every day, Bloomberg’s clients rely on secure and seamless access to our products. Our team makes that possible by building infrastructure that veri…
- **#6** Senior Software Engineer @ Bloomberg
  - Location: New York City | Remote: hybrid
  - Salary: $160,000 – $240,000
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.677
  - Snippet: Bloomberg | Senior Software Engineer | Hybrid (NYC) | Full-time | $160k - $240k USD + bonus Every day, Bloomberg’s clients rely on secure and seamless access to our products. Our team makes that possible by building infrastructure that veri…
- **#7** Senior Software Engineer @ Bloomberg
  - Location: New York City | Remote: hybrid
  - Salary: $160,000 – $240,000
  - Tags: AI, Go, ML
  - Category: backend
  - Final score: 0.677
  - Snippet: Bloomberg | Senior Software Engineer | Hybrid (NYC) | Full-time | $160k - $240k USD + bonus Every day, Bloomberg’s clients rely on secure and seamless access to our products. Our team makes that possible by building infrastructure that veri…
- **#8** Various Software Engineering Roles @ Prophet Town LLC
  - Location: Hybrid | Remote: hybrid
  - Salary: $150,000 – $250,000
  - Tags: AI, AWS, Go, Python, React, TypeScript
  - Category: backend
  - Final score: 0.673
  - Snippet: Prophet Town LLC | Various Software Engineering Roles | US – Remote and Hybrid | English fluency required | Full-time | $150K-$250K annual total comp (multiple) I’m the founder, trying to do “enlightened business.” We are a people-first, fu…
- **#9** Staff backend engineer @ Nango
  - Location: Remote | Remote: remote
  - Salary: $120,000 – $200,000
  - Tags: Go, Rust
  - Category: backend
  - Final score: 0.669
  - Snippet: Nango | Staff backend engineer | Remote | Full time | $120-200k + equity Nango (YC W23) is an open source product: Developer infrastructure for product integrations. We power the integrations of Semgrep, Motion, Vapi, Exa, and hundreds of o…
- **#10** Staff backend engineer @ Nango
  - Location: Remote | Remote: remote
  - Salary: $120,000 – $200,000
  - Tags: AI, Go, Rust
  - Category: backend
  - Final score: 0.668
  - Snippet: Nango | Staff backend engineer | Remote | Full time | $120-200k + equity Nango (YC W23) is an open-source developer infrastructure for product integrations. We power the integrations of Replit, Semgrep, Motion, Vapi, Exa, and hundreds of ot…

**System answer to rate:**

Here are the top job matches for a Backend Go Developer position with a hybrid work preference and a salary of $160,000 or more:

1. **Company:** DISCORD  
   **Title:** Software Engineer - Database Infrastructure  
   **Location:** San Francisco Bay Area  
   **Remote:** Onsite  
   **Salary:** $160,000+  
   **Key Matching Details:** This position meets your salary target and is in the backend category with a strong tech stack that includes Go. However, it is onsite, which may not align with your hybrid preference.  
   **Tradeoff:** Onsite work may limit flexibility.

2. **Company:** Vestwell  
   **Title:** Senior Software Engineer  
   **Location:** New York City  
   **Remote:** Hybrid  
   **Salary:** $145,000 - $160,000  
   **Key Matching Details:** This role offers a hybrid work model and aligns closely with your desired tech stack (Go). The salary is slightly below your target but includes potential bonuses and equity.  
   **Tradeoff:** Salary is at the lower end of your range.

3. **Company:** Bloomberg  
   **Title:** Senior Software Engineer  
   **Location:** New York City  
   **Remote:** Hybrid  
   **Salary:** $160,000 - $240,000  
   **Key Matching Details:** This position offers a strong salary range that meets and exceeds your target, along with a hybrid work model and relevant tech stack (Go).  
   **Tradeoff:** High competition and expectations in a well-established company.

4. **Company:** Prophet Town LLC  
   **Title:** Various Software Engineering Roles  
   **Location:** Hybrid  
   **Remote:** Hybrid  
   **Salary:** $150,000 - $250,000  
   **Key Matching Details:** This role offers a flexible hybrid model and a competitive salary range. It also includes Go in its tech stack.  
   **Tradeoff:** The specific role within the company may vary, so clarity on responsibilities is needed.

5. **Company:** Nango  
   **Title:** Staff Backend Engineer  
   **Location:** Remote  
   **Remote:** Remote  
   **Salary:** $120,000 - $200,000  
   **Key Matching Details:** This fully remote position meets your tech stack requirement (Go) and offers a competitive salary range.  
   **Tradeoff:** The lower end of the salary range is below your target, but the remote flexibility is a strong plus.

### Summary
The best options for you include Bloomberg and Vestwell, both offering hybrid work and salaries that meet or exceed your target. Bloomberg stands out for its higher salary potential, while Vestwell provides a solid hybrid model with a slightly lower salary. If remote work is a priority, Nango offers flexibility but at a lower salary range. Consider what tradeoffs you're willing to make regarding salary versus work flexibility.

---

### q28
**User query:** Full stack JavaScript developer in San Francisco, remote friendly, around 140k

**Extracted preferences:**
```json
{
  "description_keywords": [
    "full stack",
    "JavaScript developer"
  ],
  "target_salary": 140000,
  "preferred_location": "San Francisco",
  "remote_preference": "hybrid",
  "desired_tags": [
    "JavaScript"
  ],
  "preferred_category": "fullstack",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** iOS Software Engineer, Host Pricing @ AIRBNB
  - Location: Remote, USA | Remote: remote
  - Salary: $157,000+
  - Tags: AI
  - Category: management
  - Final score: 0.413
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Full Stack Product Engineer (Ruby, JavaScript) @ Digital Health Strategies
  - Location: Remote or New York City | Remote: remote
  - Salary: $140,000 – $220,000
  - Tags: AI, AWS, Docker, Java
  - Category: fullstack
  - Final score: 0.597
  - Snippet: Digital Health Strategies | Full Stack Product Engineer (Ruby, JavaScript) | REMOTE (USA or Canada); Washington, DC; NYC; Vancouver, BC; | https://digitalhealthstrategies.com | $140k - $220k We are a series B health tech and data company bu…
- **#3** Full Stack Product Engineer (Ruby, JavaScript) @ Digital Health Strategies
  - Location: Remote or New York City | Remote: remote
  - Salary: $140,000 – $220,000
  - Tags: AI, AWS, Docker, Java
  - Category: fullstack
  - Final score: 0.596
  - Snippet: Digital Health Strategies | Full Stack Product Engineer (Ruby, JavaScript) | REMOTE; Washington, DC; NYC; Vancouver, BC; (only USA or Canada) | https://digitalhealthstrategies.com | $140k - $220k We are a series A health tech and data compa…
- **#4** Software Engineer, Guest & Host  @ AIRBNB
  - Location: Remote, USA  | Remote: remote
  - Salary: $160,000+
  - Tags: AI, Go, Java, ML, React
  - Category: management
  - Final score: 0.399
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Full Stack Web Developer @ Level 12
  - Location: Remote | Remote: remote
  - Salary: $95,000 – $145,000
  - Tags: Go, Java, Python
  - Category: fullstack
  - Final score: 0.563
  - Snippet: Level 12 | Full Stack Web Developer - Python, JavaScript, SQL | Mid-Level & Senior | REMOTE | SALARY:$95K-145K+ | https://www.level12.io/careers/ Level 12 is a software consulting and custom development agency. We have mid and senior level …
- **#6** Full Stack Web Developer @ Level 12
  - Location: Remote | Remote: remote
  - Salary: $95,000 – $145,000
  - Tags: Go, Java, Python
  - Category: fullstack
  - Final score: 0.563
  - Snippet: Level 12 | Full Stack Web Developer - Python, JavaScript, SQL | Mid-Level & Senior | REMOTE | SALARY:$95K-145K+ | https://www.level12.io/careers/ Level 12 is a software consulting and custom development agency. We have mid and senior level …
- **#7** Founding Engineer @ Miniswap
  - Location: San Francisco | Remote: hybrid
  - Salary: $150,000+
  - Tags: AI, React, Rust
  - Category: fullstack
  - Final score: 0.546
  - Snippet: Miniswap | Founding Engineer | Full-time | ONSITE (hybrid) San Francisco | No visa sponsorships Miniswap is a marketplace for complex hobbies, starting with Warhammer. We're backed by Y Combinator and have just closed our seed funding round…
- **#8** Founding Engineer @ YourTechResume
  - Location: Remote | Remote: remote
  - Salary: $150,000 – $350,000
  - Tags: AI, AWS, Docker, Go, Java, ML, Python
  - Category: fullstack
  - Final score: 0.525
  - Snippet: YourTechResume — Founding Engineer Remote (Global) | Full-time | $150k-$350k About: AI-powered platform for resume optimization and job application automation. Role: Build technical foundation as the first engineering hire. Own end-to-end f…
- **#9** Full Stack Engineer $150k–$230k @ PetsApp – The future of pet care
  - Location: Remote | Remote: remote
  - Salary: $150,000+
  - Tags: AI, AWS, React, TypeScript
  - Category: fullstack
  - Final score: 0.517
  - Snippet: PetsApp – The future of pet care | Remote (US/UK/EU) | https://petsapp.com Open roles: - Full Stack Engineer $150k–$230k | Full-time We’re building an AI-powered clinic assistant that actually gets things done—booking appointments, managing…
- **#10** Unknown @ Pure / collectpure.com
  - Location: Remote or Los Angeles | Remote: remote
  - Salary: $145,000 – $200,000
  - Tags: AI, TypeScript
  - Category: fullstack
  - Final score: 0.516
  - Snippet: Pure / collectpure.com | Los Angeles ability to start remote |$145,000 - $200,000 + significant early-stage equity About Pure: Modernizing a Multi-Billion Dollar Market Started in 2023, Pure is one of the fastest-growing marketplaces for ta…

**System answer to rate:**

Here are the top job matches for a Full Stack JavaScript Developer in San Francisco, with a focus on remote-friendly positions around your target salary of $140,000:

1. **Digital Health Strategies**
   - **Title:** Full Stack Product Engineer (Ruby, JavaScript)
   - **Location:** Remote or New York City
   - **Salary:** $140,000 - $220,000
   - **Matching Details:** This role offers a salary that meets your target and is fully remote, providing flexibility. The tech stack includes JavaScript, aligning well with your skills.
   - **Tradeoffs:** While the location is not San Francisco, it allows for remote work, which may compensate for that.

2. **Miniswap**
   - **Title:** Founding Engineer
   - **Location:** San Francisco (hybrid)
   - **Salary:** $150,000+
   - **Matching Details:** This position is located in San Francisco and offers a hybrid work model, which fits your preference. The salary is above your target but reflects the seniority of the role.
   - **Tradeoffs:** The salary is higher than your target, which may be a positive if you are open to negotiating.

3. **Level 12**
   - **Title:** Full Stack Web Developer
   - **Location:** Remote
   - **Salary:** $95,000 - $145,000
   - **Matching Details:** This job is remote and offers a salary range that includes your target. It also involves full stack development, which is what you are looking for.
   - **Tradeoffs:** The upper limit of the salary is slightly below your target, but it may still be a good opportunity if you value remote work.

4. **YourTechResume**
   - **Title:** Founding Engineer
   - **Location:** Remote
   - **Salary:** $150,000 - $350,000
   - **Matching Details:** This role is fully remote and offers a competitive salary range that exceeds your target. It also involves working with a modern tech stack.
   - **Tradeoffs:** The salary range is quite broad, and the lower end is above your target, which may indicate a high level of expectation for the role.

5. **PetsApp**
   - **Title:** Full Stack Engineer
   - **Location:** Remote
   - **Salary:** $150,000 - $230,000
   - **Matching Details:** This position is remote and offers a salary that exceeds your target, along with a focus on full stack development.
   - **Tradeoffs:** Similar to the previous roles, the salary is above your target, which may reflect the demands of the position.

### Summary
The best match for your criteria is the **Full Stack Product Engineer** role at **Digital Health Strategies**, as it meets your salary target and offers remote flexibility. The **Miniswap** position is also strong, offering a hybrid model in San Francisco but at a higher salary. Other options like **Level 12**, **YourTechResume**, and **PetsApp** provide remote opportunities with salaries above your target, which could be worth considering if you're flexible on compensation.

---

### q29
**User query:** Senior data engineer with Spark and Kafka experience, preferably remote, 170k+

**Extracted preferences:**
```json
{
  "description_keywords": [
    "senior",
    "data engineer"
  ],
  "target_salary": 170000,
  "preferred_location": null,
  "remote_preference": "remote",
  "desired_tags": [
    "Spark",
    "Kafka"
  ],
  "preferred_category": "data",
  "weight_adjustments": {
    "salary": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Data Scientist, Core Data -  PhD (2026) @ FIGMA
  - Location: New York, NY • United States; San Francisco, CA • New York, NY | Remote: remote
  - Salary: $170,000+
  - Tags: AI, Go, ML, Python
  - Category: data
  - Final score: 0.602
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#2** Principal Product Engineer, Principal ML Engineer @ HelloData (Grace Hill)
  - Location: Remote | Remote: remote
  - Salary: $175,000+
  - Tags: AI, Go, ML, Python, TypeScript
  - Category: data
  - Final score: 0.649
  - Snippet: HelloData (Grace Hill) | Principal Product Engineer, Principal ML Engineer | Remote (US Only) | Full-Time | $175K–$250K + Bonus | https://www.hellodata.ai HelloData is an automated market analysis platform for multifamily real estate. We pr…
- **#3** Senior Data Scientist, Causal Inference @ AIRBNB
  - Location: Remote | Remote: remote
  - Salary: $179,000+
  - Tags: AI, Python
  - Category: data
  - Final score: 0.585
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Senior Data Scientist, Platform - Identity/Algorithms @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $177,000+
  - Tags: AI, Go, ML, Python, Rust
  - Category: data
  - Final score: 0.577
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Senior Data Scientist, Platform (Algorithms/Trust) @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $177,000+
  - Tags: AI, Go, ML, Python, Rust
  - Category: data
  - Final score: 0.575
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#6** Founding ML Engineer, Growth Engineer @ Lucia
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $240,000
  - Tags: AI, ML
  - Category: data
  - Final score: 0.613
  - Snippet: Lucia | Founding ML Engineer, Growth Engineer | Remote | Luciaprotocol.com Lucia is changing how data can be used for growth and revenue generation. With our open source SDK you can collect 10x the amount of data from your visitors whether …
- **#7** Founding AI Engineer + Founding Data Engineer @ Rapport
  - Location: Remote | Remote: remote
  - Salary: $160,000 – $220,000
  - Tags: AI, AWS, ML, Python
  - Category: data
  - Final score: 0.604
  - Snippet: Rapport | Founding AI Engineer + Founding Data Engineer | REMOTE (US) | Full-time | USD$160-220K+ Rapport is fixing healthcare's broken payment infrastructure. Hospitals lose billions annually to opaque payer rules and outdated contracts. W…
- **#8** Founding AI Engineer + Founding Data Engineer @ Rapport
  - Location: Remote | Remote: remote
  - Salary: $160,000 – $220,000
  - Tags: AI, AWS, ML, Python
  - Category: data
  - Final score: 0.603
  - Snippet: Rapport | Founding AI Engineer + Founding Data Engineer | REMOTE (US) | Full-time | USD$160-220K+ Rapport is fixing healthcare's broken payment infrastructure. Hospitals lose billions annually to opaque payer rules and outdated contracts. W…
- **#9** Staff Software Engineer, Data Engineering @ AIRBNB
  - Location: United States | Remote: remote
  - Salary: $191,000+
  - Tags: AI, Go, Java, ML, PostgreSQL, Python, Rust
  - Category: data
  - Final score: 0.562
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#10** Software Engineers & Designers @ Brilliant.org
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $170,000+
  - Category: data
  - Final score: 0.588
  - Snippet: Brilliant.org | Software Engineers & Designers | Remote (North America), SF, NYC | Full-time | $170k — $235k | https://brilliant.org Brilliant is building world-class interactive learning experiences that combine challenging problems, compe…

**System answer to rate:**

Here are the top job opportunities for a Senior Data Engineer with Spark and Kafka experience, focusing on remote positions and a salary of $170k or more:

1. **Company:** HelloData (Grace Hill)  
   **Title:** Principal Product Engineer, Principal ML Engineer  
   **Location:** Remote  
   **Salary:** $175,000+  
   **Key Matching Details:** This position offers a salary above your target and is fully remote. While the tech stack includes AI and ML, it does not specifically mention Spark or Kafka, which may be a tradeoff.  
   **Final Score:** 0.649  

2. **Company:** AIRBNB  
   **Title:** Senior Data Scientist, Causal Inference  
   **Location:** Remote  
   **Salary:** $179,000+  
   **Key Matching Details:** This role is remote and offers a salary above your target. It focuses on data science, and while it does not explicitly mention Spark or Kafka, it is in the data category, which may align with your skills.  
   **Final Score:** 0.585  

3. **Company:** AIRBNB  
   **Title:** Senior Data Scientist, Platform - Identity/Algorithms  
   **Location:** Remote  
   **Salary:** $177,000+  
   **Key Matching Details:** Similar to the previous Airbnb position, this role is remote and offers a competitive salary. It also does not specify Spark or Kafka but is relevant to data engineering.  
   **Final Score:** 0.577  

4. **Company:** AIRBNB  
   **Title:** Senior Data Scientist, Platform (Algorithms/Trust)  
   **Location:** Remote  
   **Salary:** $177,000+  
   **Key Matching Details:** This is another remote role at Airbnb with a high salary. Like the others, it focuses on data science and may not directly align with your Spark and Kafka experience.  
   **Final Score:** 0.575  

5. **Company:** Lucia  
   **Title:** Founding ML Engineer, Growth Engineer  
   **Location:** Remote  
   **Salary:** $135,000 - $240,000  
   **Key Matching Details:** This position is fully remote and offers a salary range that exceeds your target. However, it focuses on ML and AI, which may not directly utilize your Spark and Kafka skills.  
   **Final Score:** 0.613  

### Summary
The top match is with HelloData, offering a strong salary and remote work, though it lacks specific mention of Spark and Kafka. Airbnb has multiple roles that provide good salaries and remote flexibility but also do not focus on your desired tech stack. Lucia offers a high salary range and remote work but may not align closely with your experience. Overall, while there are good options, none specifically highlight Spark and Kafka, which may require some consideration on your part.

---

### q30
**User query:** React frontend roles in Chicago or nearby, 120k minimum

**Extracted preferences:**
```json
{
  "description_keywords": [
    "frontend",
    "React"
  ],
  "target_salary": 120000,
  "preferred_location": "Chicago",
  "remote_preference": null,
  "desired_tags": [
    "React"
  ],
  "preferred_category": "frontend",
  "weight_adjustments": {
    "location": "high",
    "salary": "medium"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Frontend Engineer, Reliability Experience @ AIRBNB
  - Location: Brazil - Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, Java, ML, React, TypeScript
  - Category: management
  - Final score: 0.489
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Senior Full Stack Developer @ Pelairo Inc.
  - Location: Remote | Remote: remote
  - Salary: $100,000 – $150,000
  - Tags: AI, AWS, Go, React, TypeScript
  - Category: frontend
  - Final score: 0.675
  - Snippet: Pelairo Inc. | Senior Full Stack Developer | REMOTE (US Only) | Full-time | $100-150k At Pelairo we're building the most intuitive and flexible Laboratory Information Management System (LIMS) on the market. "Manage the lab, not the LIMS!" A…
- **#3** Software Engineer, Guest & Host  @ AIRBNB
  - Location: Remote, USA  | Remote: remote
  - Salary: $160,000+
  - Tags: AI, Go, Java, ML, React
  - Category: management
  - Final score: 0.486
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Senior JS developer @ Digital Vitamins
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: React
  - Category: frontend
  - Final score: 0.651
  - Snippet: Digital Vitamins | Senior JS developer | Electron.js + React.js | Remote (EU) | Full-time Digital Vitamins is building a secure messaging application on top of Electron.js and React.js. Looking for developers with relevant experience. Send …
- **#5** Staff Software Engineer - Consumer Revenue @ DISCORD
  - Location: Remote (U.S.) | Remote: remote
  - Salary: $248,000+
  - Tags: AI, Go, Python, React, TypeScript
  - Category: frontend
  - Final score: 0.454
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#6** Staff Full-Stack Software Engineer, Social Commerce @ DISCORD
  - Location: San Francisco Bay Area or Remote (U.S.) | Remote: remote
  - Salary: $248,000+
  - Tags: AI, AWS, Go, Python, React, TypeScript
  - Category: frontend
  - Final score: 0.449
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#7** Staff Full-Stack Software Engineer, New Gaming Features @ DISCORD
  - Location: San Francisco Bay Area or Remote (U.S.) | Remote: remote
  - Salary: $248,000+
  - Tags: AI, Java, ML, Python, React, Rust
  - Category: frontend
  - Final score: 0.448
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#8** Staff Full-Stack Software Engineer, Player Experience @ DISCORD
  - Location: San Francisco Bay Area or Remote (U.S.) | Remote: remote
  - Salary: $248,000+
  - Tags: AI, Java, ML, Python, React, Rust
  - Category: frontend
  - Final score: 0.448
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#9** Unknown @ Parseur
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: React
  - Category: frontend
  - Final score: 0.586
  - Snippet: Parseur | Front-end dev with design appetite | REMOTE [GMT:GMT+6] Parseur is a B2B Saas that automates document-processing workflows. We are a 100% office-less, fully remote team of 5 looking for the 6th full-time (or 80%) team member. We'r…
- **#10** Senior Frontend Engineer @ Level
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, React, TypeScript
  - Category: frontend
  - Final score: 0.584
  - Snippet: Level | Senior Frontend Engineer | REMOTE (US + international with US-ET overlap) | https://level.io Level builds a modern Remote Monitoring & Management (RMM) platform for IT teams and Managed Service Providers. We help IT professionals mo…

**System answer to rate:**

Here are the top matching React frontend roles based on your criteria of a minimum salary of $120,000 and proximity to Chicago:

1. **Company: Pelairo Inc.**
   - **Title:** Senior Full Stack Developer
   - **Location:** Remote
   - **Salary:** $100,000 - $150,000
   - **Key Matching Details:** This role offers a salary range that meets your minimum requirement, with a strong tech stack that includes React and TypeScript. The remote nature allows flexibility, although it's not location-specific to Chicago.
   - **Tradeoffs:** While the salary range fits, the lower end is slightly below your target.

2. **Company: Digital Vitamins**
   - **Title:** Senior JS Developer
   - **Location:** Remote
   - **Salary:** Not specified
   - **Key Matching Details:** This position focuses on React, aligning well with your desired tech stack. It is fully remote, which provides flexibility but does not meet the location preference.
   - **Tradeoffs:** Salary details are unspecified, which may be a concern for meeting your financial expectations.

3. **Company: Discord**
   - **Title:** Staff Software Engineer - Consumer Revenue
   - **Location:** Remote (U.S.)
   - **Salary:** $248,000+
   - **Key Matching Details:** This role exceeds your salary requirement significantly and includes React in its tech stack. The remote option provides flexibility.
   - **Tradeoffs:** The position is not location-specific to Chicago, and the high salary may come with high expectations.

4. **Company: Discord**
   - **Title:** Staff Full-Stack Software Engineer, Social Commerce
   - **Location:** San Francisco Bay Area or Remote (U.S.)
   - **Salary:** $248,000+
   - **Key Matching Details:** Similar to the previous Discord role, this position offers a high salary and includes React in its tech stack. It also allows for remote work.
   - **Tradeoffs:** Again, not tied to Chicago, and the salary is at the high end of the spectrum.

### Summary
The best match for your criteria is the **Senior Full Stack Developer** role at **Pelairo Inc.**, as it meets your salary requirements and includes React in the tech stack. However, it is fully remote. The **Discord** positions offer excellent salaries and tech alignment but are also remote and not specific to Chicago. If proximity to Chicago is essential, consider the trade-offs with remote roles or broaden your search to include more local opportunities.

---

### q31
**User query:** DevOps with AWS and Docker in Austin, hybrid OK

**Extracted preferences:**
```json
{
  "description_keywords": [
    "devops"
  ],
  "target_salary": null,
  "preferred_location": "Austin",
  "remote_preference": "hybrid",
  "desired_tags": [
    "AWS",
    "Docker"
  ],
  "preferred_category": "devops",
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Principal Software Engineer, Performance @ AIRBNB
  - Location: Remote-US | Remote: remote
  - Salary: $292,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes, ML, React
  - Category: devops
  - Final score: 0.494
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Staff Software Engineer, Platform Security @ DISCORD
  - Location: San Francisco Bay Area or Remote | Remote: remote
  - Salary: $248,000+
  - Tags: AI, AWS, Docker, Kubernetes, Python, Rust
  - Category: devops
  - Final score: 0.494
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#3** DevOps Engineer @ RePro
  - Location: Remote | Remote: remote
  - Salary: not specified
  - Tags: AI, AWS, Docker
  - Category: devops
  - Final score: 0.653
  - Snippet: RePro | UK REMOTE (GMT ±3) | DevOps Engineer | https://reprostream.com About us: RePro is an online platform for film & TV production. Role: We're looking for a strong DevOps engineer to join our small team, to help build resiliance & scale…
- **#4** Software Engineer & Senior DevOps Engineer @ Blackshark AI
  - Location: Remote | Remote: remote
  - Salary: $35,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes, Python
  - Category: devops
  - Final score: 0.623
  - Snippet: Blackshark AI | Software Engineer & Senior DevOps Engineer | Full-time | Austria or Remote EU | VISA sponsorship available Vo to satellite and drone imagery is on the rise, while traditional image processing methods struggle to keep up. Our…
- **#5** Software Engineer & Senior DevOps Engineer @ Blackshark AI
  - Location: Remote | Remote: remote
  - Salary: $35,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes, Python
  - Category: devops
  - Final score: 0.621
  - Snippet: Blackshark AI | Software Engineer & Senior DevOps Engineer | Full-time | Austria or Remote EU | VISA sponsorship available Satellite and drone imagery access is on the rise, and traditional image processing methods are struggling to keep up…
- **#6** Unknown @ EnigmoFi
  - Location: Remote | Remote: remote
  - Salary: $192,000+
  - Tags: AI, AWS, Docker, Go, Kubernetes
  - Category: devops
  - Final score: 0.570
  - Snippet: EnigmoFi | DevOps / SRE (Cloud & Infrastructure) | Remote | $192k + bonus EnigmoFi is a crypto financial infrastructure startup building secure, scalable digital finance systems. We’re hiring a senior DevOps / SRE to own and scale productio…
- **#7** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer @ Prompt Health
  - Location: Remote | Remote: remote
  - Salary: $100,000+
  - Tags: AI, AWS, Docker, Kubernetes, ML, Python
  - Category: devops
  - Final score: 0.567
  - Snippet: Prompt Health| Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer | REMOTE (US) Prompt Health is a fast-growing Healthcare SaaS company with over $100M in ARR, growing 100%+ YoY. We build software used by large healthcare …
- **#8** Senior Software Engineer, Infrastructure @ AIRBNB
  - Location: Remote - Brazil | Remote: remote
  - Salary: not specified
  - Tags: AI, AWS, Go, Kubernetes, ML
  - Category: devops
  - Final score: 0.431
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#9** Senior Software Engineer, Cloud Networking @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $195,000+
  - Tags: AI, AWS, Go
  - Category: devops
  - Final score: 0.431
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#10** Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer @ Prompt Health
  - Location: Remote | Remote: remote
  - Salary: $100,000+
  - Tags: AI, AWS, Docker, Kubernetes, ML, Python
  - Category: devops
  - Final score: 0.559
  - Snippet: Prompt Health| Senior Full Stack Engineer, Senior DevOps Engineer, Support Engineer | REMOTE (US) Prompt Health is a fast-growing Healthcare SaaS company with over $100M in ARR, growing 100%+ YoY. We build software used by large healthcare …

**System answer to rate:**

Here are the top job matches for a DevOps position with AWS and Docker in Austin, considering your preference for hybrid work:

1. **Company:** AIRBNB  
   **Title:** Principal Software Engineer, Performance  
   **Location:** Remote-US  
   **Remote:** Yes  
   **Salary:** $292,000+  
   **Key Matching Details:** Strong alignment with your tech stack (AWS, Docker) and a high salary. However, it is fully remote, which may not meet your location preference for Austin.  
   **Tradeoff:** Excellent salary but not in Austin.

2. **Company:** DISCORD  
   **Title:** Staff Software Engineer, Platform Security  
   **Location:** San Francisco Bay Area or Remote  
   **Remote:** Yes  
   **Salary:** $248,000+  
   **Key Matching Details:** Matches your desired tech stack (AWS, Docker) and offers a competitive salary. Like Airbnb, this role is remote, which may not align with your preference for Austin.  
   **Tradeoff:** High salary and tech match, but remote location.

3. **Company:** RePro  
   **Title:** DevOps Engineer  
   **Location:** Remote  
   **Remote:** Yes  
   **Salary:** Not specified  
   **Key Matching Details:** Strong tech stack match (AWS, Docker) and a focus on DevOps. This position is fully remote, which may not meet your Austin preference.  
   **Tradeoff:** Salary not specified, but good tech alignment.

4. **Company:** Blackshark AI  
   **Title:** Software Engineer & Senior DevOps Engineer  
   **Location:** Remote  
   **Remote:** Yes  
   **Salary:** $35,000+  
   **Key Matching Details:** Matches your tech stack (AWS, Docker) but has a significantly lower salary compared to others. Fully remote, which may not fit your location preference.  
   **Tradeoff:** Low salary but good tech match.

5. **Company:** EnigmoFi  
   **Title:** Unknown  
   **Location:** Remote  
   **Remote:** Yes  
   **Salary:** $192,000+  
   **Key Matching Details:** Strong tech stack match (AWS, Docker) with a competitive salary. This role is also remote.  
   **Tradeoff:** Good salary but not in Austin.

### Summary
All top matches are remote positions, which may not align with your preference for Austin. The roles at Airbnb and Discord offer the highest salaries but are fully remote. RePro and Blackshark AI provide good tech stack matches, though their salaries vary significantly. If being in Austin is a priority, you may want to broaden your search criteria or consider local companies that may not have surfaced in this query.

---

### q32
**User query:** Remote Python or Java backend, good salary above 150k, no PhD required

**Extracted preferences:**
```json
{
  "description_keywords": [
    "backend",
    "Python",
    "Java"
  ],
  "target_salary": 150000,
  "preferred_location": null,
  "remote_preference": "remote",
  "desired_tags": [
    "Python",
    "Java"
  ],
  "preferred_category": "backend",
  "weight_adjustments": {
    "salary": "high",
    "remote": "high"
  },
  "hard_filters": [
    {
      "field": "degree_req",
      "exclude": [
        "phd"
      ]
    }
  ]
}
```

**Top-10 retrieved jobs:**
- **#1** Software Engineer, Growth & Monetization @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $153,000+
  - Tags: AI, C++, Go, ML, PostgreSQL, Python, React, TypeScript
  - Category: backend
  - Final score: 0.655
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#2** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.674
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#3** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.674
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#4** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.674
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#5** Backend Software Engineer @ Enveritas (YC S18, non
  - Location: Remote | Remote: remote
  - Salary: $135,000 – $155,000
  - Tags: AI, AWS, Docker, Python
  - Category: backend
  - Final score: 0.674
  - Snippet: Enveritas (YC S18, non-profit) | Backend Software Engineer | Remote (Global) | https://enveritas.org/jobs/ Enveritas is a 501(c)(3) nonprofit working on sustainability issues facing smallholder coffee farmers. We collect field data in 25+ c…
- **#6** Software Engineer, AI Platforms @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $153,000+
  - Tags: AI, Go, ML, Python, TypeScript
  - Category: backend
  - Final score: 0.654
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#7** Full Stack Software Engineer @ Piq Energy
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000 – $250,000
  - Tags: AI, Python, TypeScript
  - Category: backend
  - Final score: 0.666
  - Snippet: Piq Energy | Full Stack Software Engineer | SF, Athens, or US REMOTE | Full-time | $150k-$250k + equity (SF; location-adjusted) https://jobs.gem.com/piqenergy/am9icG9zdDp5j21vRWEpgIUq005H6... Piq Energy builds software that helps renewable …
- **#8** Full Stack Software Engineer @ Piq Energy
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000 – $250,000
  - Tags: AI, Python, TypeScript
  - Category: backend
  - Final score: 0.666
  - Snippet: Piq Energy | Full Stack Software Engineer | SF, Athens, or US REMOTE | Full-time | $150k-$250k + equity (SF; location-adjusted) https://jobs.gem.com/piqenergy/am9icG9zdDp5j21vRWEpgIUq005H6... Piq Energy builds software that helps renewable …
- **#9** Software Engineer @ MachineSP
  - Location: Remote or San Francisco | Remote: remote
  - Salary: $150,000+
  - Tags: AI, AWS, Python
  - Category: backend
  - Final score: 0.665
  - Snippet: MachineSP | Software Engineer | NYC or SF (Hybrid → Remote) | Full-time | $150K–$200K+ MachineSP ( https://www.machinesp.com/ ) is a fast growing mortgage-backed securities (MBS) fintech company with a client list that includes most of the …
- **#10** Software Engineer, C++ @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $153,000+
  - Tags: AI, C++, Go, Java, ML, Python, React, Rust, TypeScript
  - Category: frontend
  - Final score: 0.640
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…

**System answer to rate:**

Here are the top job matches for your query regarding remote backend positions in Python or Java with a salary above $150k:

1. **Company:** FIGMA  
   **Title:** Software Engineer, Growth & Monetization  
   **Remote:** Yes  
   **Salary:** $153,000+  
   **Key Matching Details:** This position offers a salary above your target and is fully remote. It involves backend work with Python, aligning well with your tech stack preference.  
   **Tradeoffs:** The tech stack includes additional languages (C++, Go) that may not be your primary focus.

2. **Company:** Enveritas (YC S18, non-profit)  
   **Title:** Backend Software Engineer  
   **Remote:** Yes  
   **Salary:** $135,000 - $155,000  
   **Key Matching Details:** This role is fully remote and offers a salary that meets your requirement at the upper end. It utilizes Python and fits your backend focus.  
   **Tradeoffs:** The salary is slightly below your target, but the remote flexibility and mission-driven work may appeal to you.

3. **Company:** Piq Energy  
   **Title:** Full Stack Software Engineer  
   **Remote:** Yes  
   **Salary:** $150,000 - $250,000  
   **Key Matching Details:** This position is remote and offers a competitive salary range starting at your target. It includes Python in the tech stack, aligning with your preferences.  
   **Tradeoffs:** As a full stack role, it may require more front-end work than you prefer.

4. **Company:** MachineSP  
   **Title:** Software Engineer  
   **Remote:** Yes  
   **Salary:** $150,000+  
   **Key Matching Details:** This role is remote and offers a salary that meets your requirement. It involves backend work with Python, fitting your tech stack preference.  
   **Tradeoffs:** The company is in the fintech sector, which may have a different pace and culture compared to other industries.

### Summary
The top picks include FIGMA and Piq Energy, both offering salaries above your target and remote work. FIGMA is a strong match for tech stack alignment but includes additional languages, while Piq Energy offers a wider salary range but may require more full-stack responsibilities. Enveritas provides a mission-driven opportunity but is slightly below your salary target. MachineSP also meets your salary requirement and tech preferences, focusing on backend development.

---

### q33
**User query:** Management positions in Denver or Boulder area, 180k+

**Extracted preferences:**
```json
{
  "description_keywords": [
    "management"
  ],
  "target_salary": 180000,
  "preferred_location": "Denver or Boulder",
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": "management",
  "weight_adjustments": {
    "location": "high",
    "salary": "high"
  },
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Software Engineer,Trust Platform  @ AIRBNB
  - Location: Remote, USA  | Remote: remote
  - Salary: $190,000+
  - Tags: AI, Java, Rust
  - Category: management
  - Final score: 0.661
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Engineering Manager (Analytics Product) @ Greenhouse Software
  - Location: Remote | Remote: remote
  - Salary: $142,700 – $214,100
  - Tags: AI, Go, Java, React, TypeScript
  - Category: management
  - Final score: 0.737
  - Snippet: Greenhouse Software | Engineering Manager (Analytics Product) | REMOTE (Ontario or BC, Canada) | Full-time | We're unable to support sponsorship at this time. Greenhouse is the company dedicated to making hiring work for everyone. We help o…
- **#3** Senior Software Engineer, Community Support Engineering  @ AIRBNB
  - Location: Remote, USA | Remote: remote
  - Salary: $195,000+
  - Tags: AI, C++, Java
  - Category: management
  - Final score: 0.651
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#4** Engineering Manager, Listings Products @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, ML, Rust
  - Category: management
  - Final score: 0.639
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#5** Staff Android Engineer, Reservation Management & Additional Products @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI
  - Category: management
  - Final score: 0.638
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#6** Engineer (Senior @ Triumph Financial
  - Location: Remote | Remote: remote
  - Salary: $150,000 – $300,000
  - Tags: AI, Java, ML, React
  - Category: management
  - Final score: 0.705
  - Snippet: Triumph Financial | https://triumph.io | Engineer (Senior | Lead | Staff) & Senior Product Manager | REMOTE (USA only) | Full Time | $150-$300k At Triumph Financial, we’re building the modern freight payments network powering over $37B in a…
- **#7** Engineering Manager, Identity & Privacy Experience (Users, Identity & Community) @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, Go, Rust
  - Category: management
  - Final score: 0.628
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#8** Senior Software Engineer @ Lithic ( https://lithic.com )
  - Location: Remote | Remote: remote
  - Salary: $169,000 – $265,000
  - Tags: AI
  - Category: management
  - Final score: 0.697
  - Snippet: Lithic ( https://lithic.com ) | Senior Software Engineer ; Engineering Manager | REMOTE Lithic is the modern API for issuing & processing payment cards across Visa, Mastercard, and Amex. We're a small engineering team building the infrastru…
- **#9** Staff Android Engineer, Guest & Host  @ AIRBNB
  - Location: Remote, USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, Go
  - Category: management
  - Final score: 0.621
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#10** Engineering Manager, Network Infrastructure (Cloud) @ AIRBNB
  - Location: Remote - USA | Remote: remote
  - Salary: $204,000+
  - Tags: AI, AWS, Go
  - Category: management
  - Final score: 0.620
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…

**System answer to rate:**

Here are the top management positions that match your criteria of being in the Denver or Boulder area with a salary of $180,000 or more:

1. **Company:** Airbnb  
   **Title:** Senior Software Engineer, Trust Platform  
   **Location:** Remote, USA  
   **Salary:** $190,000+  
   **Key Matching Details:** High salary fit and category match, with a strong tech stack in AI, Java, and Rust.  
   **Tradeoff:** Fully remote position, which may not meet your location preference.

2. **Company:** Greenhouse Software  
   **Title:** Engineering Manager (Analytics Product)  
   **Location:** Remote  
   **Salary:** $142,700 - $214,100  
   **Key Matching Details:** Salary range meets your target, with a strong category match. Remote work available.  
   **Tradeoff:** Location is remote, not specifically in Denver or Boulder.

3. **Company:** Airbnb  
   **Title:** Senior Software Engineer, Community Support Engineering  
   **Location:** Remote, USA  
   **Salary:** $195,000+  
   **Key Matching Details:** High salary fit and category match, with a tech stack including AI, C++, and Java.  
   **Tradeoff:** Fully remote, not in your preferred location.

4. **Company:** Airbnb  
   **Title:** Engineering Manager, Listings Products  
   **Location:** Remote - USA  
   **Salary:** $204,000+  
   **Key Matching Details:** Excellent salary fit and strong category match, focusing on AI and ML.  
   **Tradeoff:** Remote position, which may not align with your location preference.

5. **Company:** Triumph Financial  
   **Title:** Engineer (Senior)  
   **Location:** Remote  
   **Salary:** $150,000 - $300,000  
   **Key Matching Details:** Salary range exceeds your target, with a strong category match.  
   **Tradeoff:** Remote position, not located in Denver or Boulder.

Overall, while there are several high-paying management roles available, most of them are remote and do not meet your specific location preference for Denver or Boulder. If you are open to remote opportunities, there are strong matches available. Otherwise, consider broadening your search criteria to include on-site roles or positions in nearby areas.

---

### q34
**User query:** Companies with good culture for junior developers

**Extracted preferences:**
```json
{
  "description_keywords": [
    "junior developer"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": null,
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Senior Frontend Engineer, Hosting Services @ AIRBNB
  - Location: London, England | Remote: onsite
  - Salary: not specified
  - Tags: AI, ML, React, TypeScript
  - Category: management
  - Final score: 0.170
  - Snippet: Airbnb was born in 2007 when two hosts welcomed three guests to their San Francisco home, and has since grown to over 5 million hosts who have welcomed over 2 billion guest arrivals in almost every country across the globe. Every day, hosts…
- **#2** Junior Software Developer @ CT RISE Network
  - Location: Remote or CT | Remote: remote
  - Salary: not specified
  - Tags: Go
  - Category: frontend
  - Final score: 0.394
  - Snippet: CT RISE Network | Junior Software Developer | REMOTE (US) | Nonprofit | Full-Time CT RISE Network is a Connecticut-based nonprofit improving educational outcomes through data tools and technology that support schools and educators. We’re hi…
- **#3** Junior Software Developer @ CT RISE Network
  - Location: Remote or CT | Remote: remote
  - Salary: not specified
  - Tags: Go
  - Category: frontend
  - Final score: 0.394
  - Snippet: CT RISE Network | Junior Software Developer | REMOTE (US) | Nonprofit | Full-Time CT RISE Network is a Connecticut-based nonprofit improving educational outcomes through data tools and technology that support schools and educators. We’re hi…
- **#4** Junior Software Engineer:  https://www.volcore.co.uk/junior @ Volcore
  - Location: Unknown | Remote: onsite
  - Salary: not specified
  - Tags: Python, Rust, TypeScript
  - Category: fullstack
  - Final score: 0.313
  - Snippet: Volcore | Manchester, UK | On-site | Full-Time | Software Engineer, Forecaster, Mathematical Modelling Developer At Volcore, we model the electricity system to do proprietary trading that helps balance the grid and facilitate renewables int…
- **#5** Junior Software Engineer (Contract, 1099) @ Doubling
  - Location: Remote or New York City | Remote: remote
  - Salary: not specified
  - Tags: AI, React, TypeScript
  - Category: fullstack
  - Final score: 0.311
  - Snippet: Doubling | Junior Software Engineer (Contract, 1099) | NYC ONSITE | doubling.io Doubling is partnering with an early-stage AI-driven fintech startup building a platform that converts real-time financial data and news into clear, actionable …
- **#6** Junior Developers (2) @ iM3
  - Location: Hybrid | Remote: hybrid
  - Salary: not specified
  - Tags: AI, Go, Python
  - Category: fullstack
  - Final score: 0.302
  - Snippet: iM3 | Junior Developers (2) | Christchurch, NZ | Hybrid (mostly WFH) | Contract → possible long-term We build AI-driven imaging software for vets - capturing and analysing x-rays to find dental issues in animals. We train our own models, ar…
- **#7** Backend Engineers (Junior & Senior) @ Treatment Technologies & Insights, Inc. (TTI)
  - Location: Los Angeles | Remote: hybrid
  - Salary: not specified
  - Category: backend
  - Final score: 0.297
  - Snippet: Treatment Technologies & Insights, Inc. (TTI) | Backend Engineers (Junior & Senior) | El Segundo, CA | Hybrid TTI is a fast-growing, mission-driven healthtech company building an ePRO (electronic patient-reported outcomes) platform for pati…
- **#8** Junior to Senior Fullstack Engineer multiple positions @ SerpApi
  - Location: Remote or Austin | Remote: remote
  - Salary: $150,000 – $180,000
  - Tags: AI, Go, Python, React, Rust
  - Category: fullstack
  - Final score: 0.284
  - Snippet: SerpApi | https://serpapi.com | Junior to Senior Fullstack Engineer multiple positions | Customer Success Engineer | Hiring Coordinator | Python/Ruby/PHP/Js/Rust/Cotlin/C#/Crystal/Nim/Elixir Developer Advocate positions | Based in Austin, T…
- **#9** Junior to Senior Fullstack Engineer multiple positions @ SerpApi
  - Location: Remote or Austin | Remote: remote
  - Salary: $150,000 – $180,000
  - Tags: AI, Go, Python, React, Rust
  - Category: fullstack
  - Final score: 0.284
  - Snippet: SerpApi | https://serpapi.com | Junior to Senior Fullstack Engineer multiple positions | Customer Success Engineer | Hiring Coordinator | Python/Ruby/PHP/Js/Rust/Cotlin/C#/Crystal/Nim/Elixir Developer Advocate positions | Based in Austin, T…
- **#10** Junior to Senior Fullstack Engineer multiple positions @ SerpApi
  - Location: Remote or Austin | Remote: remote
  - Salary: $150,000 – $180,000
  - Tags: AI, Go, Python, React, Rust
  - Category: fullstack
  - Final score: 0.284
  - Snippet: SerpApi | https://serpapi.com | Junior to Senior Fullstack Engineer multiple positions | Customer Success Engineer | Hiring Coordinator | Python/Ruby/PHP/Js/Rust/Cotlin/C#/Crystal/Nim/Elixir Developer Advocate positions | Based in Austin, T…

**System answer to rate:**

Here are the top job opportunities that match your interest in companies with a good culture for junior developers:

1. **CT RISE Network**
   - **Title:** Junior Software Developer
   - **Location:** Remote or CT
   - **Remote:** Fully remote
   - **Salary:** Not specified
   - **Tech Stack:** Go
   - **Why it matches:** This nonprofit organization focuses on improving educational outcomes, suggesting a mission-driven culture that is supportive for junior developers.
   - **Tradeoff:** Salary details are not provided, but the remote option offers flexibility.

2. **CT RISE Network** (duplicate listing)
   - **Title:** Junior Software Developer
   - **Location:** Remote or CT
   - **Remote:** Fully remote
   - **Salary:** Not specified
   - **Tech Stack:** Go
   - **Why it matches:** Same as above, emphasizing a supportive environment for junior developers in a nonprofit setting.
   - **Tradeoff:** Again, salary is unspecified, but the remote work option is a plus.

3. **Volcore**
   - **Title:** Junior Software Engineer
   - **Location:** Unknown
   - **Remote:** Onsite
   - **Salary:** Not specified
   - **Tech Stack:** Python, Rust, TypeScript
   - **Why it matches:** The company focuses on innovative solutions in energy, which could indicate a collaborative and forward-thinking culture.
   - **Tradeoff:** Onsite work may limit flexibility compared to remote options.

4. **Doubling**
   - **Title:** Junior Software Engineer (Contract, 1099)
   - **Location:** Remote or New York City
   - **Remote:** Fully remote
   - **Salary:** Not specified
   - **Tech Stack:** AI, React, TypeScript
   - **Why it matches:** As a startup in the fintech space, it likely has a dynamic culture that fosters growth for junior developers.
   - **Tradeoff:** Contract position may lack some benefits of full-time employment.

5. **iM3**
   - **Title:** Junior Developers (2)
   - **Location:** Hybrid (mostly WFH)
   - **Remote:** Hybrid
   - **Salary:** Not specified
   - **Tech Stack:** AI, Go, Python
   - **Why it matches:** The focus on AI-driven software for veterinary applications suggests a caring and innovative culture.
   - **Tradeoff:** Hybrid model may not suit those looking for fully remote work.

6. **Treatment Technologies & Insights, Inc. (TTI)**
   - **Title:** Backend Engineers (Junior & Senior)
   - **Location:** Los Angeles
   - **Remote:** Hybrid
   - **Salary:** Not specified
   - **Why it matches:** As a healthtech company, TTI's mission-driven approach may foster a supportive environment for junior developers.
   - **Tradeoff:** Location in Los Angeles may not be ideal for everyone, and hybrid work could limit flexibility.

7. **SerpApi**
   - **Title:** Junior to Senior Fullstack Engineer (multiple positions)
   - **Location:** Remote or Austin
   - **Remote:** Fully remote
   - **Salary:** $150,000 - $180,000
   - **Tech Stack:** AI, Go, Python, React, Rust
   - **Why it matches:** The salary range indicates a strong investment in talent, and the remote option is appealing for flexibility.
   - **Tradeoff:** The wide range of experience levels may mean varying expectations for junior roles.

In summary, the **CT RISE Network** positions stand out for their fully remote options and mission-driven culture, ideal for junior developers. **SerpApi** offers a competitive salary and remote flexibility, while **Volcore** and **TTI** provide opportunities in innovative sectors but may require onsite presence. If you're looking for a supportive environment, consider focusing on nonprofit or mission-driven organizations.

---

### q35
**User query:** Fast-paced startup environment with equity compensation

**Extracted preferences:**
```json
{
  "description_keywords": [
    "fast-paced",
    "startup",
    "equity compensation"
  ],
  "target_salary": null,
  "preferred_location": null,
  "remote_preference": null,
  "desired_tags": null,
  "preferred_category": null,
  "weight_adjustments": {},
  "hard_filters": []
}
```

**Top-10 retrieved jobs:**
- **#1** Data Scientist   @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $140,000+
  - Tags: AI, Go, ML, Python
  - Category: frontend
  - Final score: 0.056
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#2** Senior Software Engineer, Data Platform @ DISCORD
  - Location: San Francisco Bay Area | Remote: onsite
  - Salary: $196,000+
  - Tags: AI, AWS, Docker, Go, Java, Kubernetes, Python, Rust
  - Category: devops
  - Final score: 0.056
  - Snippet: Discord is used by over 200 million people every month for many different reasons, but there’s one thing that nearly everyone does on our platform: play video games. Over 90% of our users play games, spending a combined 1.5 billion hours pl…
- **#3** Unknown @ Stealth AI Startup
  - Location: San Francisco | Remote: onsite
  - Salary: $200,000 – $500,000
  - Tags: AI, ML
  - Category: backend
  - Final score: 0.158
  - Snippet: Stealth AI Startup | Full-time | SF | onsite | Founding engineer We are looking for engineers (ML & backend) to join a startup where we’re building LLM-based forecasting systems that output calibrated probability distributions (not just ans…
- **#4** Manager, Software Engineering - AI Product  @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $258,000+
  - Tags: AI, Go, ML
  - Category: management
  - Final score: 0.053
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#5** Software Engineer @ Northstar Security
  - Location: San Francisco | Remote: onsite
  - Salary: not specified
  - Tags: AI
  - Category: backend
  - Final score: 0.148
  - Snippet: Northstar Security | Software Engineer | SF Bay Area | Onsite | Full-time Northstar is a seed-stage cybersecurity startup building an agentic platform to help security teams understand and defend the complex environments they're responsible…
- **#6** Software Engineer @ Northstar Security
  - Location: San Francisco | Remote: onsite
  - Salary: not specified
  - Tags: AI
  - Category: backend
  - Final score: 0.148
  - Snippet: Northstar Security | Software Engineer | SF Bay Area | Onsite | Full-time Northstar is a seed-stage cybersecurity startup building an agentic platform to help security teams understand and defend the complex environments they're responsible…
- **#7** Data Scientist, Core Data -  PhD (2026) @ FIGMA
  - Location: New York, NY • United States; San Francisco, CA • New York, NY | Remote: remote
  - Salary: $170,000+
  - Tags: AI, Go, ML, Python
  - Category: data
  - Final score: 0.053
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#8** Unknown @ Vouch
  - Location: San Francisco | Remote: hybrid
  - Salary: $75,000+
  - Tags: AI
  - Category: backend
  - Final score: 0.142
  - Snippet: Vouch | Business Development Representative | On-site (hybrid) SF or NY only Vouch is the insurance broker that powers ambition — We’re a tech-enabled insurance advisory and brokerage purpose-built for growing companies in technology, life …
- **#9** Manager, Software Engineering - Creation Engine @ FIGMA
  - Location: San Francisco, CA • New York, NY • United States | Remote: remote
  - Salary: $258,000+
  - Tags: AI, C++, Go, ML
  - Category: management
  - Final score: 0.050
  - Snippet: Figma is growing our team of passionate creatives and builders on a mission to make design accessible to all. Figma’s platform helps teams bring ideas to life—whether you're brainstorming, creating a prototype, translating designs into code…
- **#10** Unknown @ > $8k contract → 5% equity Surely this is a typo, 
  - Location: Unknown | Remote: onsite
  - Salary: $8,000+
  - Category: frontend
  - Final score: 0.137
  - Snippet: > $8k contract → 5% equity Surely this is a typo, and you mean 50% equity?

**System answer to rate:**

Here are the top job opportunities that match your interest in a fast-paced startup environment with equity compensation:

1. **Company:** Stealth AI Startup  
   **Title:** Unknown  
   **Location:** San Francisco  
   **Remote:** Onsite  
   **Salary:** $200,000 - $500,000  
   **Key Matching Details:** This position is at a stealth AI startup, which typically indicates a fast-paced and innovative environment. The salary range is substantial, and while specific equity details aren't mentioned, startups often offer equity as part of compensation.  
   **Tradeoffs:** Exact job title and responsibilities are unclear, which may require further inquiry.

2. **Company:** DISCORD  
   **Title:** Senior Software Engineer, Data Platform  
   **Location:** San Francisco Bay Area  
   **Remote:** Onsite  
   **Salary:** $196,000+  
   **Key Matching Details:** Discord is a well-known platform with a large user base, indicating a dynamic work environment. The salary is competitive, and while equity specifics are not detailed, larger companies often provide stock options.  
   **Tradeoffs:** This role is not remote, which may limit flexibility.

3. **Company:** FIGMA  
   **Title:** Data Scientist  
   **Location:** San Francisco, CA • New York, NY • United States  
   **Remote:** Remote  
   **Salary:** $140,000+  
   **Key Matching Details:** Figma is a rapidly growing company focused on design accessibility, offering a remote position. The salary is good, and while equity isn't specified, startups typically include it in their compensation packages.  
   **Tradeoffs:** Salary is slightly below the other options but offers remote flexibility.

4. **Company:** FIGMA  
   **Title:** Manager, Software Engineering - AI Product  
   **Location:** San Francisco, CA • New York, NY • United States  
   **Remote:** Remote  
   **Salary:** $258,000+  
   **Key Matching Details:** This managerial role at Figma involves AI product development, indicating a fast-paced environment. The salary is high, and equity is likely part of the package.  
   **Tradeoffs:** This position may require more experience in management.

5. **Company:** Northstar Security  
   **Title:** Software Engineer  
   **Location:** San Francisco  
   **Remote:** Onsite  
   **Salary:** Not specified  
   **Key Matching Details:** As a seed-stage cybersecurity startup, Northstar Security offers a fast-paced environment. While salary details are missing, startups often provide equity as part of compensation.  
   **Tradeoffs:** Lack of salary transparency may be a concern.

### Summary
The Stealth AI Startup offers the highest potential salary and a startup vibe, but lacks clarity on the role. Discord provides a strong salary in a well-established company but requires onsite presence. Figma roles offer remote flexibility and competitive salaries, with a focus on innovation. Northstar Security presents a promising startup environment, though salary specifics are unclear. Depending on your priorities (salary, remote work, or company size), you can choose the best fit for your career aspirations.

---
