from contextvars import ContextVar
from typing import Optional
from uuid import UUID

# This context variable will hold the parent run ID from the orchestrator
# for the duration of a single incoming API request.
parent_run_id_var: ContextVar[Optional[UUID]] = ContextVar("parent_run_id_var", default=None)