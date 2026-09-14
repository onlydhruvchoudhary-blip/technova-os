# TECHNOVA OS

> **The digital operating system of a technology club.**
> Learning, projects, competitions, events, contribution and achievement — connected into one ecosystem.

**Flow:** Discover → Learn → Practice → Collaborate → Build → Compete → Showcase → Earn → Lead

TECHNOVA OS is not a club website and not a generic school ERP. Its defining feature is
**interconnection**: every meaningful action emits a domain event that ripples across the whole
system. Finish a course → a skill levels up → the skill unlocks harder challenges → solving them
earns points → points move your leaderboard rank → milestones grant achievements and verifiable
certificates → your profile becomes a real technology portfolio.

---

## ✨ Feature highlights

| Area | What it does |
|---|---|
| **Ecosystem Engine** | Event bus + append-only, idempotent points ledger wiring every module together. |
| **Academy** | Courses → lessons/quizzes with a progression gate; completion grows real skills. |
| **Skill Tree** | Beginner → Intermediate → Advanced → Mentor, earned via evidence, not clicks. |
| **Challenges** | Coding problems judged safely in an isolated sandbox vs hidden tests; weekly challenges. |
| **Project Incubator** | Idea → Showcase pipeline, workspace with a Kanban board, explainable team matching. |
| **Mentor system** | Reviews, scores and feedback that become part of a project's history. |
| **Competitions** | Registration, rubric-based judging, ranking → winner certificates + points. |
| **Events + QR attendance** | Signed, time-limited QR tokens (90s rotation) — no forever-valid codes. |
| **Leaderboard** | Rewards real contribution across categories; daily caps stop farming. |
| **Achievements & Certificates** | Evidence-linked; certificates are cryptographically verifiable & revocable. |
| **Admin** | RBAC member/role management, analytics that drive decisions, audit log, announcements. |
| **Command Center** | A public "live TECHNOVA screen" for the lab/projector. |
| **Global search, notifications, resources, showcase, dark/light, mobile** | All included. |

## 🏗️ Architecture

```
React + TypeScript (Vite)  ──/api──▶  FastAPI  ──▶  Ecosystem Engine (event bus)
                                         │                │
                                         │                ├─ Points ledger (append-only, idempotent, capped)
                                         ▼                ├─ Skill XP / tiers
                                    SQLAlchemy            ├─ Achievements (evidence-linked)
                                  SQLite / Postgres       ├─ Certificates (HMAC-signed, verifiable)
                                                          └─ Notifications
```

See [`ARCHITECTURE.md`](./ARCHITECTURE.md) for the full design and [`docs/`](./docs) for details.

## 🚀 Quick start (development)

**Backend** (Python 3.11+):
```bash
cd backend
pip install -r requirements.txt
python -m app.seed --reset          # create + seed the SQLite dev DB
uvicorn app.main:app --reload --port 8000
```

**Frontend** (Node 18+):
```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173  (proxies /api → :8000)
```

Open http://localhost:5173. Demo accounts (password `password123`):
`admin@technova.club` (Super Admin) · `head@technova.club` · `mentor@technova.club` · `isha@technova.club`.
Live club screen: http://localhost:5173/command-center.

## 🧪 Tests

```bash
cd backend && pytest -q          # 33 tests: auth, RBAC matrix, engine/points, judging,
                                 # competitions, certificates, QR expiry, anti-farming, full E2E journey
```

## 🐳 Production deployment (Docker + Postgres)

```bash
cp .env.example .env             # set SECRET_KEY, QR_SECRET, DB_PASSWORD (use: openssl rand -hex 32)
cd frontend && npm ci && npm run build && cp -r dist ../backend/frontend_dist && cd ..
docker compose up --build        # API on :8000 serves the SPA + API; Postgres + nightly backups
```

The API serves the built SPA (single origin, no CORS headaches). See [`docs/DEPLOYMENT.md`](./docs/DEPLOYMENT.md).

## 🔒 Security & fairness

- JWT auth, bcrypt password hashing, 7-tier RBAC with per-endpoint checks.
- Append-only **idempotent** points ledger + **daily category caps** → no point farming / double counting.
- Coding submissions run in an **isolated subprocess** with a static guard, time & memory limits.
- **Signed, time-limited** QR attendance tokens; certificates HMAC-signed, publicly verifiable, revocable.
- Audit log on every privileged action; rate limiting on auth & submissions.

## 📁 Project structure

```
technova-os/
├── ARCHITECTURE.md          # full architecture & plan
├── README.md
├── CRITIC_HISTORY.md        # independent-critic review log + scores
├── docker-compose.yml       # Postgres + API + nightly backups
├── .env.example
├── docs/                    # DEPLOYMENT, API, SECURITY, DATA_MODEL, ROADMAP
├── backend/
│   ├── app/
│   │   ├── main.py          # FastAPI app (also serves built SPA in prod)
│   │   ├── engine.py        # ⭐ the ecosystem engine (event bus + reactors)
│   │   ├── models.py        # relational data model
│   │   ├── security.py      # auth, RBAC, signed QR & certificates
│   │   ├── judge.py         # safe isolated code judge
│   │   ├── seed.py          # rich demo dataset
│   │   └── routers/         # auth, profile, academy, challenges, projects,
│   │                          events, competitions, general, admin
│   ├── tests/               # pytest suite
│   ├── requirements.txt
│   └── Dockerfile
└── frontend/
    └── src/
        ├── App.tsx, Layout.tsx, api.ts, store.tsx, ui.tsx, styles.css
        └── pages/           # Dashboard, Academy, Skills, Challenges, Projects,
                               Events, Competitions, Leaderboard, Profile, Admin,
                               CommandCenter, Verify, Showcase, Resources, Members
```

## 📜 License

Open-source ready (add your preferred license, e.g. MIT).
