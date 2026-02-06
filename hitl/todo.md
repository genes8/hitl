# HITL Credit Approval System - Development Phases & TODOs

This document contains all development tasks organized by phase, ready for engineer handoff.

-----

## Phase Overview

PHASE 1 ──────► PHASE 2 ──────► PHASE 5 ──────► PHASE 7 ──────► PHASE 8
Foundation      Core Backend     Workbench       Testing         Production
(4 weeks)       (5 weeks)        (4 weeks)       (3 weeks)       (2 weeks)
   │               │
   ├── PHASE 3 ────┘ (Parallel)
   │    ML Pipeline
   │    (4 weeks)
   │
   └── PHASE 4 ────► PHASE 6 (Parallel)
        Frontend       Analytics
        (5 weeks)      (3 weeks)

-----

# PHASE 1: Foundation (4 weeks)

## Sprint 1.1: Infrastructure Setup (Week 1)

### TODO-1.1.1: Docker Environment Setup
Assignee: DevOps Engineer
Priority: P0 (Critical)
Dependencies: None
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [x] Create project directory structure:

  ```text
  /
  ├── docker/
  │   ├── backend/Dockerfile
  │   ├── ml-service/Dockerfile
  │   ├── frontend/Dockerfile
  │   ├── postgres/init.sql
  │   └── nginx/nginx.conf
  ├── src/
  ├── frontend/
  ├── docker-compose.yml
  ├── docker-compose.override.yml
  └── .env.example
  ```

- [x] Write base Dockerfile for backend (Python 3.11, FastAPI)
- [x] Write Dockerfile for ML service (Python 3.11, scikit-learn, XGBoost) (placeholder)
- [x] Write Dockerfile for frontend (Node 20, multi-stage build) (placeholder)
- [ ] Create docker-compose.yml with services: postgres, redis, api, ml-service, worker, scheduler, frontend, traefik, prometheus, grafana
- [ ] Configure PostgreSQL with health checks
- [ ] Configure Redis with persistence
- [ ] Set up Traefik reverse proxy with auto-SSL
- [x] Create .env.example with all environment variables (initial)
- [x] Create docker-compose.override.yml for dev (volume mounts, hot reload)
- [ ] Test: docker-compose up starts all services
- [ ] Test: All health checks pass
- [ ] Document Docker setup in README.md

Definition of Done:
- All containers start successfully
- Health checks pass
- Network communication works between services

-----

### TODO-1.1.2: PostgreSQL Schema Implementation
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.1.1
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [x] Initialize Alembic migration framework
- [x] Create migration: 001_create_tenants.py (included in 001_create_tenants_users)
- [x] Create migration: 002_create_users.py (included in 001_create_tenants_users)
- [x] Create migration: 003_create_applications.py (in 002_create_core_tables)
- [x] Create migration: 004_create_scoring_results.py (in 002_create_core_tables)
- [x] Create migration: 005_create_analyst_queues.py (in 002_create_core_tables)
- [x] Create migration: 006_create_decisions.py (in 002_create_core_tables)
- [x] Create migration: 007_create_decision_thresholds.py (in 003_thresholds_audit_and_triggers)
- [x] Create migration: 008_create_audit_logs.py (in 003_thresholds_audit_and_triggers)
- [x] Create migration: 009_create_model_registry.py (in 004_remaining_tables)
- [x] Create migration: 010_create_similar_cases.py (in 004_remaining_tables)
- [x] Create migration: 011_create_notifications.py (in 004_remaining_tables)
- [x] Create migration: 012_create_loan_outcomes.py (in 004_remaining_tables)
- [ ] Create all indexes as specified in PRD
- [x] Create trigger: update_updated_at_column()
- [x] Apply trigger to all tables with updated_at (tenants/users/applications/analyst_queues/decision_thresholds)
- [x] Create function: sync_application_status()
- [x] Create function: calculate_queue_priority()
- [x] Create function: get_active_threshold()
- [x] Create view: v_daily_decision_summary
- [x] Create view: v_analyst_performance
- [x] Create view: v_queue_metrics
- [x] Write seed data script for development
- [x] Test: All migrations run successfully (up/down) (CI smoke test)
- [x] Test: Constraints work correctly
- [x] Test: Functions return expected results

Definition of Done:
- Database schema matches PRD specification
- All migrations reversible
- Functions and views working

-----

### TODO-1.1.3: FastAPI Project Structure
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.1.1
Estimated Hours: 16
Can be parallelized: Yes (with TODO-1.1.2)

Tasks:
- [x] Initialize project with Poetry (pyproject.toml) (minimal pyproject scaffold)
- [x] Create src/ directory structure:

  ```text
  src/
  ├── __init__.py
  ├── main.py
  ├── config.py
  ├── database.py
  ├── api/
  │   ├── __init__.py
  │   ├── deps.py
  │   └── v1/
  │       ├── __init__.py
  │       ├── router.py
  │       └── endpoints/
  ├── models/
  ├── schemas/
  ├── crud/
  ├── services/
  └── utils/
  ```

- [x] Configure Pydantic Settings (BaseSettings class)
- [x] Set up SQLAlchemy async engine
- [x] Create async session dependency
- [ ] Create base CRUD class with generic methods
- [x] Set up structured logging with request context (lightweight access logging in middleware)
- [x] Configure CORS middleware (configurable origins)
- [x] Create health check endpoint: GET /health
- [ ] Create global exception handlers (400, 401, 403, 404, 500)
- [x] Create request ID middleware
- [x] Configure OpenAPI documentation (/docs, /redoc) (FastAPI defaults)
- [ ] Write pytest configuration (conftest.py)
- [x] Write first test: test_health_check
- [x] Test: Server starts without errors (CI)
- [x] Test: /health returns 200
- [x] Test: /docs accessible (FastAPI defaults)

Definition of Done:
- FastAPI server runs
- Health check works
- OpenAPI docs accessible

-----

## Sprint 1.2: Authentication System (Week 2)

### TODO-1.2.1: JWT Authentication Backend
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.1.2, TODO-1.1.3
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Create src/auth/ module
- [ ] Implement JWTHandler class:
  - [ ] create_access_token(data: dict) -> str
  - [ ] create_refresh_token(data: dict) -> str
  - [ ] verify_token(token: str) -> dict
  - [ ] decode_token(token: str) -> dict
- [ ] Configure bcrypt password hashing
- [ ] Create User SQLAlchemy model
- [ ] Create Pydantic schemas: UserCreate, UserRead, UserLogin, TokenResponse
- [ ] Implement UserCRUD class
- [ ] Create POST /auth/login endpoint
- [ ] Create POST /auth/refresh endpoint
- [ ] Create POST /auth/logout endpoint (blacklist token)
- [ ] Create GET /auth/me endpoint
- [ ] Implement get_current_user FastAPI dependency
- [ ] Implement token blacklist in Redis
- [ ] Test: Login with valid credentials returns tokens
- [ ] Test: Login with invalid credentials returns 401
- [ ] Test: Access token expires correctly
- [ ] Test: Refresh token works
- [ ] Test: Blacklisted tokens rejected

Definition of Done:
- Full authentication flow working
- Token expiration handled
- Tests pass

-----

