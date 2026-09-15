"""Seed TECHNOVA OS with a rich, realistic dataset so the ecosystem is demonstrable end-to-end."""
from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.orm import Session

from . import engine as eng
from .database import Base, SessionLocal, engine
from .models import (
    Achievement,
    Announcement,
    Challenge,
    Competition,
    CompetitionEntry,
    Course,
    Event,
    Lesson,
    Project,
    ProjectMember,
    ProjectState,
    Resource,
    Role,
    RubricScore,
    Skill,
    User,
)
from .security import hash_password

SKILLS = [
    ("python", "Python", "Programming", "🐍"),
    ("csharp", "C#", "Programming", "🎯"),
    ("java", "Java", "Programming", "☕"),
    ("algorithms", "Algorithms", "Programming", "🧮"),
    ("html", "HTML", "Web Development", "📄"),
    ("css", "CSS", "Web Development", "🎨"),
    ("javascript", "JavaScript", "Web Development", "⚡"),
    ("apis", "APIs", "Web Development", "🔌"),
    ("ai", "AI Fundamentals", "AI / Data", "🤖"),
    ("data", "Data Analysis", "AI / Data", "📊"),
    ("ml", "Machine Learning", "AI / Data", "🧠"),
    ("git", "Git", "Other", "🌿"),
    ("linux", "Linux", "Other", "🐧"),
    ("electronics", "Electronics", "Other", "🔧"),
]

# key, name, description, icon, points, rarity
ACHIEVEMENTS = [
    # --- Learning ---
    ("first_lesson", "First Steps", "Completed your first lesson", "🎓", 10, "Common"),
    ("course_complete", "Course Graduate", "Completed a full course", "📜", 30, "Uncommon"),
    ("scholar", "Scholar", "Completed 5 courses", "📚", 80, "Rare"),
    ("polymath", "Polymath", "Completed 10 courses", "🧑‍🏫", 150, "Epic"),
    # --- Challenges ---
    ("first_challenge", "Problem Solver", "Solved your first coding challenge", "💡", 20, "Common"),
    ("ten_challenges", "Challenge Crusher", "Solved 10 coding challenges", "🔥", 60, "Uncommon"),
    ("fifty_challenges", "Code Warrior", "Solved 50 coding challenges", "⚔️", 200, "Rare"),
    ("hundred_challenges", "Century Coder", "Solved 100 coding challenges", "💯", 400, "Epic"),
    ("flawless", "Flawless Victory", "Passed a challenge on the first submission", "🎯", 30, "Uncommon"),
    ("speed_demon", "Speed Demon", "Solved a challenge in under 2 minutes", "⚡", 40, "Rare"),
    ("night_owl", "Night Owl", "Solved a challenge after midnight", "🦉", 25, "Uncommon"),
    ("polyglot", "Polyglot", "Solved challenges in 3+ languages", "🗣️", 90, "Rare"),
    # --- Streaks & consistency ---
    ("streak_7", "On Fire", "Maintained a 7-day activity streak", "🔥", 70, "Uncommon"),
    ("streak_30", "Unstoppable", "Maintained a 30-day activity streak", "🌋", 250, "Epic"),
    ("early_bird", "Early Bird", "Checked in before 8 AM", "🌅", 20, "Common"),
    # --- Projects ---
    ("first_project", "Builder", "Started your first project", "🛠️", 15, "Common"),
    ("project_complete", "Shipped It", "Completed a project", "🚀", 50, "Uncommon"),
    ("open_sourcerer", "Open Sourcerer", "Published a project to the showcase", "🌟", 70, "Rare"),
    ("team_player", "Team Player", "Joined a project team", "🧩", 25, "Common"),
    # --- Skills ---
    ("skill_advanced", "Specialist", "Reached Advanced in a skill", "⭐", 40, "Uncommon"),
    ("skill_mentor", "Grandmaster", "Reached Mentor in a skill", "🎖️", 120, "Epic"),
    ("renaissance", "Renaissance Dev", "Reached Mentor in 5+ skills", "🏛️", 500, "Legendary"),
    ("full_stack", "Full Stack", "Advanced in both frontend and backend skills", "🥞", 100, "Rare"),
    # --- Community ---
    ("team_mentor", "Team Mentor", "Helped or taught a fellow member", "🤝", 25, "Common"),
    ("workshop_leader", "Workshop Leader", "Led a workshop", "🎤", 40, "Uncommon"),
    ("event_regular", "Regular", "Attended 5 events", "📅", 60, "Uncommon"),
    ("connector", "Connector", "Matched with a project team", "🔗", 30, "Common"),
    # --- Competition & prestige ---
    ("competition_winner", "Champion", "Won a competition", "🏆", 100, "Epic"),
    ("podium", "On the Podium", "Placed top 3 in a competition", "🥉", 60, "Rare"),
    ("leaderboard_top", "Apex", "Reached #1 on the leaderboard", "👑", 300, "Legendary"),
    ("certified", "Certified", "Earned a verifiable certificate", "🪪", 50, "Uncommon"),
    ("point_master", "Point Master", "Accumulated 10,000 lifetime points", "💎", 200, "Epic"),
    ("legend", "TECHNOVA Legend", "Unlocked every achievement", "🌌", 1000, "Legendary"),
]

