# Day 12 Lab - Mission Answers

## Student Information
- Name: Nguyen Thi Thanh Huyen
- Student ID: 2A202600211
- Date: 17/04/2026

## Part 1: Localhost vs Production

### Exercise 1.1: Anti-patterns found
1. Hardcoded secret trong source code: `OPENAI_API_KEY = "sk-hardcoded-fake-key-never-do-this"`.
2. Hardcoded thông tin database trong code: `DATABASE_URL` chứa user/password.
3. Không có config management chuẩn, dùng biến cố định trong file (`DEBUG = True`, `MAX_TOKENS = 500`).
4. Dùng `print()` cho logging thay vì structured logging.
5. Log lộ secret (`print(f"[DEBUG] Using key: {OPENAI_API_KEY}")`).
6. Không có health check endpoint để platform giám sát và auto-restart.
7. Port bị hardcode (`port=8000`), không đọc từ environment variable `PORT`.
8. Bind host là `localhost` nên không truy cập được từ bên ngoài container/cloud.
9. Bật `reload=True` (debug behavior) không phù hợp production.

### Exercise 1.3: Comparison table
| Feature | Develop | Production | Why Important? |
|---------|---------|------------|----------------|
| Config | Hardcode trực tiếp trong `app.py` | Tập trung trong `config.py`, đọc từ environment variables | Tách config khỏi code, deploy linh hoạt giữa môi trường, tránh lộ secret |
| Secrets handling | Secret nằm trong source code và còn bị log ra | Không hardcode, lấy từ env var, có validate ở production | Giảm rủi ro lộ khóa/API key, an toàn khi push repo |
| Logging | `print()` tự do, không cấu trúc | Structured JSON logging qua `logging` | Dễ tìm kiếm/phân tích log trên cloud (Datadog, Loki, ELK) |
| Health check | Không có `/health` | Có `/health` trả trạng thái liveness | Orchestrator biết app còn sống để restart khi lỗi |
| Readiness check | Không có | Có `/ready` kiểm tra trạng thái sẵn sàng | Load balancer chỉ route traffic tới instance đã sẵn sàng |
| Shutdown | Không xử lý vòng đời rõ ràng | Có lifecycle startup/shutdown + handler SIGTERM | Tránh mất request đang chạy, giảm lỗi khi scale down/redeploy |
| Network binding | `host="localhost"` | `host=settings.host` mặc định `0.0.0.0` | Chạy được trong container/cloud, nhận request từ bên ngoài |
| Port management | `port=8000` cố định | `port=settings.port` lấy từ env `PORT` | Tương thích Railway/Render/Cloud Run |
| Runtime mode | `reload=True` luôn bật | `reload=settings.debug` chỉ bật khi debug | Tránh overhead và hành vi không ổn định trong production |
| CORS & middleware | Chưa cấu hình | Có CORS middleware, origins từ config | Kiểm soát truy cập frontend an toàn và đúng môi trường |

---

## Part 2: Docker

### Exercise 2.1: Dockerfile questions
1. Base image:
	- Develop Dockerfile: `python:3.11` (full image, de doc).
	- Production Dockerfile: `python:3.11-slim` cho ca builder va runtime (nhe hon).
2. Working directory:
	- Duoc dat la `/app` trong ca hai Dockerfile. Tat ca lenh COPY/RUN/CMD sau do chay theo thu muc nay.
3. Why copy requirements first:
	- De tan dung Docker layer cache. Khi code thay doi nhung dependencies khong doi, Docker khong can cai lai pip packages, build nhanh hon dang ke.
4. CMD vs ENTRYPOINT:
	- CMD la command mac dinh, co the bi override de dang luc `docker run ... <command>`.
	- ENTRYPOINT dinh nghia executable chinh cua container, thuong dung khi muon container luon chay mot process co dinh.
	- Trong bai nay dang dung CMD (`python app.py` o develop, `uvicorn ...` o production) de linh hoat khi can override.

