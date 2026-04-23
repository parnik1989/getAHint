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
docker run -p 8000:8000 ghcr.io/parnik/getAHintService:latest
```

### Manual Build (Optional)

Build locally without pushing:
```bash
docker build -t getahintservice:latest .
docker run -p 8000:8000 getahintservice:latest
```

### Docker Improvements Made

✅ **Multi-stage build** - Smaller final image
✅ **Non-root user** - Better security (runs as `appuser`)
✅ **Health checks** - Automatic health monitoring
✅ **Better caching** - Faster rebuilds
✅ **Environment variables** - Proper Python config
✅ **Port 8000** - Updated from port 80

### Deployment to Cloud

You can now deploy from any cloud provider:

**Kubernetes:**
```yaml
containers:
- image: ghcr.io/parnik/getAHintService:latest
  ports:
  - containerPort: 8000
```

**Docker Compose:**
```yaml
services:
  app:
    image: ghcr.io/parnik/getAHintService:latest
    ports:
      - "8000:8000"
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