### TODO-1.2.2: RBAC Implementation
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.2.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create Permission enum with all permissions:

  ```py
  class Permission(Enum):
    APPLICATION_VIEW = "application:view"
    APPLICATION_CREATE = "application:create"
    APPLICATION_SCORE = "application:score"
    QUEUE_VIEW = "queue:view"
    QUEUE_ASSIGN = "queue:assign"
    DECISION_VIEW = "decision:view"
    DECISION_CREATE = "decision:create"
    DECISION_OVERRIDE = "decision:override"
    DECISION_APPROVE_OVERRIDE = "decision:approve_override"
    ANALYTICS_VIEW = "analytics:view"
    CONFIG_MANAGE = "config:manage"
    USER_MANAGE = "user:manage"
    AUDIT_VIEW = "audit:view"
  ```

- [ ] Create ROLE_PERMISSIONS mapping:
  - admin: All permissions
  - senior_analyst: View, score, decide, approve overrides, analytics
  - analyst: View, decide (override needs approval), basic analytics
  - readonly: View only
  - api_consumer: Create applications, view decisions
- [ ] Implement RBACChecker class
- [ ] Create require_permission() FastAPI dependency
- [ ] Create require_role() FastAPI dependency
- [ ] Support custom permissions override per user
- [ ] Include permissions in JWT payload
- [ ] Test: Admin has all permissions
- [ ] Test: Analyst blocked from admin-only endpoints
- [ ] Test: Custom permissions work

Definition of Done:
- Role-based access control working
- Permission checks on all endpoints
- Tests pass

-----

### TODO-1.2.3: Multi-tenancy Setup
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.2.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create Tenant SQLAlchemy model
- [ ] Create TenantCreate, TenantRead schemas
- [ ] Implement TenantCRUD class
- [ ] Create get_current_tenant() dependency
- [ ] Add tenant_id filter to all database queries
- [ ] Create tenant context middleware
- [ ] Implement tenant isolation in base CRUD
- [ ] Create tenant management endpoints (admin only):
  - [ ] POST /admin/tenants
  - [ ] GET /admin/tenants
  - [ ] GET /admin/tenants/{id}
  - [ ] PATCH /admin/tenants/{id}
- [ ] Test: Users can only access own tenant data
- [ ] Test: Cross-tenant queries blocked
- [ ] Test: Admin can manage tenants

Definition of Done:
- Data completely isolated between tenants
- Tests pass

-----

## Sprint 1.3: Core Models & Audit (Weeks 3-4)

### TODO-1.3.1: SQLAlchemy Models
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.2.3
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Create Application model with JSONB columns
- [ ] Create ScoringResult model
- [ ] Create AnalystQueue model
- [ ] Create Decision model
- [ ] Create DecisionThreshold model
- [ ] Create SimilarCase model
- [ ] Create Notification model
- [ ] Create ModelRegistry model
- [ ] Create LoanOutcome model
- [ ] Create AuditLog model
- [ ] Define all relationships (ForeignKey, relationship())
- [ ] Add hybrid properties for computed fields
- [ ] Create model factory for testing (using factory_boy)
- [ ] Test: Models map to database correctly
- [ ] Test: Relationships work

Definition of Done:
- All models complete and tested

-----

### TODO-1.3.2: Pydantic Schemas
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.3.1
Estimated Hours: 20
Can be parallelized: Yes (with TODO-1.3.1)

Tasks:
- [ ] Create nested schemas for applicant_data:
  - [ ] PersonalInfo, Address, Employment
- [ ] Create nested schemas for financial_data:
  - [ ] Income, Expenses, Assets, Liabilities
- [ ] Create ApplicationCreate schema
- [ ] Create ApplicationRead schema
- [ ] Create ApplicationList schema (minimal fields)
- [ ] Create ScoringResultRead schema with top_factors
- [ ] Create AnalystQueueRead schema
- [ ] Create DecisionCreate schema (all decision types)
- [ ] Create DecisionRead schema
- [ ] Create ThresholdCreate/Read schemas
- [ ] Create analytics response schemas
- [ ] Create PaginatedResponse[T] generic schema
- [ ] Add field validators (amounts > 0, valid dates, etc.)
- [ ] Add OpenAPI examples
- [ ] Test: Schema validation works

Definition of Done:
- All schemas complete with validation
- Examples show in API docs

-----

### TODO-1.3.3: Audit Logging System
Assignee: Backend Engineer
Priority: P1
Dependencies: TODO-1.3.1
Estimated Hours: 16
Can be parallelized: Yes (with TODO-1.3.2)

Tasks:
- [ ] Create AuditLogger class
- [ ] Create PIIHandler class for masking sensitive data:
  - [ ] Mask email: ***@domain.com
  - [ ] Mask phone: +381******67
  - [ ] Mask national_id: 1503*********
  - [ ] Mask names: Ma***ć
- [ ] Create audit middleware for automatic logging
- [ ] Log on create operations (new_value only)
- [ ] Log on update operations (old_value, new_value, diff)
- [ ] Log on delete operations (old_value only)
- [ ] Create audit query endpoints:
  - [ ] GET /audit/logs
  - [ ] GET /audit/logs/{entity_type}/{entity_id}
- [ ] Implement audit log filtering (by entity, user, date range)
- [ ] Test: All changes logged
- [ ] Test: PII masked in logs
- [ ] Test: Query endpoints work

Definition of Done:
- Complete audit trail
- PII masked
- No performance impact

-----

### TODO-1.3.4: Base CRUD Operations
Assignee: Backend Engineer
Priority: P0
Dependencies: TODO-1.3.2
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create generic BaseCRUD[Model, CreateSchema, UpdateSchema] class:
  - [ ] create(session, obj_in) -> Model
  - [ ] get(session, id) -> Model | None
  - [ ] get_multi(session, skip, limit, filters) -> list[Model]
  - [ ] update(session, db_obj, obj_in) -> Model
  - [ ] delete(session, id) -> Model
- [ ] Add tenant_id filtering to all methods
- [ ] Add audit logging integration
- [ ] Create ApplicationCRUD extending BaseCRUD
- [ ] Create DecisionCRUD extending BaseCRUD
- [ ] Create QueueCRUD extending BaseCRUD
- [ ] Create ThresholdCRUD extending BaseCRUD
- [ ] Test: CRUD operations work
- [ ] Test: Tenant isolation enforced
- [ ] Test: Audit logs created

Definition of Done:
- CRUD operations work for all entities
- Tests pass

-----

# PHASE 2: Core Backend (5 weeks)

## Sprint 2.1: Application Management (Weeks 5-6)

### TODO-2.1.1: Application Intake API
Assignee: Backend Engineer A
Priority: P0
Dependencies: Phase 1 Complete
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [x] Create POST /applications endpoint
- [x] Validate required fields in applicant_data
- [x] Validate required fields in financial_data
- [x] Validate loan_request fields
- [x] Calculate derived fields:
  - [x] dti_ratio = (monthly_obligations + existing_loans_payment) / net_monthly_income
  - [x] loan_to_income = loan_amount / (net_monthly_income * 12)
  - [x] payment_to_income = estimated_payment / net_monthly_income
- [x] Set initial status = ‘pending’
- [x] Generate external_id if not provided
- [x] Set expires_at (default: 30 days)
- [x] Emit Celery task: score_application
- [x] Create audit log entry
- [x] Return 201 with application ID
- [x] Test: Valid application created
- [x] Test: Validation errors return 422
- [x] Test: Derived fields calculated correctly

