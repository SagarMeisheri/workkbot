"""
Workkbot Local PoC: Human-In-The-Loop (HITL) Gatekeeper
Provides interactive verification for state-changing operations before mutation.
"""
from dataclasses import dataclass, field
import datetime
from typing import Any, Callable, Dict, List, Optional
import uuid


@dataclass
class PendingApproval:
    id: str
    action_name: str
    target_service: str
    summary: str
    payload: Dict[str, Any]
    status: str  # "pending", "approved", "rejected"
    created_at: str = field(
        default_factory=lambda: datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    resolved_at: Optional[str] = None
    rejection_reason: Optional[str] = None


class HitlGatekeeper:
    def __init__(self):
        self.pending_approvals: Dict[str, PendingApproval] = {}
        self.history: List[PendingApproval] = []

    def create_approval_request(
        self, action_name: str, target_service: str, summary: str, payload: Dict[str, Any]
    ) -> PendingApproval:
        req_id = str(uuid.uuid4())[:8]
        req = PendingApproval(
            id=req_id,
            action_name=action_name,
            target_service=target_service,
            summary=summary,
            payload=payload,
            status="pending",
        )
        self.pending_approvals[req_id] = req
        return req

    def approve(self, req_id: str) -> Optional[PendingApproval]:
        if req_id in self.pending_approvals:
            req = self.pending_approvals.pop(req_id)
            req.status = "approved"
            req.resolved_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.append(req)
            return req
        return None

    def reject(self, req_id: str, reason: str = "User declined action") -> Optional[PendingApproval]:
        if req_id in self.pending_approvals:
            req = self.pending_approvals.pop(req_id)
            req.status = "rejected"
            req.rejection_reason = reason
            req.resolved_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.history.append(req)
            return req
        return None

    def list_pending(self) -> List[PendingApproval]:
        return list(self.pending_approvals.values())

    def list_history(self) -> List[PendingApproval]:
        return self.history
