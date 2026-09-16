# Job Category Classification Task (Evaluation Set)

You are helping to evaluate a job-classification system. Please classify each of the following job postings into exactly **ONE** of 7 categories. These are real postings scraped from HackerNews "Who is Hiring" threads, so formatting is messy and many single posts advertise multiple roles.

## Categories

- **backend**: server-side engineering (APIs, microservices, databases, distributed systems, backend platforms).
- **frontend**: client-side / browser development (UI components, UX, web apps, design systems).
- **data**: data science, data engineering, ML / AI research or engineering, analytics, NLP, computer vision.
- **devops**: infrastructure, SRE, DevOps, platform reliability, cloud ops, CI/CD, observability.
- **fullstack**: A SINGLE role that explicitly requires the SAME engineer to build BOTH frontend UI AND backend APIs (e.g. "Fullstack Engineer: build React UI and Node.js backend"). NOT for multi-role "we're hiring frontend AND backend engineers" postings.
- **mobile**: iOS, Android, or cross-platform mobile (React Native, Flutter).
- **management**: engineering manager, director, VP, head-of-engineering, CTO — people managers of engineers.

## Classification rules

1. **Multi-role / aggregate postings (very common on HackerNews)**: titles like "Engineers (Backend, Frontend, Data, Mobile)" or "Backend + Data Engineer" list MULTIPLE distinct positions. Classify by the **FIRST or MOST-EMPHASIZED** role, **NOT as fullstack**. Examples:
   - "Backend + Data Engineer" → **backend** (backend listed first, data is a separate role)
   - "SRE, data platform, backend engineers" → **devops** (SRE is first)
   - "Backend+AI focus" → **backend** (backend is primary focus)
   - "Engineers (Backend, Frontend, Data)" → **backend** (first listed)
2. **Only use `fullstack`** when a single role description says the engineer personally builds both FE/UI AND backend/APIs. If the post lists frontend and backend as separate positions, pick the first one, NOT fullstack.
3. If the primary focus is ML / AI / data even with a generic "software engineer" title → **data**.
4. People managers of engineers → **management** (even if some individual-contributor technical work is mentioned).
5. If a "senior engineer" title is generic but the description is backend-heavy → **backend**.
6. Prefer the closest fit when ambiguous; do not invent categories outside the 7 listed.

## Output format

Output **ONLY** a JSON array in the exact order of the jobs below. Each entry has `job_id` and `category`. No explanation, no extra fields, no markdown fences.

```json
[
  {"job_id": "hn_XXX", "category": "backend"},
  {"job_id": "hn_YYY", "category": "data"}
]
```

---

## Jobs to classify (63 total)

### Job 1 — job_id: `hn_1448`
- **Title**: Senior Backend Developer
- **Company**: Zeven
- **Tags**: AI, AWS, ML, Python, React, TypeScript
- **Description**: Zeven | Senior Backend Developer | ONSITE in Zurich (Switzerland) | Full-time | Competitive salary + stock options We're a newly-founded and well-funded startup that is seeking to revolutionize the sports industry with AI-powered solutions. Our mission is to unlock human potential and redefine the sports experience through innovation and technology. We are looking for an experienced Senior Backend Developer and sports enthusiast to join our on-site team in Zurich, Switzerland. This is a hands-on, high impact role. We use Typescript for web, Python for ML, PostgreSQL, React + TanStack, AWS and...

### Job 2 — job_id: `hn_1102`
- **Title**: Founding Engineer
- **Company**: Hatchet
- **Tags**: AI, Go, Kubernetes, React, TypeScript
- **Description**: Hatchet | Founding Engineer | NYC or REMOTE (US and EU) |  https://hatchet.run Hey HN! I'm Alexander, one of the founders of Hatchet. Hatchet is an open-source platform for running background jobs at scale. We're hiring engineers who are excited to build the next class of engineering primitives, starting with queues, background tasks and durable execution. We started in early 2024 after launching our distributed task queue ( https://news.ycombinator.com/item?id=39643136 ). Hatchet is currently used by thousands of engineers for all kinds of workloads: log ingestion pipelines, code review agent...

### Job 3 — job_id: `hn_2023`
- **Title**: Staff backend engineer
- **Company**: Nango
- **Tags**: Go, Rust
- **Description**: Nango | Staff backend engineer | Remote | Full time | $120-200k + equity Nango (YC W23) is an open source product: Developer infrastructure for product integrations. We power the integrations of Semgrep, Motion, Vapi, Exa, and hundreds of other B2B software. Small but highly experienced team, hard technical challenges (scale + infra devtool running untrusted user code), tons of ownership, direct customer contact, growing very fast. We are looking for a Staff engineer that can touch every part of stack and is passionate about dev infrastructure. Website:  https://nango.dev  Jobs:  https://nango...

### Job 4 — job_id: `hn_19`
- **Title**: Staff Embedded Systems Engineer
- **Company**: Copper Home
- **Tags**: AI, AWS, Python
- **Description**: Copper Home | Staff Embedded Systems Engineer | ONSITE (Berkeley, CA) Copper Home (fka Channing Street Copper) builds battery-integrated induction appliances for home electrification — we're making decarbonization accessible by putting energy storage inside everyday products, starting with the stove. The firmware team is small and owns application firmware, device connectivity, automated testing, manufacturing tools, and an MQTT backend for OTA updates and fleet telemetry. We're hiring a  staff embedded systems engineer  focused core firmware architecture on the Charlie induction range. In thi...

