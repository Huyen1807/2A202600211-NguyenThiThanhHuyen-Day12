# Deployment Information

## Student Information
- Name: Nguyen Thi Thanh Huyen
- Student ID: 2A202600211
- Date: 17/04/2026

## Public URL
https://considerate-integrity-production-0462.up.railway.app

## Platform
Railway

## Project Dashboard
https://railway.com/project/4acab772-e06a-40dc-bd24-c62c34c6361c

## Service Details
- Service: considerate-integrity
- Region: us-west1
- Health endpoint: /health

## Test Commands

### Health Check
```bash
curl https://considerate-integrity-production-0462.up.railway.app/health
# Expected: {"status":"ok", ...}
```

### API Test (without authentication)
```bash
curl -X POST https://considerate-integrity-production-0462.up.railway.app/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello from deployment test"}'
# Expected: 401 (Lab 06 requires API key)
```

### API Test (with authentication, Lab 06 requirement)
```bash
curl -X POST https://considerate-integrity-production-0462.up.railway.app/ask \
  -H "X-API-Key: YOUR_KEY" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
# Expected: 200
```

### Authentication Required Check (Lab 06 requirement)
```bash
curl https://considerate-integrity-production-0462.up.railway.app/ask
# Expected: 401
```

### Rate Limiting Check (Lab 06 requirement)
```bash
for i in {1..15}; do \
  curl -X POST https://considerate-integrity-production-0462.up.railway.app/ask \
    -H "X-API-Key: YOUR_KEY" \
    -H "Content-Type: application/json" \
    -d '{"question":"rate limit test"}'; \
done
# Expected: eventually return 429
```

## Environment Variables Set
- PORT
- REDIS_URL
- AGENT_API_KEY
- LOG_LEVEL
- RATE_LIMIT_PER_MINUTE
- MONTHLY_BUDGET_USD
- ENVIRONMENT

## Screenshots
- [Deployment dashboard](screenshots/dashboard.png)
- [Service running](screenshots/running.png)
- [Test results](screenshots/test.png)

## Verification Notes
- Public URL is accessible.
- Health check returns status ok.
- Railway deployment completed successfully.
- Build and deploy logs available in Railway dashboard link above.

## Submission URL
https://github.com/Huyen1807/2A202600211-NguyenThiThanhHuyen-Day12
