# Workkbot: Sovereign Enterprise AI Assistant

An enterprise-grade, sovereign AI assistant engineered for strict compliance with India's **Digital Personal Data Protection (DPDP) Act 2023**. Pinned strictly to **`asia-south1` (Mumbai)** with Zero Data Retention (ZDR), Row-Level Security (RLS) tenant isolation, Model Context Protocol (MCP) integrations, and hardware-backed credential vaults.

---

## 🏛️ Sovereign Architecture Invariants

- **Zero Cross-Border Routing**: All compute (Cloud Run), storage (Cloud SQL), encryption keys (Cloud KMS CMEK), and LLM inference (Vertex AI Gemini Flash) are regionally restricted to `asia-south1` (Mumbai).
- **Zero Data Retention (ZDR)**: Context caching and persistent prompt logging are disabled. Ephemeral translation states (e.g. `temp:pii_map`) are strictly scrubbed before touching PostgreSQL.
- **Tenant Isolation via RLS**: Every database table holding personal or session data enforces PostgreSQL Row-Level Security (`FORCE ROW LEVEL SECURITY`) via transaction-scoped `SET LOCAL app.current_user_id`.
- **Hardware-Backed Device Security**: Mobile and client authentication tokens are stored exclusively in hardware keystores / iOS Keychain via `expo-secure-store`.

---

## 📁 Repository Structure

```
workkbot/
├── backend/                  # Python 3.12+ FastAPI & Google ADK 2.6+ service
│   ├── src/
│   │   ├── auth.py           # Google Cloud Identity Platform (Firebase Auth) OIDC JWT verification
│   │   ├── config.py         # Sovereign configuration & region assertion
│   │   ├── db.py             # asyncpg connection pool & RLS transaction context manager
│   │   ├── main.py           # FastAPI entrypoint, healthcheck, session & consent routes
│   │   └── session/          # ADK 2.6+ CloudSqlSessionService with temp: key scrubbing
│   ├── tests/                # Automated pytest suite (B1-G1, B1-G2, B1-G3)
│   └── pyproject.toml        # Backend dependencies & package definition (managed via uv)
│
├── frontend/                 # Expo (React Native) shell based on assistant-ui architecture
│   ├── app/
│   │   ├── _layout.tsx       # Root layout with theme & safe area
│   │   └── (tabs)/           # Expo Router tabs: /chat, /consent, /settings
│   ├── lib/
│   │   └── auth.ts           # Hardware-backed SecureStore token vault adapter
│   ├── tests/                # Frontend storage unit tests
│   └── package.json          # Expo SDK 51+ & assistant-ui dependencies
│
├── infra/                    # Sovereign Cloud & Container Infrastructure
│   ├── docker/
│   │   └── Dockerfile        # Multi-stage non-root container (appuser:10001, port 8080)
│   ├── migrations/
│   │   └── 001_adk_foundation.sql  # Users, consent_logs, adk_sessions, adk_events + RLS
│   ├── scripts/
│   │   └── provision_gcp.sh  # VPC, PSA Peering, Cloud SQL, and IAP Bastion provisioning
│   └── cloudbuild.yaml       # Sovereign CI/CD pipeline for asia-south1
│
├── specs/                    # Project specifications, constitution, and scorecards
├── pnpm-workspace.yaml       # Monorepo workspace configuration
└── package.json              # Root monorepo scripts
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.12+** & [uv](https://github.com/astral-sh/uv) (`curl -LsSf https://astral.sh/uv/install.sh | sh`)
- **Node.js 18+** & **pnpm 9+** (`corepack enable && corepack prepare pnpm@latest --activate`)
- **Docker**
- **Google Cloud SDK (`gcloud`)** authenticated to project `workkbot`

---

### 1. Backend Setup & Testing

```bash
cd backend

# Create Python 3.12 virtual environment using uv
uv venv --python 3.12 .venv
source .venv/bin/activate

# Install backend dependencies in editable mode
uv pip install -e ".[dev]"

# Run backend unit & mock RLS isolation tests
pytest -v tests/
```

### 2. Frontend Setup & Testing

```bash
cd frontend

# Install frontend dependencies
pnpm install

# Run hardware SecureStore unit tests
node --test tests/auth.test.ts

# Start Expo development server
pnpm start
```

### 3. Docker Container Verification

Verify non-root execution (`appuser:10001`) on port `8080`:

```bash
# Build multi-stage image
docker build -t enterprise-ai-backend:block1 -f infra/docker/Dockerfile backend

# Verify container executes as non-root user
docker run --rm enterprise-ai-backend:block1 whoami
# Output: appuser
```

### 4. Cloud SQL & Sovereign VPC Provisioning (GCP)

When ready to provision live cloud resources in project `workkbot` (`asia-south1`):

```bash
bash infra/scripts/provision_gcp.sh
```

This automates:
1. Creation of `workkbot-sovereign-vpc` and subnet `10.10.0.0/24` in `asia-south1`.
2. Private Services Access (PSA) peering for Cloud SQL Private IP.
3. Cloud SQL PostgreSQL 16 instance (`workkbot-db`) with IAM Database Authentication enabled.
4. IAP Bastion VM (`workkbot-bastion`) for tunneling port 5432 to your local workstation.

---

## 🎯 Verification Gates (Block 1 Scorecard)

| Gate ID | Verification Item | Target | Verification Command |
| :--- | :--- | :--- | :--- |
| **B1-G1** | Cloud SQL RLS Tenant Isolation | User B receives 0 rows when attempting to access User A's data | `pytest backend/tests/test_rls_isolation.py` |
| **B1-G2** | ADK Session Persistence | CRUD operations succeed and `temp:` keys strictly discarded | `pytest backend/tests/test_session_service.py` |
| **B1-G3** | Sovereign Region Health Endpoint | `GET /health` returns HTTP 200 with `"region": "asia-south1"` | `pytest backend/tests/test_health.py` |
| **B1-G4** | Non-Root Container Execution | Executes as `appuser` (UID 10001) binding to port 8080 | `docker run --rm enterprise-ai-backend:block1 whoami` |
| **B1-G5** | Hardware SecureStore Vault | Client tokens stored in hardware keychain/keystore | `cd frontend && node --test tests/auth.test.ts` |

---

## 📜 License

Proprietary enterprise software. All rights reserved.
