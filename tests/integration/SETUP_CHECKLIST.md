# Integration Test Setup Checklist

Use this checklist to ensure you have everything needed to run the integration tests.

## Prerequisites Checklist

### ✅ Services Running

- [ ] PostgreSQL database is running (port 5432)
- [ ] Redis is running (port 6379)
- [ ] Temporal server is running (port 7233)
- [ ] MinIO is running (port 9000)
- [ ] GitLab server is running and accessible
- [ ] Computor API is running (port 8000)

**Quick check:**
```bash
docker ps  # Should show postgres, redis, temporal, minio containers
curl http://localhost:8000/health  # API health check
```

### ✅ GitLab Configuration

- [ ] GitLab root username: `_______________`
- [ ] GitLab root password: `_______________`
- [ ] GitLab URL: `_______________` (e.g., http://localhost:8929)

### ✅ GitLab Parent Group Setup

**Step 1: Create Parent Group**
- [ ] Logged into GitLab as root
- [ ] Created a new group (suggested name: "computor-tests")
- [ ] Parent group ID noted: `_______________`

**Step 2: Create Group Owner Token**
- [ ] Navigated to parent group Settings → Access Tokens
- [ ] Created new group access token with:
  - [ ] Role: **Owner**
  - [ ] Scopes: `api`, `read_repository`, `write_repository`
- [ ] Token saved: `glpat-_______________`

### ✅ Environment Configuration

- [ ] Copied `.env.template` to `.env`
- [ ] Filled in GitLab URL
- [ ] Filled in GitLab root credentials
- [ ] Filled in parent group ID
- [ ] Filled in group owner token
- [ ] Verified other settings (database, API URL, etc.)

### ✅ Python Environment

- [ ] Python 3.10+ installed
- [ ] Virtual environment activated
- [ ] Installed computor-types package
- [ ] Installed computor-client package
- [ ] Installed computor-cli package
- [ ] Installed computor-backend package
- [ ] Installed test dependencies (httpx, python-dotenv)

**Quick install:**
```bash
cd /home/theta/computor/computor-fullstack
source .venv/bin/activate
pip install -e computor-types/
pip install -e computor-client/
pip install -e computor-cli/
pip install -e computor-backend/
pip install -r tests/integration/requirements.txt
```

## Running the Setup

Once all prerequisites are met:

```bash
cd tests/integration/scripts
./setup_test_environment.sh
```

Expected output:
```
✓ Configuration loaded from .env
✓ API is running at http://localhost:8000
✓ GitLab is accessible at http://localhost:8929
✓ Database is running
✓ Deployment successful
✓ Organization 'test-university' exists
✓ Course 'programming-101' exists
✓ Admin login successful
```

## Running Tests

After successful setup:

```bash
# Run all tests
./quick_test.sh all

# Or run specific test suites
./quick_test.sh student
./quick_test.sh tutor
./quick_test.sh lecturer
```

## Troubleshooting

### GitLab Token Issues

If you see authentication errors:
- Verify the token has **Owner** role (not Maintainer or Developer)
- Verify token has all required scopes: `api`, `read_repository`, `write_repository`
- Check token hasn't expired

### Parent Group ID

To find the parent group ID:
1. Go to your GitLab instance
2. Navigate to the parent group
3. Go to Settings → General
4. The group ID is shown at the top (e.g., "Group ID: 123")

### GitLab URL Format

Correct formats:
- ✅ `http://localhost:8929`
- ✅ `https://gitlab.example.com`
- ✅ `http://192.168.1.100:8080`

Incorrect formats:
- ❌ `localhost:8929` (missing http://)
- ❌ `http://localhost:8929/` (trailing slash may cause issues)

## What You'll Provide

When ready to run tests, you only need to provide:

1. **GitLab URL** - Where your GitLab instance is running
2. **Root Username** - Usually "root"
3. **Root Password** - Your GitLab root password
4. **Parent Group ID** - The ID of the group you created
5. **Group Owner Token** - The token you generated for that group

Everything else is auto-configured!