Definition of Done:
- Applications can be created via API
- Scoring triggered automatically

-----

### TODO-2.1.2: Application Listing & Filtering
Assignee: Backend Engineer A
Priority: P0
Dependencies: TODO-2.1.1
Estimated Hours: 16
Can be parallelized: Yes (with TODO-2.1.3)

Tasks:
- [x] Create GET /applications endpoint
- [x] Implement query parameters:
  - [x] status: string (pending, scoring, review, approved, declined)
  - [x] from_date: datetime
  - [x] to_date: datetime
  - [x] search: string (external_id, applicant name)
  - [x] sort_by: string (created_at, amount, score)
  - [x] sort_order: asc | desc
  - [x] page: int (default 1)
  - [x] page_size: int (default 20, max 100)
- [x] Implement cursor pagination option
- [x] Optimize query with proper indexes
- [x] Return paginated response with total count
- [x] Test: Filters work correctly
- [x] Test: Pagination returns correct pages
- [x] Test: Response time < 100ms for 10k records

Definition of Done:
- Listing endpoint complete with all filters

-----

### TODO-2.1.3: Application Detail & Updates
Assignee: Backend Engineer A
Priority: P0
Dependencies: TODO-2.1.1
Estimated Hours: 16
Can be parallelized: Yes (with TODO-2.1.2)

Tasks:
- [x] Create GET /applications/{id} endpoint
- [x] Include scoring_result (if exists)
- [x] Include queue_info (if in queue)
- [x] Include decision_history (all decisions)
- [ ] Include similar_cases (if available)
- [ ] Create PATCH /applications/{id} endpoint
- [ ] Validate status transitions:
  - [ ] pending -> cancelled ✓
  - [ ] pending -> scoring ✓ (internal only)
  - [ ] scoring -> review ✓ (internal only)
  - [ ] scoring -> approved ✓ (internal only)
  - [ ] scoring -> declined ✓ (internal only)
  - [ ] review -> approved ✓
  - [ ] review -> declined ✓
  - [ ] [others blocked]
- [ ] Only allow field updates on pending applications
- [ ] Create DELETE /applications/{id} endpoint (sets status = cancelled)
- [ ] Test: Detail includes all related data
- [ ] Test: Invalid transitions blocked
- [ ] Test: Cancel works

Definition of Done:
- Detail and update endpoints complete

-----

## Sprint 2.2: Queue Management (Week 7)

### TODO-2.2.1: Queue Core Logic
Assignee: Backend Engineer A
Priority: P0
Dependencies: TODO-2.1.3
Estimated Hours: 20
Can be parallelized: No

Tasks:
- [ ] Create QueueService class
- [ ] Implement create_queue_entry():
  - [ ] Calculate priority using calculate_queue_priority()
  - [ ] Set SLA deadline (default: 8 hours from creation)
  - [ ] Store score_at_routing
  - [ ] Store routing_reason
- [ ] Create GET endpoint
- [ ] Query parameters:
  - [ ] status: pending | assigned | in_progress
  - [ ] analyst_id: UUID
  - [ ] priority_max: int
  - [ ] sort_by: priority | created_at | sla_deadline
- [ ] Create GET /queue/summary endpoint: { "total_pending": 45,"total_assigned": 8, "total_in_progress": 12, "approaching_sla": 8, "breached_sla": 2, "by_priority": {"high": 10, "medium": 30, "low": 5} }
- [ ] Test: Queue entries created correctly
- [ ] Test: Priority calculated per spec
- [ ] Test: Summary returns correct counts

Definition of Done:
- Queue creation and listing working

-----

### TODO-2.2.2: Queue Assignment & Workflow
Assignee: Backend Engineer A
Priority: P0
Dependencies: TODO-2.2.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create POST /queue/{id}/assign endpoint:
  - [ ] Validate analyst has queue:assign permission
  - [ ] Check analyst workload (max 5 active cases)
  - [ ] Set analyst_id, assigned_at, status = ‘assigned’
- [ ] Create POST /queue/{id}/start endpoint:
  - [ ] Record started_at timestamp
  - [ ] Set status = ‘in_progress’
  - [ ] Update application status = ‘review’
- [ ] Create POST /queue/{id}/release endpoint:
  - [ ] Clear analyst_id, assigned_at, started_at
  - [ ] Set status = ‘pending’
  - [ ] Recalculate priority (lower due to release)
- [ ] Create Celery task: auto_assign_cases
  - [ ] Run every 5 minutes
  - [ ] Find pending cases approaching SLA
  - [ ] Assign to available analysts based on workload
- [ ] Test: Assignment works
- [ ] Test: Workload limits enforced
- [ ] Test: Release resets correctly

Definition of Done:
- Full queue workflow functional

-----

### TODO-2.2.3: SLA Management
Assignee: Backend Engineer A
Priority: P1
Dependencies: TODO-2.2.2
Estimated Hours: 12
Can be parallelized: Yes (with other Sprint 2.2 tasks)

Tasks:
- [ ] Create Celery task: check_sla_status
  - [ ] Run every minute via Celery Beat
  - [ ] Find cases approaching SLA (< 2 hours)
  - [ ] Find cases breaching SLA (deadline passed)
- [ ] Mark breached cases: sla_breached = true
- [ ] Create notifications for SLA warnings (2 hours before)
- [ ] Create notifications for SLA breaches
- [ ] Implement escalation on breach (notify senior analyst)
- [ ] Create GET /queue/sla-metrics endpoint
- [ ] Test: SLA breaches detected within 2 minutes
- [ ] Test: Notifications sent

Definition of Done:
- SLA monitoring complete

-----

## Sprint 2.3: Decision Processing (Weeks 8-9)

### TODO-2.3.1: Decision Submission
Assignee: Backend Engineer B
Priority: P0
Dependencies: TODO-2.2.2
Estimated Hours: 24
Can be parallelized: Yes (with Phase 3)

Tasks:
- [ ] Create POST /decisions endpoint
- [ ] Validate request based on decision_outcome:
  - [ ] approved: approved_terms required
  - [ ] approved (with conditions): conditions array required
  - [ ] declined: reasoning required
- [ ] Determine decision_type:
  - [ ] auto_approve (from scoring task)
  - [ ] auto_decline (from scoring task)
  - [ ] analyst_approve
  - [ ] analyst_decline
  - [ ] analyst_approve_with_conditions
- [ ] Calculate review_time_seconds (now - queue.started_at)
- [ ] Update application status
- [ ] Complete queue entry (status = ‘completed’, completed_at)
- [ ] Create audit log
- [ ] Emit event: decision_created
- [ ] Trigger notification to applicant (if configured)
- [ ] Test: All decision types work
- [ ] Test: Validation enforced
- [ ] Test: Application status updated

Definition of Done:
- Decision submission working for all types

-----

### TODO-2.3.2: Override Management
Assignee: Backend Engineer B
Priority: P0
Dependencies: TODO-2.3.1
Estimated Hours: 20
Can be parallelized: No

Tasks:
- [ ] Detect override condition:
  - [ ] Model said approve (score >= threshold), analyst declines
  - [ ] Model said decline (score <= threshold), analyst approves
