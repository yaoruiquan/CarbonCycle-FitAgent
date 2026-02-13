"""
LLM Judge evaluator.
LLM Judge 评估器 - 使用大模型评估生成数据质量
"""

from typing import Any, Dict, List, Optional

from app.evaluation.base import EvaluationMetrics


class LLMJudge:
    """LLM Judge for evaluating generated data quality."""
    
    def __init__(
        self,
        llm: Any,
        evaluation_prompt: Optional[str] = None,
    ):
        """
        Initialize LLM Judge.
        
        Args:
            llm: LLM client for evaluation
            evaluation_prompt: Custom evaluation prompt
        """
        self.llm = llm
        self.evaluation_prompt = evaluation_prompt or self._default_prompt()
    
    def _default_prompt(self) -> str:
        """Default evaluation prompt."""
        return """You are an expert evaluator. Please evaluate the quality of the generated output compared to the reference.

Output: {output}
Reference: {reference}

Rate the quality on a scale of 0-100, where:
- 90-100: Excellent - Output is correct and well-formed
- 70-89: Good - Output is mostly correct with minor issues
- 50-69: Fair - Output has some correct elements but significant issues
- 0-49: Poor - Output is incorrect or not useful

Provide your evaluation in the following format:
SCORE: [your score]
REASON: [brief explanation]"""
    
    def evaluate(
        self,
        output: str,
        reference: str,
    ) -> Dict[str, Any]:
        """
        Evaluate a single output.
        
        Args:
            output: Generated output
            reference: Reference output
            
        Returns:
            Evaluation result with score and reason
        """
        prompt = self.evaluation_prompt.format(
            output=output,
            reference=reference,
        )
        
        response = self.llm.chat(prompt)
        
        score = self._extract_score(response)
        reason = self._extract_reason(response)
        
        return {
            "score": score,
            "reason": reason,
            "output": output,
            "reference": reference,
        }
    
    def evaluate_batch(
        self,
        outputs: List[str],
        references: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Evaluate multiple outputs.
        
        Args:
            outputs: List of generated outputs
            references: List of reference outputs
            
        Returns:
            List of evaluation results
        """
        results = []
        
        for output, reference in zip(outputs, references):
            result = self.evaluate(output, reference)
            results.append(result)
        
        return results
    
    def compute_average_score(
        self,
        results: List[Dict[str, Any]],
    ) -> float:
        """Compute average score."""
        if not results:
            return 0.0
        
        total = sum(r.get("score", 0) for r in results)
        return total / len(results)
    
    def _extract_score(self, response: str) -> int:
        """Extract score from LLM response."""
        import re
        
        match = re.search(r'SCORE:\s*(\d+)', response, re.IGNORECASE)
        if match:
            return int(match.group(1))
        
        numbers = re.findall(r'\d+', response)
        if numbers:
            return min(int(numbers[0]), 100)
        
        return 0
    
    def _extract_reason(self, response: str) -> str:
        """Extract reason from LLM response."""
        import re
        
        match = re.search(r'REASON:\s*(.+)', response, re.IGNORECASE | re.DOTALL)
        if match:
            return match.group(1).strip()
        
        return response.strip()
