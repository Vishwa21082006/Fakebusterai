# ═══════════════════════════════════════════════════════════
#  FakeBuster AI — Deepfake Forensics & Media Trust Platform
# ═══════════════════════════════════════════════════════════

Production-grade deepfake detection platform with multi-layer AI analysis,
forensic reporting, and enterprise API capabilities.

## Quick Start

### Prerequisites
- Docker & Docker Compose
- (Optional) Python 3.11+ for local dev without Docker

### 1. Configuration
```bash
cp .env.example .env
# Edit .env and set a strong JWT_SECRET
```

### 2. Launch Stack
```bash
docker-compose up --build -d
```
Wait ~30s for all services (including ClamAV signature download) to initialize.

### 3. Verify
```bash
curl http://localhost:8000/api/v1/health
# → {"status":"ok","db":true,"redis":true,"clamav":true}
```

### 4. API Docs
Open [http://localhost:8000/docs](http://localhost:8000/docs) for interactive Swagger UI.

## API Endpoints

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| `POST` | `/api/v1/auth/register` | Create account | No |
| `POST` | `/api/v1/auth/login` | Get JWT token | No |
| `GET` | `/api/v1/auth/me` | Current user info | Yes |
| `POST` | `/api/v1/upload` | Upload image/video | Yes |
| `POST` | `/api/v1/ingest/url` | Ingest from URL | Yes |
| `GET` | `/api/v1/analysis/{id}` | Get analysis result | Yes |
| `GET` | `/api/v1/analysis` | List analyses | Yes |
| `GET` | `/api/v1/health` | Health check | No |
| `GET` | `/api/v1/ready` | Readiness probe | No |

## Architecture

```
Client → FastAPI → Redis (rate limit)
                 → ClamAV (virus scan)
                 → PostgreSQL (data)
                 → ML Detector (background)
```

## Tech Stack
- **Backend**: FastAPI + Uvicorn
- **Database**: PostgreSQL 16
- **Cache/Rate Limit**: Redis 7
- **Virus Scanning**: ClamAV
- **Auth**: JWT + RBAC (user / analyst / admin)
- **ML**: PyTorch (Phase 3)
- **Frontend**: React (Phase 6)

## Project Status
- ✅ Phase 1: Core Infrastructure
- ✅ Phase 2: Media Ingestion Pipeline
- ⬜ Phase 3: ML Detection Pipeline
- ⬜ Phase 4: Video Processing
- ⬜ Phase 5: Explainable AI
- ⬜ Phase 6: React Frontend
- ⬜ Phase 7: Forensic Reporting
- ⬜ Phase 8: Security Hardening
- ⬜ Phase 9: Deployment & Scaling

## License
Proprietary — All rights reserved.
