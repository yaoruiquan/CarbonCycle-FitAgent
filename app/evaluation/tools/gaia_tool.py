"""
GAIA evaluation tool.
GAIA 评估工具封装
"""

from typing import Any, Dict, Optional

from app.evaluation.benchmarks.gaia.dataset import GAIADataset
from app.evaluation.benchmarks.gaia.evaluator import GAIAEvaluator
from app.evaluation.benchmarks.gaia.metrics import GAIAMetrics


class GAIAEvaluationTool:
    """GAIA evaluation tool for easy integration."""
    
    def __init__(
        self,
        dataset_name: str = "gaia-benchmark/GAIA",
        split: str = "validation",
        level: Optional[int] = None,
    ):
        """
        Initialize GAIA evaluation tool.
        
        Args:
            dataset_name: HuggingFace dataset name
            split: Dataset split
            level: Difficulty level (1, 2, 3) or None for all
        """
        self.dataset_name = dataset_name
        self.split = split
        self.level = level
        self.dataset = GAIADataset(
            dataset_name=dataset_name,
            split=split,
            level=level,
        )
        self.evaluator = GAIAEvaluator(dataset=self.dataset)
        self.metrics = GAIAMetrics()
    
    def run(
        self,
        agent: Any,
        max_samples: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Run GAIA evaluation.
        
        Args:
            agent: Agent to evaluate
            max_samples: Maximum samples to evaluate
            
        Returns:
            Evaluation results
        """
        report = self.evaluator.evaluate(agent, max_samples=max_samples)
        
        drop_rates = self.evaluator.compute_difficulty_drop_rate(
            report.category_metrics
        )
        
        return {
            "overall_accuracy": report.overall_metrics.accuracy,
            "correct_samples": report.correct_samples,
            "total_samples": report.total_samples,
            "level_metrics": {
                k: v.to_dict() for k, v in report.category_metrics.items()
            },
            "difficulty_drop_rates": drop_rates,
            "metadata": report.metadata,
        }
    
    def generate_report(
        self,
        results: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Generate markdown report."""
        report_lines = [
            "# GAIA 评估报告",
            "",
            f"**总体准确率**: {results['overall_accuracy']:.2%}",
            f"**正确样本数**: {results['correct_samples']}/{results['total_samples']}",
            "",
            "## 分级准确率",
            "",
        ]
        
        for level, metrics in results.get("level_metrics", {}).items():
            report_lines.append(
                f"- **{level}**: {metrics['accuracy']:.2%}"
            )
        
        drop_rates = results.get("difficulty_drop_rates", {})
        if drop_rates:
            report_lines.append("")
            report_lines.append("## 难度递进下降率")
            report_lines.append("")
            for key, value in drop_rates.items():
                report_lines.append(f"- **{key}**: {value:.2%}")
        
        report = "\n".join(report_lines)
        
        if output_file:
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
        
        return report
