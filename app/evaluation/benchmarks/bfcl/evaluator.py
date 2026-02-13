"""
BFCL evaluator.
BFCL 评估器 - 使用 AST 匹配算法评估工具调用能力
"""

import ast
import json
import re
from typing import Any, Dict, List, Optional
from datetime import datetime

from app.evaluation.base import (
    BaseEvaluator,
    BaseDataset,
    EvaluationResult,
    EvaluationMetrics,
    EvaluationReport,
)


class BFCLEvaluator(BaseEvaluator):
    """BFCL evaluator using AST matching."""
    
    def __init__(
        self,
        dataset: BaseDataset,
        evaluation_mode: str = "ast",
    ):
        """
        Initialize BFCL evaluator.
        
        Args:
            dataset: BFCL dataset
            evaluation_mode: Evaluation mode - "ast" or "exact"
        """
        super().__init__("BFCL")
        self.dataset = dataset
        self.evaluation_mode = evaluation_mode
    
    def evaluate(
        self,
        agent: Any,
        max_samples: Optional[int] = None,
        **kwargs,
    ) -> EvaluationReport:
        """
        Run BFCL evaluation on agent.
        
        Args:
            agent: Agent to evaluate
            max_samples: Maximum number of samples to evaluate
            
        Returns:
            Evaluation report
        """
        data = self.dataset.load()
        if max_samples:
            data = data[:max_samples]
        
        results = []
        for item in data:
            result = self._evaluate_single(agent, item)
            results.append(result)
        
        overall_metrics = self.compute_metrics(results)
        
        category_metrics = self._compute_category_metrics(results)
        
        report = EvaluationReport(
            benchmark_name="BFCL",
            evaluation_time=datetime.now().isoformat(),
            total_samples=len(results),
            correct_samples=sum(1 for r in results if r.is_correct),
            results=results,
            overall_metrics=overall_metrics,
            category_metrics=category_metrics,
            metadata={
                "category": self.dataset.category,
                "evaluation_mode": self.evaluation_mode,
            },
        )
        
        return report
    
    def _evaluate_single(
        self,
        agent: Any,
        sample: Dict[str, Any],
    ) -> EvaluationResult:
        """Evaluate a single sample."""
        sample_id = sample.get("id", "")
        question = sample.get("question", "")
        functions = sample.get("function", [])
        ground_truth = self.dataset.get_ground_truth(sample_id)
        
        try:
            prompt = self._build_prompt(question, functions)
            response = agent.run(prompt)
            
            predicted_calls = self._extract_function_calls(response)
            
            is_correct = self._compare_calls(
                predicted_calls,
                ground_truth.get("ground_truth", []) if ground_truth else [],
            )
            
            return EvaluationResult(
                sample_id=sample_id,
                input_data={"question": question, "functions": functions},
                expected_output=ground_truth,
                actual_output=predicted_calls,
                is_correct=is_correct,
                metrics=EvaluationMetrics(accuracy=1.0 if is_correct else 0.0),
            )
            
        except Exception as e:
            return EvaluationResult(
                sample_id=sample_id,
                input_data={"question": question, "functions": functions},
                expected_output=ground_truth,
                actual_output=None,
                is_correct=False,
                metrics=EvaluationMetrics(accuracy=0.0),
                error_message=str(e),
            )
    
    def _build_prompt(
        self,
        question: str,
        functions: List[Dict[str, Any]],
    ) -> str:
        """Build prompt for agent."""
        functions_str = json.dumps(functions, indent=2, ensure_ascii=False)
        
        prompt = f"""You have access to the following tools:

{functions_str}

Question: {question}

Please call the appropriate function(s) to answer the question.
If no function call is needed, respond with "NO_FUNCTION_CALL".
"""
        return prompt
    
    def _extract_function_calls(self, response: str) -> List[Dict[str, Any]]:
        """Extract function calls from agent response."""
        calls = []
        
        try:
            json_matches = re.findall(r'\{[^{}]*\}', response, re.DOTALL)
            for match in json_matches:
                try:
                    data = json.loads(match)
                    if isinstance(data, dict) and "name" in data:
                        calls.append(data)
                    elif isinstance(data, list):
                        for item in data:
                            if isinstance(item, dict) and "name" in item:
                                calls.append(item)
                except json.JSONDecodeError:
                    continue
        except Exception:
            pass
        
        return calls
    
    def _compare_calls(
        self,
        predicted: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
    ) -> bool:
        """Compare predicted calls with ground truth using AST matching."""
        if self.evaluation_mode == "ast":
            return self._ast_match(predicted, ground_truth)
        else:
            return predicted == ground_truth
    
    def _ast_match(
        self,
        predicted: List[Dict[str, Any]],
        ground_truth: List[Dict[str, Any]],
    ) -> bool:
        """AST matching for function calls."""
        if len(predicted) != len(ground_truth):
            return False
        
        for pred in predicted:
            pred_name = pred.get("name", "")
            pred_args = pred.get("arguments", {})
            
            matched = False
            for gt in ground_truth:
                gt_name = gt.get("function_name", {})
                if isinstance(gt_name, dict):
                    gt_name = gt_name.get("name", "")
                
                if pred_name == gt_name:
                    gt_args = gt.get("arguments", {})
                    if self._args_match(pred_args, gt_args):
                        matched = True
                        break
            
            if not matched:
                return False
        
        return True
    
    def _args_match(
        self,
        pred_args: Dict[str, Any],
        gt_args: Dict[str, Any],
    ) -> bool:
        """Check if arguments match (ignoring order)."""
        if not pred_args and not gt_args:
            return True
        
        if set(pred_args.keys()) != set(gt_args.keys()):
            return False
        
        for key in pred_args:
            pred_val = pred_args[key]
            gt_val = gt_args[key]
            
            if not self._value_match(pred_val, gt_val):
                return False
        
        return True
    
    def _value_match(self, pred_val: Any, gt_val: Any) -> bool:
        """Check if values match (including equivalent expressions)."""
        if pred_val == gt_val:
            return True
        
        try:
            pred_str = str(pred_val)
            gt_str = str(gt_val)
            
            pred_ast = ast.parse(pred_str, mode="eval")
            gt_ast = ast.parse(gt_str, mode="eval")
            
            return ast.dump(pred_ast) == ast.dump(gt_ast)
        except Exception:
            return False
    
    def _compute_category_metrics(
        self,
        results: List[EvaluationResult],
    ) -> Dict[str, EvaluationMetrics]:
        """Compute metrics by category."""
        category_results: Dict[str, List[EvaluationResult]] = {}
        
        for result in results:
            category = result.sample_id.split("_")[0] if result.sample_id else "unknown"
            if category not in category_results:
                category_results[category] = []
            category_results[category].append(result)
        
        category_metrics = {}
        for category, cat_results in category_results.items():
            metrics = self.compute_metrics(cat_results)
            category_metrics[category] = metrics
        
        return category_metrics
    
    def export_to_bfcl_format(
        self,
        results: EvaluationReport,
        output_path: str,
    ) -> None:
        """Export results to BFCL official format."""
        output_data = []
        
        for result in results.results:
            output_data.append({
                "id": result.sample_id,
                "result": result.actual_output,
            })
        
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output_data, f, indent=2, ensure_ascii=False)


import os
