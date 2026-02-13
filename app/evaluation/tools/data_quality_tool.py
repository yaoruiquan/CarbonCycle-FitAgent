"""
Data generation quality evaluation tool.
数据生成质量评估工具
"""

from typing import Any, Dict, List, Optional

from app.evaluation.benchmarks.data_generation.llm_judge import LLMJudge
from app.evaluation.benchmarks.data_generation.win_rate import WinRateEvaluator


class DataQualityEvaluationTool:
    """Data generation quality evaluation tool."""
    
    def __init__(
        self,
        judge_llm: Optional[Any] = None,
    ):
        """
        Initialize data quality evaluation tool.
        
        Args:
            judge_llm: LLM for judging quality
        """
        self.judge_llm = judge_llm
        self.llm_judge = LLMJudge(llm=judge_llm) if judge_llm else None
        self.win_rate = WinRateEvaluator(judge_llm=judge_llm)
    
    def evaluate_with_reference(
        self,
        outputs: List[str],
        references: List[str],
    ) -> Dict[str, Any]:
        """
        Evaluate outputs against references.
        
        Args:
            outputs: Generated outputs
            references: Reference outputs
            
        Returns:
            Evaluation results
        """
        if self.llm_judge:
            results = self.llm_judge.evaluate_batch(outputs, references)
            avg_score = self.llm_judge.compute_average_score(results)
            
            return {
                "method": "llm_judge",
                "average_score": avg_score,
                "total_samples": len(outputs),
                "results": results,
            }
        else:
            return self._simple_evaluate(outputs, references)
    
    def evaluate_comparison(
        self,
        outputs_a: List[str],
        outputs_b: List[str],
        references: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Compare two sets of outputs.
        
        Args:
            outputs_a: Outputs from model A
            outputs_b: Outputs from model B
            references: Reference outputs
            
        Returns:
            Win rate statistics
        """
        stats = self.win_rate.evaluate(outputs_a, outputs_b, references)
        
        return {
            "method": "win_rate",
            "model_a_win_rate": stats["win_rate_a"],
            "model_b_win_rate": stats["win_rate_b"],
            "tie_rate": stats["tie_rate"],
            "total": stats["total"],
        }
    
    def _simple_evaluate(
        self,
        outputs: List[str],
        references: List[str],
    ) -> Dict[str, Any]:
        """Simple evaluation without LLM."""
        correct = 0
        
        for output, reference in zip(outputs, references):
            if output.strip().lower() == reference.strip().lower():
                correct += 1
        
        return {
            "method": "exact_match",
            "accuracy": correct / len(outputs) if outputs else 0.0,
            "correct": correct,
            "total": len(outputs),
        }
    
    def generate_report(
        self,
        results: Dict[str, Any],
        output_file: Optional[str] = None,
    ) -> str:
        """Generate markdown report."""
        method = results.get("method", "unknown")
        
        report_lines = [
            "# 数据生成质量评估报告",
            "",
            f"**评估方法**: {method}",
        ]
        
        if method == "llm_judge":
            report_lines.extend([
                f"**平均分数**: {results.get('average_score', 0):.2f}/100",
                f"**样本数**: {results.get('total', 0)}",
            ])
        elif method == "win_rate":
            report_lines.extend([
                f"**模型A胜率**: {results.get('model_a_win_rate', 0):.2%}",
                f"**模型B胜率**: {results.get('model_b_win_rate', 0):.2%}",
                f"**平局率**: {results.get('tie_rate', 0):.2%}",
            ])
        elif method == "exact_match":
            report_lines.extend([
                f"**准确率**: {results.get('accuracy', 0):.2%}",
                f"**正确数**: {results.get('correct', 0)}/{results.get('total', 0)}",
            ])
        
        report = "\n".join(report_lines)
        
        if output_file:
            import os
            os.makedirs(os.path.dirname(output_file), exist_ok=True)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(report)
        
        return report
