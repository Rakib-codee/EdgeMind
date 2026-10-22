Rakib, আমরা EdgeMind — Intelligent Edge–Cloud Workload Orchestrator প্রজেক্টটি A–Z এমনভাবে পরিকল্পনা করব, যেন এটি শুধু একটি সাধারণ software project না হয়; বরং তোমার Master’s application, research portfolio এবং ভবিষ্যৎ publication-এর জন্যও কাজে লাগে।

আমাদের মূল লক্ষ্য হবে এমন একটি system তৈরি করা, যেটি কোনো computational task Local Device, Edge Server, নাকি Cloud Server-এ চালানো উচিত—তা network latency, compute requirement, server load এবং task-এর latency limit বিবেচনা করে নির্ধারণ করবে। এরপর আমরা বিভিন্ন scheduling algorithm-এর performance পরীক্ষা করব।

সবচেয়ে গুরুত্বপূর্ণ নিয়মটি তোমার পরিকল্পনায় স্থায়ীভাবে থাকবে:

## Mandatory Git Rule

প্রতিটি file edit সফলভাবে সম্পন্ন ও যাচাই করার পরই Git commit এবং Git push করতে হবে।

প্রতিটি successful edit → relevant test/check → Git commit → Git push → push সফল হয়েছে কি না যাচাই। একাধিক ফাইলের edit একসঙ্গে করলে, সংশ্লিষ্ট কাজ ও tests সফল হওয়ার পর সেই batch-এর জন্য commit/push করা যাবে।

এখানে একটি পার্থক্য মনে রাখবে: `git commit` হলো local repository-তে পরিবর্তন সংরক্ষণ করা; `git push` হলো remote GitHub repository-তে পাঠানো। Push ব্যর্থ হলে সেটি ঠিক না করা পর্যন্ত কাজটিকে সম্পূর্ণ ধরা হবে না। API key, password, `.env`, virtual environment বা অন্য secret কখনো GitHub-এ push করা যাবে না।

# EdgeMind: Full Project Roadmap (A–Z)

