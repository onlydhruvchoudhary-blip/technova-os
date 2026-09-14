"""Seed TECHNOVA OS with a rich, realistic dataset so the ecosystem is demonstrable end-to-end."""
from __future__ import annotations

import datetime as dt
from sqlalchemy import select
from sqlalchemy.orm import Session

from .database import SessionLocal, Base, engine
from .models import (User, Role, Skill, Course, Lesson, Challenge, Achievement, Resource,
                     Announcement, Event, Project, ProjectMember, ProjectState)
from .security import hash_password
from . import engine as eng

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

        admin = mkuser("admin@technova.club", "Aarav Sharma", Role.SUPER_ADMIN, "aarav")
        head = mkuser("head@technova.club", "Diya Patel", Role.CLUB_HEAD, "diya")
        advisor = mkuser("advisor@technova.club", "Mr. Rao", Role.ADVISOR, "rao")
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
        ]):
            db.add(Lesson(course_id=ai.id, title=title, order=i, kind="article", content=content, xp=25))

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
        now = dt.datetime.now(dt.timezone.utc)
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

        print("Seed complete. Login: admin@technova.club / password123")
    finally:
        db.close()


if __name__ == "__main__":
    import sys
    seed(reset="--reset" in sys.argv)
