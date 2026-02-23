# Environment Variables in Docker

## Important: NEXT_PUBLIC_* Variables

Next.js `NEXT_PUBLIC_*` environment variables have **special behavior**:

- ⚠️ **Baked into the build at BUILD TIME**
- ⚠️ **Cannot be changed at runtime**
- ⚠️ **Used in the browser (client-side)**

### What This Means

When you run `./docker/build.sh`, Next.js:
1. Reads `NEXT_PUBLIC_API_URL` from `.env`
2. **Embeds it** into the JavaScript bundle
3. Ships that bundle in the Docker image

**You CANNOT change it later** without rebuilding the image!

## Configuration

### .env File (Used for Docker Build)

```bash
# FastAPI Backend URL (accessible from user's browser)
# IMPORTANT: This URL must be accessible from the CLIENT (browser), not just Docker network
NEXT_PUBLIC_API_URL=http://localhost:8080/api

# Docker Configuration
DOCKER_IMAGE_NAME=computor-web
DOCKER_IMAGE_TAG=latest
DOCKER_REGISTRY=
```

### API URL Considerations

The `NEXT_PUBLIC_API_URL` must be accessible from:
- ✅ The **user's browser** (client-side)
- ❌ NOT just the Docker network

#### Examples

**❌ WRONG** (Docker internal network):
```bash
NEXT_PUBLIC_API_URL=http://uvicorn:8000
```
Browser cannot resolve `uvicorn` hostname.

**✅ CORRECT** (Accessible from browser):
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080/api
```
Browser can access localhost:8080 (Traefik proxy).

**✅ CORRECT** (Production):
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com
```
Browser can access public domain.

## Rebuilding After Changes

If you change `NEXT_PUBLIC_API_URL` in `.env`, you **MUST** rebuild:

```bash
# Rebuild with new configuration
./docker/build.sh --no-cache

# Or manually
docker build -f docker/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=http://localhost:8080/api \
  -t computor-web:latest .
```

## Checking Current Value

To see what API URL is baked into a running container:

```bash
# This WON'T work (not a runtime variable):
docker exec <container> env | grep NEXT_PUBLIC

# Instead, check the browser's Network tab:
# - Open DevTools (F12)
# - Go to Network tab
# - Look at the API request URLs
```

## Development vs Production

### Development (.env)
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080/api
```

### Production (.env)
```bash
NEXT_PUBLIC_API_URL=https://api.production.com
```

Remember to rebuild when switching environments!

## Troubleshooting

### Problem: API requests go to wrong URL

**Symptom**: Browser makes requests to old API URL

**Cause**: Image was built with old `.env` value

**Solution**:
```bash
# 1. Update .env with correct URL
# 2. Rebuild image
./docker/build.sh --no-cache

# 3. Restart docker-compose
docker-compose down
docker-compose up -d
```

### Problem: "Cannot resolve hostname"

**Symptom**: Browser error: `Failed to fetch` or `net::ERR_NAME_NOT_RESOLVED`

**Cause**: Using Docker internal hostname (e.g., `http://uvicorn:8000`)

**Solution**: Use external URL accessible from browser:
```bash
NEXT_PUBLIC_API_URL=http://localhost:8080/api
```

### Problem: CORS errors

**Symptom**: Browser shows CORS policy error

**Cause**: Backend CORS not configured for frontend origin

**Solution**: Configure FastAPI backend:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Frontend dev
        "http://localhost:8080",  # Traefik
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Summary

1. ✅ `.env` is used for Docker builds (committed to git with example values)
2. ✅ `.env.local` is for local development (ignored by git)
3. ✅ `NEXT_PUBLIC_API_URL` must be browser-accessible
4. ✅ Rebuild image after changing `.env`
5. ✅ Use `./docker/build.sh` to read from `.env`
