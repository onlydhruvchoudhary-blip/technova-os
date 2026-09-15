# Roadmap & known limitations

## Known limitations (honest)
- **Code judge** supports Python function-signature problems judged by return value. Stdin/stdout
  problems and other languages aren't supported yet. For scale it should move from a subprocess
  guard to a container/nsjail/gVisor sandbox with no network.
- **Schema management** uses **Alembic migrations** (auto-applied on startup, with safe stamping of pre-existing DBs).
  (models are structured to make this straightforward).
- **Event bus is in-process & synchronous.** Great for a school-scale deployment; heavy async work
  (e.g. large batch emails) would want a real queue (Celery/RQ + Redis).
- **File uploads** (project attachments, avatars) use URLs/links rather than object storage.
- **Rate limiting** is in-memory per-process; a multi-worker deployment should use Redis.
- **Notifications** are in-app; email/push are not wired (preferences are configurable in the model).
- **Real-time** updates use polling (20–30s); could move to websockets/SSE.

## Extension points already built in
- Add a module = add tables + new event names + reactors in `engine.py`. No rewrites.
- RBAC roles are ordered ranks — new roles slot in without touching endpoint logic.
- Rubrics, quizzes and test cases are data (JSON), so club leaders create content without code.

## Future modules (designed for, not yet implemented)
- Robotics / IoT / Hardware-lab management (inventory, checkouts).
- AI tooling (auto-hint on challenges, project idea suggestions).
- School-wide & inter-school competitions (multi-club tenancy).
- Alumni network & external mentors.
- Public community + internship/opportunity board.
- Email/push notifications with the existing preference model.
- Websocket live updates for the Command Center and notifications.
- Object storage for uploads; CDN for assets.
```
