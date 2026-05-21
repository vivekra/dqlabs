# DigitalQ Labs
### AI-native Kubernetes, DevOps and Infrastructure Learning Cloud

DigitalQ Labs is a production-ready multi-tenant SaaS learning platform engineered for high-density, low-cost operational infrastructure practice. 

Students, DevOps engineers, and teams can launch actual Kubernetes environments, connect to live browser-based VSCode and terminal sessions, and troubleshoot cluster failures with the guidance of a hybrid AI diagnostic system.

---

## 🚀 Monorepo Architecture Overview

This platform is structured as a modular monorepo powered by **pnpm workspaces** and **Turborepo** for caching pipeline tasks.

```text
digitalq-platform/
 ├── apps/
 │    ├── web/                 # Next.js App Router (Dashboard, Billing, Workspaces, Admin)
 │    ├── api/                 # FastAPI Core API (Auth, Tenancy, workspaces state machine CRUD, audits)
 │    ├── ai-gateway/          # FastAPI AI Service (pgvector RAG, Ollama/OpenAI routing, log analysis)
 │    └── orchestrator/        # Celery Workers & Event Loop (Workspace creation, lifecycle, K8s SDK)
 │
 ├── packages/
 │    ├── ui/                  # Component Library (Design tokens, custom Tailwind theme settings)
 │    ├── auth/                # Supabase SDK Shared Clients, Middlewares, RBAC definitions
 │    ├── billing/             # Paymenter API Client, Metering Engine, Quota Validators
 │    ├── shared/              # Zod schemas, shared constants (User Roles, Workspace Status)
 │    └── kubernetes-sdk/      # Custom K8s/k3s client wrappers, manifest templates, ingress mappers
 │
 ├── infra/
 │    └── docker/              # Dockerfiles and development service overrides
 ├── scripts/                  # Seeders, local initialization SQL files
 ├── pnpm-workspace.yaml       # PNPM Workspace Configuration
 ├── package.json              # Monorepo Scripts
 └── docker-compose.yml        # Development Stack Setup
```

---

## 🛠️ Stack Components & Core Logic (Phase 2 Additions)

- **Managed Database & Auth Strategy**: Relies on Supabase Auth and hosted Supabase PostgreSQL (retains pgvector RAG support).
- **Core SaaS Tenancy Rules**: Implements hierarchical boundaries (`Organization` -> `Tenants` -> `Workspaces`). Access is validated using Row-Level Security (RLS) policies and `X-Tenant-ID` header routing.
- **FastAPI Modular Layout**: 
  - `apps/api/models.py`: Declarative SQLAlchemy models.
  - `apps/api/middleware/auth.py`: JWT decrypting + tenant switching + WebSocket authorization validation.
  - `apps/api/middleware/audit.py`: Mutation action logger and persistent logging.
  - `apps/api/repositories/`: Tenant-aware repo structures enforcing strict `tenant_id` filters.
  - `apps/api/routers/`: Versioned API gateways (`/api/v1`) exposing templates CRUD, organizations creation, and workspaces lifecycle handlers.
  - `apps/api/init_db.py`: Async migration hook executed dynamically on application start.

---

## 💻 Local Development Sandbox

### Prerequisites
- [Docker & Docker Compose](https://docs.docker.com/get-docker/)
- [Node.js v18+](https://nodejs.org/)
- [pnpm package manager](https://pnpm.io/installation)

### 1. Boot up Infrastructure Services
Spin up the PostgreSQL database, Redis, MailHog, MinIO, Ollama, Paymenter, Supabase Auth, and the bootstrapped services concurrently:
```bash
docker compose up -d
```

### 2. Install Monorepo Dependencies
```bash
pnpm install
```

### 3. Initialize & Seed Database Schema
Populate your local Postgres container with default organizations, tenants, quotas, templates, and running mock workspace parameters:
```bash
docker exec -i digitalq-postgres psql -U postgres -d digitalq_dev < scripts/init-db.sql
```

### 4. Run Development Gateways
Execute Turborepo to launch the web dashboard and FastAPI backends concurrently with live-reload support:
```bash
pnpm dev
```

---

## 💸 Cost Optimization Boundaries

To host labs profitably at ₹499/student:
- **Autosleep Mechanism**: Inactive terminals/workspaces trigger a Celery background cron task that scales the Kubernetes Deployment replicas down to **0** while saving state inside **Longhorn PVC snapshots**. Compute costs drop to **0%** during sleep.
- **AI Hybrid Routing**: Common CLI and configuration lookups are handled by the local **Ollama** model. Critical errors are escalated to **OpenAI**, maintaining token spending control.
- **Namespace Quotas**: Enforces strict `ResourceQuotas` and `LimitRanges` per namespace.

---

## 🔒 Security Practices

1. **Row-Level Security (RLS)**: Enforced in PostgreSQL on all tenant resource queries.
2. **Container Security**: Workspace pods run as non-root users (`uid: 1000`), block privilege escalation, and drop standard Linux capabilities.
