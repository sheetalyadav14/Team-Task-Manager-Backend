# Team Task Manager — Backend (SY)

FastAPI + MongoDB backend. JWT-based auth, role-based access (admin / member), projects and tasks.

## Requirements

- Python 3.12+
- MongoDB 6+ running locally (default: `mongodb://localhost:27017`)

## Setup

1. Create and activate a virtualenv:

   ```bash
   python3.12 -m venv .venv
   source .venv/bin/activate
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy the env template and edit if needed:

   ```bash
   cp .env.example .env
   ```

   Set at minimum:

   ```
   MONGODB_URI=mongodb://localhost:27017
   MONGODB_DB_NAME=sy_team_task_manager
   JWT_SECRET=<some-long-random-string>
   PORT=8001
   CLIENT_ORIGIN=http://localhost:5174
   ```

## Run

```bash
uvicorn app.main:app --reload --port 8001
```

Health check: http://localhost:8001/health
API base: http://localhost:8001/api

## Layout

```
app/
  api/endpoints/   Route handlers (auth, users, projects, tasks)
  api/dependencies.py
  config/          Settings + security helpers
  database/        Mongo client + indexes
  models/          Shared types
  schemas/         Pydantic request/response models
  services/        Business logic
  main.py          App factory
```
