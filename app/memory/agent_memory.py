"""
Agent memory storage.
智能体记忆存储

Manages persistent storage of agent decisions and reasoning chains.
管理智能体决策和推理链的持久存储
"""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.memory.user_memory import InMemoryStore, MemoryStore

logger = get_logger(__name__)


class DecisionRecord(BaseModel):
    """
    Record of a single agent decision.
    
    Attributes:
        id: Unique decision identifier.
        run_id: Parent agent run identifier.
        node: Agent node that made the decision.
        decision: The decision made.
        reasoning: Explanation of the reasoning.
        input_summary: Summary of inputs considered.
        output_summary: Summary of outputs produced.
        confidence: Confidence score (0-1).
        timestamp: When the decision was made.
    """
    
    id: UUID = Field(default_factory=uuid4)
    run_id: UUID
    node: str
    decision: str
    reasoning: str
    input_summary: str = ""
    output_summary: str = ""
    confidence: float = Field(default=0.8, ge=0, le=1)
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentRun(BaseModel):
    """
    Record of a complete agent execution.
    
    Attributes:
        id: Unique run identifier.
        user_id: User this run was for.
        trigger: What triggered the run.
        decisions: List of decisions made.
        final_output: Final result of the run.
        status: Run status (running, completed, failed).
        started_at: Run start timestamp.
        completed_at: Run completion timestamp.
        error: Error message if failed.
    """
    
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    trigger: str
    decisions: list[DecisionRecord] = Field(default_factory=list)
    final_output: Optional[dict[str, Any]] = None
    status: str = "running"  # running, completed, failed
    started_at: datetime = Field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def add_decision(self, decision: DecisionRecord) -> None:
        """Add a decision record to this run."""
        decision.run_id = self.id
        self.decisions.append(decision)
    
    def complete(self, output: dict[str, Any]) -> None:
        """Mark the run as completed."""
        self.status = "completed"
        self.final_output = output
        self.completed_at = datetime.now()
    
    def fail(self, error: str) -> None:
        """Mark the run as failed."""
        self.status = "failed"
        self.error = error
        self.completed_at = datetime.now()


class AgentMemory:
    """
    Manages agent execution history and decision auditing.
    
    Provides methods to record, retrieve, and analyze agent decisions.
    """
    
    def __init__(self, store: MemoryStore) -> None:
        """
        Initialize agent memory with storage backend.
        
        Args:
            store: Storage backend implementing MemoryStore protocol.
        """
        self._store = store
        self._current_runs: dict[UUID, AgentRun] = {}
    
    def _run_key(self, run_id: UUID) -> str:
        """Generate storage key for agent run."""
        return f"agent:run:{run_id}"
    
    def _user_runs_key(self, user_id: UUID) -> str:
        """Generate storage key for user's run history."""
        return f"agent:user:{user_id}:runs"
    
    async def start_run(self, user_id: UUID, trigger: str) -> AgentRun:
        """
        Start a new agent run.
        
        Args:
            user_id: User the run is for.
            trigger: What triggered the run.
            
        Returns:
            AgentRun: The new run record.
        """
        run = AgentRun(user_id=user_id, trigger=trigger)
        self._current_runs[run.id] = run
        
        logger.info(f"Started agent run {run.id} for user {user_id}")
        return run
    
    async def record_decision(
        self,
        run_id: UUID,
        node: str,
        decision: str,
        reasoning: str,
        input_summary: str = "",
        output_summary: str = "",
        confidence: float = 0.8,
    ) -> DecisionRecord:
        """
        Record a decision within an agent run.
        
        Args:
            run_id: Parent run identifier.
            node: Agent node making the decision.
            decision: The decision made.
            reasoning: Explanation of reasoning.
            input_summary: Summary of inputs.
            output_summary: Summary of outputs.
            confidence: Confidence score.
            
        Returns:
            DecisionRecord: The recorded decision.
        """
        record = DecisionRecord(
            run_id=run_id,
            node=node,
            decision=decision,
            reasoning=reasoning,
            input_summary=input_summary,
            output_summary=output_summary,
            confidence=confidence,
        )
        
        if run_id in self._current_runs:
            self._current_runs[run_id].add_decision(record)
        
        logger.info(
            f"Agent decision: run={run_id}, node={node}, "
            f"decision={decision[:50]}..."
        )
        
        return record
    
    async def complete_run(
        self,
        run_id: UUID,
        output: dict[str, Any],
    ) -> Optional[AgentRun]:
        """
        Complete an agent run successfully.
        
        Args:
            run_id: Run identifier.
            output: Final output data.
            
        Returns:
            Completed AgentRun or None if not found.
        """
        if run_id not in self._current_runs:
            logger.warning(f"Run {run_id} not found for completion")
            return None
        
        run = self._current_runs.pop(run_id)
        run.complete(output)
        
        # Persist the completed run
        await self._store.set(
            self._run_key(run_id),
            run.model_dump(mode="json"),
        )
        
        # Update user's run history
        await self._add_to_user_history(run.user_id, run_id)
        
        logger.info(f"Completed agent run {run_id}")
        return run
    
    async def fail_run(self, run_id: UUID, error: str) -> Optional[AgentRun]:
        """
        Mark an agent run as failed.
        
        Args:
            run_id: Run identifier.
            error: Error message.
            
        Returns:
            Failed AgentRun or None if not found.
        """
        if run_id not in self._current_runs:
            logger.warning(f"Run {run_id} not found for failure")
            return None
        
        run = self._current_runs.pop(run_id)
        run.fail(error)
        
        await self._store.set(
            self._run_key(run_id),
            run.model_dump(mode="json"),
        )
        
        logger.error(f"Agent run {run_id} failed: {error}")
        return run
    
    async def get_run(self, run_id: UUID) -> Optional[AgentRun]:
        """
        Retrieve an agent run by ID.
        
        Args:
            run_id: Run identifier.
            
        Returns:
            AgentRun if found, None otherwise.
        """
        # Check current runs first
        if run_id in self._current_runs:
            return self._current_runs[run_id]
        
        # Check persisted runs
        data = await self._store.get(self._run_key(run_id))
        if data:
            return AgentRun.model_validate(data)
        return None
    
    async def get_user_runs(
        self,
        user_id: UUID,
        limit: int = 10,
    ) -> list[UUID]:
        """
        Get recent run IDs for a user.
        
        Args:
            user_id: User identifier.
            limit: Maximum number of runs to return.
            
        Returns:
            List of run IDs, most recent first.
        """
        data = await self._store.get(self._user_runs_key(user_id))
        if data and "runs" in data:
            return [UUID(r) for r in data["runs"][:limit]]
        return []
    
    async def _add_to_user_history(self, user_id: UUID, run_id: UUID) -> None:
        """Add a run to user's history."""
        key = self._user_runs_key(user_id)
        data = await self._store.get(key)
        
        runs = data.get("runs", []) if data else []
        runs.insert(0, str(run_id))
        runs = runs[:100]  # Keep last 100 runs
        
        await self._store.set(key, {"runs": runs})


# Singleton instance
_agent_memory: Optional[AgentMemory] = None


def get_agent_memory() -> AgentMemory:
    """
    Get or create the singleton agent memory instance.
    
    Returns:
        AgentMemory: Configured memory instance.
    """
    global _agent_memory
    if _agent_memory is None:
        store = InMemoryStore()
        _agent_memory = AgentMemory(store)
    return _agent_memory
