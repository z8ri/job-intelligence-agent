# Job Category Classification Task

Please classify each of the following job postings into exactly **ONE** of 7 categories. These postings are scraped from HackerNews "Who is Hiring" threads and public company ATS APIs, so formatting is messy and many single posts advertise multiple roles.

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

Output **ONLY** a JSON array in the exact order of the jobs below. Each entry has `job_id` and `category`. No explanation, no extra fields.

```json
[
  {"job_id": "hn_XXX", "category": "backend"},
  {"job_id": "hn_YYY", "category": "data"}
]
```

---

## Jobs to classify (120 total)

### Job 1 — job_id: `hn_1706`
- **Title**: Distributed Systems & Backend Engineers
- **Company**: Krea
- **Tags**: AI, Go, Kubernetes, ML, Python
- **Description**: Krea | Distributed Systems & Backend Engineers | San Francisco, CA (onsite+remote) I'm the cofounder & CTO of Krea ( https://www.krea.ai ). We are a startup in San Francisco building browser-based AI creative tools for professional designers and creatives. Small team (~27); millions of active users; and raised +$80M from top SV investment firms. We're looking for talented engineers who want to tackle hard technical challenges with smart people while building a creative platform that big companies and startups will rely on. You will... - Build distributed systems to process massive (billions of...

### Job 2 — job_id: `hn_528`
- **Title**: Software Engineer #2 (Frontend focus)
- **Company**: Comper
- **Tags**: AI, Go
- **Description**: Comper | Software Engineer #2 (Frontend focus)  | €80-110k + equity | Utrecht, The Netherlands | ONSITE |  https://comper.io We make software landscapes understandable and explorable. Our canvas is zoom-to-code, and shows data on overlays from all of the git repos in your company. LLMs go through the codebase and extract the architecture. We provide clarity when it's most needed: re-orgs, onboarding, explaining the tech stack at board meetings. Or just being stuck in your IDE and want to ask your team mate a question. We'd like to do to large org codebases what Figma did to design. Comper need...

### Job 3 — job_id: `hn_1248`
- **Title**: Senior Software Engineers (Frontend, Mobile)
- **Company**: Noise
- **Tags**: AI, React, TypeScript
- **Description**: Noise | Senior Software Engineers (Frontend, Mobile) | NYC | ONSITE | Full-time | $160k-$210k + equity Noise is building a way to measure and trade attention — something the internet produces endlessly but no one has been able to objectively track. We create a transparent, real-time market for attention itself, revealing what the world actually cares about as it changes. Team of 10 in SoHo. We look for people with great taste who ship code, design, or convey user needs into delightful products. Hiring: Senior Frontend Engineer — Own and ship features across the stack with a frontend focus. Wor...

### Job 4 — job_id: `hn_1239`
- **Title**: Lead Edge AI Engineer
- **Company**: Source ( https://source.network )
- **Tags**: AI, Rust
- **Description**: Source ( https://source.network )| USA/Canada: REMOTE | Full-Time |  https://careers.source.network Our mission is to make it normal, not heroic, for edge AI, mobile apps, and critical software to run close to where data is born: on devices, in vehicles, in field hardware, not just in a distant GPU farm. We’re building the data and trust layer that lets developers ship systems that still behave correctly when links are flaky, latency is awful, and the cloud is optional instead of mandatory—instead of the usual “SQLite everywhere + ad-hoc sync” duct tape. We’re growing fast and are looking to f...

### Job 5 — job_id: `hn_1615`
- **Title**: AI/ML Engineer
- **Company**: NODA AI
- **Tags**: AI, ML
- **Description**: NODA AI | Multiple Roles | Austin TX | Full-time | ONSITE NODA is a veteran-owned, venture-backed technology company that is transforming how unmanned systems collaborate in complex, mission-critical environments. We are developing next-generation solutions that enable the autonomous orchestration of heterogeneous unmanned systems across air, sea, land, and space with vital applications in the defense, intelligence, and commercial sectors. We're looking to scale fast in 2026 and actively hiring for multiple roles, including: - AI/ML Engineer - Autonomy Engineer - Field Ops Engineer - Forward D...

### Job 6 — job_id: `hn_1050`
- **Title**: Data Engineer (pyspark, databricks)
- **Company**: control
- **Tags**: Go
- **Description**: control-f | Data Engineer (pyspark, databricks) | Full-Time | Remote (GER) Wir bei control-f sind echte Daten-Nerds und bauen Big Data Plattformen für Telemetriedaten in der Industrie. Wir suchen jemanden, der Lust hat, mit uns gemeinsam aus Daten-Chaos smarte Lösungen zu machen. Wenn du Spaß daran hast, mit PySpark und Databricks richtig große Datenmengen zu bewegen und dabei technische Herausforderungen nicht scheust, dann bist du bei uns goldrichtig. https://www.controlf.io/jobs-1/data-engineer-(m%2Fw%2Fd)

### Job 7 — job_id: `hn_1973`
- **Title**: Fullstack Platform Engineer
- **Company**: Gaia AI
- **Tags**: AI, AWS, Go, React, TypeScript
- **Description**: Gaia AI | Fullstack Platform Engineer | Full-Time | Boston Hi, I’m Mel at Gaia AI ( https://www.gaia-ai.eco/ ). We’re a small GreenTech startup in Boston building hardware and software in the forestry space. Role: Full stack / platform engineer working on the web app and mobile app. Preferred Years of Experience: >= 3 Our Stack: TypeScript, React, Mongo, AWS, React-native Company Size: 7 people Company Location: Downtown Boston near South Station Apply here:  https://docs.google.com/forms/d/e/1FAIpQLSeXplH__tMz_EIRS4yq...  Feel free to reach out to me with questions: mel at gaia-ai.eco

### Job 8 — job_id: `hn_571`
- **Title**: Senior/Staff Infrastructure Engineer
- **Company**: Bitrise (YC, CI/CD for DevOps)
- **Tags**: AWS, Go
- **Description**: Bitrise (YC, CI/CD for DevOps) | Senior/Staff Infrastructure Engineer | Remote (EU); Budapest, Hungary Own the full stack for real: BGP/EVPN, transit, data center hardware, one of the world's largest Mac build fleets, and a private cloud spanning multiple locations — not just wiring up AWS components. Hybrid Linux/macOS environment, heavy Terraform/Ansible, usage. If blinking LEDs and routing tables get you going, this is the rare infra role where you can touch everything end-to-end. https://bitrise.bamboohr.com/careers/130

### Job 9 — job_id: `hn_477`
- **Title**: Senior Fullstack Engineer
- **Company**: Careforce AI (aka Helpcare)
- **Tags**: AI, Python, React
- **Description**: Careforce AI (aka Helpcare) | Senior Fullstack Engineer | REMOTE (US) Location: Remote (US) Remote: Yes (US Only) Willing to relocate: No Technologies: Python, FastAPI, React, Supabase, GCP, LLMs Résumé/CV:  https://bookface.ycombinator.com/company/30124/jobs/78672  Email: Apply via link above Description: Careforce AI is building autonomous AI agents that eliminate the manual administrative burden in healthcare (fax machines, scheduling, calling). We find, call, and schedule patients, breaking interoperability barriers that have plagued the industry for 40 years. We are a well-funded, YC-back...

### Job 10 — job_id: `hn_1906`
- **Title**: Full Stack Engineer, ML Engineer, Member of Technical Staff
- **Company**: Artificial Analysis
- **Tags**: AI, Java, ML, Python, React, TypeScript
- **Description**: Artificial Analysis |  https://artificialanalysis.ai  | Full Stack Engineer, ML Engineer, Member of Technical Staff | Onsite in San Francisco or in Australia/New Zealand | Competitive Salary + Equity Artificial Analysis is an independent AI benchmarking and insights provider. We benchmark AI to help engineers and companies understand AI and make informed decisions regarding which AI technologies to use. We are fast growing with a team of 20 and have backing from investors including Nat Friedman, Daniel Gross & Andrew Ng. We are hiring for four roles: 1. Full Stack Engineer: Full Stack Engineer...

### Job 11 — job_id: `hn_958`
- **Title**: Staff Fullstack Engineer/Senior Software Engineer/Forward Deployed Engineer
- **Company**: Notable Health
- **Tags**: AI, ML
- **Description**: Notable Health | Staff Fullstack Engineer/Senior Software Engineer/Forward Deployed Engineer | San Mateo, CA | Hybrid Join us at Notable Health! We're building intelligent automation to transform how healthcare works—freeing up clinicians and staff to focus on what matters most: patient care. Our platform uses AI to eliminate manual workflows, streamline operations, and improve outcomes across leading health systems. If you're passionate about meaningful impact and cutting-edge technology, we’d love to hear from you. Apply here:  https://jobs.ashbyhq.com/notable   More at:  https://www.notable...

### Job 12 — job_id: `hn_1551`
- **Title**: Stack Engineers (Senior and Staff), Mobile Engineers, Devops Engineers
- **Company**: ASBL
- **Tags**: AI, AWS, Docker, React, TypeScript
- **Description**: ASBL | Full-Stack Engineers (Senior and Staff), Mobile Engineers, Devops Engineers | Hyderabad, India | ONSITE | 35-80L INR We're a fast-growing, profitable proptech company in India, using technology to solve deeply complex problems in the construction and real estate space. Our mission is to build high-quality homes and deliver them on time—a massive challenge in this industry. Your code directly impacts everything from our supply chain and project management to the final home-buying experience for families. We're looking for product-minded engineers who want to own problems end-to-end in a...

### Job 13 — job_id: `hn_1181`
- **Title**: Senior iOS Real Time Engineer
- **Company**: Lightcraft Technology
- **Tags**: AI
- **Description**: Lightcraft Technology | Senior iOS Real Time Engineer | Remote (US) |  https://lightcraft.pro/ Hi! I’m the co-founder of Lightcraft Technology. We’re creating a collaborative virtual production platform for the future of visual storytelling. Our team includes deep expertise in robotic systems, real time video processing, and Web frameworks – and a couple of Emmys and Oscars between us! Our award-winning Jetset iOS app is the core of our real-time connection to cine cameras and stage production.  https://apps.apple.com/in/app/lightcraft-jetset/id1634621836 We’re looking for a senior iOS/real ti...

### Job 14 — job_id: `hn_1746`
- **Title**: Geospatial Data/Backend and Mobile Engineers
- **Company**: LiveMap
- **Tags**: Go
- **Description**: LiveMap | Geospatial Data/Backend and Mobile Engineers | Full-Time | Switzerland or Remote (CH, EU, UK) Visa sponsorship is not provided. LiveMap is a funded startup with a vision to build the next generation of mapping apps (think hyper-personalised Google Maps). How that looks is still being explored so we're building prototypes, getting them into customer hands and iterating quickly. We're looking to bring on a couple of people to help accelerate this development process. As a data engineer you'll set up a data pipeline, work with product to identify relevant datasets, connect, persist and...

### Job 15 — job_id: `hn_1620`
- **Title**: level Product Managers and Engineers, and Engineering Managers
- **Company**: Chainguard
- **Tags**: AI, Java, Python, Rust
- **Description**: Chainguard | Senior and Staff-level Product Managers and Engineers, and Engineering Managers | REMOTE (US/CAN) We're building the safe, trusted source for open source. We created the secure Container Image market and we've recently expanded into VMs and Libraries for popular language ecosystems such as JavaScript, Python, and Java. We're hiring quite a few PMs and engineers for our Containers and Libraries products, amongst other roles. Check out the listings here  https://www.chainguard.dev/careers  and if you're a highly-technical PM that wants to SHIP email me directly at patrick at chaingu...

### Job 16 — job_id: `hn_1491`
- **Title**: Engineering Manager, ML Security/Research
- **Company**: Intuition Machines, Inc.
- **Tags**: AI, ML
- **Description**: Intuition Machines, Inc. | Engineering Manager, ML Security/Research | MULTIPLE ROLES REMOTE - WORLDWIDE Want to lead ML systems that protect hundreds of millions of users daily, operating at millions of req/s? Interested in building models under strict latency/compute constraints while adapting to adversarial drift? Intuition Machines (company behind hCaptcha security suite) is hiring an Engineering Manager, ML Security/Research to lead a distributed team, own architecture, and stay hands-on with real-time ML + distributed systems. If you have strong experience in production ML, MLOps, and la...

### Job 17 — job_id: `hn_1671`
- **Title**: Software Engineer, Engineering Manager, Director of Engineering
- **Company**: Second Nature
- **Tags**: AI, AWS, Java, Kubernetes, Python, React, TypeScript
- **Description**: Second Nature | Software Engineer, Engineering Manager, Director of Engineering | REMOTE (US) | Full-time Second Nature (< https://secondnature.com >) is redefining professional property management with fully managed Resident Benefits Packages. We're a Resident Experience Platform helping 1,000+ property management companies automate resident onboarding, credit-building, renters insurance, utilities, and other resident services—creating "Triple Win" experiences for residents, property managers, and investors. We're the only 5-time national NARPM vendor of the year! Tech Stack: TypeScript, Reac...

### Job 18 — job_id: `hn_197`
- **Title**: $275,000 [Leadership] Engineering Manager (SF)  https://grnh.se/s7yxefzs5us 8+ yrs
- **Company**: Back by Sequoia Capital, Peregrine is the operatio
- **Tags**: AI
- **Description**: Back by Sequoia Capital, Peregrine is the operational AI platform powering decision making and operations SF / NYC / DC | In-office 4 days | $130,000 - $275,000 [Leadership] Engineering Manager (SF)  https://grnh.se/s7yxefzs5us 8+ yrs - Staff SWE, AI (SF)  https://grnh.se/cq0caps45us 8+ yrs - Staff SWE, Product Security (SF / NYC)  https://grnh.se/b2kbmt3j5us Senior Infrastructure Engineer (UK)  https://grnh.se/6c1kjk525us SWE, AI (SF, NYC, DC)  https://grnh.se/yl9kuqrg5us Sr Software Engineer (SF, NYC, DC)  https://grnh.se/gwf63pot5us Sr Product Designer (SF / NYC)  https://grnh.se/s96svypy5u...

### Job 19 — job_id: `hn_211`
- **Title**: Senior Backend Engineer, Engineering Leadership
- **Company**: Courted ( https://courted.io )
- **Tags**: AI, AWS, Go, ML, Python
- **Description**: Courted ( https://courted.io ) | Senior Backend Engineer, Engineering Leadership | NYC (In-Office 3-4 days) | Python/Django We're building AI-powered recruiting and market intelligence for real estate — an industry that moves $100B+ in annual commissions and still runs on spreadsheets and cold calls. Our backend ingests data from dozens of sources, processes millions of records daily through Celery pipelines, and serves real-time analytics via a Django REST API backed by PostgreSQL/PostGIS. Integrations with OpenAI, HubSpot, Twilio, and MLS data providers. Sub-second response requirements at s...

### Job 20 — job_id: `hn_1182`
- **Title**: Director of Engineering (Player
- **Company**: 2NDNATURE
- **Tags**: AI
- **Description**: 2NDNATURE | Director of Engineering (Player-Coach) | Santa Cruz, CA | ONSITE 2NDNATURE is a small SaaS company providing stormwater management software to municipalities and corporations. We have a mature product grounded in science, a solid customer base, and are at a technical inflection point. We are looking for our Director of Engineering to be a true "player-coach"—a hands-on leader who loves writing code (60% of the role) and mentoring a small team of developers. You will lead our transition into an AI-first platform, helping us adopt modern tools like Claude Code and Copilot to scale ou...

### Job 21 — job_id: `hn_1773`
- **Title**: Software Developer
- **Company**: Communications Security Establishment Canada (CSE)
- **Tags**: Go
- **Description**: Communications Security Establishment Canada (CSE) | Software Developer | On-site Ottawa, Ontario, Canada | Full-time | $103-139k + pension + benefits | https://www.cse-cst.gc.ca/en/careers Communications Security Establishment Canada (CSE) is the national cryptologic agency, providing the Government of Canada with information technology security and foreign signals intelligence. We are team players, pathfinders, and problem solvers, all different, all united by a common mission: protecting Canada and Canadians. We are looking for entry-level, intermediate, and experienced software developers...

### Job 22 — job_id: `ext_01024`
- **Title**: Backend Software Engineer
- **Company**: Second Spectrum, of Genius Sports
- **Tags**: (no tags)
- **Description**: Salary 100,000 - 140,000 USD per year Requirements: - What You Have: Proficiency with Rust and/or TypeScript Experience with architecting and benchmarking high-performance, real-time systems Enthusiasm towards framework development Team-first mindset Ability to excel in a fast-paced environment You care about your craft Learning and mentoring mentality 3 years of industry experience Responsibilities: - What You’ll Get To Do: Work as an integral part of our capture team supporting its mission of…

### Job 23 — job_id: `ext_01451`
- **Title**: Software Engineer, Backend
- **Company**: Harvey
- **Tags**: (no tags)
- **Description**: Why Harvey Harvey is a secure AI platform for professionals in law, tax, and finance that augments productivity and automates complex workflows. Harvey uses algorithms with reasoning-adept LLMs that have been customized and developed by our expert team of lawyers, engineers and research scientists. We’ve found product market fit and are scaling our team very quickly. Some reasons to join Harvey are: Exceptional product market fit: We have partnered with the largest law firms and professional se…

### Job 24 — job_id: `ext_01938`
- **Title**: Senior Back End Python Developer
- **Company**: DMI
- **Tags**: (no tags)
- **Description**: Senior Back End Python Developer Job ID 2024-27354 Category Software Development Location US-OH-Cincinnati About DMI DMI is a leading global provider of digital services working at the intersection of public and private sectors. With broad capabilities across IT managed services, cybersecurity, cloud migration and application development, DMI provides on-site and remote support to clients within governments, healthcare, financial services, transportation, manufacturing, and other critical infra…

### Job 25 — job_id: `ext_01931`
- **Title**: Online Banking – Sr. Back End Developer
- **Company**: First Horizon
- **Tags**: (no tags)
- **Description**: Location: On site at location listed in job posting. Summary The Online Banking – Sr. Back End Developer is responsible for working closely with Front End developer teams and Application Architect to design and develop clean and intuitive APIs to help implement or improve features. Work in an agile team environment, collaborating with all team members to produce high quality interfaces. Requires Qualification Include: Bachelor’s degree in Computer Science, Management Information Systems, relate…

### Job 26 — job_id: `ext_03031`
- **Title**: AI Backend Engineer
- **Company**: Replit, Inc.
- **Tags**: (no tags)
- **Description**: AI Backend Engineer Company: Replit, Inc. Location: San Francisco, CA Position Type: Full Time Experience: See below Education: See below Responsibilities: Design, develop, and maintain the backend systems that support AI features on the Replit platform; Collaborate with AI researchers and engineers to integrate AI models and algorithms into our platform; Optimize and scale Large Language Model serving infrastructure to ensure the platform can handle increasing user demands; Implement monitorin…

### Job 27 — job_id: `ext_01005`
- **Title**: Senior Backend Software Engineer
- **Company**: Hireio, Inc.
- **Tags**: (no tags)
- **Description**: Responsibilities: Create innovative monetization products that drive engagement and business outcomes. Develop highly scalable services that powers new ad products for billions of requests. Design systems that will optimize monetization efficiency with product engineering and state-of-the-art machine learning technologies. Implement new ad solutions that will continuously protect the user experiences. Collaborate with strategy team, product managers, and other key stakeholders to define product…

### Job 28 — job_id: `ext_01440`
- **Title**: Backend Software Engineer
- **Company**: Booz Allen Hamilton United States
- **Tags**: (no tags)
- **Description**: Backend Software Engineer The Opportunity: As an AI software engineer, you know that good software is more than just a nice-looking interface and data. Today, you need to develop user-focused solutions that increase organizational efficiency and enable better decision-making. Booz Allen is the leading provider of AI services to the nation—we’re looking for a software engineer like you to create artificial intelligence and machine learning solutions that help solve the defense industry's toughes…

### Job 29 — job_id: `ext_00342`
- **Title**: Lead Software Engineer, Backend Java
- **Company**: J.B. Hunt Transport Services, Inc.
- **Tags**: (no tags)
- **Description**: Job Summary: Under general supervision, this Software Engineer is responsible for applying advanced programming techniques during development and design tasks. This position documents programs, develops and implements new features, and supports critical web applications' layer architecture, various back end systems supporting the platform, and other digital initiatives. The incumbent serves as a team lead and ensures compliance with J.B. Hunt's architectural standards. Job Description: Key Resp…

### Job 30 — job_id: `ext_01842`
- **Title**: Front End Developer
- **Company**: Acoustic
- **Tags**: (no tags)
- **Description**: Develop dynamic UI screens using HTML5, CSS3, JavaScript, AngularJS, ReactJS, Bootstrap, NodeJS, ExpressJS, Dojo, Rappid, JointJS and jQuery. Use AngularJS components like directives, factories and service resources, routing, dependency injection, 2-way data binding, filters and events. Work on Rappid and JointJS framework to create an interactive flowchart, diagrams for programs and enable users to manipulate the data. Develop custom AngularJS directives to build custom reusable components to …

### Job 31 — job_id: `ext_01865`
- **Title**: Jr. Front End Developer
- **Company**: GCommerce
- **Tags**: (no tags)
- **Description**: Jr. Front-End Developer (1-2 Years Experience) Grow your skill-set, accelerate your career and work with an awesome team in Park City, UT Updated: 02/04/2016 GCommerce is looking for a full-time or Jr. Front-End Developer to join our development team. The ideal candidate has a creative personality and a passion for building clean, functional front end interfaces. Experience with HTML5 and JavaScript frameworks is important, but even more important is your drive to learn and keep up on the lates…

### Job 32 — job_id: `ext_01891`
- **Title**: Website Designer & Wordpress Front End Developer
- **Company**: Clix
- **Tags**: (no tags)
- **Description**: Are you a creative and skilled Website Designer and Front-End Developer looking to elevate your career in a remote , dynamic , and collaborative digital environment? Clix is a team of expert digital marketers, creatives, and problem-solvers who lead and manage impactful digital marketing campaigns across diverse industries. Our culture thrives on collaboration, professional growth, and performance, empowering individuals to excel and innovate. We are seeking a talented, ambitious Website Design…

### Job 33 — job_id: `ext_01888`
- **Title**: Sr. Angular & Chrome Extensions Front End Developer
- **Company**: Mozaic.io
- **Tags**: (no tags)
- **Description**: About Mozaic: Mozaic.io is a fast-growing payments startup focused on facilitating payouts to creators and their collaborators all over the world. Our dynamic and collaborative team is dedicated to revolutionizing the way creators get paid. The company has offices in Chicago and Nashville, and aims to make compensation as equally distributed as talent is in the Creator Economy. Location: Nashville, TN Job Description As a Senior Front-End Developer specializing in Angular and Chrome Extensions,…

### Job 34 — job_id: `ext_01889`
- **Title**: Senior Front End Developer - Fully Cleared
- **Company**: Eqlipse Technologies
- **Tags**: (no tags)
- **Description**: At BlueHalo, we don’t just witness the future of national security – we create it. We're on the search for a Senior Front End Development Engineer to embark on challenging, mission-critical projects at Laurel, MD , directly impacting the nation’s security and intelligence mission. In our team of problem solvers, innovators, technologists, and operators, you'll be at the forefront of driving meaningful change and making an enduring impact. Are you ready to advance your career and make a signific…

### Job 35 — job_id: `ext_01906`
- **Title**: Multimedia Specialist/Front End Web Developer - Journeyman
- **Company**: Global Dimensions
- **Tags**: (no tags)
- **Description**: Global Dimensions is a HUBZone, service disabled, veteran-owned small business based in Fredericksburg, VA. We are a dynamic, expanding company with exciting opportunities in language/culture, training/education/instruction, IT, cyber security, and intelligence. Global Dimensions is seeking a Journeyman Multimedia Specialist/Front End Web Developer for a position in Springfield, VA. Requirements TS/SCI (with ability to pass CI poly if requested) Position requires more than three (3) years of re…

### Job 36 — job_id: `ext_08384`
- **Title**: Cloud Compute Frontend Software Engineer, Core Compute Experience
- **Company**: Google
- **Tags**: (no tags)
- **Description**: Minimum qualifications: Bachelor’s degree, or equivalent practical experience. 8 years of experience with software development in one or more programming languages Python, C, C++, Java, JavaScript etc. 5 years of experience with Front-End Development. 5 years of experience with web application development. 3 years of experience in a technical leadership role, overseeing projects, with 2 years of experience in a people management, supervision/team leadership role. Preferred qualifications: Maste…

### Job 37 — job_id: `ext_01901`
- **Title**: Front End Web Developer
- **Company**: The Timberline Group
- **Tags**: (no tags)
- **Description**: Front End Web Developer works with a team of talented individuals who share a strong passion for their work. The primary role of this individual will be to build and maintain web pages using a variety of graphics software applications, techniques and tools. The Web Developer applies the best of standards-based web development, information architecture and usability principles to produce quality and user-friendly creative work. We warn potential hires in advance: this full-time position will cha…

### Job 38 — job_id: `ext_01866`
- **Title**: Front-End Developer, Angular
- **Company**: Schneider Electric USA, Inc
- **Tags**: (no tags)
- **Description**: For this U.S. based position, the expected compensation range is $96,000 - $144,000 per year, which includes base pay and short-term incentive. The compensation range for this full-time position applies to candidates located within the United States. Our salary ranges are determined by reviewing roles of similar responsibility and level. Within the salary range, individual pay is determined by several factors including performance, knowledge, job-related skills, experience, and relevant educati…

### Job 39 — job_id: `ext_01864`
- **Title**: Senior Front-End Developer
- **Company**: PTP
- **Tags**: (no tags)
- **Description**: PTP is a fast-growing system integrator that offers strategic Customer Experience (CX) solutions to our clients. We are looking for a Senior Front-End Developer to help us develop CX solutions that provide our clients with customer journeys that achieve results. At PTP we value aptitude and creativity as well as experience. We are a diverse organization and are looking for bright, passionate, and committed professionals who strive to be the best at what they do. Responsibilities Develop and mai…

### Job 40 — job_id: `ext_01869`
- **Title**: Senior Front End Developer
- **Company**: Intercontinental Exchange Holdings
- **Tags**: (no tags)
- **Description**: Intercontinental Exchange (ICE) is seeking a Senior Front-End Web Developer who will be responsible for building and supporting single page applications (SPA). These large-scale applications will need to integrate with disparate systems using RESTful web services, JavaScript APIs, and various other back-end systems. The ideal candidate should have deep knowledge of JavaScript, CSS, and HTML5 concepts as well as modern toolsets, such as React, Redux and TypeScript Responsibilities • Contribute t…

### Job 41 — job_id: `ext_01872`
- **Title**: Senior Front End Developer
- **Company**: Perr&Knight
- **Tags**: (no tags)
- **Description**: What We'll Bring to the Table: - Friendly, dynamic work environment – Includes certification as a Great Place to Work ® (three years in a row) along with Climate Neutral Status - Competitive salary including merit-based bonus plan - Flexible Work Program - Clear opportunities for career progression - Company-funded professional educational program - Visible management commitment to our company core values of: Diversity & Inclusion, Environmental, Community and Employee Wellbeing, Excellent Work…

### Job 42 — job_id: `ext_01874`
- **Title**: Senior Front-End Developer
- **Company**: Drexel University
- **Tags**: (no tags)
- **Description**: Senior Front-End Developer Apply now Job no: 504144 Work type: Full-Time Location: University City - Philadelphia, PA Categories: Drexel University Job Summary Collaborates with user-experience designers, web developers, and back-end developers to design and develop sophisticated, modern user interfaces for high-volume, large-scale web applications with a focus on mobile-first responsive design. Build and maintain technical knowledge relevant to assigned projects while learning and adapting to …

### Job 43 — job_id: `ext_01861`
- **Title**: Front End Developer
- **Company**: Creative Financial Staffing
- **Tags**: (no tags)
- **Description**: Position: Front End Developer (Remote) An industry leading Software as a Service (SaaS) company based out of the Madison, WI area is looking to add a mid-senior level Front End Developer to their software development team Mid-sized organization with a casual and supportive work culture. Great opportunity to work with modern web development technologies. Technology & Software driven company specializing in the education industry. Company likes to promote from within, and provides training opport…

### Job 44 — job_id: `ext_01908`
- **Title**: Front-End Web Developer Vice President
- **Company**: JPMorgan Chase Bank, N.A.
- **Tags**: (no tags)
- **Description**: Join our dynamic Consumer & Community Banking Multimedia Center of Excellence team, where we focus on enhancing communication and engagement within our organization. We are committed to leveraging technology to streamline processes and improve the efficiency of our communications professionals. As a Front-End Web Developer Vice President you will create customer custom web applications that support various internal communications needs, including event registration, rehearsal scheduling, award …

### Job 45 — job_id: `ext_01863`
- **Title**: Front End Developer (On-site)
- **Company**: Melink Corporation
- **Tags**: (no tags)
- **Description**: Location: Milford, OH (On- site) Salary Range: $65,000-$70,000 Target Start: January, 2025 Front End Developer Job Description: We are looking for a full-time Front-End Developer to help take our company to the next level. As a small-medium sized business in the emerging energy efficiency and renewable energy space, our goal is to grow sales 30% per year and become a national leader. The ideal candidate will be able to enhance existing applications, develop new applications, and help define fun…

### Job 46 — job_id: `ext_02629`
- **Title**: AI & Machine Learning Engineer
- **Company**: SynergisticIT
- **Tags**: (no tags)
- **Description**: Since 2010 Synergisticit has helped Jobseekers get employed in the tech Job market by providing candidates the requisite skills, experience, and technical competence to outperform at interviews and clients. Here at SynergisticIT We just don't focus on getting you a tech Job we make careers. In this Job market also, our candidates can achieve multiple job offers and $100k salaries. please check the below links to see the success outcomes and salaries of our candidates . https://www.synergistici…

### Job 47 — job_id: `ext_02459`
- **Title**: Data Scientist - Senior
- **Company**: bcore
- **Tags**: (no tags)
- **Description**: GeoYeti is a division of Bcore, a full-spectrum intelligence company built on trust and teamwork whose core mission is to innovate within the national security space. GeoYeti focuses on advanced analytics, data science, development of the applications that support such work. We seek senior DATA SCIENTIST to support a client in St Louis, MO . We support a broad range of IC and DoD clients, though a common theme across our portfolio is that our team members, regardless of their role, interact wit…

### Job 48 — job_id: `ext_02601`
- **Title**: Machine Learning Engineer (The AI Innovator)
- **Company**: Unreal Gigs
- **Tags**: (no tags)
- **Description**: Are you passionate about designing, building, and maintaining data pipelines that support robust data architectures and facilitate seamless data flow? Do you excel in creating scalable solutions that empower data-driven decision-making? If you’re ready to develop and optimize data systems that drive impactful analytics, our client has the perfect role for you. We’re seeking a Data Engineer (aka The Data Pipeline Architect) to build and manage cloud-based data infrastructures that support analyt…

### Job 49 — job_id: `ext_02492`
- **Title**: Senior Data Scientist
- **Company**: Shipwell
- **Tags**: (no tags)
- **Description**: Data Scientist ABOUT US Shipwell believes we are fundamentally changing the logistics industry and breaking the mold for how the supply chain has been operated for centuries. We work with thousands of shippers and carriers to create the first real solution in logistics through an unmatched technology platform. With a fast-paced and gritty startup mentally, which is generating a buzz in the investment world, Shipwell provides a unique opportunity to get in on the ground floor of a future Fortune…

### Job 50 — job_id: `ext_06898`
- **Title**: Senior Data Analyst, Product Analytics
- **Company**: Extend
- **Tags**: (no tags)
- **Description**: Extend is modernizing the $100 billion-per-year protection plan industry using cutting-edge technology and top-notch customer service. Our technology-forward omnichannel and API-first solution allows any merchant to offer protection plans, both online and in store, while also providing a merchants end customers with a vastly improved and modern support experience that eliminates many of the issues customers face today with legacy underwriters. More recently, Extend also launched a shipping prot…

### Job 51 — job_id: `ext_03278`
- **Title**: AI & Machine Learning Engineer - Manager - Consulting - Location OPEN
- **Company**: EY
- **Tags**: (no tags)
- **Description**: At EY, you’ll have the chance to build a career as unique as you are, with the global scale, support, inclusive culture and technology to become the best version of you. And we’re counting on your unique voice and perspective to help EY become even better. Join us and build an exceptional experience for yourself, and a better working world for all. The exceptional EY experience. It's yours to build. EY focuses on high-ethical standards and integrity among its employees and expects all candidate…

### Job 52 — job_id: `ext_02672`
- **Title**: Senior Machine Learning Engineer
- **Company**: Samsara
- **Tags**: (no tags)
- **Description**: Samsara (NYSE: IOT) is the pioneer of the Connected Operations™ Cloud, which is a platform that enables organizations that depend on physical operations to harness Internet of Things (IoT) data to develop actionable insights and improve their operations. At Samsara, we are helping improve the safety, efficiency and sustainability of the physical operations that power our global economy. Representing more than 40% of global GDP, these industries are the infrastructure of our planet, including ag…

### Job 53 — job_id: `ext_02786`
- **Title**: AI & Machine Learning Engineer - Manager - Consulting - Location OPEN
- **Company**: EY
- **Tags**: (no tags)
- **Description**: At EY, you’ll have the chance to build a career as unique as you are, with the global scale, support, inclusive culture and technology to become the best version of you. And we’re counting on your unique voice and perspective to help EY become even better. Join us and build an exceptional experience for yourself, and a better working world for all. The exceptional EY experience. It's yours to build. EY focuses on high-ethical standards and integrity among its employees and expects all candidate…

### Job 54 — job_id: `ext_03282`
- **Title**: AI & Machine Learning Engineer - Manager - Consulting - Location OPEN
- **Company**: EY
- **Tags**: (no tags)
- **Description**: At EY, you’ll have the chance to build a career as unique as you are, with the global scale, support, inclusive culture and technology to become the best version of you. And we’re counting on your unique voice and perspective to help EY become even better. Join us and build an exceptional experience for yourself, and a better working world for all. The exceptional EY experience. It's yours to build. EY focuses on high-ethical standards and integrity among its employees and expects all candidate…

### Job 55 — job_id: `ext_03088`
- **Title**: AI and ML Engineer
- **Company**: Booz Allen Hamilton United States
- **Tags**: (no tags)
- **Description**: AI and ML Engineer The Opportunity: As an experienced engineer, you know that machine learning is critical to understanding and processing massive datasets. Your ability to conduct statistical analyses on business processes using ML techniques makes you an integral part of delivering a customer-focused solution. We need your technical knowledge and desire to problem-solve to support our clients' challenges. As a machine learning engineer on our team, you’ll train, test, deploy, and maintain mod…

### Job 56 — job_id: `ext_02006`
- **Title**: Human Behavior Data Scientist
- **Company**: Air Force Research Laboratory
- **Tags**: (no tags)
- **Description**: Job Overview This announcement will be accepting candidate submissions until 09 December 2024. The Cognitive Models Branch of the 711 th Human Performance Wing within the Air Force Research Laboratory (711 HPW/RHWE) seeks to hire a qualified individual to support a cross-disciplinary team with the development of data analytic and mining representations of human multisensory perception and behavior in the information environment in support of the creation of computational models and engineering …

### Job 57 — job_id: `ext_02490`
- **Title**: Senior Data Scientist
- **Company**: Launch Potato
- **Tags**: (no tags)
- **Description**: WHO ARE WE? Launch Potato is a digital media company with a portfolio of brands and technologies. As The Discovery and Conversion Company, Launch Potato is a leading connector of advertisers to customers at all parts of the consumer journey, from awareness to consideration to purchase. The company is headquartered in vibrant downtown Delray Beach, Florida , with a unique international team across over a dozen countries. Launch Potato's success comes from a diverse, energetic culture and high-pe…

### Job 58 — job_id: `ext_02746`
- **Title**: Staff Machine Learning Engineer - ML Algorithms
- **Company**: Earnin
- **Tags**: (no tags)
- **Description**: ABOUT EARNIN As one of the first pioneers of earned wage access, our passion at EarnIn is building products that deliver real-time financial flexibility for those with the unique needs of living paycheck to paycheck. Our community members access their earnings as they earn them, with options to spend, save, and grow their money without mandatory fees, interest rates, or credit checks. We're fortunate to have an incredibly experienced leadership team, combined with world-class funding partners l…

### Job 59 — job_id: `ext_02479`
- **Title**: Data Scientist - Senior
- **Company**: bcore
- **Tags**: (no tags)
- **Description**: GeoYeti is a division of Bcore, a full-spectrum intelligence company built on trust and teamwork whose core mission is to innovate within the national security space. GeoYeti focuses on advanced analytics, data science, development of the applications that support such work. We seek senior-level Data Scientist to support a client in St Louis, MO . We support a broad range of IC and DoD clients, though a common theme across our portfolio is that our team members, regardless of their role, intera…

### Job 60 — job_id: `ext_02939`
- **Title**: Senior AI Engineer
- **Company**: Unreal Gigs
- **Tags**: (no tags)
- **Description**: Company Overview: Welcome to the forefront of AI engineering At our company, we're passionate about leveraging the latest advancements in artificial intelligence to drive innovation and solve complex challenges. Our mission is to develop cutting-edge AI solutions that transform industries and improve people's lives. Join us and be part of a dynamic team committed to pushing the boundaries of AI technology. Position Overview: As a Senior AI Engineer, you'll lead the design, development, and depl…

### Job 61 — job_id: `ext_02561`
- **Title**: Machine Learning Engineer
- **Company**: Tiger Analytics
- **Tags**: (no tags)
- **Description**: Tiger Analytics is looking for experienced Machine Learning Engineers to join our fast-growing advanced analytics consulting firm. Our employees bring deep expertise in Machine Learning, Data Science, and AI. We are the trusted analytics partner for multiple Fortune 500 companies, enabling them to generate business value from data. Our business value and leadership has been recognized by various market research firms, including Forrester and Gartner. We are looking for top-notch talent as we co…

### Job 62 — job_id: `ext_07749`
- **Title**: Sr. Devops/Network Automation Engineer
- **Company**: Moody's
- **Tags**: (no tags)
- **Description**: Moody’s is a developmental culture where we value candidates who are willing to grow. So, if you are excited about this opportunity but don’t meet every single requirement, please apply You may be a perfect fit for this role or other open roles. Moody's is a global integrated risk assessment firm that empowers organizations to make better decisions. At Moody’s, we’re taking action. We’re hiring diverse talent and providing underrepresented groups with equitable opportunities in their careers. W…

### Job 63 — job_id: `ext_07448`
- **Title**: DevOps Engineer 3
- **Company**: Bickham Services Unlimited, LLC
- **Tags**: (no tags)
- **Description**: Job Title : DevOps Engineer 3 Location: Remote : (Any location within Texas) Type : Full-Time Schedule: Monday to Friday, 8:00 AM – 5:00 PM Position Overview : Our client seeks a skilled DevOps Engineer 3 to join the DevSecOps team, playing a crucial role in developing and maintaining CI/CD pipelines and deploying applications for Eligibility Supporting Technology applications. This role includes environment triage support and on-call support to ensure the availability of development, testing, …

### Job 64 — job_id: `ext_07330`
- **Title**: DevOps Engineer
- **Company**: LeafLink
- **Tags**: (no tags)
- **Description**: LeafLink is the largest unified B2B cannabis platform, providing licensed cannabis businesses a suite of tools to manage their business more effectively, sell or order from their favorite brands and accelerate growth. We are one platform, one solution and we’re defining the way thousands of cannabis brands, distributors, and retailers streamline their operations. With thousands of brands and retailers across 30 markets in North America, we are setting the industry standard for how cannabis busi…

### Job 65 — job_id: `ext_07637`
- **Title**: DevOps Engineer 4 - Tysons, VA
- **Company**: M.C. Dean, Inc.
- **Tags**: (no tags)
- **Description**: DevOps Engineer 4 - Tysons, VA ID 12678 Location Tysons, VA Apply Now (https://phg.tbe.taleo.net/phg04/ats/careers/v2/applyRequisition?orgMCDEAN&cws62&rid12678) Your Future at M.C. Dean We're seeking people driven to excellence and inspired to have a meaningful impact powering, automating, integrating, and securing the world’s most critical infrastructure and facilities. This translates into fulfilling opportunities for employees driven to excel in a meaningful career. As an employee at M.C. De…

### Job 66 — job_id: `ext_07556`
- **Title**: Confluent Kafka DevOps Engineer
- **Company**: ApTask
- **Tags**: (no tags)
- **Description**: About Client: The client is a global technology, consulting, and digital solutions company with problem-solving abilities and an emphasis on developing ingenious solutions that allow its clients to remain competitive, profitable, and secure in an evolving business environment. Client anticipates and leads change to remain in the leader's quadrant for profitable growth, driven by partnerships with globally leading hyperscales like AWS, Google Cloud, and Microsoft. It has built strong capabilitie…

### Job 67 — job_id: `ext_01468`
- **Title**: Software Engineer, DevOps
- **Company**: Universal Orlando
- **Tags**: (no tags)
- **Description**: Universal Orlando Resort believes in-person collaboration is key to our success. Many of our Team Members work in a hybrid capacity, contributing from the workplace a minimum of three days per week. There are also roles that require being on-site full time. Limited remote opportunities may be available within specific departments. You’ll learn more about this during the recruitment process. JOB SUMMARY: The Software Engineer, DevOps is responsible for implementing and maintaining the continuous…

### Job 68 — job_id: `ext_07981`
- **Title**: Senior Principal Consultant - Cloud Engineer/Developer
- **Company**: CLBPTS
- **Tags**: (no tags)
- **Description**: Description Must currently hold and have the ability to maintain a TS/SCI with a Poly. An experienced consulting professional who has a broad understanding of solutions, industry best practices, multiple business processes or technology designs within a product/technology family. Operates independently to provide quality work products to an engagement. Performs varied and complex duties and tasks that need independent judgment, in order to implement Oracle products and technology to meet custom…

### Job 69 — job_id: `ext_07744`
- **Title**: DevOps - Lead Software Engineer
- **Company**: 241387-Comp & Ben Admin Prof Fees
- **Tags**: (no tags)
- **Description**: Description We have an opportunity to impact your career and provide an adventure where you can push the limits of what's possible. As a Lead Software Engineer at JPMorgan Chase within the Commercial & Investment Bank (CIB) Payments Technology team, you are an integral part of an agile team that works to enhance, build, and deliver trusted market-leading technology products in a secure, stable, and scalable way. As a core technical contributor, you are responsible for conducting critical techno…

### Job 70 — job_id: `ext_07316`
- **Title**: DevOps Engineer
- **Company**: Syntricate Technologies
- **Tags**: (no tags)
- **Description**: Greetings, My name is Swati and I'm a recruiter at Syntricate Technologies Inc. Our records show that you are an experienced professional with relevant experience. This experience is relevant to one of my current openings. Job Title: DevOps Engineer Location: Cary, NC (Onsite) Duration :Full Time Job Description: • Strong DevOps experience • Strong experience with CI/CD • Experience with TeamCity • Experience with Jenkins • Experience with Ansible, Chef, Puppet • Strong shell scripting/other sc…

### Job 71 — job_id: `ext_07529`
- **Title**: Cloud DevOps Engineer
- **Company**: Zoom
- **Tags**: (no tags)
- **Description**: Sponsorship is not available for this position What you can expect Zoom is looking for Cloud DevOps Engineers to join our Zoom for Government organization. You will design and maintain scalable cloud infrastructure, and implement best practices for CI/CD, IaC, logging, monitoring, and automation. You'll partner with our international teams to ensure the platform is constantly running at the highest level. About the Team The Zoom for Government organization is responsible for the critical produ…

### Job 72 — job_id: `ext_07929`
- **Title**: Cloud Engineer (TS SCI)
- **Company**: Progressive Technology Federal Systems
- **Tags**: (no tags)
- **Description**: Title: Cloud Engineer (TS/SCI Clearance) PTFS is a leader in digital content management solutions, content digitization, and library services/solutions, serving more than 500 organizations around the world. Position Summary: The Cloud Engineer will be responsible for working with highly functional development team automating service deployments; optimizing system performance; integrating with enterprise authentication services; establishing/improving system monitoring; maintaining established s…

### Job 73 — job_id: `ext_07301`
- **Title**: DevOps Engineer
- **Company**: Trident Consulting
- **Tags**: (no tags)
- **Description**: Trident Consulting is seeking a " DevOps Engineer " for one of our clients in "McLean, VA ". Role:- DevOps Engineer with Groovy Scripting Location :- McLean, VA (Day 1 Onsite 3 days onsite 2 days Remote) Job mode : Contract Skills Needed- CI/CD, Groovy, Jenkins, AWS Services (EC2 & etc.) Job Duties:- Hands on experience on DevOps CI/CD process and methodologies. Have a development experience on Java, Python and many more. Hands on experience on Jenkins and Groovy scripting. Have experience on A…

### Job 74 — job_id: `ext_07561`
- **Title**: Senior DevOps Engineer I
- **Company**: Zip
- **Tags**: (no tags)
- **Description**: Join Zip’s Engineering function and put your name to solving fascinating challenges at scale in an agile, test-driven development environment. If you value good domain-driven design and enjoy delivering quality work at pace, you’ll be a great fit with the squads responsible for building cloud-native software applications that serve millions of customers and process billions of dollars in payments. We are seeking a seasoned leader with extensive senior leadership experience to spearhead our Infr…

### Job 75 — job_id: `ext_09343`
- **Title**: Cyber Security Systems Engineer
- **Company**: The Pennsylvania State University
- **Tags**: (no tags)
- **Description**: APPLICATION INSTRUCTIONS: CURRENT PENN STATE EMPLOYEE (faculty, staff, technical service, or student), please login to Workday to complete the internal application process . Please do not apply here, apply internally through Workday. CURRENT PENN STATE STUDENT (not employed previously at the university) and seeking employment with Penn State, please login to Workday to complete the student application process. Please do not apply here, apply internally through Workday. If you are NOT a current …

### Job 76 — job_id: `ext_01603`
- **Title**: Java Full stack Developer
- **Company**: Capgemini
- **Tags**: (no tags)
- **Description**: We need a full-stack developer who will use their passion to learn new tools and techniques, and identify and implement system improvements. Using Agile development in a Cloud environment, you’ll work with the development team to build an advanced microservices platform for our Healthcare Manufacturing client. You’ll analyze the needs and the environment to make sure the solution you’re developing considers the current architecture and operating environment, as well as future functionality and …

### Job 77 — job_id: `ext_00983`
- **Title**: Full Stack Software Engineer
- **Company**: SciTec
- **Tags**: (no tags)
- **Description**: SciTec has been awarded multiple government contracts and is growing our creative Team SciTec, Inc. is a dynamic small business with the mission to deliver advanced sensor data processing technologies and scientific instrumentation capabilities in support of National Security and Defense. We support customers throughout the Department of Defense and U.S. Government in building innovative new tools to deliver unique world-class data exploitation capabilities. Important Notice : SciTec exclusivel…

### Job 78 — job_id: `ext_01645`
- **Title**: Dot Net Full Stack Developer
- **Company**: Diverse Lynx
- **Tags**: (no tags)
- **Description**: Job Title: Dot Net Full Stack Developer Location: Redmond, WA (Onsite) Job Type: Full time Position Job Description: Key Responsibilities : Design, develop, and maintain robust and scalable full-stack applications using .NET and C#. Architect and implement microservices-based applications deployed on Azure, ensuring modularity and scalability. Integrate and utilize Azure backend services such as Azure API Management, Azure Service Bus, Azure Event Grid, Azure Logic Apps, and Azure Functions. Im…

### Job 79 — job_id: `ext_00912`
- **Title**: AI Software Engineer - Full Stack (Junior to Mid Level)
- **Company**: Human Resources Research Organization
- **Tags**: (no tags)
- **Description**: AI Software Engineer - Full Stack (Junior to Mid Level) The Human Resources Research Organization (HumRRO) is a non-profit leader in applied research, evaluation, and analytics in the arenas of employment, student, and military testing, and professional credentialing and licensing. We work with federal and state government agencies, private sector organizations, and professional associations. About the Organization As a non-profit, HumRRO is dedicated to work that contributes to science and soc…

### Job 80 — job_id: `ext_01784`
- **Title**: Senior Full Stack .Net Developer
- **Company**: Verisk
- **Tags**: (no tags)
- **Description**: We are looking for a strong and motivated software developer to work as part of a team in developing and implementing innovative software solutions. You will work closely with a cross-functional team of developers, QA engineers, and product owners in a fast-paced and cutting-edge environment. You will use your deep technical knowledge and experience to build robust, efficient, and performant software applications. You will always find new challenges that excite you and keep you motivated. Respo…

### Job 81 — job_id: `ext_01597`
- **Title**: Senior Full-stack Developer
- **Company**: University of Chicago
- **Tags**: (no tags)
- **Description**: Department BSD PED - Hematology, Oncology, and Stem Cell Transplantation - Pediatric Cancer Data Commons - Software Engineering About the Department The Biological Sciences Division’s ‘Data for the Common Good’ (D4CG), is a rapidly growing team of experts in medicine, clinical research, public health, data standards, data infrastructure and programming, data governance, and international data sharing. Headquartered in the Department of Pediatrics at the University of Chicago, Data for the Commo…

### Job 82 — job_id: `ext_01699`
- **Title**: Mid-Senior Level Full Stack Developer
- **Company**: Ion Solar
- **Tags**: (no tags)
- **Description**: Job Details Job Location UT Corp - Orem, UT Position Type Full Time Salary Range $100,000.00 - $150,000.00 Salary Description About Us: ION Solar is a leading sales organization focused on bringing sustainable energy solutions to communities. We build and leverage technology to enhance and streamline our sales and operational processes, making a real impact in the solar industry. As part of our tech team, you'll play a key role in developing the tools that empower our sales and operations teams…

### Job 83 — job_id: `ext_01749`
- **Title**: Full Stack/ETL Developer
- **Company**: Leidos
- **Tags**: (no tags)
- **Description**: Why wake up every day and want more when YOU CAN HAVE IT? Do you love KNOWING at the end of each day that your work made a difference? We embrace and solve some of the world's toughest challenges. We’re focused on ensuring our intelligence customers have the right tools, technologies, and tactics to keep pace with an ever evolving threat landscape and succeed in their mission to protect people and critical assets around the world. Who wouldn’t be fulfilled being part of that every day? We know …

### Job 84 — job_id: `ext_01684`
- **Title**: Lead java full stack developer sc
- **Company**: ESR Healthcare
- **Tags**: (no tags)
- **Description**: If you post this job on a job board, please do not use company name or salary. Experience level: Mid-senior Experience required: 5 Years Education level: Bachelor’s degree Job function: Engineering Industry: Chemicals Compensation: View salary Total position: 1 Relocation assistance: Yes Visa : Only US citizens and Greencard holders JOB DESCRIPTION: DuPont is seeking an experienced Electrical Engineer for our Healthcare and Specialty Lubricants (HSL) operations at the Cooper River North plant i…

### Job 85 — job_id: `ext_00990`
- **Title**: Full Stack Software Engineer
- **Company**: LIGHTFEATHER IO LLC
- **Tags**: (no tags)
- **Description**: LightFeather is currently seeking talented Full Stack Software Engineers who are well versed in Agile Development using Object Oriented Programming and microservices in the AWS cloud using React and Java Spring Boot . This is a long-term project. Successful candidates must thrive in a collaborative team culture. This Position is Full Time, Remote. Essential Job Functions: Devises and modifies applications programs and procedures from detailed specifications to solve complex problems. Designs, c…

### Job 86 — job_id: `ext_01563`
- **Title**: Full Stack Developer (Java, Angular)
- **Company**: Syzygy Integration
- **Tags**: (no tags)
- **Description**: Syzygy is rapidly growing, and we want you to join our world-class team today Syzygy Integration is currently looking for a Full Stack Developer with agile methodology experience to join our BEAGLE (Border Enforcement Applications for Government Leading-Edge Information Technology) Agile Solution Factory (ASF) Team supporting Customs and Border Protection (CBP) client located in Northern Virginia Join this passionate team of industry-leading individuals supporting the best practices in Agile So…

### Job 87 — job_id: `ext_01570`
- **Title**: Full Stack Developer, Senior
- **Company**: Technica Corporation
- **Tags**: (no tags)
- **Description**: About Technica : At Technica Corporation, our goal is to provide exceptional professional services and innovative technology solutions that meet or exceed our customer’s expectations. We specialize in a wide range of advanced information technology solutions from Systems Engineering to Cyber Security, and from Software Development to Product Solutions. From our locations across the DC Metro area, Hampton, Virginia, and Huntsville, Alabama, we provide technological subject matter expertise, prog…

### Job 88 — job_id: `ext_01951`
- **Title**: Mac/iOS Mobile App Developer - Remote
- **Company**: Versa Networks
- **Tags**: (no tags)
- **Description**: Versa Networks, Inc. is a leading vendor of next-generation Software Defined solutions and architectures, called SASE (Secure Access Service Edge). Versa is providing an end-to-end solution that both simplifies and secures the WAN/branch office network. The goal of Versa Networks is to provide unprecedented business advantages through a software-based approach that allows for unmatched agility, cost savings and flexibility. We have created a feature-rich, scalable yet simple to use software pla…

### Job 89 — job_id: `ext_01959`
- **Title**: Mac/iOS Mobile App Developer - Remote
- **Company**: Versa Networks
- **Tags**: (no tags)
- **Description**: Versa Networks, Inc. is a leading vendor of next-generation Software Defined solutions and architectures, called SASE (Secure Access Service Edge). Versa is providing an end-to-end solution that both simplifies and secures the WAN/branch office network. The goal of Versa Networks is to provide unprecedented business advantages through a software-based approach that allows for unmatched agility, cost savings and flexibility. We have created a feature-rich, scalable yet simple to use software pla…

### Job 90 — job_id: `ext_01945`
- **Title**: Mobile App Development Engineer, Android
- **Company**: TP-Link Systems Inc.
- **Tags**: (no tags)
- **Description**: About Us: Headquartered in the United States, TP-Link Systems Inc. is a global provider of reliable networking devices and smart home products, consistently ranked as the world’s top provider of Wi-Fi devices. The company is committed to delivering innovative products that enhance people’s lives through faster, more reliable connectivity. With a commitment to excellence, TP-Link serves customers in over 170 countries and continues to grow its global footprint. We believe technology changes the …

### Job 91 — job_id: `ext_00341`
- **Title**: Lead Software Engineer, iOS
- **Company**: DraftKings
- **Tags**: (no tags)
- **Description**: We’re defining what it means to build and deliver the most extraordinary sports and entertainment experiences. Our global team is trailblazing new markets, developing cutting-edge products, and shaping the future of responsible gaming. Here, “impossible” isn’t part of our vocabulary. You’ll face some of the toughest but most rewarding challenges of your career. They’re worth it. Channeling your inner grit will accelerate your growth, help us win as a team, and create unforgettable moments for o…

### Job 92 — job_id: `ext_07543`
- **Title**: DevOps Engineering Manager 1
- **Company**: Northrop Grumman
- **Tags**: (no tags)
- **Description**: RELOCATION ASSISTANCE: Relocation assistance may be available CLEARANCE TYPE: Secret TRAVEL: No Description At Northrop Grumman, our employees have incredible opportunities to work on revolutionary systems that impact people's lives around the world today, and for generations to come. Our pioneering and inventive spirit has enabled us to be at the forefront of many technological advancements in our nation's history - from the first flight across the Atlantic Ocean, to stealth bombers, to landin…

### Job 93 — job_id: `ext_08719`
- **Title**: Security Engineering Manager
- **Company**: Sidley Austin LLP
- **Tags**: (no tags)
- **Description**: This is a hands-on technical, team management position accountable for security administration inclusive of Firewalls, Cloud Access Security Broker (CASB), Data Loss Prevention (DLP), Logging/SIEM, Anti-Virus and Vulnerability Management technologies. The incumbent will also have responsibility for the supervision of all individuals assigned to their team. Deploy and support security operations tools, processes and procedures to ensure the continuous delivery of a secure computing environment a…

### Job 94 — job_id: `ext_08432`
- **Title**: Software Engineering Manager II, Google Cloud Business Platforms
- **Company**: Google
- **Tags**: (no tags)
- **Description**: Minimum qualifications: Bachelor’s degree, or equivalent practical experience. 8 years of experience with software development in one or more programming languages (e.g., Python, C, C++, Java, JavaScript). 3 years of experience in a technical leadership role; overseeing strategic projects, with 2 years of experience in a people management, supervision/team leadership role. Preferred qualifications: Master's degree or PhD in Computer Science or related technical field. 3 years of experience work…

### Job 95 — job_id: `ext_01252`
- **Title**: Software Engineering Manager
- **Company**: Emerald Resource Group
- **Tags**: (no tags)
- **Description**: Software Engineer Manager Columbus Metropolitan Area, OH. Full-time / Direct Hire I'm seeking a highly-skilled Software Engineer Manager for a high-growth and innovative IT company in the Columbus Metropolitan Area, OH. ﻿ Main Duties and Responsibilities: Provide overall direction, oversight, and coaching for a team of entry-level to mid-level software engineers that work on basic to moderately complex tasks Accountable for decisions that influence teams' resources, budget, tactical operations,…

### Job 96 — job_id: `ext_09827`
- **Title**: Network Engineering Manager
- **Company**: Peraton
- **Tags**: (no tags)
- **Description**: Peraton is seeking a Network Engineering Manager to work at USSTRATCOM at Offutt Air Force Base, NE. What you will do: Requirements analysis Functional analysis and synthesis of USSTRATCOM’s Network Requirements. Responsible for being the Networking Subject Matter Expert and leading a team in all functions related to the Network Engineering Line of Service. Provides Subject Matter Expert (SME) level ongoing support, addresses availability issues, overcomes performance problems and provides over…

### Job 97 — job_id: `ext_02921`
- **Title**: Engineering Manager, Machine Learning and Robotics Applications and Services
- **Company**: Nvidia Usa
- **Tags**: (no tags)
- **Description**: We are looking for a Robotics Engineer Manager for Isaac Robotics Applications and Services for AI-enabled Robots. Physical AI is becoming more ubiquitous in real-world applications. Today, robots are expected to handle increasingly sophisticated tasks in a wide range of environments, from industrial facilities to public spaces. NVIDIA is a pioneer in revolutionizing AI & Robotics, and we are seeking an experienced and accomplished full stack robotics lead for our Isaac robotics applications an…

### Job 98 — job_id: `ext_09329`
- **Title**: Security Engineering Manager (SENIOR PUBLIC SERVICE ADMINISTRATOR, OPT 3)
- **Company**: State of Illinois
- **Tags**: (no tags)
- **Description**: ​Agency: Department of Innovation and Technology Class Title: SENIOR PUBLIC SERVICE ADMINISTR - 40070 Skill Option: Management Information System/Data Processing/Telecommunications Bilingual Option: None Posting Date: 10/29/2024 Closing Date/Time: 11/26/2024 Salary: Anticipated Starting Salary $10,000 -11,000 Monthly Job Type: Salaried Category: Full Time County: Sangamon Number of Vacancies: 1 Plan/BU: None A RESUME IS REQUIRED FOR THIS JOB POSTING Please attach a DETAILED Resume/Curriculum Vi…

### Job 99 — job_id: `ext_08418`
- **Title**: Software Engineering Manager II, Google Cloud Compute
- **Company**: Google
- **Tags**: (no tags)
- **Description**: info_outline X Note: By applying to this position you will have an opportunity to share your preferred working location from the following: Seattle, WA, USA; Kirkland, WA, USA . Minimum qualifications: Bachelor’s degree, or equivalent practical experience. 8 years of experience with software development in one or more programming languages (e.g., Python, C, C++, Java, JavaScript). 3 years of experience in a technical leadership role; overseeing projects, with 2 years of experience in a people m…

### Job 100 — job_id: `ext_02930`
- **Title**: AIML - Cloud Infra Engineering Manager, Machine Learning Platform & Infrastructure
- **Company**: Apple
- **Tags**: (no tags)
- **Description**: Do you want to lead a team that builds scalable, cutting-edge infrastructure powering Apple Intelligence? The AIML Search Infrastructure team is pioneering the next generation of search, AI, and machine learning. Our platform forms the core of Apple Intelligence, supporting critical products and services across Apple, including Music, App Store, TV, News, Spotlight, Safari, Siri, and many more exciting products in the pipeline. Each day, we process millions of user queries with exceptional perf…

### Job 101 — job_id: `ext_02869`
- **Title**: Director of Engineering, Machine Learning
- **Company**: Waymo
- **Tags**: (no tags)
- **Description**: Waymo is an autonomous driving technology company with the mission to be the most trusted driver. Since its start as the Google Self-Driving Car Project in 2009, Waymo has focused on building the Waymo Driver—The World's Most Experienced Driver™—to improve access to mobility while saving thousands of lives now lost to traffic crashes. The Waymo Driver powers Waymo One, a fully autonomous ride-hailing service, and can also be applied to a range of vehicle platforms and product use cases. The Way…

### Job 102 — job_id: `ext_10540`
- **Title**: Database Admin, Entry Level
- **Company**: Spathe Systems
- **Tags**: (no tags)
- **Description**: Spathe is currently searching for a Database Admin, Entry Level to join our team in the Fayetteville, NC area. Spathe Systems is a rapidly growing SOF led, 8(a) defense contractor headquartered in Tampa, FL with offices in Fayetteville, NC and strategic partner locations in Virginia Beach and Coronado. As a small business with a tight knit family feel, Spathe empowers its employees to solve problems and make decisions. Administer, test, and implement computer databases, applying knowledge of da…

### Job 103 — job_id: `ext_09131`
- **Title**: Staff Security Engineer - Data Discovery
- **Company**: CVS Health
- **Tags**: (no tags)
- **Description**: Bring your heart to CVS Health. Every one of us at CVS Health shares a single, clear purpose: Bringing our heart to every moment of your health. This purpose guides our commitment to deliver enhanced human-centric health care for a rapidly changing world. Anchored in our brand — with heart at its center — our purpose sends a personal message that how we deliver our services is just as important as what we deliver. Our Heart At Work Behaviors™ support this purpose. We want everyone who works at …

### Job 104 — job_id: `ext_00770`
- **Title**: Software Engineer
- **Company**: bcore
- **Tags**: (no tags)
- **Description**: Bridge Core provides high energy, unified teams; technology integration experience; and innovative approaches, to enable our clients’ mission. We enable our clients’ mission by integrating innovative technologies and implementing adoption processes that modernize the digital workplace. Our trusted, skilled, and diverse team members are making a lasting impact by building tailored, client focused solutions. Do you want to join a team that is building tailored technical solutions to modernize our…

### Job 105 — job_id: `ext_00644`
- **Title**: Software Engineer
- **Company**: 02 Caci-Federal
- **Tags**: (no tags)
- **Description**: Software Engineer Job Category: Engineering Time Type: Full time Minimum Clearance Required to Start: Secret Employee Type: Regular Percentage of Travel Required: Type of Travel: CACI seeks a talented Software Engineer to join our Software and Solutions Group , within the National Security and Innovative Solutions Sector. We enable national security missions through creation and delivery of innovative, technology-centric solutions that provide decision advantage to our customers. Our client …

### Job 106 — job_id: `ext_10758`
- **Title**: SAP Solution Architect
- **Company**: Ben E. Keith Company
- **Tags**: (no tags)
- **Description**: For more than a century, Ben E. Keith Company has been a leader in fine food and premium beverage distribution, and we strive to consistently exceed our customers’ expectations. Our Food Division is a complete broad line multi-state distributor, and our Beverage Division operates throughout the state of Texas as a proud distributor of Anheuser-Busch products, craft and import beer brands, spirits, and wine. We are dedicated to the growth and success of our business, our customers, and our emplo…

### Job 107 — job_id: `ext_00075`
- **Title**: Real-Time Software Engineer
- **Company**: Boeing
- **Tags**: (no tags)
- **Description**: The successful candidate will enjoy working in a fast paced, team-oriented environment, while working creatively in all phases of the software development life cycle Leads activities to develop, document and maintain architectures, requirements, algorithms, interfaces and designs for software systems Leads development of code and integration of complex software components into a fully functional software system Develops software verification plans, test procedures and test environments, executi…

### Job 108 — job_id: `ext_06473`
- **Title**: Lead Business Management Analyst (Multiple Openings)
- **Company**: DGN Technologies
- **Tags**: (no tags)
- **Description**: Job Title: Lead Business Management Analyst (Multiple Openings) Job Duties: Lead efforts to gather and analyze data to identify business needs and define requirements; Design and implement solutions to improve operational and cost efficiencies and minimize errors through quality control and SOPs; and Develop and update functional or operational manuals and customized reports in accordance with internal policy. Requirements: Bachelor's degree (or foreign equivalent degree) in Management Informat…

### Job 109 — job_id: `ext_06211`
- **Title**: Sr Business Planning Analyst
- **Company**: Atmos Energy Corporation
- **Tags**: (no tags)
- **Description**: THIS JOB DESCRIPTION DOES NOT ATTEMPT TO LIST ALL OF THE DUTIES THAT ARE OR MAY BE PERFORMED IN THIS POSITION Primary Duties 1. Researches, develops and maintains relevant business plan models and reporting systems, consistent with the Corporate strategy, and comprised of financial and business related information consistent with similar natural gas industry public companies. 2. Prepares comparative analysis based on Company statistics and industry norms for internal management purposes. 3. Dev…

### Job 110 — job_id: `ext_09177`
- **Title**: Senior Security Engineer - Penetration Testing
- **Company**: CVS Health
- **Tags**: (no tags)
- **Description**: Bring your heart to CVS Health. Every one of us at CVS Health shares a single, clear purpose: Bringing our heart to every moment of your health. This purpose guides our commitment to deliver enhanced human-centric health care for a rapidly changing world. Anchored in our brand — with heart at its center — our purpose sends a personal message that how we deliver our services is just as important as what we deliver. Our Heart At Work Behaviors™ support this purpose. We want everyone who works at …

### Job 111 — job_id: `ext_08830`
- **Title**: Cyber Security Engineer
- **Company**: Regions Bank
- **Tags**: (no tags)
- **Description**: Thank you for your interest in a career at Regions. At Regions, we believe associates deserve more than just a job. We believe in offering performance-driven individuals a place where they can build a career a place to expect more opportunities. If you are focused on results, dedicated to quality, strength and integrity, and possess the drive to succeed, then we are your employer of choice. Regions is dedicated to taking appropriate steps to safeguard and protect private and personally identif…

### Job 112 — job_id: `ext_00903`
- **Title**: Advanced Software Engineer - Industrial Software
- **Company**: Symbotic
- **Tags**: (no tags)
- **Description**: Who we are With its A.I.-powered robotic technology platform, Symbotic is changing the way consumer goods move through the supply chain. Intelligent software orchestrates advanced robots in a high-density, end-to-end system – reinventing warehouse automation for increased efficiency, speed and flexibility. What we need Symbotic is seeking an Advanced Software Engineer to join our Industrial Software Team within our Hardware R&D organization. Y ou will be responsible for the development and main…

### Job 113 — job_id: `ext_09209`
- **Title**: Senior Security Engineer - Service Delivery and Engineering
- **Company**: CVS Health
- **Tags**: (no tags)
- **Description**: Bring your heart to CVS Health. Every one of us at CVS Health shares a single, clear purpose: Bringing our heart to every moment of your health. This purpose guides our commitment to deliver enhanced human-centric health care for a rapidly changing world. Anchored in our brand — with heart at its center — our purpose sends a personal message that how we deliver our services is just as important as what we deliver. Our Heart At Work Behaviors™ support this purpose. We want everyone who works at …

### Job 114 — job_id: `ext_00531`
- **Title**: Senior Software Engineer
- **Company**: Lynx Software Technologies
- **Tags**: (no tags)
- **Description**: Thompson Software Solutions is seeking a senior-level Embedded Software Engineer who is ready to work with a talented team to provide innovative solutions for tomorrow’s problems. This position requires a software engineer to use a wide application of technical principles, theories, and concepts in the software field to develop, integrate, and test software products. The successful candidate will be a member of a high-performing multi-site team and must be self-motivated with a strong work ethi…

### Job 115 — job_id: `ext_08650`
- **Title**: Security Engineer
- **Company**: Foursquare
- **Tags**: (no tags)
- **Description**: Foursquare is the leading independent location technology and data cloud platform dedicated to building meaningful bridges between digital spaces and physical places. Our proprietary technology unlocks the most accurate, trustworthy location data in the world, empowering businesses to answer key questions, uncover hidden insights, improve customer experiences, and achieve better business outcomes. A pioneer of the geo-location space, Foursquare’s location tech stack is being utilized by the wor…

### Job 116 — job_id: `ext_00433`
- **Title**: Director of Software Engineering
- **Company**: Path Construction
- **Tags**: (no tags)
- **Description**: Path Construction is growing and looking for a Director of Software Engineering We are a mid-size, growing general contracting firm located in Arlington Heights, IL. We are looking for the right person to head the development in execution of a software system. We are in the process of developing a complex and comprehensive software program tied to the construction industry. It will significantly change the way construction will be carried out in the future. The patents for this process are alre…

### Job 117 — job_id: `ext_00172`
- **Title**: Real-Time Software Engineer
- **Company**: Boeing
- **Tags**: (no tags)
- **Description**: The successful candidate will enjoy working in a fast paced, team-oriented environment, while working creatively in all phases of the software development life cycle Leads activities to develop, document and maintain architectures, requirements, algorithms, interfaces and designs for software systems Leads development of code and integration of complex software components into a fully functional software system Develops software verification plans, test procedures and test environments, executi…

### Job 118 — job_id: `ext_00199`
- **Title**: Real-Time Software Engineer
- **Company**: Boeing
- **Tags**: (no tags)
- **Description**: The successful candidate will enjoy working in a fast paced, team-oriented environment, while working creatively in all phases of the software development life cycle Leads activities to develop, document and maintain architectures, requirements, algorithms, interfaces and designs for software systems Leads development of code and integration of complex software components into a fully functional software system Develops software verification plans, test procedures and test environments, executi…

### Job 119 — job_id: `ext_00150`
- **Title**: Real-Time Software Engineer
- **Company**: Boeing
- **Tags**: (no tags)
- **Description**: The successful candidate will enjoy working in a fast paced, team-oriented environment, while working creatively in all phases of the software development life cycle Leads activities to develop, document and maintain architectures, requirements, algorithms, interfaces and designs for software systems Leads development of code and integration of complex software components into a fully functional software system Develops software verification plans, test procedures and test environments, executi…

### Job 120 — job_id: `ext_00021`
- **Title**: Real-Time Software Engineer
- **Company**: Boeing
- **Tags**: (no tags)
- **Description**: The successful candidate will enjoy working in a fast paced, team-oriented environment, while working creatively in all phases of the software development life cycle Leads activities to develop, document and maintain architectures, requirements, algorithms, interfaces and designs for software systems Leads development of code and integration of complex software components into a fully functional software system Develops software verification plans, test procedures and test environments, executi…
