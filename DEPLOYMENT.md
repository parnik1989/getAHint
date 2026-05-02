# Docker & CI/CD Deployment Guide

## Automated Docker Build & Push

Your application is now containerized with automated CI/CD pipeline using GitHub Actions.

### How It Works

When you push to `main` or `master` branch:
1. **GitHub Actions** automatically triggers
2. **Docker image** is built using multi-stage build (optimized)
3. **Image is pushed** to GitHub Container Registry (GHCR)
4. **Tags are created**: `latest`, branch name, commit SHA

### Image Registry

Images are pushed to: `ghcr.io/<your-org>/<your-repo>`

Example: `ghcr.io/parnik/getAHintService`

### Getting Your Images

#### 1. View Available Images
Go to your GitHub repository → Packages (right sidebar)

#### 2. Pull Image Locally
```bash
docker login ghcr.io
docker pull ghcr.io/parnik/getAHintService:latest
```

#### 3. Run Container
```bash
docker run -p 8080:8080 ghcr.io/parnik/getAHintService:latest
```

### Manual Build (Optional)

Build locally without pushing:
```bash
docker build -t getahintservice:latest .
docker run -p 8080:8080 getahintservice:latest
```

### Docker Improvements Made

✅ **Multi-stage build** - Smaller final image
✅ **Non-root user** - Better security (runs as `appuser`)
✅ **Health checks** - Automatic health monitoring
✅ **Better caching** - Faster rebuilds
✅ **Environment variables** - Proper Python config
✅ **Port 8080** - Defaults to 8080 when `PORT` is not provided

### Deployment to Cloud

You can now deploy from any cloud provider:

**Railway:**
- Connect the GitHub repository directly if you want Railway to build from the Dockerfile.
- Or deploy the GHCR image produced by GitHub Actions: `ghcr.io/<your-org>/<your-repo>:latest`.
- Railway provides the runtime `PORT` environment variable automatically. The Dockerfile uses `${PORT:-8080}`, so it works on Railway and still defaults to `8080` locally.
- Add a PostgreSQL database in Railway:
  1. Open your Railway project.
  2. Click **New**.
  3. Choose **Database** → **Add PostgreSQL**.
  4. Open your app service settings.
  5. Add a variable named `DATABASE_URL`.
  6. Set it to reference the Postgres service connection URL, usually available from Railway's variable picker.
- The app creates the `events` table automatically on startup.
- On Railway Postgres, the app enables `pgvector` with `CREATE EXTENSION IF NOT EXISTS vector` and adds an `event_embedding vector(384)` column automatically.
- Add or update a single event in Postgres:
  ```bash
  curl -X POST "https://your-app.up.railway.app/eventService/events" \
    -H "Content-Type: application/json" \
    -d '{
      "event_name": "Hyderabad Science Talk",
      "event_description": "A public lecture and discussion for science enthusiasts.",
      "event_date": "2026-06-01",
      "event_address": "Hyderabad",
      "source_name": "manual",
      "source_type": "api"
    }'
  ```
  By default this also generates and stores the event embedding so the new event is searchable immediately.
- Add or update many events at once:
  ```bash
  curl -X POST "https://your-app.up.railway.app/eventService/ingestEvents" \
    -H "Content-Type: application/json" \
    -d '[
      {
        "event_name": "Cultural Evening",
        "event_description": "Music, dance, and food festival.",
        "event_date": "2026-06-10",
        "event_address": "Hyderabad",
        "source_name": "manual",
        "source_type": "api"
      }
    ]'
  ```
- Bulk ingestion also stores embeddings by default. For very large imports, you can skip per-row embedding generation and backfill once afterward:
  ```bash
  curl -X POST "https://your-app.up.railway.app/eventService/ingestEvents?train_model=false" \
    -H "Content-Type: application/json" \
    -d '[...]'
  ```
  ```bash
  curl -X GET "https://your-app.up.railway.app/modelService/trainEventModel"
  ```
- Sync events from configured web pages or web search:
  ```bash
  curl -X POST "https://your-app.up.railway.app/eventService/syncWebEvents" \
    -H "Content-Type: application/json" \
    -d '{
      "city": "Hyderabad",
      "source_urls": [
        "https://example.com/events"
      ],
      "queries": [
        "upcoming cultural events",
        "science events",
        "music events"
      ],
      "max_search_results": 10,
      "train_model": true
    }'
  ```
- Optional web ingestion variables:
  - `EVENT_SOURCE_URLS`: comma-separated event listing URLs to check when no URLs are passed.
  - `SERPER_API_KEY`: enables web search for `queries`; without it, only explicit `source_urls` / `EVENT_SOURCE_URLS` are used.
- Daily web event sync scheduler variables:
  - `ENABLE_DAILY_WEB_SYNC`: set to `true` to run web sync daily.
  - `WEB_SYNC_RUN_AT_UTC`: daily run time in UTC, for example `02:00`.
  - `WEB_SYNC_CITY`: defaults to `Hyderabad`.
  - `WEB_SYNC_QUERIES`: pipe-separated queries, for example `upcoming cultural events|music events|science events`.
  - `WEB_SYNC_SOURCE_URLS`: pipe-separated source URLs for the scheduler. The manual endpoint can still use `source_urls`.
  - `WEB_SYNC_MAX_SEARCH_RESULTS`: defaults to `10`.
  - `WEB_SYNC_TRAIN_MODEL`: defaults to `true`; stores embeddings during ingestion.
  - `WEB_SYNC_RUN_ON_STARTUP`: optional; set to `true` to run once immediately when the app starts.
- Add runtime variables in Railway:
  - `TELEGRAM_BOT_TOKEN`: your token from BotFather.
  - `PUBLIC_BASE_URL`: your Railway app URL, for example `https://your-app.up.railway.app`.
- Open Swagger UI at `https://your-app.up.railway.app/docs`.
- Check Telegram config at `https://your-app.up.railway.app/telegramService/telegram/status`.
- Register the Telegram webhook after deployment:
  ```bash
  curl -X POST "https://your-app.up.railway.app/telegramService/telegram/setWebhook"
  ```

**Kubernetes:**
```yaml
containers:
- image: ghcr.io/parnik/getAHintService:latest
  ports:
  - containerPort: 8080
```

**Docker Compose:**
```yaml
services:
  app:
    image: ghcr.io/parnik/getAHintService:latest
    ports:
      - "8080:8080"
    environment:
      - PYTHONUNBUFFERED=1
```

**AWS ECS, Google Cloud Run, Azure Container Instances** - All support pulling from GHCR

### GitHub Token Permissions

Your workflow uses `GITHUB_TOKEN` which is automatically created. Make sure it has permissions:
- ✅ Already configured in workflow with `packages: write`

### Troubleshooting

**Image build fails?**
- Check logs in: GitHub → Actions → Latest workflow run
- Common issue: Missing dependencies in `requirements.txt`

**Can't pull image?**
- Make sure you're logged in: `docker login ghcr.io`
- Token should be your GitHub personal access token or GITHUB_TOKEN

**Health check failing?**
- Ensure your FastAPI app starts successfully
- Check logs: `docker logs <container-id>`

### Next Steps

1. Push to GitHub: `git push origin main`
2. Go to GitHub Actions tab and watch the build
3. Once complete, pull and run the image
4. Deploy to your hosting platform

---

For questions, check:
- [GitHub Container Registry Docs](https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry)
- [GitHub Actions Docs](https://docs.github.com/en/actions)