- [ ] Set override_flag = true
- [ ] Set override_direction: model_approve_analyst_decline | model_decline_analyst_approve
- [ ] Require override_justification (min 50 characters)
- [ ] Create GET /decisions/pending-overrides endpoint
  - [ ] Return decisions where override_flag = true AND override_approved_by IS NULL
  - [ ] Require senior_analyst or admin role
- [ ] Create POST /decisions/{id}/approve-override endpoint
  - [ ] Require decision:approve_override permission
  - [ ] Set override_approved_by, override_approved_at
  - [ ] Finalize the decision
- [ ] Create POST /decisions/{id}/reject-override endpoint
  - [ ] Reject override, decision reverted
  - [ ] Notify analyst
- [ ] Test: Override detected correctly
- [ ] Test: Justification required
- [ ] Test: Approval workflow works

Definition of Done:
- Override workflow complete

-----

### TODO-2.3.3: Conditions Management
Assignee: Backend Engineer B
Priority: P1
Dependencies: TODO-2.3.1
Estimated Hours: 12
Can be parallelized: Yes

Tasks:
- [ ] Define condition types enum:
  - [ ] documentation (bank statements, pay stubs)
  - [ ] collateral (vehicle registration, property deed)
  - [ ] guarantor (guarantor information)
  - [ ] reduced_amount (approved for less)
  - [ ] reduced_term (shorter loan period)
  - [ ] other
- [ ] Validate conditions structure in decision
- [ ] Store conditions in decision.conditions JSONB
- [ ] Create condition tracking table (optional v1.1)
- [ ] Create endpoint to mark condition fulfilled
- [ ] Test: Conditions stored correctly

Definition of Done:
- Conditional approvals working

-----

## Sprint 2.4: Background Workers (Week 9)

### TODO-2.4.1: Celery Configuration
Assignee: Backend Engineer B
Priority: P0
Dependencies: Phase 1 Complete
Estimated Hours: 12
Can be parallelized: Yes (early start possible)

Tasks:
- [ ] Create src/worker/ module
- [ ] Configure Celery with Redis broker
- [ ] Define task queues:
  - [ ] default: General tasks
  - [ ] scoring: ML scoring tasks (separate for scaling)
  - [ ] notifications: Email/webhook delivery
- [ ] Configure retry policies:
  - [ ] max_retries: 3
  - [ ] default_retry_delay: 60
  - [ ] exponential_backoff: True
- [ ] Configure Celery Beat scheduler
- [ ] Create base task class with:
  - [ ] Automatic logging
  - [ ] Error handling
  - [ ] Metrics emission
- [ ] Configure Redis result backend
- [ ] Create health check task
- [ ] Test: Tasks execute correctly
- [ ] Test: Retries work
- [ ] Test: Beat schedules tasks

Definition of Done:
- Celery infrastructure ready

-----

### TODO-2.4.2: Scoring Worker Task
Assignee: Backend Engineer B
Priority: P0
Dependencies: TODO-2.4.1, TODO-3.3.1 (ML Service)
Estimated Hours: 16
Can be parallelized: No (requires ML Service)

Tasks:
- [ ] Create task: score_application(application_id)
- [ ] Fetch application data
- [ ] Extract features for scoring
- [ ] Call ML service: POST /score
- [ ] Handle ML service errors (retry 3x)
- [ ] Store ScoringResult in database
- [ ] Get active threshold configuration
- [ ] Call routing logic
- [ ] If human_review: create queue entry
- [ ] If auto_approve: create Decision
- [ ] If auto_decline: create Decision
- [ ] Update application status
- [ ] Emit event: scoring_completed
- [ ] Test: Scoring completes reliably
- [ ] Test: Errors retried
- [ ] Test: Routing decision applied

Definition of Done:
- Automated scoring working end-to-end

-----

### TODO-2.4.3: Notification Worker
Assignee: Backend Engineer B
Priority: P1
Dependencies: TODO-2.4.1
Estimated Hours: 12
Can be parallelized: Yes

Tasks:
- [ ] Create task: send_notification(notification_id)
- [ ] Implement email channel (SMTP/SendGrid)
- [ ] Implement in-app channel (create Notification record)
- [ ] Implement webhook channel (HTTP POST)
- [ ] Create notification templates:
  - [ ] case_assigned: “New case assigned: {external_id}”
  - [ ] sla_warning: “SLA approaching for {external_id}”
  - [ ] decision_required: “Override pending approval”
- [ ] Handle delivery failures (log and mark)
- [ ] Track delivered_channels in Notification record
- [ ] Test: Notifications sent correctly
- [ ] Test: Multiple channels work
- [ ] Test: Failures tracked

Definition of Done:
- Notification system working

-----

# PHASE 3: ML Pipeline (4 weeks) - PARALLEL with Phase 2

## Sprint 3.1: Feature Engineering (Week 5)

### TODO-3.1.1: Feature Extraction
Assignee: ML Engineer
Priority: P0
Dependencies: Phase 1 Complete
Estimated Hours: 24
Can be parallelized: Yes (with Phase 2)

Tasks:
- [ ] Create src/ml/features/ module
- [ ] Create FeatureExtractor class
- [ ] Implement feature calculations:
  - [ ] dti_ratio = total_monthly_debt / net_monthly_income
  - [ ] loan_to_income = loan_amount / annual_net_income
  - [ ] payment_to_income = estimated_payment / net_monthly_income
  - [ ] employment_stability = years_employed * contract_type_multiplier
  - [ ] savings_ratio = savings / loan_amount
  - [ ] existing_debt_ratio = existing_loans / loan_amount
  - [ ] credit_utilization (if credit data available)
- [ ] Handle missing values:
  - [ ] Numeric: median imputation
  - [ ] Categorical: ‘unknown’ category
- [ ] Document all features with formulas
- [ ] Test: Features calculated correctly
- [ ] Test: Edge cases handled (division by zero, etc.)

Definition of Done:
- All features extractable from application data

-----

### TODO-3.1.2: Feature Pipeline
Assignee: ML Engineer
Priority: P0
Dependencies: TODO-3.1.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create sklearn Pipeline
- [ ] Configure ColumnTransformer:

  ```py
  preprocessor = ColumnTransformer([
    ('num', Pipeline([
      ('imputer', SimpleImputer(strategy='median')),
      ('scaler', StandardScaler())
    ]), numeric_features),
    ('cat', Pipeline([
      ('imputer', SimpleImputer(strategy='constant', fill_value='unknown')),
      ('encoder', OneHotEncoder(handle_unknown='ignore'))
    ]), categorical_features)
  ])
  ```

- [ ] Implement fit/transform methods
- [ ] Handle unknown categories gracefully
- [ ] Create pipeline serialization (joblib)
- [ ] Create pipeline loading function
- [ ] Test: Pipeline transforms data correctly
- [ ] Test: Serialization/deserialization works

Definition of Done:
- Feature pipeline ready for training and inference

-----

## Sprint 3.2: Model Development (Weeks 6-7)

### TODO-3.2.1: Model Training Script
Assignee: ML Engineer
Priority: P0
Dependencies: TODO-3.1.2
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Create src/ml/training/ module
- [ ] Create training data loader (from CSV or database)
- [ ] Implement train/test split with stratification:

  ```py
  X_train, X_test, y_train, y_test = train_test_split(
    X, y,
    test_size=0.2,
    stratify=y,
    random_state=42
  )
  ```