### Exercise 2.3: Image size comparison
- Develop: 1700 MB (tag `my-agent:develop-v5`)
- Production: 236 MB (tag `my-agent:advanced-v5`)
- Difference: 86.65% smaller (production so voi develop)

Nhan xet:
- Multi-stage build giam size rat manh vi runtime image khong chua build tools.
- Dung base `python:3.11-slim` o production giup image gon hon dang ke.

## Part 3: Cloud Deployment

### Exercise 3.1: Railway deployment
- URL: https://considerate-integrity-production-0462.up.railway.app
- Platform: Railway
- Deployment status: Success (build + deploy complete, healthcheck passed on /health)
- Health check (public):
	- GET /health -> {"status":"ok", ...}
- Railway project link:
	- https://railway.com/project/4acab772-e06a-40dc-bd24-c62c34c6361c

Screenshot reminders (can nop bai):
- [ ] [railway dashboard](screenshots\dashboard.png)
- [ ] [Trang public URL mo duoc](screenshots\running.png)
- [ ] [Test results](screenshots\test.png)

## Part 4: API Security

### Exercise 4.1-4.3: Test results
- Exercise 4.1 (API Key authentication - develop):
	- Test without API key: POST /ask -> 401
	- Test with wrong API key: POST /ask -> 403
	- Test with correct API key: POST /ask -> 200
	- Recorded output:
		- EX4_1 401 403 200

- Exercise 4.2 (JWT authentication flow - production/auth.py):
	- Login/auth check with demo user:
		- authenticate_user("student", "demo123") -> {"username": "student", "role": "user"}
	- Create JWT token:
		- create_token(...) returns valid string token
	- Verify token:
		- verify_token(Bearer <token>) -> {"username": "student", "role": "user"}
	- Invalid token test:
		- verify_token("bad.token.value") -> 403
	- Recorded output:
		- EX4_2_USER {'username': 'student', 'role': 'user'}
		- EX4_2_TOKEN_CREATED True True
		- EX4_2_VERIFIED {'username': 'student', 'role': 'user'}
		- EX4_2_INVALID 403

- Exercise 4.3 (Rate limiting - production/rate_limiter.py):
	- Algorithm: Sliding Window Counter (in-memory deque theo user)
	- Config user limit: 10 requests / 60 seconds
	- Test loop 11 requests for user tier:
		- Requests 1-10 -> 200
		- Request 11 -> 429 (Rate limit exceeded)
	- Recorded output:
		- EX4_3_SERIES [200, 200, 200, 200, 200, 200, 200, 200, 200, 200, 429]
		- EX4_3_LIMIT_STATUS 429
		- EX4_3_LIMIT_DETAIL {'error': 'Rate limit exceeded', 'limit': 10, 'window_seconds': 60, 'retry_after_seconds': 60}

Note khi test app production end-to-end:
- Phat hien loi middleware trong app production:
	- response.headers.pop("server", None) gay AttributeError vi MutableHeaders khong co method pop.
	- Loi nay anh huong test API qua app.py bang TestClient.
	- Khuyen nghi sua thanh: if "server" in response.headers: del response.headers["server"].

### Exercise 4.4: Cost guard implementation
Implement dung theo yeu cau lab: moi user co budget 10 USD/thang, luu tren Redis, reset theo thang.

Code implementation:

```python
import os
import redis
from datetime import datetime, timezone

r = redis.from_url(os.getenv("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True)

MONTHLY_BUDGET_USD = 10.0


def check_budget(user_id: str, estimated_cost: float) -> bool:
	"""
	Return True neu con budget, False neu vuot budget.

	Logic:
	- Moi user co budget 10 USD/thang
	- Track spending trong Redis
	- Reset dau thang (thong qua key theo YYYY-MM)
	"""
	month_key = datetime.now(timezone.utc).strftime("%Y-%m")
	key = f"budget:{user_id}:{month_key}"

	current = float(r.get(key) or 0.0)
	if current + estimated_cost > MONTHLY_BUDGET_USD:
		return False

	r.incrbyfloat(key, estimated_cost)
	# TTL > 1 thang de key tu dong het han sau khi qua chu ky nop
	r.expire(key, 32 * 24 * 3600)
	return True
```

