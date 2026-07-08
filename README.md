# expeditions-admin

Backend API for expedition management. The service exposes a REST API for
administering expeditions along with the chiefs and members who take part in
them. Authentication is handled with JWT access/refresh tokens, the schema is
documented through OpenAPI/Swagger, and real-time expedition events are
delivered over WebSockets via Django Channels.

## Stack

- Python 3.14 / Django 6.0
- Django REST Framework + SimpleJWT
- drf-spectacular (OpenAPI 3 schema, Swagger UI, ReDoc)
- Django Channels (ASGI, real-time WebSocket events)
- PostgreSQL
- pytest + pytest-django, ruff

## Local setup

1. Create and activate a virtual environment, then install dependencies:

   ```bash
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   source .venv/bin/activate
   pip install -r requirements-dev.txt
   ```

2. Create your environment file and adjust the values:

   ```bash
   cp .env.example .env
   ```

   Configure either `DATABASE_URL` or the individual `POSTGRES_*` variables to
   point at a running PostgreSQL instance.

3. Apply migrations and create an admin user:

   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

4. Run the development server:

   ```bash
   python manage.py runserver
   ```

## Docker

The service ships with a Docker setup for local review and demos: a Django
ASGI container served by daphne, a PostgreSQL database and a Redis instance
backing the Channels layer.

Build and start everything:

```bash
docker compose up --build
```

Migrations are applied automatically on startup — the `web` service runs
`python manage.py migrate` before launching the ASGI server, so the database
schema is ready by the time daphne accepts connections. No manual migration
step is required.

Once the stack is up:

- Swagger UI: <http://localhost:8000/api/schema/swagger-ui/>
- REST API base URL: <http://localhost:8000/api/>
- WebSocket URL: `ws://localhost:8000/ws/expeditions/?token=<access_token>`

Create an admin user inside the running container if needed:

```bash
docker compose exec web python manage.py createsuperuser
```

Stop the containers, and remove them together with the database volume:

```bash
docker compose down          # stop and remove containers
docker compose down -v       # also remove the postgres_data volume
```

## Domain models

**Expedition** — an organized trip led by a chief.

- `status`: `draft` → `ready` → `active` → `finished` (defaults to `draft`).
- `chief` references a `User` and is protected from deletion.
- `capacity` is a positive integer (database-enforced `>= 1`).
- `start_at` is required; `end_at` and `description` are optional.

**ExpeditionMember** — a user's participation in an expedition.

- `state`: `invited` → `confirmed` (defaults to `invited`).
- `invited_at` is set automatically; `confirmed_at` is optional.
- A user can appear at most once per expedition (unique `expedition`/`user` pair).

Lifecycle transitions are enforced by the domain service layer in
`expeditions/services.py`; the API views only validate request shape, call the
services and serialize the result.

## API surface

| Path | Method | Auth | Purpose |
| --- | --- | --- | --- |
| `/api/users/register/` | POST | Public | Register a user (email, name, password, role) |
| `/api/users/me/` | GET | Required | Current authenticated user |
| `/api/users/` | GET | Required | List users, optional `?role=member` filter |
| `/api/auth/token/` | POST | Public | Obtain a JWT access/refresh pair |
| `/api/auth/token/refresh/` | POST | Public | Refresh an access token |
| `/api/auth/token/verify/` | POST | Public | Verify a token |
| `/api/schema/` | GET | Public | Raw OpenAPI schema |
| `/api/schema/swagger-ui/` | GET | Public | Swagger UI |
| `/api/schema/redoc/` | GET | Public | ReDoc |
| `/admin/` | — | — | Django admin |

### Expeditions

All expedition endpoints require authentication. Read access is scoped to
expeditions the user leads or belongs to; anything else returns `404`. Mutations
defer chief/member, status and invitation checks to the service layer.

| Path | Method | Auth | Purpose |
| --- | --- | --- | --- |
| `/api/expeditions/` | POST | Required | Create an expedition (chief only, enforced by the service) |
| `/api/expeditions/` | GET | Required | List expeditions the user leads or belongs to |
| `/api/expeditions/{id}/` | GET | Required | Expedition detail (chief or member only) |
| `/api/expeditions/{id}/invite/` | POST | Required | Invite a member (`member_id`); chief only |
| `/api/expeditions/{id}/confirm/` | POST | Required | Confirm the current user's own invitation |
| `/api/expeditions/{id}/set-ready/` | POST | Required | Move a draft expedition to `ready`; chief only |
| `/api/expeditions/{id}/start/` | POST | Required | Start a ready expedition; chief only |
| `/api/expeditions/{id}/finish/` | POST | Required | Finish an active expedition; chief only |

