# SproutOS Export Package

可携带、可自部署的「养」系统包。

## Run
```bash
docker compose up --build
```

Then open:
- UI: http://localhost:8080
- Engine: http://localhost:18795/api/sprout/health

## Files
- `sprout_engine.py` — growth engine
- `server.py` — standalone UI server
- `static/index.html` — minimal portable UI
- `Dockerfile` / `docker-compose.yml`

## Environment
Optional:
- `HUOSHAN_API_KEY` for LLM growth/alert parsing

```bash
HUOSHAN_API_KEY=xxx docker compose up --build
```