- [ ] Configure XGBoost classifier:

  ```py
  XGBClassifier(
    n_estimators=200,
    max_depth=6,
    learning_rate=0.1,
    subsample=0.8,
    colsample_bytree=0.8
  )
  ```

- [ ] Configure Logistic Regression (baseline)
- [ ] Configure MLPClassifier (neural network)
- [ ] Create VotingClassifier ensemble
- [ ] Implement 5-fold cross-validation
- [ ] Calculate metrics:
  - [ ] AUC-ROC
  - [ ] Gini coefficient
  - [ ] KS statistic
  - [ ] Precision, Recall, F1
- [ ] Implement hyperparameter tuning (GridSearchCV)
- [ ] Save trained model and preprocessor
- [ ] Test: Model trains successfully
- [ ] Test: Metrics calculated correctly

Definition of Done:
- Training pipeline complete

-----

### TODO-3.2.2: MLflow Integration
Assignee: ML Engineer
Priority: P1
Dependencies: TODO-3.2.1
Estimated Hours: 16
Can be parallelized: Yes

Tasks:
- [ ] Set up MLflow tracking server (Docker)
- [ ] Configure experiment tracking in training script
- [ ] Log parameters (hyperparameters, features used)
- [ ] Log metrics (all evaluation metrics)
- [ ] Log artifacts (model files, plots)
- [ ] Implement model versioning
- [ ] Create model registry entries
- [ ] Implement model promotion (staging -> production)
- [ ] Test: Experiments tracked
- [ ] Test: Models versioned correctly

Definition of Done:
- MLflow tracking operational

-----

### TODO-3.2.3: SHAP Explanations
Assignee: ML Engineer
Priority: P0
Dependencies: TODO-3.2.1
Estimated Hours: 20
Can be parallelized: No

Tasks:
- [ ] Create src/ml/explainability/ module
- [ ] Initialize TreeExplainer for XGBoost model
- [ ] Implement calculate_shap_values():

  ```py
  def calculate_shap_values(self, X):
    return self.explainer.shap_values(X)
  ```

- [ ] Create feature-to-description mapping:

  ```py
  FACTOR_DESCRIPTIONS = {
    'dti_ratio': ('Debt-to-income ratio', '{:.1%}'),
    'employment_years': ('Employment tenure', '{:.1f} years'),
    'savings_ratio': ('Savings buffer', '{:.1%}'),
    # ...
  }
  ```

- [ ] Implement extract_top_factors():
  - [ ] Sort by absolute SHAP value
  - [ ] Return top 5 positive and top 5 negative
  - [ ] Include human-readable descriptions
- [ ] Optimize SHAP calculation (< 100ms target)
- [ ] Consider caching common patterns
- [ ] Test: SHAP values calculated correctly
- [ ] Test: Top factors extracted properly
- [ ] Test: Performance acceptable

Definition of Done:
- Explainability working and performant

-----

## Sprint 3.3: Scoring Service (Week 8)

### TODO-3.3.1: ML Service API
Assignee: ML Engineer
Priority: P0
Dependencies: TODO-3.2.3
Estimated Hours: 20
Can be parallelized: No

Tasks:
- [ ] Create FastAPI ML service (separate from main API)
- [ ] Implement model loading on startup:

  ```py
  @app.on_event("startup")
  async def load_model():
    global model, preprocessor
    model = joblib.load("models/model.pkl")
    preprocessor = joblib.load("models/preprocessor.pkl")
  ```

- [ ] Create POST /score endpoint:
  - [ ] Input: features dict
  - [ ] Output: score, probability_default, risk_category, shap_values, top_factors
- [ ] Validate input features against schema
- [ ] Execute feature preprocessing
- [ ] Run model prediction
- [ ] Calculate SHAP values
- [ ] Return complete scoring result
- [ ] Implement GET /health endpoint
- [ ] Implement GET /model-info endpoint
- [ ] Test: Service starts with model loaded
- [ ] Test: Scoring returns correct structure
- [ ] Test: Response time < 200ms

Definition of Done:
- ML service deployable and functional

-----

### TODO-3.3.2: Routing Logic
Assignee: ML Engineer
Priority: P0
Dependencies: TODO-3.3.1
Estimated Hours: 12
Can be parallelized: Yes

Tasks:
- [ ] Create DecisionRouter class
- [ ] Implement threshold-based routing:

  ```py
  def route(self, score, loan_amount, loan_purpose):
    if score >= self.config.auto_approve_min:
      return ('auto_approve', 'score_above_threshold')
    if score <= self.config.auto_decline_max:
      return ('auto_decline', 'score_below_threshold')
    return ('human_review', 'borderline_score')
  ```

- [ ] Implement rule-based overrides:
  - [ ] high_value_loan: amount > max_loan_amount_auto
  - [ ] long_term: term > max_term_months_auto
  - [ ] purpose_review: purpose in require_review_purposes
- [ ] Return routing decision with reason
- [ ] Test: Routing matches specification
- [ ] Test: Rules applied correctly

Definition of Done:
- Routing logic complete

-----

### TODO-3.3.3: Model Monitoring Setup
Assignee: ML Engineer
Priority: P1
Dependencies: TODO-3.3.2
Estimated Hours: 16
Can be parallelized: Yes

Tasks:
- [ ] Create src/ml/monitoring/ module
- [ ] Implement DriftDetector class
- [ ] Implement KS test for each feature
- [ ] Implement PSI (Population Stability Index) calculation
- [ ] Create Celery task: check_model_drift (daily)
- [ ] Store monitoring results in database
- [ ] Create drift alerting (if PSI > 0.2)
- [ ] Create GET /ml/monitoring/drift endpoint
- [ ] Test: Drift detected correctly
- [ ] Test: Alerts triggered

Definition of Done:
- Model monitoring operational

-----

# PHASE 4: Frontend Core (5 weeks) - PARALLEL with Phases 2-3

## Sprint 4.1: Project Setup (Week 5)

### TODO-4.1.1: React Project Initialization
Assignee: Frontend Engineer A
Priority: P0
Dependencies: None
Estimated Hours: 12
Can be parallelized: Yes (with Phase 2)

Tasks:
- [ ] Create Vite React TypeScript project: npm create vite@latest frontend -- --template react-ts
- [ ] Install TanStack Router: npm install @tanstack/react-router @tanstack/router-devtools
- [ ] Install TanStack Query: npm install @tanstack/react-query @tanstack/react-query-devtools
- [ ] Install Zustand: npm install zustand
- [ ] Configure Tailwind CSS
- [ ] Install and configure shadcn/ui
- [ ] Set up ESLint + Prettier
- [ ] Configure path aliases in vite.config.ts
- [ ] Create directory structure per PRD spec
- [ ] Create first component test
- [ ] Test: Project builds successfully

Definition of Done:
- Frontend project bootstrapped

-----

### TODO-4.1.2: API Client Setup
Assignee: Frontend Engineer A
Priority: P0
Dependencies: TODO-4.1.1
Estimated Hours: 12
Can be parallelized: No

Tasks:
- [ ] Create src/api/client.ts
- [ ] Configure base URL from environment variable
- [ ] Implement request interceptor:
  - [ ] Attach Authorization header with JWT
  - [ ] Add request ID header
- [ ] Implement response interceptor:
  - [ ] Handle 401 (redirect to login)
  - [ ] Handle 403 (show permission error)
  - [ ] Handle 5xx (show error message)