### Job 5 — job_id: `hn_1836`
- **Title**: Unknown
- **Company**: Kubermatic
- **Tags**: AI
- **Description**: Kubermatic| Full-time | Product Eng & Open Source Dev | Remote Europe I am looking for Product Engineers and Open Source Developers to join the KDP and kcp teams at Kubermatic. - Open Source Software Engineer ( https://kubermatic.bamboohr.com/careers/24 ): Work directly on the upstream kcp project. Your contributions will have a direct impact on the open-source community and will help build a framework for managing multi-tenant services at scale. Kubermatic is the project’s maintainer. - Product Software Engineer ( https://kubermatic.bamboohr.com/careers/25 ): Build a platform that makes other...

### Job 6 — job_id: `hn_1554`
- **Title**: Mid + Senior level Engineers (Backend)
- **Company**: Archera
- **Tags**: AI, AWS, Go, Python, React, TypeScript
- **Description**: Archera | Mid + Senior level Engineers (Backend) | REMOTE (US/Canada) or Hybrid (Seattle) | Full-time Archera empowers organizations of all sizes to optimize their cloud costs through unique, short-term, insured GRI (Guaranteed Reserved Instance) and GSP (Guaranteed Savings Plan) commitments. We’re looking for a Mid and a Senior Software Engineer to join the platform team, working on ETL pipelines, APIs, product features and more. Stack: Python (SQLAlchemy, Flask), TypeScript (React), PostgreSQL, Snowflake, Argo Workflows, k8s, AWS/GCP/Azure Benefits: RRSP/401k match, healthcare, stock, wework...

### Job 7 — job_id: `hn_1417`
- **Title**: Staff Engineer
- **Company**: Clerq
- **Tags**: AI, AWS, Go, ML, Python, React
- **Description**: Clerq | Staff Engineer | Onsite 3 days (New York City) |  https://clerq.io  Clerq is a NYC based fintech startup building a next generation platform payments platform that delivers a seamless checkout experience for high-ticket transactions. By leveraging modern bank rails, the platform offers the conversion and UX benefits of cards with risk and money movement infrastructure purpose-built for large purchases. Clerq replaces outdated manual payment methods like cash, checks and wires and expensive card surcharges with a smooth, integrated solution that helps merchants convert more customers wi...

### Job 8 — job_id: `hn_1378`
- **Title**: Python + TypeScript Engineers
- **Company**: Fusionbox
- **Tags**: AI, Go, Python, React, TypeScript
- **Description**: Fusionbox | Python + TypeScript Engineers | United States| Full-time | REMOTE (Legal to work in the US) We're a software engineering consultancy that builds enterprise software the right way. We negotiate the right to open source all our client code, maintain a handful of popular libraries, and our engineers contribute to Django core. We sponsor PyCon, DjangoCon, and Django Girls because we're invested in the ecosystem we build on. We're looking for software engineers who value software design, system architecture, and collaboration. You should be comfortable with about half of these areas and...

### Job 9 — job_id: `hn_654`
- **Title**: Stack Engineers
- **Company**: expand.ai (YC S24)
- **Tags**: AI
- **Description**: expand.ai (YC S24) | SF onsite | Full-Stack Engineers We're building infrastructure that makes the web queryable for AI agents. Already in production with major AI labs. Looking for experienced full-stack devs who are comfortable wielding agent swarms to ship fast. Small team, well-funded, high intensity. founders@expand.ai

### Job 10 — job_id: `hn_1091`
- **Title**: Unknown
- **Company**: Careful
- **Tags**: (no tags)
- **Description**: Careful - I applied to this role and the founder (I assume) ghosted me mid-way.

### Job 11 — job_id: `hn_1062`
- **Title**: Software Engineer
- **Company**: Runable
- **Tags**: AI
- **Description**: Runable | Software Engineer | Bangalore | 60-120K USD depending on the candidate https://runable.com  is an AI suite for everyone. You can create decks, reports, documents, designs, websites etc by just describing what you want. We are looking for exceptional engineers to join us as we scale. We already process 100 billion+ tokens and billions of requests monthly. Send your best work to saksham@runable.com We don’t do DSA, leetcode etc and have a very hands on approach to interviewing

### Job 12 — job_id: `hn_1241`
- **Title**: Junior Software Engineer (Contract, 1099)
- **Company**: Doubling
- **Tags**: AI, React, TypeScript
- **Description**: Doubling | Junior Software Engineer (Contract, 1099) | NYC ONSITE | doubling.io Doubling is partnering with an early-stage AI-driven fintech startup building a platform that converts real-time financial data and news into clear, actionable client communications. We are actively hiring a junior full-stack engineer to help ship web, mobile, and AI-enabled features. You will work directly with the company’s CEO and CTO as one of the earliest engineering contributors. Tech: TypeScript, React, Firebase Hours: ~20 hrs/week Location: NYC ONSITE (no remote) Authorization: US work authorization require...

### Job 13 — job_id: `hn_1666`
- **Title**: Unknown
- **Company**: Parseur
- **Tags**: React
- **Description**: Parseur | Front-end dev with design appetite | REMOTE [GMT:GMT+6] Parseur is a B2B Saas that automates document-processing workflows. We are a 100% office-less, fully remote team of 5 looking for the 6th full-time (or 80%) team member. We're looking for an excellent front-end dev who ideally knows React. And it would be nice if you could also design and know your way around CSS. More info here:  https://parseur.com/jobs

### Job 14 — job_id: `hn_1685`
- **Title**: Unknown
- **Company**: Quantitative Trading Co
- **Tags**: AI
- **Description**: Quantitative Trading Co-Founder | US  https://0dte.tech/ Seeking US-based co-founder with _strong_ FOSS credentials to establish and operate quantitative trading firm. Prior  Trading experience desired. email me: lakshmipathi [dot] g [at] gmail [dot] com

### Job 15 — job_id: `hn_605`
- **Title**: Seasoned Ui Engineer
- **Company**: We at Avride are hiring in Austin for a full
- **Tags**: React
- **Description**: We at Avride are hiring in Austin for a full-time, onsite position. In this role, you'll help build state-of-the-art 3D data annotation tools that advance autonomous driving. We're looking for a seasoned UI engineer with a strong React background and relevant experience building highly stateful, low-latency interactive applications. Experience with 3D graphics is a plus. Apply here:  https://job-boards.greenhouse.io/avride/jobs/4012877009

### Job 16 — job_id: `hn_963`
- **Title**: Unknown
- **Company**: SEEKING REMOTE UI/UX DESIGN OPPORTUNITIES Location
- **Tags**: AI
- **Description**: SEEKING REMOTE UI/UX DESIGN OPPORTUNITIES Location: India Remote: Yes Willing to relocate: Open to discuss Technologies: Figma, Canva, Figjam, Notion, Miro, Visily, Maze, Jitter, Asana, AI, Framer, Wireframing, Prototyping, Mockups, Microinteractions, User Research, Competitive Analysis, User Flows, UI Design, UX Research, Product Management, Jira, Lottie Animations Portfolio:  https://anshimasainiproduct.framer.website/ Email: sainianshima@gmail.com I'm a Product designer and manager looking for remote opportunities anywhere. Feel free to check my portfolio website.

### Job 17 — job_id: `hn_888`
- **Title**: Full stack developer, React developer
- **Company**: Cliniko
- **Tags**: AI, React
- **Description**: Cliniko | Full stack developer, React developer |  https://www.cliniko.com/  | Remote | Full Time (30 hour week, full time pay) Cliniko is practice management software that makes life easy for allied health professionals by handling appointment scheduling, storing treatment notes, managing invoices and payments, running video consultations, and much more. The software is used globally by 100,000+ people every day. It’s a web application built using Ruby on Rails in the back end and we’re in the process of transitioning the front end to React. Cliniko is made up of a team of 63 considerate and...

### Job 18 — job_id: `hn_1619`
- **Title**: Senior/Staff/Principal Frontend Engineer (fullstack Typescript nice to have)
- **Company**: Document Crunch
- **Tags**: AI, ML, Python, React, TypeScript
- **Description**: Document Crunch | REMOTE(US) / HYBRID Company description: We do construction compliance AI. We're in series B, about $40m raised. Growing a lot! Feel free to reply or DM me if you want some more info. Tech Stack: Typescript full stack except for Python for ML, NestJS backend, NextJS frontend, React Native mobile, IaC in Pulumi using TS. Open Jobs: - Senior/Staff/Principal Frontend Engineer (fullstack Typescript nice to have) - Senior/Staff/Principal Node Engineer (fullstack Typescript nice to have) - Senior/Staff/Principal QA Engineer Location: Austin or Texas preferred, but open to remote fo...

### Job 19 — job_id: `hn_795`
- **Title**: Unknown
- **Company**: Layer Health
- **Tags**: AI, Go, ML, Python, React, TypeScript
- **Description**: Layer Health |  https://www.layerhealth.com/  Amazing (and no ego) engineering team:  https://www.linkedin.com/company/layerhealth/people/  Location: BOSTON (Boston Common) or NYC (downtown) - hybrid in both locations; <<NO REMOTE>> Headcount: ~37 and growing Stack:React / Typescript / Python / GCP Open Roles (all roles require a MINIMUM of 6 years of work experience): ML Infrastructure (Staff+) * Data Infrastructure Lead * ML Engineer  * ML/Research Scientist (PhD's) * Security Engineer We Offer: * competitive base salary + equity + great health/medical benefits * unlimited PTO * collaborativ...

### Job 20 — job_id: `hn_343`
- **Title**: Unknown
- **Company**: Baseten Labs
- **Tags**: AI, Kubernetes, ML, Python, Rust
- **Description**: Baseten Labs | San Francisco, New York |ONSITE, REMOTE, HYBRID | VISA SPONSORSHIP | RELOCATION SUPPORT We are Baseten, the team that powers mission-critical inference for the world’s most dynamic AI companies such as Cursor, Notion, OpenEvidence, Abridge, Clay, Gamma and Writer. We’re growing quickly and recently raised our $300M Series E, backed by investors including BOND, IVP, Spark Capital, Greylock and Conviction. By uniting applied AI research, flexible infrastructure, and seamless developer tooling, we enable companies operating at the frontier of AI to bring cutting-edge models into pr...

### Job 21 — job_id: `hn_1630`
- **Title**: Machine Learning Engineers Atlassian's flagship AI product
- **Company**: Atlassian
- **Tags**: AI, Go
- **Description**: Atlassian |  https://www.atlassian.com/software/rovo  | REMOTE | Full-time | Machine Learning Engineers Atlassian's flagship AI product - Rovo Chat is going through a hockey stick growth moment, and we are looking for machine learning engineer passionate about building machine learning systems that operate at XX million user scale We are pushing the boundaries on: - Agent Orchestration - Evals and benchmarks - Model Training (SFT + RL) Apply here:  https://www.atlassian.com/company/careers/details/22898

### Job 22 — job_id: `hn_443`
- **Title**: Unknown
- **Company**: Yuzu Health (yuzu.health, Series A)
- **Tags**: AI
- **Description**: Yuzu Health (yuzu.health, Series A) | Location: New York City (Flatiron) | ONSITE Pitch: Yuzu is not a wrapper, point solution, or integration on top of something. Our platform makes it easy for anyone to create their own health plan from scratch. That means our tech handles everything from the member/HR portals, claims adjudication, invoice automation, member support tools, to even printing and sending out ID cards. Why: We're truly rebuilding health insurance from the ground up. We currently serve over 1,000 employers, and we're growing extremely fast (like over 10x last year fast)! Investor...

### Job 23 — job_id: `hn_918`
- **Title**: Unknown
- **Company**: Rad AI
- **Tags**: AI, AWS, Kubernetes, ML, Python
- **Description**: Rad AI | Infra / Platform / ML Infra / SWE | San Francisco, CA | ONSITE/HYBRID Preferred, Remote Available | Full-time Rad AI builds AI products used by thousands of radiologists, helping reduce burnout and catch more disease across a large share of US medical imaging. We’ve raised $140M+ and are expanding our San Francisco presence with a new office at 2nd + Market, and we’re especially looking for infrastructure engineers who want to work in-person in SF. Work areas: Infra / Platform: AWS, Kubernetes, Terraform, PostgreSQL, observability, secure/HIPAA production infra ML infra / MLOps: Pytho...

### Job 24 — job_id: `hn_1835`
- **Title**: Unknown
- **Company**: Redpanda Data
- **Tags**: AI, Go
- **Description**: Redpanda Data | REMOTE | Full-time Redpanda is pioneering the Agentic Data Plane (ADP) - a new category in AI infrastructure that makes it simple and secure to connect AI agents with enterprise data and systems. Built on a multi-modal data streaming engine, Redpanda empowers agentic applications that reason and act in real-time with speed, autonomy, and precision. Global leaders including Activision Blizzard, Cisco, Moody's, Texas Instruments, Vodafone and 2 of the top 5 banks in the U.S. rely on Redpanda to process hundreds of terabytes of data a day. Backed by premier venture investors Light...

### Job 25 — job_id: `hn_1018`
- **Title**: Robotics Engineers, Infra Engineers, Product Engineers, GTM
- **Company**: xdof
- **Tags**: AI
- **Description**: xdof | Robotics Engineers, Infra Engineers, Product Engineers, GTM | SF Bay preferred, NYC & Remote possible for non-robotics roles At xdof, we're at an inflection point. Frontier labs are racing to build general-purpose robots, and high-quality training data is the bottleneck. We're building the foundation behind the foundation models – the data collection systems, operational capability, exabyte-scale data warehouse, and software toolchain – to help our partners drive the field forward. Founded by UC Berkeley Robotics PhDs and MechEs, this is a team that executes across software, hardware, a...

### Job 26 — job_id: `hn_1464`
- **Title**: Lead Edge AI Engineer
- **Company**: Source ( https://source.network )
- **Tags**: AI, Rust
- **Description**: Source ( https://source.network )| USA/Canada: REMOTE | Full-Time |  https://careers.source.network Our mission is to make it normal, not heroic, for edge AI, mobile apps, and critical software to run close to where data is born: on devices, in vehicles, in field hardware, not just in a distant GPU farm. We’re building the data and trust layer that lets developers ship systems that still behave correctly when links are flaky, latency is awful, and the cloud is optional instead of mandatory—instead of the usual “SQLite everywhere + ad-hoc sync” duct tape. We’re growing fast and are looking to f...

### Job 27 — job_id: `hn_356`
- **Title**: Stack Engineer
- **Company**: Lead Full
- **Tags**: AI, Go, React, TypeScript
- **Description**: Lead Full-Stack Engineer Marker Learning | Remote (U.S. only) | Full-time | Engineering | 185-250k I have dyslexia. I was one of the lucky ones. Diagnosed at eight, I got accommodations and support before things spiraled. Most kids aren't so lucky. The path from initial concern to diagnosis can take years and cost families upward of $5,000. For many, it never comes at all. In one study, 50% of prisoners were found to be dyslexic, with 80% functionally illiterate. Behind every missed diagnosis is a kid who gets told they're lazy, when the reality is no one ever gave them the right test. Marker...

### Job 28 — job_id: `hn_388`
- **Title**: Cloud Site Reliability Engineer
- **Company**: Ford Motor Company
- **Tags**: AI, Go, Kubernetes, Python
- **Description**: Ford Motor Company | Cloud Site Reliability Engineer | Full-Time | Remote (US) | 113k-190k USD Visa Sponsorship Is not provided. Ford is seeking an experienced and passionate Site Reliability Engineer (SRE) to join our team. You will play a critical role in designing, implementing, and enhancing Agentic triage software used across the company to drive automated and fast response times and lower MTTX. In this role, you will contribute hands-on to ensuring the reliability and scalability of our systems, working alongside a global SRE team, fostering a culture of collaboration and continuous impr...

### Job 29 — job_id: `hn_2061`
- **Title**: Senior DevOps Engineer
- **Company**: Black Hills Information Security
- **Tags**: AI
- **Description**: Black Hills Information Security | Senior DevOps Engineer | REMOTE Role focuses on developing and maintaining automation for penetration testing service infrastructure (C2, remote access, phishing, etc.).

### Job 30 — job_id: `hn_1557`
- **Title**: Equity More senior role bridging product and engineering. End
- **Company**: Saypien
- **Tags**: AI, React, TypeScript
- **Description**: Saypien | Berlin, Germany | REMOTE (Europe) | Full-time We're building an AI-native SaaS platform that helps companies extracting actionable insights from data in real-time. Think of it as an architectural intelligence layer that ingests heterogeneous data, learns your business context, and delivers decision-ready guidance. Tech stack: Next.js, React, TypeScript, PostgreSQL, Redis. – Hiring for two roles: Software Engineer (Full Stack) - €60-157k (incl. Bonus) | Equity You'll build and optimize our web platform end-to-end, work closely with AI, Product, and Design. Strong Node.js, PostgreSQL,...

### Job 31 — job_id: `hn_1792`
- **Title**: Unknown
- **Company**: Adalat AI
- **Tags**: AI, Go, Kubernetes, ML, React
- **Description**: Adalat AI |  https://www.adalat.ai  | Remote (India, but open to global for exceptional candidates) | Go, React, Next.js, k8s We're Hiring at Adalat AI: Join Us in Building the Future of Justice Adalat AI is on a mission to transform India’s judicial system with cutting-edge AI — reimagining courtroom workflows from transcription to summarization, just as UPI transformed payments and Aadhaar revolutionized identity verification. Deployed across 10 states and recently launched at the Delhi High Court, our platform is backed by global foundations and built by a team with roots at Harvard, Oxford...

### Job 32 — job_id: `hn_379`
- **Title**: Senior Software Engineer
- **Company**: Silkline
- **Tags**: AI, AWS, Go, React, TypeScript
- **Description**: Silkline | Senior Software Engineer | Seattle | ONSITE (5 days/week) | $175k-$225k + equity |  https://silkline.ai Modern hardware supply chains run on spreadsheets, email, and PDFs. It's like fax woke up in 2025. We're fixing this with an AI-first procurement platform for aerospace, defense, and nuclear manufacturing. Our customers: Machina Labs, Astranis, K2 Space, Castelion, Antares, and more. They use us to manage suppliers, track $M+ in orders, automate RFQs, and stay ITAR-compliant. Every day of production delay costs $50k+—our platform keeps them moving. The role: Own features end-to-en...

### Job 33 — job_id: `hn_1373`
- **Title**: Unknown
- **Company**: Category Labs
- **Tags**: AI, Go, Rust
- **Description**: Category Labs |  https://www.category.xyz/  | Remote and NYC | Full Time | $200K USD+ Category Labs (formerly known as Monad Labs) is a team of systems engineers and researchers on a mission to design and build at the frontier of decentralized technology. We strive to design and build step-function improvements over existing blockchain solutions. After raising $225M in series A funding, led by Paradigm, we are growing our team. Monad Mainnet Launched on November 24th! Technical Project Manager:  https://jobs.ashbyhq.com/category-labs/bdfe89a6-83f6-4ab3-b6... Senior SWE (Rust, C/C++):  https://...

### Job 34 — job_id: `hn_1326`
- **Title**: Software Engineers / DevOps
- **Company**: Common Prefix
- **Tags**: AI, Go, Rust, TypeScript
- **Description**: Common Prefix | Software Engineers / DevOps | Greece | Remote | Full-time Common Prefix is a blockchain research & development company. Blockchain technologies enable large-scale economic coordination through shared, programmable ledgers. Our mission is to solve the foundational scientific and engineering challenges standing in the way of mainstream adoption, particularly around interoperability, scalability, and usability. We combine formal scientific research with production-grade engineering. Our team publishes in top-tier peer-reviewed venues and builds open-source infrastructure used acro...

### Job 35 — job_id: `hn_5`
- **Title**: Senior Backend Engineer
- **Company**: Eequ
- **Tags**: AI, AWS, TypeScript
- **Description**: Eequ | Senior Backend Engineer | Remote (UK) | Full-time | £80k–£110k | Node.js, NestJS, TypeScript, MySQL, AWS, Terraform Join a disciplined, senior team responsible for the platform behind Eequ, where engineers have real ownership and operate with high autonomy. We are the market-leading supplier to local authorities in the UK for council-funded activity programmes and we also serve thousands of independent providers. Our platform handles bookings, payments, and sensitive data at scale. We are profitable, bootstrapped, and growing. What you'll do Build and operate the backend platform that p...

### Job 36 — job_id: `hn_1334`
- **Title**: Blockchain Security Engineer
- **Company**: ChainSecurity
- **Tags**: AI, Go, Rust
- **Description**: ChainSecurity | Blockchain Security Engineer | Full-time | INTERNS , HYBRID/REMOTE, Zurich, Switzerland | VISA possible |  https://chainsecurity.com/ ChainSecurity is a young and innovative cybersecurity company that operates in the blockchain and cryptocurrency space. Our mission is to make the blockchain space secure and trustworthy for people, companies, and governments alike. We are proud of our security experts from the renowned universities ETH Zurich, EPFL Lausanne and others. We are trusted by 100+ blockchain companies and established corporations with security audits and services. We...

### Job 37 — job_id: `hn_1911`
- **Title**: end developer:  https://docs.google.com/document/d/1IvcTtE7yE7m5u0NfrVmvtR_i... Full
- **Company**: DocSpot
- **Tags**: Go
- **Description**: DocSpot | ONSITE (Santa Clara, CA) |  https://docspot.com DocSpot helps people find doctors by indexing information from a plethora of sources and empowering patients to search through one unified interface. Tiny company, entry-level candidates welcome (no experience required): Back-end developer:  https://docs.google.com/document/d/1IvcTtE7yE7m5u0NfrVmvtR_i... Full-stack developer:  https://docs.google.com/document/d/1eX3-FuDFaK6kX6IQupm81p3S... Content specialist (non-technical):  https://docs.google.com/document/d/1YKvuLVMXgj527fMuEyaVnum1...

### Job 38 — job_id: `hn_1909`
- **Title**: Stack Engineer & Energy Modeling Engineer
- **Company**: *Maiven
- **Tags**: AI, AWS, Python, React, TypeScript
- **Description**: *Maiven | Full-Stack Engineer & Energy Modeling Engineer | Remote (US) | Full-Time* Maiven is the software platform automating home decarbonization. We’re a small, mission-driven team punching way above our weight: we have large utility customers, contracts in multiple states, and a growing pipeline of programs launching later this year. We’re venture backed and moving fast. We’re hiring two engineers: - *Full-Stack Engineer* – NestJS, React, Tailwind, TypeScript, Python, Postgres, AWS, Lambdas. Someone who cares deeply about UX and moving fast while delighting the user. - *Energy Modeling Eng...

### Job 39 — job_id: `hn_679`
- **Title**: AI Industry 1. Senior Platform Engineer
- **Company**: Beautiful.ai
- **Tags**: AI
- **Description**: Beautiful.ai | Full-Time | Remote in US & CAN | SaaS B2B Presentation Software | Series B | 16M Funding | AI Industry 1. Senior Platform Engineer | 160k - 200k Base salary + Equity |  https://job-boards.greenhouse.io/beautifulai/jobs/4802989007 2. Senior Software Engineer | 160k - 200k Base Salary + Equity |  https://job-boards.greenhouse.io/beautifulai/jobs/4802854007 3. Software Engineer | 120k - 160k Base Salary + Equity |  https://job-boards.greenhouse.io/beautifulai/jobs/4802768007 4. Staff Platform Engineer | 200k - 250k Base Salary + Equity |  https://job-boards.greenhouse.io/beautifula...

### Job 40 — job_id: `hn_1766`
- **Title**: Full time, interns/co
- **Company**: Stellar Science
- **Tags**: AI, Java, ML, Python, React, TypeScript
- **Description**: Stellar Science | Hybrid (USA) Albuquerque NM, Washington DC (Tysons VA), Dayton OH | Full time, interns/co-ops | U.S. citizenship required |  https://www.stellarscience.com Company: We're a small scientific software development company that develops custom scientific and engineering analysis applications in domains including: space situational awareness (monitoring the locations, health and status of on-orbit satellites), image simulation, high power microwave systems, modeling and simulation, laser systems modeling, AI/ML including physics-informed neural networks (PINN), human body thermore...

### Job 41 — job_id: `hn_110`
- **Title**: Staff Software Engineer (Full Stack)
- **Company**: StraighterLine (straighterline.com)
- **Tags**: AI, AWS, React, TypeScript
- **Description**: StraighterLine (straighterline.com) | Staff Software Engineer (Full Stack) | Remote (US Only) | Full Time Our mission is to create opportunities for career advancement through access to affordable education. We are also the market leaders in early childhood (ECE) training and certifications. We are looking for two Staff Engineers to help lead development on next-generation AI-assisted learning platforms. You will be building modern, API-driven, scalable services and applications with React/Next.js, TypeScript, Node.js, GraphQL, and AWS, using AI-native development practices. You will collabora...

### Job 42 — job_id: `hn_26`
- **Title**: Unknown
- **Company**: Proven Software
- **Tags**: AI
- **Description**: Proven Software | QA Analyst | REMOTE (US) Full-Time | $85k-$110k We've hired three developers from HN and now we're looking for a QA Analyst to join the team. Proven is a start-up software company delivering a modern electronic medical record (EMR) to behavioral health and physical therapy. Proven's Founders and Executive team have decades of experience successfully growing and scaling companies in healthcare. Our mission is to deliver an innovative and impactful solution to healthcare providers leveraging modern technology. At Proven, we are looking for bright, hard-working, and highly motiv...

### Job 43 — job_id: `hn_446`
- **Title**: Stack Engineer (First Hire)
- **Company**: Deep Core Technology
- **Tags**: AI, Python, TypeScript
- **Description**: Deep Core Technology | Full-Stack Engineer (First Hire) | Remote (Canada/US) | Full-Time We're building the web-native natural language geological modelling platform for geologists at mineral exploration companies. Think Cursor for 3D mining data investigation. Two founders (CTO + structural geologist CEO), early pilots, and in process of a raise. You'd be hire #1. Technical Challenges - staying performant while streaming millions of geological data points into a browser environment - dealing with the very high data security and compliance expectations - designing to hide complexity from end u...

### Job 44 — job_id: `hn_1235`
- **Title**: Staff Software Engineer
- **Company**: Tasklet
- **Tags**: AI, Kubernetes, ML, React, TypeScript
- **Description**: Tasklet | Staff Software Engineer - AI Agents | San Francisco, CA | ONSITE | $260k-$330k + 0.8-1.6% equity At Tasklet ( https://tasklet.ai/ ), we're building the world's most powerful AI agent platform for business automation. We're looking for a staff-level software engineer to share technical leadership of our core agent infrastructure. You'll architect systems for multi-step agent orchestration, state management, trigger systems, and seamless integration with thousands of APIs. Our stack: TypeScript, React, GCP, Kubernetes, Claude Looking for: 5+ years experience building production-scale s...

### Job 45 — job_id: `hn_2042`
- **Title**: Software Engineer, Android
- **Company**: Suno
- **Tags**: AI, Go, Python, React, TypeScript
- **Description**: Suno | Cambridge, MA | New York, NY | Full-time | Onsite We are building a future where anyone can make music. We’re scaling our engineering team and hiring for the following roles: - Software Engineer, Android - Jetpack Compose, Kotlin - Software Engineer, iOS - SwiftUI - Software Engineer, Fullstack Web - Typescript, React,  NextJS, Python, Django  - Software Engineer, Growth - all the things - AI Researchers - Other roles here  https://jobs.ashbyhq.com/suno Apply at the link above or feel free to shoot me an email at matthiesen (at) suno.com if you have any questions or want to learn more.

### Job 46 — job_id: `hn_1117`
- **Title**: Unknown
- **Company**: Eleos Technologies
- **Tags**: AI, Go
- **Description**: Eleos Technologies | DNS Consulting | REMOTE (US) | Contractor We build mobile apps and supporting systems for long-haul truck drivers. We have a critical DNS registrar/hosting migration to do this year and while I did the last one (on a less-critical domain), I'd really like support from someone who has done >5 of these to help our team get it right. Good news: no DNSSEC. =) Please reach out to me at phil@eleostech.com and mention this post if this is you and you have a reference or two. It should be really easy project for the right person, but we'll compensate commensurate with the business...

### Job 47 — job_id: `hn_1981`
- **Title**: Unknown
- **Company**: Product Consultant / AudioDiary /  https://audiodi
- **Tags**: AI, Go
- **Description**: Product Consultant / AudioDiary /  https://audiodiary.ai  / Remote / CONTRACT / flexible hours / Up to $250 daily or performance-based - subject to discussion. Our app, AudioDiary, has recently been through a period of highly organic growth. We need a someone with successful experience in scaling apps to help us grow more intentionally. We're open to any kind of improvement, from product to app store presence and beyond—the main goal being growth. AudioDiary is a new and exciting project that's already helping thousands of people. We have big ambitions and we hope that working with us could be...

### Job 48 — job_id: `hn_382`
- **Title**: Stack Engineer
- **Company**: Instinct Science
- **Tags**: AI, AWS, React, TypeScript
- **Description**: Instinct Science | Senior Full-Stack Engineer | REMOTE (US) | Full-Time | $150K–$175K Instinct Science is the AI leader in veterinary medicine - and we're just getting started. Our platform is already transforming how veterinary teams practice, combining a cloud-native EMR with real-time clinical decision support and applied AI that saves animal lives every single day. We didn't enter this space to make incremental improvements. We're here to disrupt a massive, underserved industry from the ground up - and we're looking for the engineers who want to help us define what comes next. What you'll...

### Job 49 — job_id: `hn_939`
- **Title**: Unknown
- **Company**: Product incubator
- **Tags**: AI, Go, Rust
- **Description**: Product incubator | REMOTE (US) | Consulting (1099) We are a small team with a wide network, bringing ideas to market with a focus on simplicity and trust. Clients a mix of early-stage and enterprise. Seeking long-term collaboration with imaginative people who communicate well. Teams are built around projects: At the moment, looking for experience in F&B logistics, pickup/delivery/scheduling systems, price monitoring, banking integration, mobile shopping tools and redundancy for a neat client. Otherwise, there's more in the pipeline so feel free to reach out. As a consultant, collaboration cou...

### Job 50 — job_id: `hn_1261`
- **Title**: Unknown
- **Company**: MyLegalPal
- **Tags**: (no tags)
- **Description**: MyLegalPal | India (Remote/Hybrid) | Full Time |  https://mylegalpal.com MyLegalPal is a legal technology platform that simplifies contract drafting, review, and legal support for startups, founders, and businesses globally. We help people deal with legal work without confusion, delays, or unnecessary costs. We are looking for: Frontend Developer Backend Developer Full Stack Developer Legal Operations / Legal Tech Associate Our current stack includes modern web technologies with a strong focus on performance, security, and scalability. Legal understanding is a plus, but curiosity and problem-s...

### Job 51 — job_id: `hn_350`
- **Title**: Software Engineers
- **Company**: FUTO
- **Tags**: AI, Rust
- **Description**: FUTO | Software Engineers | Austin, TX | Remote or Onsite | Full Time FUTO is an organization dedicated to developing, both through in-house engineering and investment, technologies that frustrate centralization and industry consolidation. Our work consists of a combination of in-house engineering projects, targeted investments, generous grants, and multi-media public education efforts. We are hiring for a few of our projects, Immich and Grayjay. Immich is on a mission to provide a secure and private home for your most precious memories through our high-performance, self-hostable photo and vid...

### Job 52 — job_id: `hn_1067`
- **Title**: Unknown
- **Company**: Bliro.io
- **Tags**: (no tags)
- **Description**: Bliro.io | Munich | Germany | Seed Founding Product Manager Tech Lead iOS App

### Job 53 — job_id: `hn_1029`
- **Title**: Frontend Engineer (Mobile), Head of Product Design
- **Company**: Clutch  https://www.clutchapp.io
- **Tags**: AI, React
- **Description**: Clutch  https://www.clutchapp.io  - building future of padel with AI cameras | Full-time | Frontend Engineer (Mobile), Head of Product Design | Remote (worldwide) | 50-96k + equity We are Clutch, building an automated videographer and coaching experience for padel players. We are small but quickly-growing startup with cameras in over 30 clubs around the world. We are hiring for two key positions to enhance our app and our self-designed camera. Frontend Engineer (Mobile): Experienced mobile developers (iOS, Android) only. Expertise in React Native, PostgreSQL, Amazon lambdas or similar, Amazon...

### Job 54 — job_id: `hn_28`
- **Title**: Unknown
- **Company**: Revelare Networks / Mobile Software Engineer/ Full
- **Tags**: (no tags)
- **Description**: Revelare Networks / Mobile Software Engineer/ Fully Remote/ Full-Time/ US Citizen We are hiring a Mobile Software Engineer with extensive experience in Android (Kotlin/Jetpack Compose) and iOS (Swift/SwiftUI).  The salary range for this position is $110,000 - $155,000, depending on experience level. You must be a U.S. citizen for this position Please apply here:  https://apply.workable.com/revelare-networks/j/3B32865D60/

### Job 55 — job_id: `hn_1651`
- **Title**: person team, half scientists (cryptographer PhDs, post
- **Company**: Common Prefix – Software Engineers / Auditors – Gr
- **Tags**: AI, Rust
- **Description**: Common Prefix – Software Engineers / Auditors – Greece – Remote – Full-Time Common Prefix is a science-first blockchain consulting company. Our vision is to make blockchains usable for mainstream users and everyday people – paying at the supermarket, remittances, moving money across borders, saving, investing – and solving the real problems of usability, scalability, and interoperability that come with it. We're a 30-person team, half scientists (cryptographer PhDs, post-docs, and professors) from renowned universities, half engineers with long web2 experience. A lot of our field is broken and...

### Job 56 — job_id: `hn_1842`
- **Title**: Unknown
- **Company**: VIVA Finance
- **Tags**: AWS, React
- **Description**: VIVA Finance | Atlanta, GA (In Person)| Front-End Developer VIVA is a Fintech Startup based in Atlanta, GA with the mission to build a more inclusive financial system. VIVA offers unsecured personal loans to customers who have traditionally been excluded and taken advantage of by the legacy financial institutions. The VIVA difference is to underwrite heavily on employment history and set up repayments through voluntary direct deposit payments from the borrower's paycheck. Our interest rates are less than 1/3 of the rates our customers are able to get from other financing options. We are a VC b...

### Job 57 — job_id: `hn_1230`
- **Title**: stack Software Engineer
- **Company**: Pango
- **Tags**: AI, Go, React
- **Description**: Pango | Founding Full-stack Software Engineer | On-site (hybrid) in Stockholm, Sweden (Visa Sponsorship possible) | Full time Pango is building the world's first Agentic Operating System for e-commerce logistics. Our vision is to create the AI e-commerce employee of the future. We are forming our core team in Stockholm and are looking for exceptional engineers. We are based at the SSE Business Lab, where companies such as Klarna, Voi, Budbee or Legora originated. We have achieved a product-market fit and are growing rapidly. You are a good fit if: * You are comfortable maintaining, expanding a...

### Job 58 — job_id: `hn_1674`
- **Title**: Technical Program Manager Our mission is to empower field
- **Company**: 40GRID
- **Tags**: AI
- **Description**: 40GRID - Full-time Remote | Technical Program Manager Our mission is to empower field-service companies to grow by modernizing and automating their business operations. Every company we work with has unrealized potentials — our task is to build the platform that empowers growth and helps them unlock opportunities. Email: jobs [at] 40grid.com (no recruiters or agencies, please put HN in subject line, thanks).

### Job 59 — job_id: `hn_1300`
- **Title**: Knowledge of architecture, testing, and deployment of distributed systems
- **Company**: Architect Financial Technologies
- **Tags**: AI, Go, React, Rust, TypeScript
- **Description**: Architect Financial Technologies | Chicago | Onsite / Remote | Full-time | architect.co Architect recently raised a $35M series A and is looking to fill a number of software engineering roles. As a key member of our growing team, you will help build out our advanced exchange which is the world's first centralized and regulated exchange for perpetual futures on traditional assets (FX, stocks, metals, interest rates, energy, compute, and other commodities). Bonus points if you have: - Experience with Rust - Experience working in the finance industry, or a strong interest in electronic trading -...

### Job 60 — job_id: `hn_2088`
- **Title**: manager
- **Company**: Logs SRL
- **Tags**: AI
- **Description**: i-Logs SRL | Brussels, Belgium | Full Time | On Site |  https://www.i-logs.com Brussels based company specialized in Custom Web & Android Applications, Security and Compliance, Managed IT Services and Cloud Hosting. We are looking for Commercial Manager M/F. As a Commercial Manager, you will play a central role in the development of our business. You will work directly with the management committee, actively contribute to defining the commercial strategy, represent the company’s image in the field, and stay continuously trained and informed on cybersecurity issues. Info & Application:  https:/...

### Job 61 — job_id: `hn_1815`
- **Title**: Unknown
- **Company**: Optimal
- **Tags**: AI, Go, Python, React
- **Description**: Optimal | London, UK | ONSITE Simulation and Control Engineer: Up to £150k + 2% depending on experience. Full-stack Software Engineer (Python, React): Up to £150k + 2% depending on experience. Reach out directly to me (founder): david@optimal.ag Optimal is building agents to control the world’s most critical infrastructure - from factories, to datacenters, to farms. We are backed by the Director of AI Research at Google DeepMind as well as early VC investors in SpaceX, Anduril, and Palantir. We have built the world’s most advanced climate control system for high-tech greenhouses and have custo...

### Job 62 — job_id: `hn_338`
- **Title**: Product Engineering (Backend+AI focus)
- **Company**: Kinelo
- **Tags**: AI, Go, Python, TypeScript
- **Description**: Kinelo | kinelo.com | Product Engineering (Backend+AI focus) | San Francisco | Onsite (with flexibility) We are hiring two Product Engineers to join us in our newly opened office in SF. We're small and early and you'll help shape team culture. Kinelo solves "context myopia": autonomous and semi-autonomous AI agents don't know what they don't know, so they can't search or find the background information required to accomplish tasks accurately and effectively. The result looks like slop but it's not due to model performance, more due to workflow integration. From there, we're rapidly moving into...

### Job 63 — job_id: `hn_751`
- **Title**: Unknown
- **Company**: Cloudflare
- **Tags**: AI, Python, Rust
- **Description**: Cloudflare | New York City, Austin, London, Lisbon, San Francisco, Seattle | Full Time I’m hiring for some (IMHO) really fun product manager roles on Cloudflare’s Developer Platform (workers.cloudflare.com) - Workers Runtime - Set vision for our V8 isolate based runtime that lets people deploy JS, TS, Rust and Python to the globe in seconds with great dev ex. - Containers - Help build our new containers platform into the best place for both agent Sandboxes and stateless global apps. - AI Agents - Define what Agents on Cloudflare look like: from our AgentsSDK, to Sandboxes, to MCP Servers, “Cod...
