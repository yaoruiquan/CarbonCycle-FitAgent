"""
BFCL evaluation tool.
BFCL 评估工具封装
"""

from typing import Any, Dict, Optional

from app.evaluation.benchmarks.bfcl.dataset import BFCLDataset
from app.evaluation.benchmarks.bfcl.evaluator import BFCLEvaluator
from app.evaluation.benchmarks.bfcl.metrics import BFCLMetrics


class BFCLEvaluationTool:
    """BFCL evaluation tool for easy integration."""
    
    def __init__(
        self,
        data_dir: str = "./data/bfcl",
        category: str = "simple_python",
    ):
        """
        Initialize BFCL evaluation tool.
        
        Args:
            data_dir: Directory containing BFCL data
            category: BFCL category to evaluate
        """
        self.data_dir = data_dir
        self.category = category
        self.dataset = BFCLDataset(data_dir=data_dir, category=category)
        self.evaluator = BFCLEvaluator(dataset=self.dataset)
        self.metrics = BFCLMetrics()
    
    def run(
        self,
        agent: Any,
        max_samples: Optional[int] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Run BFCL evaluation.
        
        Args:
            agent: Agent to evaluate
            max_samples: Maximum samples to evaluate
            
        Returns:
            Evaluation results
        """
        report = self.evaluator.evaluate(agent, max_samples=max_samples)
        
        return {
            "overall_accuracy": report.overall_metrics.accuracy,
            "correct_samples": report.correct_samples,
            "total_samples": report.total_samples,
            "category_metrics": {
                k: v.to_dict() for k, v in report.category_metrics.items()
            },
            "metadata": report.metadata,
        }
    
    def generate_report(
        self,
        results: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Generate markdown report."""
        report_lines = [
            "# BFCL 评估报告",
            "",
            f"**评估类别**: {self.category}",
            f"**总体准确率**: {results['overall_accuracy']:.2%}",
            f"**正确样本数**: {results['correct_samples']}/{results['total_samples']}",
            "",
            "## 分类准确率",
            "",
        ]
        
        for category, metrics in results.get("category_metrics", {}).items():
            report_lines.append(
                f"- **{category}**: {metrics['accuracy']:.2%} ({metrics.get('correct', 0)}/{metrics.get('total', 0)})"
            )
        
        report = "\n".join(report_lines)
        
        if output_file:
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
        
        return report
