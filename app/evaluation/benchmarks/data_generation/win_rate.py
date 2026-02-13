"""
Win Rate evaluator.
Win Rate 评估器 - 评估模型对比中的胜率
"""

from typing import Any, Dict, List, Optional
import random

from app.evaluation.base import EvaluationMetrics


class WinRateEvaluator:
    """Win Rate evaluator for comparing two models."""
    
    def __init__(
        self,
        judge_llm: Optional[Any] = None,
    ):
        """
        Initialize Win Rate evaluator.
        
        Args:
            judge_llm: LLM to judge which output is better
        """
        self.judge_llm = judge_llm
    
    def evaluate(
        self,
        outputs_a: List[str],
        outputs_b: List[str],
        references: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Evaluate win rate between two sets of outputs.
        
        Args:
            outputs_a: Outputs from model A
            outputs_b: Outputs from model B
            references: Reference outputs (optional)
            
        Returns:
            Win rate statistics
        """
        if len(outputs_a) != len(outputs_b):
            raise ValueError("Output lists must have the same length")
        
        wins_a = 0
        wins_b = 0
        ties = 0
        details = []
        
        for i, (output_a, output_b) in enumerate(zip(outputs_a, outputs_b)):
            reference = references[i] if references else None
            
            result = self._compare(
                output_a,
                output_b,
                reference,
            )
            
            if result == "a":
                wins_a += 1
            elif result == "b":
                wins_b += 1
            else:
                ties += 1
            
            details.append({
                "output_a": output_a,
                "output_b": output_b,
                "reference": reference,
                "winner": result,
            })
        
        total = len(outputs_a)
        
        stats = {
            "total": total,
            "wins_a": wins_a,
            "wins_b": wins_b,
            "ties": ties,
            "win_rate_a": wins_a / total if total > 0 else 0.0,
            "win_rate_b": wins_b / total if total > 0 else 0.0,
            "tie_rate": ties / total if total > 0 else 0.0,
            "details": details,
        }
        
        return stats
    
    def _compare(
        self,
        output_a: str,
        output_b: str,
        reference: Optional[str] = None,
    ) -> str:
        """
        Compare two outputs and determine winner.
        
        Returns:
            "a" if A wins, "b" if B wins, "tie" if equal
        """
        if self.judge_llm:
            return self._llm_judge(output_a, output_b, reference)
        else:
            return self._default_compare(output_a, output_b, reference)
    
    def _llm_judge(
        self,
        output_a: str,
        output_b: str,
        reference: Optional[str],
    ) -> str:
        """Use LLM to judge which output is better."""
        prompt = f"""Compare the following two outputs and determine which is better.

Output A: {output_a}

Output B: {output_b}

{"Reference: " + reference if reference else ""}

Respond with only one of these options:
- "A" if Output A is better
- "B" if Output B is better
- "TIE" if they are equally good or bad"""

        response = self.judge_llm.chat(prompt).strip().upper()
        
        if "A" in response and "B" not in response:
            return "a"
        elif "B" in response:
            return "b"
        else:
            return "tie"
    
    def _default_compare(
        self,
        output_a: str,
        output_b: str,
        reference: Optional[str],
    ) -> str:
        """Default comparison using reference if available."""
        if not reference:
            if len(output_a) > len(output_b):
                return "a"
            elif len(output_b) > len(output_a):
                return "b"
            return "tie"
        
        from difflib import SequenceMatcher
        
        ratio_a = SequenceMatcher(None, output_a, reference).ratio()
        ratio_b = SequenceMatcher(None, output_b, reference).ratio()
        
        if ratio_a > ratio_b:
            return "a"
        elif ratio_b > ratio_a:
            return "b"
        return "tie"
    
    def compute_metrics(
        self,
        results: Dict[str, Any],
    ) -> EvaluationMetrics:
        """Compute metrics from win rate results."""
        return EvaluationMetrics(
            accuracy=results.get("win_rate_a", 0.0),
            extra={
                "win_rate_b": results.get("win_rate_b", 0.0),
                "tie_rate": results.get("tie_rate", 0.0),
            },
        )