- [ ] Create TypeScript interfaces for API responses
- [ ] Create API modules:
  - [ ] src/api/auth.ts
  - [ ] src/api/applications.ts
  - [ ] src/api/queue.ts
  - [ ] src/api/decisions.ts
  - [ ] src/api/analytics.ts
- [ ] Test: API calls work
- [ ] Test: Auth token attached

Definition of Done:
- API client configured

-----

### TODO-4.1.3: TanStack Query Setup
Assignee: Frontend Engineer A
Priority: P0
Dependencies: TODO-4.1.2
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create QueryClient with defaults:

  ```ts
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000, // 5 minutes
        gcTime: 30 * 60 * 1000, // 30 minutes
        retry: 3,
      },
    },
  });
  ```

- [ ] Create query key factories for each entity
- [ ] Create hooks:
  - [ ] useApplications(filters)
  - [ ] useApplication(id)
  - [ ] useCreateApplication()
  - [ ] useQueue(filters)
  - [ ] useQueueSummary()
  - [ ] useAssignCase()
  - [ ] useSubmitDecision()
  - [ ] useAnalytics(params)
- [ ] Implement optimistic updates for mutations
- [ ] Test: Hooks fetch data correctly
- [ ] Test: Caching works
- [ ] Test: Invalidation triggers refetch

Definition of Done:
- Data fetching layer complete

- Approve: Show approved terms summary
- Approve with conditions: Show ConditionsBuilder
- Decline: Show reasoning field (required)
- Request docs: Show document checklist
- [ ] Create reasoning textarea:
  - Required for all decisions
  - Character count
  - Minimum 20 characters
- [ ] Create reasoning category dropdown
- [ ] Create template selector (pre-fill common responses)
- [ ] Implement form validation
- [ ] Handle submission (useSubmitDecision mutation)
- [ ] Show loading state during submission
- [ ] Test: All options work
- [ ] Test: Validation enforced
- [ ] Test: Submission works

Definition of Done:
- Decision panel fully functional

-----

### TODO-5.3.2: Conditions Builder
Assignee: Frontend Engineer B
Priority: P0
Dependencies: TODO-5.3.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create ConditionsBuilder component
- [ ] Create condition type selector (dropdown):
  - Documentation required
  - Collateral required
  - Guarantor required
  - Amount adjustment
  - Term adjustment
  - Custom
- [ ] For amount adjustment:
  - New amount input
  - Show difference from requested
  - Recalculate monthly payment
- [ ] For term adjustment:
  - New term input
  - Recalculate monthly payment
- [ ] For documentation:
  - Document checklist (bank statements, pay stubs, etc.)
  - Due date picker
- [ ] Implement add/remove conditions
- [ ] Show adjusted terms preview (if modified)
- [ ] Test: Conditions addable/removable
- [ ] Test: Preview calculates correctly

Definition of Done:
- Conditions builder complete

-----

### TODO-5.3.3: Override Flow
Assignee: Frontend Engineer B
Priority: P0
Dependencies: TODO-5.3.2
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create override detection logic:
  - If score >= auto_approve_min AND decision = decline → override
  - If score <= auto_decline_max AND decision = approve → override
- [ ] Show override checkbox when applicable
- [ ] Create OverrideModal component:
  - Warning message explaining override implications
  - Justification textarea (required, min 50 chars)
  - Confirmation checkbox
  - Submit button
- [ ] Show pending approval status after override submission
- [ ] Test: Override detected correctly
- [ ] Test: Modal flow works
- [ ] Test: Pending status shown

Definition of Done:
- Override workflow complete

-----

## Sprint 5.4: Workbench Polish (Week 13)

### TODO-5.4.1: Keyboard Shortcuts
Assignee: Frontend Engineer B
Priority: P2
Dependencies: TODO-5.3.3
Estimated Hours: 8
Can be parallelized: Yes

Tasks:
- [ ] Define shortcut mappings
- [ ] Implement keyboard event listener
- [ ] Shortcuts:
  - Ctrl+Shift+A: Select Approve
  - Ctrl+Shift+D: Select Decline
  - Ctrl+Enter: Submit decision
  - Ctrl+N: Next case
  - Ctrl+P: Previous case
  - Escape: Cancel/close modals
- [ ] Create shortcuts help modal (Ctrl+?)
- [ ] Test: Shortcuts work
- [ ] Test: No conflicts with browser shortcuts

Definition of Done:
- Keyboard shortcuts functional

-----

### TODO-5.4.2: Quick Actions Panel
Assignee: Frontend Engineer B
Priority: P1
Dependencies: TODO-5.4.1
Estimated Hours: 8
Can be parallelized: Yes

Tasks:
- [ ] Create QuickActions component
- [ ] Implement “Release to Queue” button:
  - Confirmation dialog
  - Call release endpoint
  - Navigate back to queue
- [ ] Implement “Request Help” button:
  - Opens chat/comment modal
  - Notifies senior analyst
- [ ] Implement “Flag for Review” button:
  - Marks case for special attention
  - Add flag reason
- [ ] Test: Actions work correctly
- [ ] Test: Confirmations shown

Definition of Done:
- Quick actions functional

-----

### TODO-5.4.3: Workbench State Persistence
Assignee: Frontend Engineer B
Priority: P2
Dependencies: TODO-5.4.2
Estimated Hours: 8
Can be parallelized: Yes

Tasks:
- [ ] Save form state to localStorage on change
- [ ] Restore state on page reload
- [ ] Clear state on successful submission
- [ ] Handle stale state (case changed/submitted elsewhere)
- [ ] Show recovery prompt if draft exists
- [ ] Test: State survives reload
- [ ] Test: Recovery works
- [ ] Test: Stale state handled

Definition of Done:
- State persistence working

-----

# PHASE 6: Analytics & Monitoring (3 weeks) - PARALLEL with Phase 5

## Sprint 6.1: Analytics Dashboard (Weeks 10-11)

### TODO-6.1.1: Dashboard Page
Assignee: Frontend Engineer (separate)
Priority: P0
Dependencies: Phase 4 Complete
Estimated Hours: 20
Can be parallelized: Yes (with Phase 5)

Tasks:
- [ ] Create / (dashboard) route
- [ ] Create dashboard grid layout
- [ ] Create date range selector (last 7 days, 30 days, custom)
- [ ] Fetch data with useAnalytics hook
- [ ] Create MetricCard component:
  - Large number
  - Label
  - Trend indicator (↑ up, ↓ down)
  - Comparison to previous period
- [ ] Display metrics:
  - Total Applications
  - Auto-Decision Rate
  - Approval Rate
  - Average Review Time
  - SLA Compliance Rate
- [ ] Handle loading state
- [ ] Test: Metrics display correctly
- [ ] Test: Date range works

Definition of Done:
- Dashboard with key metrics

-----

### TODO-6.1.2: Decision Charts
Assignee: Frontend Engineer (separate)
Priority: P0
Dependencies: TODO-6.1.1
Estimated Hours: 16
Can be parallelized: Yes

Tasks:
- [ ] Create TrendChart component (line chart):
  - Applications over time
  - Decisions over time
  - Configurable granularity
- [ ] Create DistributionChart component (pie/donut):
  - Decision type breakdown
  - Score distribution histogram
- [ ] Add chart interactivity:
  - Tooltips on hover
  - Click to drill down
