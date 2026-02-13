"""
Base evaluation classes.
基础评估类定义
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime


@dataclass
class EvaluationMetrics:
    """Evaluation metrics container."""
    
    accuracy: float = 0.0
    precision: float = 0.0
    recall: float = 0.0
    f1_score: float = 0.0
    error_rate: float = 0.0
    latency_ms: float = 0.0
    token_usage: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "accuracy": self.accuracy,
            "precision": self.precision,
            "recall": self.recall,
            "f1_score": self.f1_score,
            "error_rate": self.error_rate,
            "latency_ms": self.latency_ms,
            "token_usage": self.token_usage,
            **self.extra,
        }


@dataclass
class EvaluationResult:
    """Single evaluation result."""
    
    sample_id: str
    input_data: Any
    expected_output: Any
    actual_output: Any
    is_correct: bool
    metrics: EvaluationMetrics
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "input_data": self.input_data,
            "expected_output": self.expected_output,
            "actual_output": self.actual_output,
            "is_correct": self.is_correct,
            "metrics": self.metrics.to_dict(),
            "error_message": self.error_message,
            "metadata": self.metadata,
        }


@dataclass
class EvaluationReport:
    """Complete evaluation report."""
    
    benchmark_name: str
    evaluation_time: str
    total_samples: int
    correct_samples: int
    results: List[EvaluationResult]
    overall_metrics: EvaluationMetrics
    category_metrics: Dict[str, EvaluationMetrics] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def __post_init__(self):
        if not self.evaluation_time:
            self.evaluation_time = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "benchmark_name": self.benchmark_name,
            "evaluation_time": self.evaluation_time,
            "total_samples": self.total_samples,
            "correct_samples": self.correct_samples,
            "overall_accuracy": self.overall_metrics.accuracy,
            "overall_metrics": self.overall_metrics.to_dict(),
            "category_metrics": {
                k: v.to_dict() for k, v in self.category_metrics.items()
            },
            "metadata": self.metadata,
        }


class BaseEvaluator:
    """Base evaluator class."""
    
    def __init__(self, name: str):
        self.name = name
    
    def evaluate(self, agent: Any, dataset: Any, **kwargs) -> EvaluationReport:
        """Run evaluation on agent."""
        raise NotImplementedError("Subclasses must implement evaluate()")
    
    def compute_metrics(self, results: List[EvaluationResult]) -> EvaluationMetrics:
        """Compute metrics from results."""
        if not results:
            return EvaluationMetrics()
        
        correct = sum(1 for r in results if r.is_correct)
        total = len(results)
        
        metrics = EvaluationMetrics(
            accuracy=correct / total if total > 0 else 0.0,
            error_rate=(total - correct) / total if total > 0 else 1.0,
        )
        
        return metrics


class BaseDataset:
    """Base dataset class."""
    
    def __init__(self, name: str):
        self.name = name
        self.data = []
    
    def load(self) -> List[Dict[str, Any]]:
        """Load dataset."""
        raise NotImplementedError("Subclasses must implement load()")
    
    def get_available_categories(self) -> List[str]:
        """Get available categories."""
        return []
