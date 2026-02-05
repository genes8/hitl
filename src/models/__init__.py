# Import models here so Alembic can discover them via metadata
from .tenant import Tenant  # noqa: F401
from .user import User  # noqa: F401
from .application import Application  # noqa: F401
from .scoring_result import ScoringResult  # noqa: F401
from .analyst_queue import AnalystQueue  # noqa: F401
from .decision import Decision  # noqa: F401
from .decision_threshold import DecisionThreshold  # noqa: F401
from .audit_log import AuditLog  # noqa: F401
from .model_registry import ModelRegistry  # noqa: F401
from .similar_case import SimilarCase  # noqa: F401
from .notification import Notification  # noqa: F401
from .loan_outcome import LoanOutcome  # noqa: F401