- [ ] Implement responsive sizing
- [ ] Test: Charts render correctly
- [ ] Test: Responsive

Definition of Done:
- Charts implemented

-----

### TODO-6.1.3: Performance Tables
Assignee: Frontend Engineer (separate)
Priority: P1
Dependencies: TODO-6.1.2
Estimated Hours: 12
Can be parallelized: Yes

Tasks:
- [ ] Create AnalystPerformanceTable:
  - Columns: Analyst, Decisions, Avg Time, Override Rate, Approval Rate
  - Sortable
- [ ] Create ModelPerformanceTable:
  - Columns: Date, Scores Generated, Avg Score, Routing Distribution
  - Sortable
- [ ] Add comparison views (week-over-week)
- [ ] Test: Tables populated correctly
- [ ] Test: Sorting works

Definition of Done:
- Performance tables complete

-----

## Sprint 6.2: Backend Analytics (Week 11)

### TODO-6.2.1: Analytics Endpoints
Assignee: Backend Engineer
Priority: P0
Dependencies: Phase 2 Complete
Estimated Hours: 20
Can be parallelized: Yes

Tasks:
- [ ] Create GET /analytics/dashboard endpoint
- [ ] Implement summary calculations:

  ```sql
  SELECT
    COUNT(*) as total,
    SUM(CASE WHEN decision_type LIKE 'auto_%' THEN 1 ELSE 0 END)::float / COUNT(*) as auto_rate,
    SUM(CASE WHEN decision_outcome = 'approved' THEN 1 ELSE 0 END)::float / COUNT(*) as approval_rate,
    AVG(review_time_seconds) as avg_review_time
  FROM decisions
  WHERE created_at BETWEEN :from_date AND :to_date
  ```

- [ ] Implement decision breakdown by type
- [ ] Implement trend data aggregation (by day/week)
- [ ] Implement queue metrics
- [ ] Create GET /analytics/analyst-performance
- [ ] Create GET /analytics/model-performance
- [ ] Create GET /analytics/cohort-analysis
- [ ] Add caching for expensive queries (Redis, 5 min TTL)
- [ ] Test: Endpoints return correct data
- [ ] Test: Response time < 500ms

Definition of Done:
- Analytics API complete

-----

### TODO-6.2.2: Export Functionality
Assignee: Backend Engineer
Priority: P1
Dependencies: TODO-6.2.1
Estimated Hours: 12
Can be parallelized: Yes

Tasks:
- [ ] Create POST /analytics/export endpoint
- [ ] Implement CSV export
- [ ] Implement Excel export (using openpyxl)
- [ ] For large datasets (>10k rows):
  - Queue as background task
  - Return export_id
  - Poll GET /analytics/export/{id}/status
- [ ] Create GET /analytics/export/{id}/download
- [ ] Test: Small exports work
- [ ] Test: Large exports async

Definition of Done:
- Export functionality working

-----

## Sprint 6.3: Monitoring Infrastructure (Week 12)

### TODO-6.3.1: Prometheus Metrics
Assignee: DevOps Engineer
Priority: P0
Dependencies: TODO-2.4.1
Estimated Hours: 16
Can be parallelized: Yes

Tasks:
- [ ] Configure Prometheus scraping (prometheus.yml)
- [ ] Add FastAPI prometheus middleware
- [ ] Create custom metrics:
  - applications_total (Counter, labels: status)
  - decisions_total (Counter, labels: type, outcome)
  - scoring_duration_seconds (Histogram)
  - queue_size (Gauge)
  - queue_wait_time_seconds (Histogram)
  - model_prediction_duration_seconds (Histogram)
  - sla_breaches_total (Counter)
- [ ] Configure alerting rules:
  - High error rate (> 1%)
  - High latency (p99 > 1s)
  - Queue growing (> 100 pending)
  - SLA breaches (> 5/hour)
- [ ] Test: Metrics collected
- [ ] Test: Alerts trigger correctly

Definition of Done:
- Prometheus monitoring operational

-----

### TODO-6.3.2: Grafana Dashboards
Assignee: DevOps Engineer
Priority: P0
Dependencies: TODO-6.3.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Create Operations Dashboard:
  - Request rate and latency panels
  - Error rate panel
  - Database connections panel
  - Redis metrics panel
- [ ] Create Business Dashboard:
  - Applications funnel
  - Decision metrics
  - Queue health
  - SLA compliance
- [ ] Create ML Dashboard:
  - Scoring latency
  - Score distribution
  - Drift indicators
- [ ] Set up alerting to Slack/email
- [ ] Document dashboards
- [ ] Test: Dashboards visualize correctly
- [ ] Test: Alerting works

Definition of Done:
- Grafana dashboards deployed

-----

### TODO-6.3.3: Logging Setup
Assignee: DevOps Engineer
Priority: P1
Dependencies: TODO-6.3.1
Estimated Hours: 12
Can be parallelized: Yes

Tasks:
- [ ] Configure Loki for log aggregation
- [ ] Configure Promtail for log shipping
- [ ] Set up log parsing rules (JSON logs)
- [ ] Create Loki data source in Grafana
- [ ] Create log query panels in dashboards
- [ ] Implement log retention policy (30 days)
- [ ] Test: Logs aggregated
- [ ] Test: Searchable in Grafana

Definition of Done:
- Centralized logging operational

-----

# PHASE 7: Integration & Testing (3 weeks)

## Sprint 7.1: Integration Testing (Week 14)

### TODO-7.1.1: API Integration Tests
Assignee: QA Engineer
Priority: P0
Dependencies: Phases 2-3 Complete
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Set up test database (Docker, isolated)
- [ ] Create test fixtures (factory_boy)
- [ ] Write auth flow tests:
  - Login success/failure
  - Token refresh
  - Token expiration
- [ ] Write application CRUD tests
- [ ] Write scoring integration tests (mock ML service)
- [ ] Write queue workflow tests (assign, start, release)
- [ ] Write decision flow tests (all types)
- [ ] Write override workflow tests
- [ ] Write analytics endpoint tests
- [ ] Configure CI to run tests (GitHub Actions)
- [ ] Test: All integration tests pass
- [ ] Test: Coverage > 80%

Definition of Done:
- Comprehensive API tests

-----

### TODO-7.1.2: E2E Test Suite
Assignee: QA Engineer
Priority: P0
Dependencies: Phases 4-5 Complete
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Set up Playwright
- [ ] Configure test environment (docker-compose.test.yml)
- [ ] Write test: Login flow
- [ ] Write test: Application list (filter, paginate)
- [ ] Write test: Application detail view
- [ ] Write test: Queue workflow (pick case)
- [ ] Write test: Workbench full flow (load, review, decide)
- [ ] Write test: Decision submission (approve)
- [ ] Write test: Decision submission (decline)
- [ ] Write test: Override flow
- [ ] Write test: Dashboard metrics
- [ ] Configure CI for E2E (headless)
- [ ] Test: All E2E tests pass

Definition of Done:
- E2E tests covering critical paths

-----

## Sprint 7.2: Performance Testing (Week 15)

### TODO-7.2.1: Load Testing
Assignee: QA Engineer
Priority: P0
Dependencies: TODO-7.1.1
Estimated Hours: 20
Can be parallelized: No

