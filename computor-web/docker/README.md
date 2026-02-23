# Docker Deployment for Computor Web Frontend

This directory contains the production Dockerfile for the Computor Next.js frontend application.

## Overview

The Dockerfile is designed to be used with the backend's `docker-compose-prod.yaml` for integrated deployment.

## Dockerfile Details

### Multi-Stage Build

The Dockerfile uses a 3-stage build process for optimal image size and security:

1. **deps**: Installs production dependencies
2. **builder**: Builds the Next.js application
3. **runner**: Minimal production runtime image

### Key Features

- **Node 20 Alpine**: Minimal base image (~40MB)
- **Non-root user**: Runs as user `nextjs` (UID 1001) for security
- **Standalone output**: Uses Next.js standalone mode for minimal bundle
- **Health check**: Built-in health monitoring
- **Build arguments**: Configurable API URL at build time

## Build Arguments

| Argument | Default | Description |
|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | Backend API URL |

## Usage in docker-compose-prod.yaml

Add this service to your backend's `docker-compose-prod.yaml`:

```yaml
services:
  frontend:
    build:
      context: ../computor-web
      dockerfile: docker/Dockerfile
      args:
        NEXT_PUBLIC_API_URL: ${NEXT_PUBLIC_API_URL:-http://backend:8000}
    image: computor-web:latest
    container_name: computor-web
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL:-http://backend:8000}
    depends_on:
      - backend
    restart: unless-stopped
    networks:
      - computor-network
    healthcheck:
      test: ["CMD", "node", "-e", "require('http').get('http://localhost:3000/', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 10s

networks:
  computor-network:
    driver: bridge
```

## Building Manually

If you need to build the image manually:

```bash
# From the computor-web directory
docker build -f docker/Dockerfile -t computor-web:latest .

# With custom API URL
docker build -f docker/Dockerfile \
  --build-arg NEXT_PUBLIC_API_URL=https://api.example.com \
  -t computor-web:latest .
```

## Running the Container

```bash
docker run -d \
  --name computor-web \
  -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=http://backend:8000 \
  computor-web:latest
```

## Environment Variables

### Build-time (--build-arg)

- `NEXT_PUBLIC_API_URL`: API endpoint (embedded in build, used for SSR and client-side)

### Runtime (-e or docker-compose environment)

These are exposed to the client browser:

- `NEXT_PUBLIC_API_URL`: Backend API URL (must match build arg for consistency)

## Image Size

Expected sizes:
- **Base image**: ~40MB (Node 20 Alpine)
- **Final image**: ~150-200MB (includes Next.js standalone bundle)

## Security Features

1. **Non-root user**: Application runs as `nextjs` (UID 1001)
2. **Minimal base**: Alpine Linux reduces attack surface
3. **No dev dependencies**: Only production dependencies included
4. **Standalone mode**: Minimal runtime dependencies

## Health Check

The container includes a health check that:
- Runs every 30 seconds
- Checks if the app responds on port 3000
- Allows 10 seconds startup time
- Retries 3 times before marking unhealthy

## Logs

View logs:

```bash
docker logs computor-web
docker logs -f computor-web  # Follow logs
```

## Troubleshooting

### Build fails with "Cannot find module"

Ensure `output: 'standalone'` is set in `next.config.ts`

### API requests fail from browser

Check that `NEXT_PUBLIC_API_URL` is:
1. Set correctly in docker-compose environment
2. Accessible from the client browser (not just the container)
3. Uses the correct protocol (http/https)

### Container keeps restarting

Check logs:
```bash
docker logs computor-web
```

Common issues:
- Port 3000 already in use
- Missing environment variables
- Backend not accessible

## CORS Configuration

Remember to configure the FastAPI backend CORS settings to allow requests from the frontend container:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://frontend:3000",  # Docker network
        "https://yourdomain.com",  # Production domain
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Production Checklist

- [ ] Update `NEXT_PUBLIC_API_URL` in docker-compose
- [ ] Configure backend CORS for frontend origin
- [ ] Set up reverse proxy (nginx) if needed
- [ ] Configure SSL/TLS certificates
- [ ] Set up cookie domain (if backend and frontend on different subdomains)
- [ ] Configure backend cookies: `samesite="lax"`, `secure=True` (for HTTPS)
- [ ] Test authentication flow end-to-end
- [ ] Set up monitoring and logging
- [ ] Configure backup strategy

## Next.js Configuration

The build uses `next.config.ts` with `output: 'standalone'` mode, which:
- Creates a minimal production server
- Includes only necessary dependencies
- Reduces image size significantly
- Optimizes startup time

## Additional Resources

- [Next.js Docker Documentation](https://nextjs.org/docs/deployment#docker-image)
- [Next.js Standalone Output](https://nextjs.org/docs/advanced-features/output-file-tracing)
- [Docker Best Practices](https://docs.docker.com/develop/dev-best-practices/)