Test cases da thuc hien:
- Case 1: user moi, estimated_cost = 0.5 -> True
- Case 2: current + estimated_cost > 10.0 -> False
- Case 3: qua thang moi (doi month_key) -> budget tinh lai tu 0

Giai thich:
- Khong can job reset thu cong, vi key tach theo tung thang (YYYY-MM).
- Neu sang thang moi se sinh key moi, tu dong bat dau budget moi.
- Redis giup chia se state cho nhieu instances (phu hop production + scale).

## Part 5: Scaling & Reliability

### Exercise 5.1-5.5: Implementation notes
- Exercise 5.1 (Health check + Readiness check):
	- Develop app da co 2 endpoint:
		- GET /health (liveness)
		- GET /ready (readiness)
	- Test voi lifespan day du (startup/shutdown duoc kich hoat):
		- EX5_DEV_WITH_LIFESPAN_HEALTH 200 ok
		- EX5_DEV_WITH_LIFESPAN_READY 200 True
		- EX5_DEV_WITH_LIFESPAN_ASK 200
	- Nhan xet:
		- /health phuc vu cho platform health probe
		- /ready dung de load balancer chi route vao instance da san sang

- Exercise 5.2 (Graceful shutdown):
	- Develop app da implement:
		- signal handler cho SIGTERM/SIGINT
		- lifespan shutdown cho phep cho in-flight requests hoan thanh (toi da 30s)
		- timeout_graceful_shutdown=30 trong uvicorn.run
	- Bang chung trong test lifecycle:
		- Log startup: Agent is ready
		- Log shutdown: Graceful shutdown initiated -> Shutdown complete

- Exercise 5.3 (Stateless design):
	- Production app da tach state ra khoi process memory theo thiet ke:
		- Session luu theo key session:<id>
		- API /chat su dung session_id cho multi-turn
		- API /chat/{session_id}/history de doc lai history
	- Test logic session:
		- EX5_PROD_CHAT1 200 (tao session thanh cong)
		- EX5_PROD_CHAT2 200 (reuse dung session_id)
		- EX5_PROD_HISTORY_COUNT 200 4 (2 cau hoi + 2 cau tra loi)
	- Luu y quan trong:
		- Moi truong test hien tai dang fallback in-memory vi Redis chua san sang
		- Output: "Redis not available - using in-memory store (not scalable!)"

- Exercise 5.4 (Load balancing voi Nginx):
	- Co cau hinh Nginx upstream + proxy trong production/nginx.conf.
	- Co y dinh scale 3 replica trong production/docker-compose.yml (deploy.replicas: 3).
	- Van de cau hinh phat hien:
		- docker-compose.yml dang tro den Dockerfile khong ton tai:
			- dockerfile: 05-scaling-reliability/advanced/Dockerfile
		- Thu muc 05-scaling-reliability/advanced khong co trong workspace.
	- He qua:
		- Chua the xac minh load balancing thuc te bang docker compose up --scale agent=3.

- Exercise 5.5 (Test stateless):
	- test_stateless.py duoc viet dung kich ban: gui nhieu request, theo doi served_by, kiem tra history.
	- Kiem tra endpoint runtime hien tai:
		- EX5_PROD_HEALTH_ERR URLError [WinError 10061] (localhost:8080 chua co service chay)
	- Nguyen nhan chinh:
		- Stack production chua start duoc do loi duong dan Dockerfile o exercise 5.4.

Tong ket Part 5:
- Da dat phan health/readiness/graceful shutdown o muc code-level.
- Da dat stateless flow o muc API/session design.
- Chua hoan tat demo scale + stateless end-to-end tren Docker Compose do loi cau hinh Dockerfile path.
- De hoan tat 100% bai nay can:
	- Sua docker-compose.yml tro den Dockerfile hop le.
	- Khoi dong stack Redis + Nginx + 3 agent instances.
	- Chay lai test_stateless.py de thu duoc bang chung multi-instance (served_by > 1).