Domain errors are mapped to HTTP responses: `PermissionDeniedError` → `403`;
`InvalidTransitionError`, `InvitationError` and `ExpeditionStartError` → `400`.
Responses carry a clean `detail` message and never expose internals.

## Real-time events (WebSocket)

Expedition lifecycle changes are pushed to interested users over a Channels
WebSocket. Events are only emitted from service success paths, and only after
the underlying database transaction commits (via `transaction.on_commit`).

**Endpoint**

```
ws://localhost:8000/ws/expeditions/?token=<access_token>
```

**Authentication** — the connection is authenticated with a JWT *access* token
passed as the `token` query-string parameter (the same token used for the HTTP
API, obtained from `/api/auth/token/`). A missing, invalid or expired token
closes the connection. The HTTP JWT endpoints are unchanged.

**Visibility rule** — a user only receives events for expeditions where they
are the chief or have an `ExpeditionMember` row (invited or confirmed).
Recipients are computed from the database per event; nobody is subscribed to
expeditions they are not part of. Each connection joins a private `user_<id>`
group, and dispatch targets those groups.

**Events** — the client-facing JSON `type` is one of:

```json
{ "type": "member_invited",    "expedition_id": 1, "member_id": 2 }
{ "type": "member_confirmed",  "expedition_id": 1, "member_id": 2 }
{ "type": "expedition_status", "expedition_id": 1, "status": "ready" }
```

- `member_invited` — fired by `invite_member`.
- `member_confirmed` — fired by `confirm_invitation`.
- `expedition_status` — fired by `set_ready`, `start_expedition` and
  `finish_expedition`; `status` is one of `draft`, `ready`, `active`,
  `finished`.

The ASGI stack requires an ASGI server (e.g. `python manage.py runserver`,
which serves WebSockets through Channels in development).

## Demo flow

Everything below can also be run interactively from `/api/schema/swagger-ui/`.
The full lifecycle is `draft → ready → active → finished`; starting requires at
least two confirmed members and a `start_at` that is not in the future.

1. Register a chief:

   ```bash
   curl -X POST http://localhost:8000/api/users/register/ \
     -H "Content-Type: application/json" \
     -d '{"email": "chief@example.com", "name": "Chief", "password": "changeme123", "role": "chief"}'
   ```

2. Register two members (note their returned `id` values):

   ```bash
   curl -X POST http://localhost:8000/api/users/register/ \
     -H "Content-Type: application/json" \
     -d '{"email": "member1@example.com", "name": "Member One", "password": "changeme123", "role": "member"}'

   curl -X POST http://localhost:8000/api/users/register/ \
     -H "Content-Type: application/json" \
     -d '{"email": "member2@example.com", "name": "Member Two", "password": "changeme123", "role": "member"}'
   ```

3. Obtain the chief's access token:

   ```bash
   curl -X POST http://localhost:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"email": "chief@example.com", "password": "changeme123"}'
   ```

4. Create an expedition as the chief (use a past `start_at` so it can start
   immediately):

   ```bash
   curl -X POST http://localhost:8000/api/expeditions/ \
     -H "Authorization: Bearer <chief_access_token>" \
     -H "Content-Type: application/json" \
     -d '{"title": "Summit Ascent", "start_at": "2026-01-01T08:00:00Z", "capacity": 5}'
   ```

5. Invite both members (repeat with each `member_id`):

   ```bash
   curl -X POST http://localhost:8000/api/expeditions/<expedition_id>/invite/ \
     -H "Authorization: Bearer <chief_access_token>" \
     -H "Content-Type: application/json" \
     -d '{"member_id": <member_id>}'
   ```

6. Obtain each member's access token:

   ```bash
   curl -X POST http://localhost:8000/api/auth/token/ \
     -H "Content-Type: application/json" \
     -d '{"email": "member1@example.com", "password": "changeme123"}'
   ```

7. Each member confirms their own invitation:

   ```bash
   curl -X POST http://localhost:8000/api/expeditions/<expedition_id>/confirm/ \
     -H "Authorization: Bearer <member_access_token>"
   ```

8. The chief sets the expedition ready, starts it, then finishes it:

   ```bash
   curl -X POST http://localhost:8000/api/expeditions/<expedition_id>/set-ready/ \
     -H "Authorization: Bearer <chief_access_token>"

   curl -X POST http://localhost:8000/api/expeditions/<expedition_id>/start/ \
     -H "Authorization: Bearer <chief_access_token>"

   curl -X POST http://localhost:8000/api/expeditions/<expedition_id>/finish/ \
     -H "Authorization: Bearer <chief_access_token>"
   ```

## Quality

```bash
ruff check .
pytest
```
