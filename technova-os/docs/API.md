# API overview

Base URL: `/api`. Auth: `Authorization: Bearer <jwt>` (from `/auth/login` or `/auth/register`).
Interactive docs (OpenAPI/Swagger) are auto-generated at **`/docs`** when the API runs.

## Auth
| Method | Path | Role | Notes |
|---|---|---|---|
| POST | `/auth/register` | public | First user → SUPER_ADMIN. Returns JWT. |
| POST | `/auth/login` | public | OAuth2 password form. Returns JWT. |
| GET | `/auth/me` | member | Current user. |

## Profile / portfolio
| GET | `/me/profile` | member | Full portfolio: points, rank, skills, achievements, projects, certs. |
| GET | `/users/{id}/profile` | member | Public-safe profile of another member. |
| GET | `/members` · `/members/{id}` | member | Directory. |

## Academy
| GET | `/academy/courses` · `/academy/courses/{slug}` | member | Courses + per-user progress. |
| GET | `/academy/lessons/{id}` | member | Gated by progression (403 if previous incomplete). Quiz answers never exposed. |
| POST | `/academy/lessons/{id}/complete` | member | Emits `lesson.completed` (+ `quiz.passed`, `course.completed`). Returns ecosystem effects. |
| GET | `/academy/skills` | member | All skills. |

## Challenges
| GET | `/challenges` · `/challenges/{slug}` | member | Hidden tests never returned. |
| POST | `/challenges/{slug}/submit` | member | Safe judge; emits `challenge.solved` on pass. |
| POST | `/challenges` | committee+ | Create a problem (incl. weekly). |

## Projects
| GET/POST | `/projects` | member | List/create (incubator). |
| GET | `/projects/{slug}` | member | Workspace: overview, team, tasks, reviews. Private drafts gated. |
| POST | `/projects/{slug}/join` · `/members/{id}/approve` | member / lead+mentor | Team forming. |
| POST | `/projects/{slug}/state?state=` | lead/mentor | Advance pipeline; COMPLETED → certs+points. |
| POST/PATCH | `/projects/{slug}/tasks` · `/tasks/{id}` | team | Kanban board. |
| POST | `/projects/{slug}/reviews` | mentor+ | Mentor feedback → history + notifications. |
| GET | `/projects/{slug}/matches` | member | Explainable, skill-based team matching. |
| GET | `/projects/showcase/public` | member | Public showcase. |

## Events + attendance
| GET/POST | `/events` | member / committee+ | |
| POST | `/events/{id}/register` | member | Capacity-checked. |
| POST | `/events/{id}/attendance/open` | committee+ | Open/close attendance. |
| GET | `/events/{id}/qr` | committee+ | Fresh signed, time-limited token. |
| POST | `/events/{id}/attendance` | member | Verifies token → emits `attendance.marked`. |

## Competitions
| GET/POST | `/competitions` · `/competitions/{id}` | member / club_head+ | Rubric-based. |
| POST | `/competitions/{id}/register` | member | Entry. |
| POST | `/competitions/{id}/status?status=` | club_head+ | open→judging→closed (closing ranks + issues certs). |
| POST | `/competitions/entries/{id}/score` | mentor+ | Rubric-bounded; averaged across judges. |

## Leaderboard / notifications / search / resources / announcements
| GET | `/leaderboard` | member | Board + your category breakdown. |
| GET/POST | `/notifications` · `/notifications/read` | member | |
| GET | `/search?q=` | member | Cross-entity global search. |
| GET | `/activity?limit=&before=` | member | Club-wide activity pulse; keyset pagination via `before`. |
| GET | `/activity/stream?token=` | member | SSE live stream of new activity events (token via query param). |
| GET | `/resources` | member | Filter by technology/difficulty/query. |
| GET/POST | `/announcements` | member / committee+ | Posting notifies all members. |

## Certificates (public verification)
| GET | `/certificates/me` | member | Your certificates. |
| POST | `/certificates/{uid}/revoke` | club_head+ | Audited revocation. |
| GET | `/verify/{uid}` | **public** | Verifies HMAC signature; reports revoked/invalid. |

## Admin
| GET | `/admin/members` | advisor+ | |
| POST | `/admin/members/{id}/role` · `/deactivate` | club_head+ | Constrained + audited. |
| GET | `/admin/analytics` | advisor+ | Club/learning/project metrics. |
| GET | `/admin/audit` | club_head+ | Audit log. |

## Command center
| GET | `/command-center` | **public** | Live club screen data. |
