"""
GAIA metrics calculator.
GAIA 指标计算器
"""

from typing import Any, Dict, List

from app.evaluation.base import EvaluationMetrics, EvaluationResult


class GAIAMetrics:
    """GAIA metrics calculator."""
    
    def compute_metrics(
        self,
        results: List[EvaluationResult],
    ) -> EvaluationMetrics:
        """
        Compute GAIA metrics.
        
        Args:
            results: List of evaluation results
            
        Returns:
            Computed metrics
        """
        if not results:
            return EvaluationMetrics()
        
        correct = sum(1 for r in results if r.is_correct)
        total = len(results)
        
        exact_match_rate = correct / total if total > 0 else 0.0
        
        metrics = EvaluationMetrics(
            accuracy=exact_match_rate,
            error_rate=1.0 - exact_match_rate,
        )
        
        return metrics
    
    def compute_level_metrics(
        self,
        results: List[EvaluationResult],
    ) -> Dict[str, EvaluationMetrics]:
        """Compute metrics by difficulty level."""
        level_results: Dict[str, List[EvaluationResult]] = {}
        
        for result in results:
            level = str(result.input_data.get("level", "unknown"))
            if level not in level_results:
                level_results[level] = []
            level_results[level].append(result)
        
        level_metrics = {}
        for level, lvl_results in level_results.items():
            level_metrics[level] = self.compute_metrics(lvl_results)
        
        return level_metrics
    
    def compute_difficulty_drop_rate(
        self,
        level_metrics: Dict[str, EvaluationMetrics],
    ) -> Dict[str, float]:
        """
        Compute difficulty progression drop rate.
        
        Args:
            level_metrics: Metrics by level
            
        Returns:
            Drop rates between levels
        """
        drop_rates = {}
        
        levels = sorted(level_metrics.keys(), key=lambda x: int(x.split('_')[-1]) if x.startswith('level_') else 0)
        
        for i in range(len(levels) - 1):
            current = levels[i]
            next_level = levels[i + 1]
            
            current_acc = level_metrics[current].accuracy
            next_acc = level_metrics[next_level].accuracy
            
            if current_acc > 0:
                drop_rate = (current_acc - next_acc) / current_acc
                drop_rates[f"drop_{current}_to_{next_level}"] = drop_rate
        
        return drop_rates
    
    def compute_average_reasoning_steps(
        self,
        results: List[EvaluationResult],
    ) -> float:
        """Compute average reasoning steps for correct answers."""
        correct_results = [r for r in results if r.is_correct]
        
        if not correct_results:
            return 0.0
        
        total_steps = sum(
            r.metadata.get("reasoning_steps", 0)
            for r in correct_results
        )
        
        return total_steps / len(correct_results)
