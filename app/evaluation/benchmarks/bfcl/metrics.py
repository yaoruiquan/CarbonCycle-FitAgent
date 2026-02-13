"""
BFCL metrics calculator.
BFCL 指标计算器
"""

from typing import Any, Dict, List

from app.evaluation.base import EvaluationMetrics, EvaluationResult


class BFCLMetrics:
    """BFCL metrics calculator."""
    
    def compute_metrics(
        self,
        results: List[EvaluationResult],
    ) -> EvaluationMetrics:
        """
        Compute BFCL metrics.
        
        Args:
            results: List of evaluation results
            
        Returns:
            Computed metrics
        """
        if not results:
            return EvaluationMetrics()
        
        correct = sum(1 for r in results if r.is_correct)
        total = len(results)
        
        accuracy = correct / total if total > 0 else 0.0
        error_rate = 1.0 - accuracy
        
        total_latency = sum(r.metrics.latency_ms for r in results)
        avg_latency = total_latency / total if total > 0 else 0.0
        
        total_tokens = sum(r.metrics.token_usage for r in results)
        avg_tokens = total_tokens / total if total > 0 else 0
        
        metrics = EvaluationMetrics(
            accuracy=accuracy,
            error_rate=error_rate,
            latency_ms=avg_latency,
            token_usage=avg_tokens,
        )
        
        return metrics
    
    def compute_category_metrics(
        self,
        results: List[EvaluationResult],
    ) -> Dict[str, EvaluationMetrics]:
        """Compute metrics by category."""
        category_results: Dict[str, List[EvaluationResult]] = {}
        
        for result in results:
            parts = result.sample_id.split("_")
            category = parts[0] if parts else "unknown"
            
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(result)
        
        category_metrics = {}
        for category, cat_results in category_results.items():
            category_metrics[category] = self.compute_metrics(cat_results)
        
        return category_metrics
    
    def compute_weighted_accuracy(
        self,
        category_metrics: Dict[str, EvaluationMetrics],
        weights: Dict[str, float],
    ) -> float:
        """
        Compute weighted accuracy.
        
        Args:
            category_metrics: Metrics by category
            weights: Weights for each category
            
        Returns:
            Weighted accuracy
        """
        weighted_sum = sum(
            metrics.accuracy * weights.get(category, 0.0)
            for category, metrics in category_metrics.items()
        )
        
        total_weight = sum(weights.values())
        
        return weighted_sum / total_weight if total_weight > 0 else 0.0