Tasks:
- [ ] Set up k6 or Locust
- [ ] Create load test scenarios:
  - Application submission: 100 req/s sustained
  - Scoring: 50 req/s sustained
  - Queue listing: 200 req/s sustained
  - Decision submission: 30 req/s sustained
- [ ] Run baseline tests (current performance)
- [ ] Identify bottlenecks:
  - Database queries
  - ML service
  - Redis
- [ ] Document performance baseline
- [ ] Create performance report

Definition of Done:
- Performance baseline established

-----

### TODO-7.2.2: Performance Optimization
Assignee: Backend Engineer
Priority: P1
Dependencies: TODO-7.2.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Optimize slow queries (EXPLAIN ANALYZE)
- [ ] Add missing indexes
- [ ] Implement query result caching (Redis)
- [ ] Fix N+1 queries (use joinedload)
- [ ] Tune database connection pool
- [ ] Optimize ML service batching
- [ ] Re-run load tests
- [ ] Document optimizations made

Definition of Done:
- Performance targets met

-----

## Sprint 7.3: Security & Documentation (Week 16)

### TODO-7.3.1: Security Audit
Assignee: Security Engineer
Priority: P0
Dependencies: All Features Complete
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Run OWASP ZAP scan
- [ ] Review authentication implementation
- [ ] Review authorization implementation
- [ ] Test for SQL injection
- [ ] Test for XSS vulnerabilities
- [ ] Review secrets management
- [ ] Review API rate limiting
- [ ] Check CORS configuration
- [ ] Review logging (ensure no sensitive data)
- [ ] Create security report
- [ ] Fix critical findings

Definition of Done:
- No critical vulnerabilities

-----

### TODO-7.3.2: Compliance Review
Assignee: Compliance Officer / Backend Engineer
Priority: P0
Dependencies: TODO-7.3.1
Estimated Hours: 16
Can be parallelized: Yes

Tasks:
- [ ] Review GDPR compliance:
  - Right to explanation (SHAP explanations)
  - Data access requests (export endpoint)
  - Data deletion (implemented?)
- [ ] Review audit trail completeness
- [ ] Review data retention implementation
- [ ] Review PII handling
- [ ] Create compliance documentation
- [ ] Sign off on compliance

Definition of Done:
- GDPR requirements verified

-----

### TODO-7.3.3: Documentation
Assignee: Technical Writer
Priority: P1
Dependencies: All Features Complete
Estimated Hours: 24
Can be parallelized: Yes

Tasks:
- [ ] Write API documentation (OpenAPI + guides)
- [ ] Write deployment guide
- [ ] Write operations runbook
- [ ] Write analyst user guide
- [ ] Write admin user guide
- [ ] Create architecture diagrams
- [ ] Document configuration options
- [ ] Create troubleshooting guide
- [ ] Review and edit all docs

Definition of Done:
- Documentation complete

-----

# PHASE 8: Production Readiness (2 weeks)

## Sprint 8.1: Infrastructure (Week 17)

### TODO-8.1.1: Production Environment
Assignee: DevOps Engineer
Priority: P0
Dependencies: Phase 7 Complete
Estimated Hours: 24
Can be parallelized: No

Tasks:
- [ ] Provision production servers (cloud or on-prem)
- [ ] Set up PostgreSQL with replication (primary + replica)
- [ ] Set up Redis cluster (or managed Redis)
- [ ] Configure SSL certificates (Let’s Encrypt or purchased)
- [ ] Set up domain and DNS
- [ ] Configure firewall rules
- [ ] Set up backup schedule:
  - Database: Daily full, hourly incremental
  - Retention: 30 days
- [ ] Configure log shipping to central logging
- [ ] Test failover scenarios
- [ ] Document infrastructure

Definition of Done:
- Production infrastructure ready

-----

### TODO-8.1.2: CI/CD Pipeline
Assignee: DevOps Engineer
Priority: P0
Dependencies: TODO-8.1.1
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [x] Configure GitHub Actions (or GitLab CI) (basic CI: migrations + pytest)
- [ ] Create build pipeline:
  - Build Docker images
  - Run linting
  - Run unit tests
- [ ] Create test pipeline:
  - Run integration tests
  - Run E2E tests
- [ ] Create staging deployment pipeline:
  - Deploy to staging
  - Run smoke tests
- [ ] Create production deployment pipeline:
  - Require manual approval
  - Blue-green deployment
  - Health check verification
- [ ] Implement rollback capability
- [ ] Test full pipeline
- [ ] Document CI/CD

Definition of Done:
- CI/CD pipeline operational

-----

## Sprint 8.2: Go-Live (Week 18)

### TODO-8.2.1: Staging Validation
Assignee: QA Engineer
Priority: P0
Dependencies: TODO-8.1.2
Estimated Hours: 16
Can be parallelized: No

Tasks:
- [ ] Deploy to staging environment
- [ ] Run full E2E test suite
- [ ] Perform UAT with stakeholders
- [ ] Validate all integrations
- [ ] Test monitoring and alerting
- [ ] Performance test on staging
- [ ] Sign off on staging

Definition of Done:
- Staging validated

-----

### TODO-8.2.2: Production Deployment
Assignee: DevOps Engineer
Priority: P0
Dependencies: TODO-8.2.1
Estimated Hours: 12
Can be parallelized: No

Tasks:
- [ ] Create deployment checklist
- [ ] Schedule deployment window
- [ ] Notify stakeholders
- [ ] Run database migrations
- [ ] Deploy backend services
- [ ] Deploy ML service
- [ ] Deploy frontend
- [ ] Verify health checks
- [ ] Run smoke tests
- [ ] Monitor for errors (30 min)
- [ ] Declare go-live

Definition of Done:
- System live in production

-----

### TODO-8.2.3: Post-Launch Support
Assignee: All Engineers
Priority: P0
Dependencies: TODO-8.2.2
Estimated Hours: 40 (1 week)
Can be parallelized: Yes

Tasks:
- [ ] Monitor system health 24/7 (first week)
- [ ] Watch for error spikes
- [ ] Track performance metrics
- [ ] Respond to incidents
- [ ] Collect user feedback
- [ ] Create bug fixes as needed
- [ ] Document lessons learned
- [ ] Plan iteration 2 improvements

Definition of Done:
- System stable for 1 week

-----

## Parallelization Summary

### Can run in parallel:
- Phase 3 (ML Pipeline) + Phase 2 (Core Backend)
- Phase 4 (Frontend Core) + Phases 2-3
- Phase 6 (Analytics) + Phase 5 (Workbench)
- Within phases, marked TODOs can parallelize

### Must be sequential:
- Phase 1 must complete before Phase 2
- Phase 4 must complete before Phase 5
- Phase 7 must complete before Phase 8

### Recommended team allocation:
- Backend Engineer A: Phase 1-2 (Foundation, Core Backend)
- Backend Engineer B: Phase 2.3-2.4 (Decisions, Workers)
- ML Engineer: Phase 3 (ML Pipeline) - can start Week 5
- Frontend Engineer A: Phase 4-5 (Core UI, Workbench)
- Frontend Engineer B: Phase 5.3-5.4 (Decision Panel)
- DevOps Engineer: Phase 1.1, 6.3, 8 (Infrastructure)
- QA Engineer: Phase 7 (Testing)

-----

Total Estimated Hours: ~600 hours
Total Duration: 16-20 weeks (with parallel execution)
