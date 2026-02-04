# HITL Credit Approval System - Product Requirements Document

Version: 1.0.0  
Last Updated: 2025-01-22  
Status: Production Ready  
Tech Stack: PostgreSQL, Docker, FastAPI, React + TanStack

-----

## Table of Contents
1. [Executive Summary](#1-executive-summary)
1. [System Architecture](#2-system-architecture)
1. [Technical Stack](#3-technical-stack)
1. [Database Schema](#4-database-schema)
1. [API Specification](#5-api-specification)
1. [Frontend Specification](#6-frontend-specification)
1. [ML Pipeline](#7-ml-pipeline)
1. [Security & Compliance](#8-security--compliance)
1. [Infrastructure](#9-infrastructure)
1. [Development Phases](#10-development-phases)

-----

## 1. Executive Summary

### 1.1 Product Vision
The HITL (Human-in-the-Loop) Credit Approval System combines ML-based credit scoring with human analyst oversight. The system automates clear-cut decisions (auto-approve/decline) while routing borderline cases to trained analysts, ensuring optimal balance between operational efficiency, risk management, and regulatory compliance.

### 1.2 Key Metrics

|Metric |Target |
|-----------------------------|----------|
|Auto-decision rate |≥55% |
|Average review time |<8 minutes|
|Default rate (auto-approved) |<2% |
|Default rate (human-approved)|<5% |
|System uptime |99.9% |
|API response time (P95) |<200ms |

### 1.3 Decision Flow

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ ZAHTEV ZA KREDIT                                                            │
└─────────────────────────────────────────────────────────────────────────────┘
        │
        ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ ML SCORING ENGINE                                                           │
│ (Score: 0-1000)                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
        │
  ┌─────────────┼─────────────┐
  ▼             ▼             ▼
┌───────────┐ ┌───────────┐ ┌───────────┐
│ SCORE     │ │ SCORE     │ │ SCORE     │
│ > 720     │ │ 480-720   │ │ < 480     │
│           │ │           │ │           │
│ AUTO      │ │ HUMAN     │ │ AUTO      │
│ APPROVE   │ │ REVIEW    │ │ DECLINE   │
└───────────┘ └───────────┘ └───────────┘
                │
                ▼
      ┌─────────────────────┐
      │ ANALYST WORKBENCH   │
      │ • Risk Summary      │
      │ • Key Factors       │
      │ • Similar Cases     │
      │ • Decision Panel    │
      └─────────────────────┘
                │
                ▼
┌─────────────────────┐
│ DECISION DATABASE    │
│ + Audit Trail        │
│ + Feedback Loop      │
└─────────────────────┘
```

-----

## 2. System Architecture

### 2.1 High-Level Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ LOAD BALANCER (Traefik)                                                     │
└─────────────────────────────────────────────────────────────────────────────┘
        │
  ┌───────────────┼────────────────┐
  ▼               ▼                ▼
┌─────────────────┐      ┌─────────────┐      ┌─────────────────┐
│ FRONTEND        │      │ API         │      │ ML SERVICE       │
│ (React)         │      │ GATEWAY     │      │ (Scoring)        │
│ Port: 3000      │      │ (FastAPI)   │      │ Port: 8001       │
│                 │      │ Port:8000   │      │                 │
└─────────────────┘      └─────────────┘      └─────────────────┘
        │                     │
        ▼                     ▼
┌──────────────────────────────────────────────────────┐
│ REDIS (Cache + Queue)                                 │
└──────────────────────────────────────────────────────┘
        │
┌─────────────────────────┼─────────────────────────┐
▼                         ▼                         ▼
┌─────────────────────┐  ┌─────────────────────┐  ┌─────────────────────┐
│ CELERY WORKER        │  │ CELERY BEAT         │  │ NOTIFICATION        │
│ - Scoring jobs       │  │ - Scheduled tasks   │  │ SERVICE             │
│ - Background         │  │ - SLA checks        │  │ - Email/Webhook     │
└─────────────────────┘  └─────────────────────┘  └─────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ POSTGRESQL 16                                         │
│ (Primary + Read Replica)                              │
└──────────────────────────────────────────────────────┘
        │
        ▼
┌──────────────────────────────────────────────────────┐
│ MONITORING (Prometheus + Grafana + Loki)              │
└──────────────────────────────────────────────────────┘
```

### 2.2 Service Responsibilities

|Service |Port|Responsibility |
|-------------|----|---------------------------------|
|Frontend |3000|React UI for analysts and admins |
|API Gateway |8000|REST API, auth, request routing |
|ML Service |8001|Credit scoring, SHAP explanations|
|Celery Worker|- |Background jobs, async processing|
|Celery Beat |- |Scheduled tasks (SLA, monitoring)|
|PostgreSQL |5432|Primary data store |
|Redis |6379|Cache, message broker |

-----

## 3. Technical Stack

### 3.1 Backend

|Component |Technology|Version|
|------------|----------|-------|
|Language |Python |3.11+ |
|Framework |FastAPI |0.109+ |
|ORM |SQLAlchemy|2.0+ |
|Validation |Pydantic |2.5+ |
|Task Queue |Celery |5.3+ |
|Cache/Broker|Redis |7.2+ |
|Database |PostgreSQL|16+ |

### 3.2 Frontend

|Component |Technology |Version|
|-------------|---------------|-------|
|Framework |React |18.2+ |
|Build Tool |Vite |5.0+ |
|Data Fetching|TanStack Query |5.17+ |
|Routing |TanStack Router|1.15+ |
|State |Zustand |4.5+ |
|Forms |React Hook Form|7.49+ |
|UI Components|shadcn/ui |latest |
|Styling |Tailwind CSS |3.4+ |
|Charts |Recharts |2.10+ |

### 3.3 ML Stack

|Component |Technology |Version|
|-----------------|------------|-------|
|ML Framework |scikit-learn|1.4+ |
|Gradient Boosting|XGBoost |2.0+ |
|Explainability |SHAP |0.44+ |
|Model Registry |MLflow |2.10+ |

### 3.4 Infrastructure

|Component |Technology |Version|
|----------------|---------------|-------|
|Containerization|Docker |24+ |
|Orchestration |Docker Compose |2.24+ |
|Reverse Proxy |Traefik |3.0+ |
|Monitoring |Prometheus |2.48+ |
|Dashboards |Grafana |10.3+ |
|Logging |Loki + Promtail|2.9+ |

-----

## 4. Database Schema

### 4.1 Core Tables Overview

```text
tenants ─────────────┬────────────── users
                     │
                     ├────────────── applications ──────── scoring_results
                     │
                     ├────────────── analyst_queues
                     │
                     ├────────────── decisions
                     │
                     └────────────── similar_cases

├────────────── decision_thresholds
├────────────── model_registry
├────────────── audit_logs
└────────────── notifications
```

### 4.2 Table Definitions

#### tenants

```sql
CREATE TABLE tenants (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  slug VARCHAR(100) NOT NULL UNIQUE,
  settings JSONB NOT NULL DEFAULT '{}',
  subscription_tier VARCHAR(50) NOT NULL DEFAULT 'standard',
  is_active BOOLEAN NOT NULL DEFAULT true,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

#### users

```sql
CREATE TABLE users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  email VARCHAR(255) NOT NULL,
  password_hash VARCHAR(255),
  first_name VARCHAR(100),
  last_name VARCHAR(100),
  role VARCHAR(50) NOT NULL DEFAULT 'analyst',
  -- Roles: admin, senior_analyst, analyst, readonly, api_consumer
  permissions JSONB NOT NULL DEFAULT '[]',
  preferences JSONB NOT NULL DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT true,
  last_login_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT uq_users_tenant_email UNIQUE (tenant_id, email)
);
```

#### applications

```sql
CREATE TABLE applications (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  external_id VARCHAR(100),
  status VARCHAR(50) NOT NULL DEFAULT 'pending',
  -- Status: pending, scoring, review, approved, declined, expired, cancelled
  applicant_data JSONB NOT NULL,
  financial_data JSONB NOT NULL,
  loan_request JSONB NOT NULL,
  credit_bureau_data JSONB,
  source VARCHAR(50) NOT NULL DEFAULT 'web',
  metadata JSONB NOT NULL DEFAULT '{}',
  submitted_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  expires_at TIMESTAMPTZ,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_applications_tenant_status ON applications(tenant_id, status);
CREATE INDEX idx_applications_submitted ON applications(tenant_id, submitted_at DESC);
```

#### scoring_results

```sql
CREATE TABLE scoring_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  model_id VARCHAR(100) NOT NULL,
  model_version VARCHAR(50) NOT NULL,
  score INTEGER NOT NULL CHECK (score >= 0 AND score <= 1000),
  probability_default DECIMAL(5,4) NOT NULL,
  risk_category VARCHAR(20) NOT NULL,
  routing_decision VARCHAR(20) NOT NULL,
  threshold_config_id UUID,
  features JSONB NOT NULL,
  shap_values JSONB NOT NULL,
  top_factors JSONB NOT NULL,
  scoring_time_ms INTEGER NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_scoring_application ON scoring_results(application_id);
CREATE INDEX idx_scoring_routing ON scoring_results(routing_decision);
```

#### analyst_queues

```sql
CREATE TABLE analyst_queues (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  analyst_id UUID REFERENCES users(id) ON DELETE SET NULL,
  priority INTEGER NOT NULL DEFAULT 50,
  -- 1=highest, 100=lowest priority
  priority_reason VARCHAR(255),
  status VARCHAR(30) NOT NULL DEFAULT 'pending',
  -- Status: pending, assigned, in_progress, completed, escalated, expired
  assigned_at TIMESTAMPTZ,
  started_at TIMESTAMPTZ,
  completed_at TIMESTAMPTZ,
  sla_deadline TIMESTAMPTZ NOT NULL,
  sla_breached BOOLEAN NOT NULL DEFAULT false,
  routing_reason VARCHAR(100),
  score_at_routing INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_queue_priority ON analyst_queues(status, priority, created_at)
  WHERE status IN ('pending', 'assigned');
CREATE INDEX idx_queue_sla ON analyst_queues(sla_deadline)
  WHERE status IN ('pending', 'assigned', 'in_progress');
```

#### decisions

```sql
CREATE TABLE decisions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  application_id UUID NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  scoring_result_id UUID REFERENCES scoring_results(id),
  analyst_id UUID REFERENCES users(id),
  decision_type VARCHAR(30) NOT NULL,
  decision_outcome VARCHAR(20) NOT NULL,
  approved_terms JSONB,
  conditions JSONB,
  reasoning TEXT,
  reasoning_category VARCHAR(50),
  override_flag BOOLEAN NOT NULL DEFAULT false,
  override_direction VARCHAR(20),
  override_justification TEXT,
  override_approved_by UUID REFERENCES users(id),
  override_approved_at TIMESTAMPTZ,
  review_time_seconds INTEGER,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_decisions_application ON decisions(application_id);
CREATE INDEX idx_decisions_override ON decisions(override_flag)
  WHERE override_flag = true;
```

#### decision_thresholds

```sql
CREATE TABLE decision_thresholds (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
  name VARCHAR(100) NOT NULL,
  description TEXT,
  auto_approve_min INTEGER NOT NULL CHECK (auto_approve_min >= 0 AND auto_approve_min <= 1000),
  auto_decline_max INTEGER NOT NULL CHECK (auto_decline_max >= 0 AND auto_decline_max <= 1000),
  rules JSONB NOT NULL DEFAULT '{}',
  is_active BOOLEAN NOT NULL DEFAULT false,
  effective_from TIMESTAMPTZ NOT NULL,
  effective_to TIMESTAMPTZ,
  created_by UUID NOT NULL REFERENCES users(id),
  approved_by UUID REFERENCES users(id),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  CONSTRAINT chk_threshold_range CHECK (auto_decline_max < auto_approve_min)
);
```

#### audit_logs

```sql
CREATE TABLE audit_logs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  tenant_id UUID NOT NULL REFERENCES tenants(id),
  user_id UUID REFERENCES users(id),
  entity_type VARCHAR(50) NOT NULL,
  -- Types: application, decision, user, threshold, model, config
  entity_id UUID NOT NULL,
  action VARCHAR(50) NOT NULL,
  -- Actions: create, update, delete, view, export, login, logout
  old_value JSONB,
  new_value JSONB,
  change_summary TEXT,
  ip_address INET,
  user_agent TEXT,
  request_id UUID,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_audit_entity ON audit_logs(entity_type, entity_id);
CREATE INDEX idx_audit_created ON audit_logs(tenant_id, created_at DESC);
```

### 4.3 Database Functions

```sql
-- Auto-update timestamps
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ language 'plpgsql';

-- Calculate queue priority
CREATE OR REPLACE FUNCTION calculate_queue_priority(
  p_score INTEGER,
  p_loan_amount DECIMAL,
  p_is_vip BOOLEAN DEFAULT FALSE,
  p_sla_hours_remaining DECIMAL DEFAULT 24
) RETURNS INTEGER AS $$
DECLARE
  v_priority INTEGER := 50;
BEGIN
  IF p_is_vip THEN
    RETURN 10;
  END IF;

  IF p_loan_amount > 5000000 THEN
    v_priority := v_priority - 15;
  ELSIF p_loan_amount > 2000000 THEN
    v_priority := v_priority - 10;
  ELSIF p_loan_amount > 1000000 THEN
    v_priority := v_priority - 5;
  END IF;

  IF p_sla_hours_remaining < 2 THEN
    v_priority := v_priority - 20;
  ELSIF p_sla_hours_remaining < 4 THEN
    v_priority := v_priority - 10;
  ELSIF p_sla_hours_remaining < 8 THEN
    v_priority := v_priority - 5;
  END IF;

  RETURN GREATEST(1, LEAST(100, v_priority));
END;
$$ language 'plpgsql';

-- Get active threshold
CREATE OR REPLACE FUNCTION get_active_threshold(p_tenant_id UUID)
RETURNS TABLE (threshold_id UUID, auto_approve_min INTEGER, auto_decline_max INTEGER, rules JSONB) AS $$
BEGIN
  RETURN QUERY
  SELECT dt.id, dt.auto_approve_min, dt.auto_decline_max, dt.rules
  FROM decision_thresholds dt
  WHERE dt.tenant_id = p_tenant_id
    AND dt.is_active = true
    AND dt.effective_from <= NOW()
    AND (dt.effective_to IS NULL OR dt.effective_to > NOW())
  ORDER BY dt.effective_from DESC
  LIMIT 1;
END;
$$ language 'plpgsql';
```

-----

## 5. API Specification

### 5.1 Authentication

#### POST /auth/login

```json
// Request
{
  "email": "analyst@example.com",
  "password": "secure_password"
}

// Response 200
{
  "access_token": "eyJ...",
  "refresh_token": "eyJ...",
  "token_type": "bearer",
  "expires_in": 3600,
  "user": {
    "id": "uuid",
    "email": "analyst@example.com",
    "role": "analyst",
    "tenant_id": "uuid"
  }
}
```

### 5.2 Applications

#### POST /applications

```json
// Request
{
  "external_id": "APP-2024-001234",
  "applicant_data": {
    "personal": {
      "first_name": "Marko",
      "last_name": "Petrović",
      "date_of_birth": "1985-03-15",
      "national_id": "1503985710123",
      "email": "marko@email.com",
      "phone": "+381641234567"
    },
    "address": {
      "street": "Knez Mihailova 15",
      "city": "Beograd",
      "postal_code": "11000",
      "country": "RS"
    },
    "employment": {
      "status": "employed",
      "employer_name": "TechCorp d.o.o.",
      "job_title": "Software Developer",
      "years_employed": 3.5,
      "contract_type": "permanent"
    }
  },
  "financial_data": {
    "income": {
      "gross_monthly": 250000,
      "net_monthly": 180000,
      "income_verified": false
    },
    "expenses": {
      "monthly_obligations": 25000,
      "rent_mortgage": 35000
    },
    "assets": {
      "savings": 500000
    },
    "liabilities": {
      "existing_loans": 150000,
      "credit_card_debt": 30000
    }
  },
  "loan_request": {
    "amount": 1200000,
    "currency": "RSD",
    "term_months": 48,
    "purpose": "car"
  }
}

// Response 201
{
  "id": "uuid",
  "external_id": "APP-2024-001234",
  "status": "pending",
  "created_at": "2024-01-22T10:30:00Z"
}
```

#### GET /applications
Query params: status, from_date, to_date, page, page_size, sort_by, sort_order

#### GET /applications/{id}
Returns full application with scoring_result, queue_info, similar_cases

### 5.3 Queue

#### GET /queue

```json
// Response 200
{
  "items": [
    {
      "queue_id": "uuid",
      "application_id": "uuid",
      "applicant_name": "Marko Petrović",
      "score": 645,
      "loan_amount": 1200000,
      "priority": 35,
      "status": "pending",
      "sla_deadline": "2024-01-22T18:30:00Z",
      "wait_time_minutes": 125
    }
  ],
  "summary": {
    "total_pending": 45,
    "total_in_progress": 12,
    "approaching_sla": 8,
    "breached_sla": 2
  }
}
```

#### POST /queue/{id}/assign
#### POST /queue/{id}/start
#### POST /queue/{id}/release

### 5.4 Decisions

#### POST /decisions

```json
// Request - Standard Approval
{
  "application_id": "uuid",
  "decision_outcome": "approved",
  "approved_terms": {
    "amount": 1200000,
    "term_months": 48,
    "interest_rate": 9.5,
    "monthly_payment": 29800
  },
  "reasoning": "Stable employment, good savings, acceptable DTI.",
  "reasoning_category": "standard_approval"
}

// Request - Approval with Conditions
{
  "application_id": "uuid",
  "decision_outcome": "approved",
  "approved_terms": {
    "amount": 1000000,
    "term_months": 36,
    "interest_rate": 11.0
  },
  "conditions": [
    {"type": "documentation", "description": "Provide 3 months bank statements"},
    {"type": "reduced_amount", "description": "Reduced due to DTI"}
  ],
  "reasoning": "Approved with reduced terms due to risk factors."
}

// Request - Override
{
  "application_id": "uuid",
  "decision_outcome": "approved",
  "reasoning": "Long-standing customer relationship.",
  "override_flag": true,
  "override_justification": "Model recommended decline (score 465). Approving due to 10-year relationship and recent salary increase."
}
```

#### GET /decisions/pending-overrides
#### POST /decisions/{id}/approve-override

### 5.5 Analytics

#### GET /analytics/dashboard
Query params: from_date, to_date, granularity

```json
// Response 200
{
  "summary": {
    "total_applications": 1250,
    "auto_decision_rate": 0.57,
    "approval_rate": 0.68,
    "average_review_time_minutes": 6.8
  },
  "decision_breakdown": {
    "auto_approve": 456,
    "auto_decline": 215,
    "analyst_approve": 389,
    "analyst_decline": 120
  },
  "queue_metrics": {
    "current_pending": 45,
    "avg_wait_time_minutes": 95,
    "sla_compliance_rate": 0.94
  }
}
```

-----

## 6. Frontend Specification

### 6.1 Directory Structure

```text
src/
├── main.tsx
├── App.tsx
├── routes/
│   ├── __root.tsx
│   ├── index.tsx # Dashboard
│   ├── login.tsx
│   ├── applications/
│   │   ├── index.tsx # List
│   │   └── $applicationId.tsx # Detail
│   ├── queue/
│   │   ├── index.tsx # Queue list
│   │   └── $queueId.tsx # Workbench
│   ├── analytics/
│   │   └── index.tsx
│   └── settings/
├── components/
│   ├── ui/ # shadcn/ui
│   ├── layout/
│   │   ├── Header.tsx
│   │   ├── Sidebar.tsx
│   │   └── PageContainer.tsx
│   ├── workbench/
│   │   ├── WorkbenchLayout.tsx
│   │   ├── RiskSummaryCard.tsx
│   │   ├── KeyFactorsCard.tsx
│   │   ├── SimilarCasesCard.tsx
│   │   ├── DecisionPanel.tsx
│   │   ├── OverrideModal.tsx
│   │   └── common/
│   │       ├── DataTable.tsx
│   │       └── Pagination.tsx
├── hooks/
│   ├── useAuth.ts
│   ├── useApplications.ts
│   ├── useQueue.ts
│   ├── useDecisions.ts
├── api/
│   └── client.ts
├── stores/
│   └── authStore.ts
└── types/
```

### 6.2 Analyst Workbench Layout

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ HEADER: Case #ID | Applicant Name | Score Badge | Timer | Nav               │
├─────────────────────────────────────────────────────────────────────────────┤
│                           │ ┌─── LEFT PANEL (60%) ───────────────────┐     │
│                           │ │                                         │     │
│                           │ │ ┌─── RISK SUMMARY ─────────────────┐    │     │
│                           │ │ │ Score Gauge (0-1000)              │    │     │
│                           │ │ │ Risk Category                     │    │     │
│                           │ │ │ Similar Cases Stats               │    │     │
│                           │ │ └──────────────────────────────────┘    │     │
│                           │ │                                         │     │
│                           │ │ ┌─── KEY FACTORS ──────────────────┐    │     │
│                           │ │ │ ▲ Positive factors (green)        │    │     │
│                           │ │ │ ▼ Negative factors (red)          │    │     │
│                           │ │ │ Impact bars                       │    │     │
│                           │ │ └──────────────────────────────────┘    │     │
│                           │ │                                         │     │
│                           │ │ ┌─── TABS ─────────────────────────┐    │     │
│                           │ │ │ [Applicant][Financial][Credit]    │    │     │
│                           │ │ │ Detailed data display             │    │     │
│                           │ │ └──────────────────────────────────┘    │     │
│                           │ │                                         │     │
│                           │ │ ┌─── SIMILAR CASES ────────────────┐    │     │
│                           │ │ │ Historical comparison table       │    │     │
│                           │ │ └──────────────────────────────────┘    │     │
│                           │ └─────────────────────────────────────────┘     │
│ ┌─── RIGHT PANEL (40%) ────┐                                                │
│ │ ┌─── DECISION PANEL ──┐  │                                                │
│ │ ○ APPROVE             │  │                                                │
│ │ ○ APPROVE w/cond      │  │                                                │
│ │ ○ DECLINE             │  │                                                │
│ │ ○ REQUEST DOCS        │  │                                                │
│ │ Reasoning:            │  │                                                │
│ │ [________________]    │  │                                                │
│ │ □ Override model      │  │                                                │
│ │ [SUBMIT DECISION]     │  │                                                │
│ └───────────────────────┘  │                                                │
│ ┌─── QUICK ACTIONS ───┐    │                                                │
│ │ Release | Help | Flag│    │                                                │
│ └──────────────────────┘    │                                                │
│ └──────────────────────────┘                                                │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 6.3 TanStack Query Hooks

```ts
// hooks/useApplications.ts
export const applicationKeys = {
  all: ['applications'] as const,
  lists: () => [...applicationKeys.all, 'list'] as const,
  list: (filters: Filters) => [...applicationKeys.lists(), filters] as const,
  detail: (id: string) => [...applicationKeys.all, 'detail', id] as const,
};

export function useApplications(filters: Filters) {
  return useQuery({
    queryKey: applicationKeys.list(filters),
    queryFn: () => api.applications.list(filters),
    placeholderData: keepPreviousData,
  });
}

export function useApplication(id: string) {
  return useQuery({
    queryKey: applicationKeys.detail(id),
    queryFn: () => api.applications.get(id),
    enabled: !!id,
  });
}

// hooks/useQueue.ts
export function useQueue(filters: QueueFilters) {
  return useQuery({
    queryKey: ['queue', 'list', filters],
    queryFn: () => api.queue.list(filters),
    refetchInterval: 30000, // Auto-refresh
  });
}

export function useSubmitDecision() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: api.decisions.create,
    onSuccess: (decision) => {
      queryClient.invalidateQueries({ queryKey: ['applications'] });
      queryClient.invalidateQueries({ queryKey: ['queue'] });
      toast.success('Decision submitted');
    },
  });
}
```

-----

## 7. ML Pipeline

### 7.1 Feature Engineering

|Feature |Type |Calculation |
|---------------------|-----|---------------------------------------|
|dti_ratio |float|total_debt / net_monthly_income |
|loan_to_income |float|loan_amount / (net_monthly_income × 12)|
|payment_to_income |float|monthly_payment / net_monthly_income |
|credit_history_months|int |months since first account |
|employment_years |float|years at current employer |
|employment_stability |float|tenure × contract_type_score |
|savings_ratio |float|savings / loan_amount |
|existing_debt_ratio |float|existing_loans / loan_amount |

### 7.2 Model Architecture

```py
# Ensemble Model
ensemble = VotingClassifier(
  estimators=[
    ('xgb', XGBClassifier(n_estimators=200, max_depth=6)), # weight: 0.5
    ('lr', LogisticRegression(C=1.0)), # weight: 0.3
    ('nn', MLPClassifier(hidden_layer_sizes=(64, 32))) # weight: 0.2
  ],
  voting='soft',
  weights=[0.5, 0.3, 0.2]
)
```

### 7.3 Scoring Service

```py
class ScoringService:
  def score(self, features: dict) -> dict:
    X = self.preprocessor.transform(features)
    probability_default = self.model.predict_proba(X)[0, 1]
    score = int(1000 * (1 - probability_default)) # Higher = lower risk

    shap_values = self.explainer.shap_values(X)
    top_factors = self._extract_top_factors(features, shap_values)

    return {
      'score': score,
      'probability_default': probability_default,
      'risk_category': self._get_category(score),
      'shap_values': shap_values,
      'top_factors': top_factors
    }

  def _get_category(self, score: int) -> str:
    if score >= 750: return 'very_low'
    if score >= 650: return 'low'
    if score >= 550: return 'medium'
    if score >= 450: return 'high'
    return 'very_high'
```

### 7.4 Routing Logic

```py
class DecisionRouter:
  def route(self, score: int, loan_amount: float, loan_purpose: str) -> tuple:
    # Check forced human review
    if loan_amount > self.config.max_loan_amount_auto:
      return ('human_review', 'high_value_loan')

    if loan_purpose in self.config.require_review_purposes:
      return ('human_review', f'purpose:{loan_purpose}')

    # Score-based routing
    if score >= self.config.auto_approve_min:
      return ('auto_approve', 'score_above_threshold')
    if score <= self.config.auto_decline_max:
      return ('auto_decline', 'score_below_threshold')

    return ('human_review', 'borderline_score')
```

-----

## 8. Security & Compliance

### 8.1 Authentication
- JWT tokens with 1-hour access / 7-day refresh
- Password hashing: bcrypt
- Token blacklist in Redis

### 8.2 Authorization (RBAC)

|Role |Permissions |
|--------------|-------------------------------------------------------|
|admin |All permissions |
|senior_analyst|View, score, decide, approve overrides, analytics |
|analyst |View, decide (override needs approval), basic analytics|
|readonly |View only |
|api_consumer |Create applications, view decisions |

### 8.3 Data Protection
- PII encrypted at rest (pgcrypto)
- PII masked in logs
- Audit trail for all changes
- Data retention: 7 years (applications/decisions), 10 years (audit)

### 8.4 GDPR Compliance
- Article 22: Human review available (HITL by design)
- Right to Explanation: SHAP-based explanations
- Data Access/Deletion: Supported via admin endpoints
- Audit Trail: Complete decision history

-----

## 9. Infrastructure

### 9.1 Docker Compose

```yaml
version: '3.9'
services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: hitl_credit
      POSTGRES_USER: hitl
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "hitl"]

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

  api:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    environment:
      DATABASE_URL: postgresql+asyncpg://hitl:${POSTGRES_PASSWORD}@postgres/hitl_credit
      REDIS_URL: redis://redis:6379/0
      SECRET_KEY: ${SECRET_KEY}
      ML_SERVICE_URL: http://ml-service:8001
    ports:
      - "8000:8000"
    depends_on:
      postgres: { condition: service_healthy }
      redis: { condition: service_healthy }

  ml-service:
    build:
      context: .
      dockerfile: docker/ml-service/Dockerfile
    ports:
      - "8001:8001"

  worker:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    command: celery -A src.worker worker -l INFO

  scheduler:
    build:
      context: .
      dockerfile: docker/backend/Dockerfile
    command: celery -A src.worker beat -l INFO

  frontend:
    build:
      context: ./frontend
      dockerfile: ../docker/frontend/Dockerfile
    ports:
      - "3000:80"

  traefik:
    image: traefik:v3.0
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro

  prometheus:
    image: prom/prometheus:v2.48.0
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:10.3.0
    ports:
      - "3001:3000"

volumes:
  postgres_data:
  redis_data:
```

### 9.2 Monitoring Metrics

|Metric |Type |Description |
|------------------------|---------|-----------------------------|
|applications_total |counter |Total applications by status |
|decisions_total |counter |Decisions by type and outcome|
|scoring_duration_seconds|histogram|ML scoring latency |
|queue_size |gauge |Current queue size |
|queue_wait_time_seconds |histogram|Time in queue |
|sla_breaches_total |counter |SLA violations |

-----

## 10. Development Phases
See [PHASES.md](./PHASES.md) for detailed phase breakdown with TODOs.

### Phase Summary

|Phase |Duration|Focus |Parallelizable |
|------------------------|--------|------------------------------|---------------------|
|**1. Foundation** |4 weeks |Infrastructure, DB, Auth |No |
|**2. Core Backend** |5 weeks |Applications, Queue, Decisions|No |
|**3. ML Pipeline** |4 weeks |Features, Model, Scoring |Yes (with Phase 2) |
|**4. Frontend Core** |5 weeks |Setup, Auth UI, Lists |Yes (with Phases 2-3)|
|**5. Analyst Workbench**|4 weeks |Review UI, Decision Panel |No |
|**6. Analytics** |3 weeks |Dashboard, Monitoring |Yes (with Phase 5) |
|**7. Testing** |3 weeks |Integration, E2E, Security |No |
|**8. Production** |2 weeks |Deploy, CI/CD, Launch |No |

Total: 16-20 weeks (with parallel execution)

-----

## Appendices

### A. Glossary

|Term|Definition |
|----|-----------------------------|
|HITL|Human-in-the-Loop |
|DTI |Debt-to-Income ratio |
|PD |Probability of Default |
|SHAP|SHapley Additive exPlanations|
|SLA |Service Level Agreement |
|PSI |Population Stability Index |

### B. API Error Codes

|Code|Description |
|----|------------------------------------|
|400 |Bad Request - Invalid input |
|401 |Unauthorized - Invalid/missing token|
|403 |Forbidden - Insufficient permissions|
|404 |Not Found |
|422 |Validation Error |
|429 |Rate Limited |
|500 |Internal Server Error |

-----

Document Version: 1.0.0  
Last Updated: 2025-01-22