RESOURCES = [
    ("Python Official Tutorial", "https://docs.python.org/3/tutorial/", "Documentation", "python", "Beginner", "Language"),
    ("MDN Web Docs", "https://developer.mozilla.org/", "Documentation", "javascript", "Beginner", "Reference"),
    ("Git Cheat Sheet", "https://education.github.com/git-cheat-sheet-education.pdf", "Cheat Sheet", "git", "Beginner", "Reference"),
    ("Big-O Cheat Sheet", "https://www.bigocheatsheet.com/", "Cheat Sheet", "algorithms", "Intermediate", "Complexity"),
    ("Intro to Machine Learning", "https://developers.google.com/machine-learning/crash-course", "Course", "ml", "Intermediate", "ML"),
    ("Linux Command Line Basics", "https://ubuntu.com/tutorials/command-line-for-beginners", "Tutorial", "linux", "Beginner", "Shell"),
    ("JavaScript.info", "https://javascript.info/", "Tutorial", "javascript", "Intermediate", "Language"),
    ("React Official Docs", "https://react.dev/learn", "Documentation", "javascript", "Intermediate", "Framework"),
    ("CSS Tricks: Flexbox Guide", "https://css-tricks.com/snippets/css/a-guide-to-flexbox/", "Cheat Sheet", "css", "Beginner", "Layout"),
    ("NeetCode 150", "https://neetcode.io/practice", "Practice", "algorithms", "Intermediate", "Interview"),
    ("Fast.ai Practical Deep Learning", "https://course.fast.ai/", "Course", "ml", "Advanced", "Deep Learning"),
    ("Pro Git Book", "https://git-scm.com/book/en/v2", "Book", "git", "Intermediate", "Reference"),
    ("Arduino Project Hub", "https://projecthub.arduino.cc/", "Reference", "electronics", "Beginner", "Hardware"),
    ("The Missing Semester (MIT)", "https://missing.csail.mit.edu/", "Course", "linux", "Intermediate", "Tooling"),
    ("REST API Design Guide", "https://restfulapi.net/", "Documentation", "apis", "Intermediate", "Backend"),
    ("Kaggle Learn", "https://www.kaggle.com/learn", "Course", "data", "Beginner", "Data"),
]


def _quiz(items):
    return {"items": items}