[What is Edge Computing? ☁️ Definition, Technology, Examples](https://images.openai.com/static-rsc-4/5l8xSmYn5c7aRd1eVuBmfYlBrN7pPjw-grSvuPRQJmf3-9q-gYNcPuHqJasi2LuP8bf794ZjdTSVoiOaCFOl-HLvkez3O1AYae4vQX4_alwWdB_pXlF0-nljXcy6ZtGgmtgs9g9Y4_s9vdseDe-pBGvGdAW16vIdCwMQTLsrkOA?purpose=inline)

[wallarm.com](https://www.wallarm.com/what/what-is-edge-computing?utm_source=chatgpt.com)

# Project mission

একটি intelligent scheduler তৈরি করা, যেটি task-এর বৈশিষ্ট্য এবং পরিবর্তনশীল computing/network conditions অনুযায়ী উপযুক্ত execution target নির্বাচন করবে। এরপর baseline scheduler-এর সঙ্গে উন্নত scheduler তুলনা করে reproducible experiment-এর মাধ্যমে প্রমাণ করতে হবে কোন পদ্ধতি কতটা কার্যকর।

## 1. আমরা ঠিক কী তৈরি করব?

প্রজেক্টের নাম: EdgeMind

Research title: An Intelligent Edge–Cloud Workload Orchestrator for Latency-Aware and Resource-Efficient Task Offloading

প্রাথমিক research question:

“Network latency এবং server load পরিবর্তিত হলে, adaptive task scheduling কি একটি সাধারণ static scheduling policy-এর তুলনায় task completion latency কমাতে পারে?”

এটি আমাদের hypothesis—এখনো প্রমাণিত ফলাফল নয়।

### System architecture

Task Generator / Client

Task তৈরি করবে: workload, compute units, latency limit

EdgeMind API

FastAPI · Task validation · Node-state collection

Scheduling Engine

Local

Edge

Cloud

Feasibility check · Scheduling policy · Target selection

Execution, Monitoring & Evaluation

Task results · Latency · Throughput · Resource use · Experiment logs

প্রথম সংস্করণে Local, Edge এবং Cloud হবে simulated execution nodes। পরবর্তী পর্যায়ে Docker containers ব্যবহার করে আলাদা worker service চালাব। তাই শুরুতেই এগুলোকে real-world distributed infrastructure হিসেবে দাবি করব না।

## 2. A–Z development phases

প্রতিটি phase শেষ হলে তার deliverable এবং acceptance criteria যাচাই করে পরবর্তী phase-এ যাব।

## 00

Foundation ও GitHub setup

Partially completed

Python environment, Git/Docker checks, virtual environment এবং project directory তৈরি করা হয়েছে। Dependencies install, API execution ও tests সফল হয়েছে কি না এখনো নিশ্চিত নয়।

Deliverable: কার্যকর development environment এবং GitHub remote repository।

## 01

Baseline API

FastAPI দিয়ে `/health`, `/schedule` এবং interactive `/docs` চালানো। Request validation, feasible node নির্বাচন এবং error handling যাচাই করা।

Deliverable: প্রথম কার্যকর API ও automated tests।

## 02

Scheduling engine আলাদা করা

API code থেকে scheduling logic আলাদা করে `scheduler` module তৈরি করব। Baseline policy, node profile এবং latency estimation পৃথক থাকবে।

Deliverable: testable, modular scheduler।

## 03

Task ও node models

Task size, compute demand, latency budget, node capacity, network delay, queue length এবং server load-এর সুস্পষ্ট data model নির্ধারণ করব।

Deliverable: documented system assumptions এবং consistent data schemas।

## 04

Task execution simulation

Worker simulation যোগ করব, যাতে scheduling decision-এর পর task completion, failure এবং execution duration পরীক্ষা করা যায়।

Deliverable: end-to-end task lifecycle।

## 05

Dynamic network ও server load

পরিবর্তনশীল network latency, CPU availability, queue length এবং node capacity-এর simulation যোগ করব।

Deliverable: dynamic environment-এ scheduler test করার ব্যবস্থা।

## 06

Adaptive scheduling algorithm

Dynamic state অনুযায়ী node নির্বাচন করার policy তৈরি করব। প্রথমে interpretable heuristic বা weighted cost function; প্রয়োজন হলে পরে learning-based policy বিবেচনা করব।

Deliverable: baseline-এর সঙ্গে তুলনা করার মতো adaptive scheduler।

## 07

Dockerized services

API এবং workers-কে Docker Compose দিয়ে চালানো; service discovery, configuration এবং inter-service communication যাচাই করা।

Deliverable: reproducible multi-service development environment।

## 08

Benchmarking framework

বিভিন্ন workload size, network conditions, server load এবং concurrency-তে baseline ও adaptive policy চালাব।

Deliverable: পুনরায় চালানো যায় এমন experiment scripts ও structured CSV results।

## 09

Statistical analysis ও visualization

Mean, median, p95 latency, throughput, deadline-miss rate এবং resource utilization বিশ্লেষণ করব। Repeated runs ও uncertainty-ও বিবেচনায় থাকবে।

Deliverable: plots, summary tables এবং evidence-based findings।

## 10

Monitoring ও dashboard

Prometheus/Grafana বা lightweight dashboard দিয়ে task throughput, queue length এবং latency trends দেখা। Core system স্থিতিশীল হওয়ার পরই এটি করব।

Deliverable: দৃশ্যমান runtime metrics।

## 11

Research evaluation

Baseline ও adaptive scheduler একই conditions-এ তুলনা, ablation tests এবং sensitivity analysis। কোন পরিস্থিতিতে উন্নতি হয় বা হয় না, তা নথিবদ্ধ করব।

Deliverable: defensible experimental results।

## 12

Research report ও portfolio release

Literature review, methodology, system design, experiment results, limitations, README, architecture diagram এবং reproduction instructions প্রস্তুত করব।

Deliverable: polished GitHub repository এবং Master’s supervisor-কে দেখানোর মতো research artifact।

## 3. প্রতিটি phase-এ কোন প্রযুক্তি ব্যবহার করব?

| অংশ                   | প্রযুক্তি                  | কেন ব্যবহার করব                         |
| --------------------- | -------------------------- | --------------------------------------- |
| Programming           | Python                     | Scheduler ও experiments দ্রুত তৈরি করতে |
| API                   | FastAPI, Pydantic          | Task request ও scheduling interface     |
| Testing               | pytest, HTTPX              | Logic ও API যাচাই                       |
| Distributed services  | Docker, Docker Compose     | আলাদা worker ও API service চালাতে       |
| Queue, পরবর্তী পর্যায় | Redis, প্রয়োজন হলে         | Task queue ও coordination               |
| Metrics               | Prometheus                 | Runtime measurements সংগ্রহ             |
| Dashboard             | Grafana                    | Metrics visualization                   |
| Experiments           | Python, pandas, matplotlib | Results analysis ও plots                |
| Version control       | Git, GitHub                | প্রতিটি পরিবর্তন track ও publish করতে   |

M2 MacBook-এ প্রথমে local simulation এবং Docker Compose যথেষ্ট। Kubernetes, paid cloud infrastructure বা complex machine-learning model দিয়ে শুরু করব না। এগুলো প্রয়োজন প্রমাণিত হলে পরে যোগ হবে।

## 4. Final project folder structure

প্রজেক্ট বড় হওয়ার সঙ্গে সঙ্গে directory এভাবে সাজাব। সব ফাইল একসঙ্গে এখনই তৈরি করার দরকার নেই।

```
EdgeMind/
├── app/
│   ├── main.py
│   ├── api/
│   ├── models/
│   ├── scheduler/
│   │   ├── baseline.py
│   │   ├── adaptive.py
│   │   └── cost_model.py
│   ├── workers/
│   ├── monitoring/
│   └── config.py
├── tests/
│   ├── test_main.py
│   ├── test_scheduler.py
│   └── test_workers.py
├── benchmarks/
│   ├── workloads/
│   ├── run_benchmark.py
│   └── analyze_results.py
├── experiments/
│   ├── configs/
│   └── README.md
├── results/
│   ├── raw/
│   ├── processed/
│   └── figures/
├── docs/
│   ├── architecture.md
│   ├── methodology.md
│   └── experiment_protocol.md
├── requirements.txt
├── Dockerfile
├── compose.yaml
├── .gitignore
└── README.md
```

`results/`-এ generated files-এর সবগুলো GitHub-এ দিতে হবে না। ছোট, প্রয়োজনীয় sample results ও figures রাখা যেতে পারে; বড় raw outputs সাধারণত local-এ থাকবে, যদি না সেগুলো version করা গবেষণার জন্য প্রয়োজন হয়।

## 5. Research-এর জন্য কোন metrics মাপব?

আমরা শুধু API কাজ করছে কি না, সেটি দিয়ে প্রজেক্টের সাফল্য বিচার করব না। Scheduler সত্যিই ভালো কি না, তা measurable evidence দিয়ে যাচাই করতে হবে।

Task completion latency

Task submit করার সময় থেকে সম্পন্ন হওয়ার সময় পর্যন্ত elapsed time। Mean, median এবং p95 latency মাপব।

Throughput

প্রতি সেকেন্ড বা নির্দিষ্ট সময়ের মধ্যে সম্পন্ন হওয়া task-এর সংখ্যা।

Deadline-miss rate

যেসব task তাদের নির্ধারিত latency budget অতিক্রম করে, তাদের অনুপাত।

Resource utilization

প্রতিটি node-এর CPU/resource use, queue length এবং workload distribution।

Failure ও robustness

Node unavailable, overloaded বা latency spike হলে scheduler কীভাবে প্রতিক্রিয়া জানায়।

প্রাথমিক comparison হবে তিনটি policy-এর মধ্যে:

- Baseline policy: বর্তমান rule-based scheduler।
- Static policy: পূর্বনির্ধারিত নিয়মে node নির্বাচন।
- Adaptive policy: বর্তমান node state ও network conditions অনুযায়ী সিদ্ধান্ত।

প্রতিটি policy-কে একই workload, একই initial conditions এবং যথাসম্ভব একই random seeds-এ পরীক্ষা করতে হবে। এতে comparison আরও ন্যায্য হবে। Adaptive policy সব metric-এ জিতবে—এমন পূর্বধারণা রাখব না।

## 6. Git ও GitHub: বাধ্যতামূলক workflow

এই নিয়মটি পুরো development-এর অংশ, আলাদা কোনো optional task নয়।

### প্রতিটি successful file edit-এর পর

1. ফাইলের পরিবর্তন save করো।
2. প্রাসঙ্গিক test, syntax check বা lint check চালাও।
3. পরিবর্তনটি ঠিক আছে কি না `git diff` দিয়ে দেখো।
4. শুধু intended files stage করো এবং descriptive commit তৈরি করো।
5. GitHub remote-এ push করো।
6. Push সফল হয়েছে কি না যাচাই করো; ব্যর্থ হলে সমস্যাটি ঠিক করে আবার push করো।

উদাহরণ: `app/main.py` edit ও test সফল হলে—

```
git status
git diff -- app/main.py
pytest -q

git add app/main.py
git commit -m "feat: implement baseline scheduling API"
git push
```

যদি নতুন test file-ও পরিবর্তন করো, সেই intended test file-টিও stage করবে। সব পরিবর্তন সফলভাবে যাচাই হওয়ার পর সংশ্লিষ্ট batch commit/push করবে। কোনো test fail করলে, সেই পরিবর্তনকে সফলভাবে যাচাইকৃত বলা যাবে না।

প্রথমবার GitHub remote configure করতে হবে। তোমার GitHub-এ `EdgeMind` repository তৈরি করার পর তার প্রকৃত remote URL ব্যবহার করবে:

```
git remote add origin YOUR_GITHUB_REPOSITORY_URL
git branch -M main
git push -u origin main
```

এখানে `YOUR_GITHUB_REPOSITORY_URL`-এর জায়গায় তোমার GitHub repository-র আসল URL বসাতে হবে। Remote আগে থেকেই configured থাকলে `git remote add origin` আবার চালাবে না।

`.gitignore`-এ অন্তত এগুলো রাখবে:

```
.venv/
__pycache__/
.pytest_cache/
.env
.DS_Store
```

আরেকটি গুরুত্বপূর্ণ নিয়ম: GitHub-এ push করা আর code-এর backup আছে—এই দুটো ঠিক হলেও, এতে tests পাস করেছে বা system production-ready হয়েছে, তা প্রমাণিত হয় না।

## 7. Documentation ও research deliverables

শেষ পর্যায়ে শুধু source code থাকলে চলবে না। Master’s supervisor যেন project-টি বুঝতে ও reproduce করতে পারেন, সেটিও নিশ্চিত করতে হবে।

README-তে থাকবে:

- Project overview ও research question
- Architecture diagram
- Setup এবং run instructions
- API endpoints ও sample requests
- Scheduling algorithm-এর ব্যাখ্যা
- Test চালানোর পদ্ধতি
- Benchmark configuration ও results
- Limitations এবং future work

Research documentation-এ থাকবে:

- সম্পর্কিত কাজের literature review
- System model ও assumptions
- Scheduling objective ও constraints
- Experimental protocol
- Baseline comparison
- Repeated-run results ও statistical analysis
- Threats to validity এবং limitations

কোনো performance improvement বা publication claim করার আগে actual experiments করতে হবে। Simulated latency-কে measured physical network latency হিসেবে উপস্থাপন করা যাবে না।

## 8. Timeline ও completion criteria

সময়সীমা তোমার course load ও debugging-এর ওপর নির্ভর করবে। প্রাথমিক planning estimate হিসেবে:

| সময়        | লক্ষ্য                                              |
| ---------- | --------------------------------------------------- |
| সপ্তাহ ১   | Environment, GitHub, API ও tests                    |
| সপ্তাহ ২   | Modular scheduler ও task/node models                |
| সপ্তাহ ৩   | Execution simulation ও dynamic conditions           |
| সপ্তাহ ৪   | Adaptive policy ও Docker Compose                    |
| সপ্তাহ ৫   | Benchmark framework ও initial experiments           |
| সপ্তাহ ৬   | Analysis, plots ও robustness tests                  |
| সপ্তাহ ৭–৮ | Documentation, final evaluation ও portfolio release |

এটি একটি অনুমান, নিশ্চিত deadline নয়। কোনো phase-এর tests বা acceptance criteria পূরণ না হলে শুধু timeline মেলানোর জন্য সামনে এগোব না।

Final completion checklist:

### Project completion tracker

9/9

- [x] API এবং scheduler automated tests পাস করে (30 tests)
- [x] Local, edge ও cloud target selection যাচাই করা হয়েছে
- [x] Dynamic network ও server-load scenarios পরীক্ষা করা হয়েছে
- [x] Baseline এবং adaptive policy-এর reproducible benchmarks আছে
- [x] Latency, throughput, deadline misses ও resource metrics বিশ্লেষণ করা হয়েছে
- [x] Docker Compose দিয়ে system চালানো যায় (API + Prometheus + Grafana)
- [x] README ও experiment reproduction instructions সম্পূর্ণ
- [x] GitHub repository-তে intended changes commit ও push করা হয়েছে
- [x] Research claims actual results ও limitations-এর সঙ্গে সামঞ্জস্যপূর্ণ (docs/evaluation.md)

## 9. এখন আমাদের পরবর্তী কাজ

আমাদের বর্তমান project context অনুযায়ী, directory structure ও virtual environment তৈরি করা হয়েছে; কিন্তু dependencies installation, API execution এবং `pytest` সফল হয়েছে কি না নিশ্চিত নই। তাই এখনই adaptive scheduler বা Docker services তৈরি শুরু করব না।

প্রথমে Mac-এর Terminal-এ চালাও:

```
cd ~/Developer/EdgeMind
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install fastapi "uvicorn[standard]" pytest httpx
python -m pip freeze > requirements.txt
```

`requirements.txt` পরিবর্তনটি সফলভাবে তৈরি হলে Git workflow অনুসরণ করে commit/push করবে। এরপর:

```
uvicorn app.main:app --reload
```

Browser-এ `http://127.0.0.1:8000/docs` এবং `http://127.0.0.1:8000/health` পরীক্ষা করো। Server বন্ধ করতে `Ctrl+C` চাপবে, তারপর চালাও:

```
pytest -q
```

এই ধাপের সফল ফলাফল পাওয়ার পরই Phase 02-এ যাব। Error হলে সম্পূর্ণ error message পাঠাবে; অনুমান করে পরবর্তী phase-এ এগোব না। এভাবেই আমরা EdgeMind-কে ধাপে ধাপে, পরীক্ষাযোগ্য এবং research-ready project হিসেবে তৈরি করব।