def seed(reset: bool = False):
    if reset:
        Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()
    try:
        if db.execute(select(User.id)).first():
            print("Already seeded.")
            return

        # ---- skills
        skill_by_key = {}
        for key, name, cat, icon in SKILLS:
            s = Skill(key=key, name=name, category=cat, icon=icon)
            db.add(s)
            skill_by_key[key] = s
        db.flush()

        # ---- achievements
        for key, name, desc, icon, pts, rarity in ACHIEVEMENTS:
            db.add(Achievement(key=key, name=name, description=desc, icon=icon,
                               points=pts, rarity=rarity))

        # ---- resources
        for title, url, kind, tech, diff, topic in RESOURCES:
            db.add(Resource(title=title, url=url, kind=kind, technology=tech,
                            difficulty=diff, topic=topic,
                            description=f"{kind} for {tech} ({diff})."))
        db.flush()

        # ---- users
        users = {}
        def mkuser(email, name, role, seed_word):
            u = User(email=email, name=name, role=role.value,
                     password_hash=hash_password("password123"), avatar_seed=seed_word,
                     bio=f"{name} — TECHNOVA member")
            db.add(u)
            db.flush()
            users[email] = u
            return u

        mkuser("admin@technova.club", "Aarav Sharma", Role.SUPER_ADMIN, "aarav")
        head = mkuser("head@technova.club", "Diya Patel", Role.CLUB_HEAD, "diya")
        mkuser("advisor@technova.club", "Mr. Rao", Role.ADVISOR, "rao")
        mentor = mkuser("mentor@technova.club", "Kabir Singh", Role.MENTOR, "kabir")
        m1 = mkuser("isha@technova.club", "Isha Verma", Role.MEMBER, "isha")
        m2 = mkuser("rohan@technova.club", "Rohan Gupta", Role.MEMBER, "rohan")
        m3 = mkuser("nisha@technova.club", "Nisha Reddy", Role.COMMITTEE, "nisha")
        m4 = mkuser("arjun@technova.club", "Arjun Mehta", Role.MEMBER, "arjun")

        # ---- courses + lessons (Python path with progression + a quiz)
        py = Course(slug="python-foundations", title="Python Foundations",
                    description="Learn Python from zero: syntax, functions, data structures, OOP.",
                    category="Programming", difficulty="Beginner",
                    skill_id=skill_by_key["python"].id, order=1)
        db.add(py)
        db.flush()
        py_lessons = [
            ("Getting Started with Python", "article",
             "# Python Basics\n\nPython is a readable, powerful language.\n\n```python\nprint('Hello TECHNOVA')\n```\n\nVariables store data: `x = 5`. Types include int, float, str, bool.", 20, None),
            ("Control Flow", "article",
             "# Control Flow\n\n```python\nif score > 90:\n    print('A')\nelse:\n    print('keep going')\n```\n\nLoops repeat work: `for`, `while`.", 20, None),
            ("Functions", "article",
             "# Functions\n\n```python\ndef add(a, b):\n    return a + b\n```\n\nFunctions make code reusable and testable.", 25, None),
            ("Data Structures", "article",
             "# Data Structures\n\nLists `[]`, dicts `{}`, sets, tuples. Choose the right one for the job.", 25, None),
            ("Basics Quiz", "quiz", "Test your Python basics.", 30,
             _quiz([
                 {"q": "How do you print in Python?", "options": ["echo", "print()", "console.log", "printf"], "answer_index": 1},
                 {"q": "Which is a list?", "options": ["{1,2}", "(1,2)", "[1,2]", "<1,2>"], "answer_index": 2},
                 {"q": "Keyword to define a function?", "options": ["func", "def", "function", "lambda"], "answer_index": 1},
             ])),
        ]
        for i, (title, kind, content, xp, quiz) in enumerate(py_lessons):
            db.add(Lesson(course_id=py.id, title=title, order=i, kind=kind, content=content,
                          xp=xp, quiz=quiz, pass_score=67))

        web = Course(slug="web-dev-starter", title="Web Development Starter",
                     description="Build web pages with HTML, CSS and JavaScript.",
                     category="Web Development", difficulty="Beginner",
                     skill_id=skill_by_key["javascript"].id, order=2)
        db.add(web)
        db.flush()
        for i, (title, content) in enumerate([
            ("HTML Structure", "# HTML\n\nHTML is the skeleton of web pages. Tags like `<h1>`, `<p>`, `<a>`."),
            ("Styling with CSS", "# CSS\n\nCSS controls layout and color. Selectors target elements."),
            ("JavaScript Basics", "# JavaScript\n\nJS adds interactivity. `document.querySelector`, events, functions."),
        ]):
            db.add(Lesson(course_id=web.id, title=title, order=i, kind="article", content=content, xp=20))

        ai = Course(slug="ai-fundamentals", title="AI Fundamentals",
                    description="Understand what AI is, how models learn, and where it's used.",
                    category="AI / Data", difficulty="Intermediate",
                    skill_id=skill_by_key["ai"].id, order=3)
        db.add(ai)
        db.flush()
        for i, (title, content) in enumerate([
            ("What is AI?", "# What is AI?\n\nAI = systems that perform tasks needing human-like intelligence."),
            ("How Models Learn", "# Learning\n\nModels learn patterns from data using training + evaluation."),
            ("Neural Networks 101", "# Neural Networks\n\nLayers of weighted connections learn features from data via backpropagation."),
            ("AI Ethics", "# Ethics\n\nBias, fairness, privacy and accountability matter as much as accuracy."),
        ]):
            db.add(Lesson(course_id=ai.id, title=title, order=i, kind="article", content=content, xp=25))

        # ---- Data Structures & Algorithms course
        algo = Course(slug="dsa-essentials", title="Data Structures & Algorithms",
                      description="Master the DSA that interviews and contests are built on.",
                      category="Programming", difficulty="Intermediate",
                      skill_id=skill_by_key["algorithms"].id, order=4)
        db.add(algo)
        db.flush()
        algo_lessons = [
            ("Big-O Notation", "article", "# Big-O\n\nMeasure how runtime grows with input size: O(1), O(log n), O(n), O(n log n), O(n^2).", 25, None),
            ("Arrays & Hashing", "article", "# Arrays & Hashing\n\nHash maps give O(1) lookups. The backbone of most fast solutions.", 25, None),
            ("Two Pointers & Sliding Window", "article", "# Two Pointers\n\nShrink/expand a window to solve subarray problems in O(n).", 25, None),
            ("Trees & Graphs", "article", "# Trees & Graphs\n\nBFS explores level by level; DFS goes deep. Both are O(V+E).", 30, None),
            ("DSA Quiz", "quiz", "Check your algorithmic foundations.", 30,
             _quiz([
                 {"q": "Big-O of binary search?", "options": ["O(n)", "O(log n)", "O(n^2)", "O(1)"], "answer_index": 1},
                 {"q": "Best structure for O(1) lookup?", "options": ["List", "Hash map", "Linked list", "Stack"], "answer_index": 1},
                 {"q": "BFS uses which structure?", "options": ["Stack", "Queue", "Heap", "Tree"], "answer_index": 1},
             ])),
        ]
        for i, (title, kind, content, xp, quiz) in enumerate(algo_lessons):
            db.add(Lesson(course_id=algo.id, title=title, order=i, kind=kind, content=content,
                          xp=xp, quiz=quiz, pass_score=67))

        # ---- Git & Collaboration course
        git = Course(slug="git-collaboration", title="Git & Collaboration",
                     description="Version control and teamwork the way real dev teams work.",
                     category="Other", difficulty="Beginner",
                     skill_id=skill_by_key["git"].id, order=5)
        db.add(git)
        db.flush()
        for i, (title, content) in enumerate([
            ("Why Version Control", "# Version Control\n\nGit tracks every change so you can experiment safely and collaborate."),
            ("Commits & Branches", "# Branches\n\n`git commit` saves a snapshot; `git branch` lets you work in parallel."),
            ("Pull Requests", "# Pull Requests\n\nPropose changes, get review, then merge. The heart of team workflows."),
        ]):
            db.add(Lesson(course_id=git.id, title=title, order=i, kind="article", content=content, xp=20))

        # ---- challenges (with real hidden tests judged safely)
        challenges = [
            ("sum-two", "Sum of Two Numbers", "Return the sum of a and b.", "Easy", "python", 40, "add",
             "def add(a, b):\n    # return a + b\n    pass\n",
             [{"args": [2, 3], "expected": 5}, {"args": [10, 20], "expected": 30}],
             [{"args": [0, 0], "expected": 0}, {"args": [-5, 5], "expected": 0}, {"args": [100, 250], "expected": 350}]),
            ("reverse-string", "Reverse a String", "Return the reversed string s.", "Easy", "python", 40, "reverse",
             "def reverse(s):\n    pass\n",
             [{"args": ["abc"], "expected": "cba"}, {"args": ["nova"], "expected": "avon"}],
             [{"args": [""], "expected": ""}, {"args": ["racecar"], "expected": "racecar"}]),
            ("fizzbuzz-count", "Count FizzBuzz", "Count numbers 1..n divisible by 3 or 5.", "Medium", "algorithms", 70, "count_fizz",
             "def count_fizz(n):\n    pass\n",
             [{"args": [15], "expected": 7}, {"args": [5], "expected": 2}],
             [{"args": [1], "expected": 0}, {"args": [100], "expected": 47}, {"args": [3], "expected": 1}]),
            ("max-of-list", "Maximum in List", "Return the largest number in the list nums.", "Easy", "python", 40, "max_of",
             "def max_of(nums):\n    pass\n",
             [{"args": [[1, 7, 3]], "expected": 7}, {"args": [[-2, -9, -1]], "expected": -1}],
             [{"args": [[5]], "expected": 5}, {"args": [[10, 10, 2]], "expected": 10}]),
        ]
        for slug, title, stmt, diff, sk, pts, fn, starter, samples, hidden in challenges:
            db.add(Challenge(slug=slug, title=title, statement=stmt, difficulty=diff,
                             skill_id=skill_by_key[sk].id, points=pts, function_name=fn,
                             starter_code=starter, sample_tests=samples, hidden_tests=hidden,
                             created_by=head.id))

        # weekly challenges
        now = dt.datetime.now(dt.UTC)
        db.add(Challenge(slug="weekly-palindrome", title="Challenge of the Week: Palindrome",
                         statement="Return True if s reads the same forwards and backwards.",
                         difficulty="Easy", skill_id=skill_by_key["python"].id, points=60,
                         function_name="is_palindrome",
                         starter_code="def is_palindrome(s):\n    pass\n",
                         sample_tests=[{"args": ["racecar"], "expected": True}, {"args": ["nova"], "expected": False}],
                         hidden_tests=[{"args": [""], "expected": True}, {"args": ["abba"], "expected": True}],
                         is_weekly=True, weekly_kind="Coding",
                         active_until=now + dt.timedelta(days=7), created_by=head.id))

        # ---- events
        db.add(Event(title="Intro to Python Workshop", description="Hands-on Python for beginners.",
                     kind="Workshop", location="Computer Lab 1",
                     starts_at=now + dt.timedelta(days=2, hours=4), capacity=40,
                     is_public=True, created_by=head.id))
        db.add(Event(title="TECHNOVA Weekly Meeting", description="Club sync + project updates.",
                     kind="Meeting", location="Room 204",
                     starts_at=now + dt.timedelta(days=5), capacity=60,
                     is_public=False, created_by=head.id))
        db.add(Event(title="Hack Night", description="Build something in one evening.",
                     kind="Hackathon", location="Innovation Hub",
                     starts_at=now + dt.timedelta(days=9), capacity=30,
                     is_public=True, created_by=head.id))
        # richer event calendar
        _more_events = [
            ("Git & GitHub Crash Course", "Version control from zero to pull requests.", "Workshop", "Computer Lab 2", 3, 35, True),
            ("Web Dev Bootcamp: Day 1", "HTML, CSS and responsive layouts.", "Workshop", "Computer Lab 1", 7, 45, True),
            ("Machine Learning Study Jam", "Hands-on notebooks with scikit-learn.", "Workshop", "AI Lab", 12, 30, True),
            ("Guest Talk: Life in Big Tech", "A senior engineer shares their journey.", "Talk", "Auditorium", 14, 150, True),
            ("Arduino Robotics Night", "Build a line-following robot.", "Workshop", "Innovation Hub", 16, 24, True),
            ("Interview Prep: DSA Mock", "Timed mock interviews with mentors.", "Session", "Room 204", 18, 20, False),
            ("Open Source Contribution Day", "Make your first PR to a real project.", "Hackathon", "Computer Lab 1", 21, 40, True),
            ("Design Thinking Workshop", "From user problem to prototype.", "Workshop", "Studio", 24, 30, True),
            ("TECHNOVA Demo Day", "Teams present their showcase projects.", "Showcase", "Auditorium", 28, 200, True),
        ]
        for title, desc, kind, loc, day_off, cap, pub in _more_events:
            db.add(Event(title=title, description=desc, kind=kind, location=loc,
                         starts_at=now + dt.timedelta(days=day_off, hours=3),
                         ends_at=now + dt.timedelta(days=day_off, hours=5),
                         capacity=cap, is_public=pub, created_by=head.id))
        db.flush()

        # ---- competitions (with entries, rubric scores, and final rankings)
        judges = [mentor, head]
        _competitions = [
            dict(title="Fall Hackathon 2025", kind="Hackathon",
                 description="A 24-hour sprint to build something that helps students. Judged on impact, execution and creativity.",
                 rubric=[{"name": "Innovation", "max": 25}, {"name": "Execution", "max": 25},
                         {"name": "Impact", "max": 25}, {"name": "Presentation", "max": 25}],
                 status="closed", start_off=-30, end_off=-29,
                 entries=[("Team Nova", m1, "Smart Attendance", "QR-based attendance that saves class time.", [92, 88]),
                          ("Green Guardians", m3, "EcoBin Tracker", "Sensor-driven recycling dashboard.", [85, 90]),
                          ("PixelPlay", m2, "Gesture Arcade", "Play games with hand gestures.", [78, 82]),
                          ("DataWise", m4, "StudyBuddy AI", "AI flashcards from your notes.", [88, 84])]),
            dict(title="Weekly Code Sprint", kind="Coding",
                 description="Solve the weekly algorithmic challenge set for the fastest, cleanest solutions.",
                 rubric=[{"name": "Correctness", "max": 50}, {"name": "Efficiency", "max": 30},
                         {"name": "Code Quality", "max": 20}],
                 status="judging", start_off=-3, end_off=2,
                 entries=[("Solo: Isha", m1, "Dynamic Programming Set", "All 5 problems, O(n) solutions.", [95]),
                          ("Solo: Rohan", m2, "Greedy Set", "4/5 problems solved.", [80]),
                          ("Solo: Arjun", m4, "Graph Set", "All 5 with BFS/DFS.", [90])]),
            dict(title="Spring Project Expo", kind="Project",
                 description="Showcase your best build. Judged live by mentors and the club advisor.",
                 rubric=[{"name": "Technical Depth", "max": 30}, {"name": "Design", "max": 20},
                         {"name": "Usefulness", "max": 30}, {"name": "Teamwork", "max": 20}],
                 status="open", start_off=5, end_off=20, entries=[]),
        ]
        for spec in _competitions:
            comp = Competition(title=spec["title"], description=spec["description"], kind=spec["kind"],
                               rubric=spec["rubric"], status=spec["status"],
                               starts_at=now + dt.timedelta(days=spec["start_off"]),
                               ends_at=now + dt.timedelta(days=spec["end_off"]),
                               created_by=head.id)
            db.add(comp)
            db.flush()
            entry_objs = []
            for team, owner, title, summary, judge_totals in spec["entries"]:
                entry = CompetitionEntry(competition_id=comp.id, user_id=owner.id, team_name=team,
                                         title=title, summary=summary)
                db.add(entry)
                db.flush()
                # record each judge's rubric score
                rubric_total_max = sum(c["max"] for c in spec["rubric"])
                for j_idx, jt in enumerate(judge_totals):
                    judge = judges[j_idx % len(judges)]
                    # distribute the judge's total across criteria proportionally
                    per = {}
                    remaining = jt
                    for k, crit in enumerate(spec["rubric"]):
                        if k == len(spec["rubric"]) - 1:
                            share = round(remaining * crit["max"] / rubric_total_max, 1)
                        else:
                            share = round(jt * crit["max"] / rubric_total_max, 1)
                        per[crit["name"]] = min(share, crit["max"])
                    db.add(RubricScore(entry_id=entry.id, judge_id=judge.id, scores=per,
                                       total=float(jt), comment="Strong entry."))
                # average across judges
                entry.total_score = sum(judge_totals) / len(judge_totals) if judge_totals else 0.0
                entry_objs.append(entry)
            # finalize rankings for closed competitions
            if spec["status"] == "closed" and entry_objs:
                for rank, e in enumerate(sorted(entry_objs, key=lambda x: x.total_score, reverse=True), start=1):
                    e.rank = rank
        db.flush()


        # ---- projects (incubator + showcase)
        p1 = Project(slug="smart-attendance", title="Smart Attendance System",
                     problem="Manual attendance wastes class time.",
                     solution="QR + web app to auto-record attendance.",
                     description="A full attendance platform with analytics.",
                     required_skills=["python", "apis", "javascript"], team_size=4,
                     state=ProjectState.DEVELOPMENT.value, owner_id=m1.id, mentor_id=mentor.id,
                     tech=["Python", "FastAPI", "React"])
        db.add(p1)
        db.flush()
        db.add(ProjectMember(project_id=p1.id, user_id=m1.id, role="Lead", status="member"))
        db.add(ProjectMember(project_id=p1.id, user_id=m2.id, role="Backend", status="member"))

        p2 = Project(slug="smart-plant-monitor", title="Smart Plant Monitor",
                     problem="Plants in the lab die during holidays.",
                     solution="IoT sensor + dashboard for soil moisture.",
                     description="An IoT project showcased at the science fair.",
                     required_skills=["electronics", "python", "data"], team_size=3,
                     state=ProjectState.SHOWCASE.value, owner_id=m3.id, mentor_id=mentor.id,
                     tech=["Arduino", "Python", "Chart.js"], showcase=True,
                     repo_url="https://github.com/technova/plant-monitor",
                     demo_url="https://technova.club/demos/plant")
        db.add(p2)
        db.flush()
        db.add(ProjectMember(project_id=p2.id, user_id=m3.id, role="Lead", status="member"))
        db.add(ProjectMember(project_id=p2.id, user_id=m4.id, role="Hardware", status="member"))

        # ---- additional showcase projects (public gallery of club work)
        _showcase = [
            dict(slug="campus-navigator", title="Campus Navigator",
                 problem="New students get lost finding classrooms and labs on campus.",
                 solution="Indoor wayfinding PWA with interactive maps and turn-by-turn routing.",
                 description="A progressive web app that maps every building, room and lab, with search and shortest-path routing between locations.",
                 tech=["React", "TypeScript", "Leaflet", "PWA"],
                 repo="https://github.com/technova/campus-navigator",
                 demo="https://technova.club/demos/navigator", team=[m1, m2]),
            dict(slug="studybuddy-ai", title="StudyBuddy AI",
                 problem="Students struggle to make good revision notes and quizzes.",
                 solution="An AI tutor that turns lecture PDFs into flashcards and practice quizzes.",
                 description="Upload notes and StudyBuddy generates summaries, spaced-repetition flashcards and auto-graded quizzes.",
                 tech=["Python", "FastAPI", "OpenAI", "React"],
                 repo="https://github.com/technova/studybuddy-ai",
                 demo="https://technova.club/demos/studybuddy", team=[mentor, m4]),
            dict(slug="ecobin-tracker", title="EcoBin Tracker",
                 problem="Campus recycling bins overflow and waste isn't sorted properly.",
                 solution="Smart bins with fill sensors and a live dashboard for the facilities team.",
                 description="ESP32 ultrasonic sensors report bin fill levels; a dashboard flags bins needing collection and tracks recycling rates.",
                 tech=["Arduino", "ESP32", "MQTT", "Node.js"],
                 repo="https://github.com/technova/ecobin",
                 demo="https://technova.club/demos/ecobin", team=[m2, m3]),
            dict(slug="clubchat", title="ClubChat",
                 problem="Club announcements get lost across WhatsApp and email.",
                 solution="A realtime chat + announcements hub built just for the club.",
                 description="Channels, threads, and pinned announcements with realtime delivery over WebSockets.",
                 tech=["React", "Socket.IO", "Node.js", "PostgreSQL"],
                 repo="https://github.com/technova/clubchat",
                 demo="https://technova.club/demos/clubchat", team=[m4, m1]),
            dict(slug="gesture-game", title="Gesture Arcade",
                 problem="Accessibility: not everyone can use a keyboard for games.",
                 solution="Play retro arcade games using hand gestures via the webcam.",
                 description="Computer-vision hand tracking maps gestures to game controls for a set of browser mini-games.",
                 tech=["Python", "MediaPipe", "OpenCV", "JavaScript"],
                 repo="https://github.com/technova/gesture-arcade",
                 demo="https://technova.club/demos/gesture", team=[mentor, m1]),
            dict(slug="lab-booking", title="Lab Slot Booking",
                 problem="Fights over who booked the 3D printer and lab equipment.",
                 solution="A booking system with calendars, approvals and reminders.",
                 description="Members reserve equipment slots; mentors approve; email + in-app reminders prevent no-shows.",
                 tech=["React", "FastAPI", "SQLite"],
                 repo="https://github.com/technova/lab-booking",
                 demo="https://technova.club/demos/labbooking", team=[m3, m2]),
            dict(slug="code-arena", title="Code Arena",
                 problem="Practicing for coding contests alone is boring and hard to track.",
                 solution="A head-to-head competitive coding playground with live scoreboards.",
                 description="Real-time 1v1 coding duels with a sandboxed judge, ELO ratings and weekly ladders.",
                 tech=["TypeScript", "React", "Docker", "WebSockets"],
                 repo="https://github.com/technova/code-arena",
                 demo="https://technova.club/demos/codearena", team=[m4, mentor]),
            dict(slug="weather-balloon", title="High-Altitude Weather Balloon",
                 problem="No affordable way for students to collect real atmospheric data.",
                 solution="A near-space balloon payload logging telemetry and capturing photos.",
                 description="A Raspberry Pi payload logs GPS, temperature and pressure to 30km altitude and streams recovered imagery.",
                 tech=["Raspberry Pi", "Python", "LoRa", "Sensors"],
                 repo="https://github.com/technova/weather-balloon",
                 demo="https://technova.club/demos/balloon", team=[m2, head]),
            dict(slug="portfolio-builder", title="Portfolio Builder",
                 problem="Members have projects but no polished way to show them to recruiters.",
                 solution="One-click developer portfolios generated from your TECHNOVA profile.",
                 description="Pulls your skills, projects and certificates into a shareable, themeable portfolio site.",
                 tech=["Next.js", "TypeScript", "Tailwind"],
                 repo="https://github.com/technova/portfolio-builder",
                 demo="https://technova.club/demos/portfolio", team=[m1, m3]),
        ]
        for spec in _showcase:
            owner = spec["team"][0]
            proj = Project(slug=spec["slug"], title=spec["title"], problem=spec["problem"],
                           solution=spec["solution"], description=spec["description"],
                           required_skills=[], team_size=max(2, len(spec["team"])),
                           state=ProjectState.SHOWCASE.value, owner_id=owner.id, mentor_id=mentor.id,
                           tech=spec["tech"], showcase=True,
                           repo_url=spec["repo"], demo_url=spec["demo"])
            db.add(proj)
            db.flush()
            for i, member in enumerate(spec["team"]):
                db.add(ProjectMember(project_id=proj.id, user_id=member.id,
                                     role="Lead" if i == 0 else "Contributor", status="member"))


        # ---- announcements
        db.add(Announcement(title="Welcome to TECHNOVA OS!",
                            body="Learn, build, compete, and lead. Complete courses to grow your skills.",
                            pinned=True, created_by=head.id))
        db.add(Announcement(title="Weekly Challenge is live",
                            body="Solve this week's palindrome challenge for 60 points.",
                            created_by=head.id))

        db.commit()

        # ---- give demo members some real ecosystem activity via the engine
        # (so leaderboard / skills / achievements are populated authentically)
        for uid, sk, xp in [(m1.id, "python", 250), (m1.id, "apis", 120),
                            (m2.id, "python", 180), (m2.id, "javascript", 90),
                            (m3.id, "electronics", 300), (m3.id, "data", 150),
                            (m4.id, "javascript", 200), (m4.id, "css", 120)]:
            eng.add_skill_xp(db, uid, sk, xp, "lesson")
        db.commit()

        # award some challenge points authentically through the ledger
        for uid, pts, cid in [(m1.id, 40, "sum-two"), (m1.id, 70, "fizzbuzz-count"),
                             (m2.id, 40, "reverse-string"), (m3.id, 40, "max-of-list"),
                             (m4.id, 40, "sum-two")]:
            eng.award_points(db, uid, pts, "challenge", "challenge", cid, "Solved challenge (seed)")
        # attendance-ish + social
        eng.award_points(db, m1.id, 150, "project", "project_complete", "seed-p", "Shipped a project")
        eng.grant_achievement(db, m1.id, "project_complete", "project:seed")
        eng.grant_achievement(db, m1.id, "first_lesson", "lesson:seed")
        eng.grant_achievement(db, m3.id, "first_project", "project:seed")
        db.commit()

        # ---- governance: a couple of demo proposals so the Governance page isn't empty
        from .models import Proposal, Vote
        prop1 = Proposal(
            title="Should we host a 24-hour hackathon next month?",
            description="A club-wide overnight hackathon with prizes. Vote to help us decide.",
            kind="decision",
            options=["Approve", "Reject", "Abstain"],
            status="open", min_tier=1, created_by=head.id,
            closes_at=now + dt.timedelta(days=7),
        )
        prop2 = Proposal(
            title="Fund the Smart Attendance project (₹5,000 for hardware)?",
            description="Requesting a budget for RFID readers and a Raspberry Pi to finish the build.",
            kind="funding", amount=5000, options=["Approve", "Reject", "Abstain"],
            status="open", min_tier=1, created_by=head.id,
            closes_at=now + dt.timedelta(days=10),
        )
        db.add_all([prop1, prop2])
        db.flush()
        # a few authentic weighted votes from members who have earned voting tier
        for voter, choice in [(m1, "Approve"), (m3, "Approve"), (m2, "Reject")]:
            pts = eng.total_points(db, voter.id)
            from .governance import tier_for_points, vote_weight
            if tier_for_points(pts)["index"] >= 1:
                db.add(Vote(proposal_id=prop1.id, user_id=voter.id, choice=choice,
                            weight=vote_weight(pts), points_at_vote=pts))
        db.commit()

        # ---- rewards store: a starter catalog so the shop isn't empty
        from .models import Reward
        _rewards = [
            ("TECHNOVA Sticker Pack", "A set of vinyl laptop stickers with the club logo.", 150, "physical", "🏷️", -1),
            ("Club T-Shirt", "Official TECHNOVA tee. Pick your size at pickup.", 1200, "physical", "👕", 25),
            ("Hoodie (Top Earners)", "Premium embroidered hoodie.", 4000, "physical", "🧥", 10),
            ("Skip-the-Queue Lab Pass", "Priority access to the lab & good equipment for a week.", 800, "perk", "🔑", -1),
            ("Custom Profile Banner", "A digital banner + badge on your public portfolio.", 500, "digital", "🎨", -1),
            ("Pizza at Next Meetup", "A free pizza voucher for the next club meetup.", 600, "perk", "🍕", 40),
            ("1:1 Mentor Session", "A 30-minute session with a senior mentor of your choice.", 1000, "perk", "🧑\u200d🏫", -1),
            ("Raspberry Pi Kit", "A Pi starter kit for your next hardware build.", 6000, "physical", "🔌", 5),
        ]
        for name, desc, cost, kind, icon, stock in _rewards:
            db.add(Reward(name=name, description=desc, cost=cost, kind=kind, icon=icon, stock=stock))
        db.commit()

        print("Seed complete. Login: admin@technova.club / password123")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    seed(reset="--reset" in sys.argv)
