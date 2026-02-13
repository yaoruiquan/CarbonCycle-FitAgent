"""
GAIA evaluator.
GAIA 评估器 - 使用准精确匹配算法评估通用AI助手能力
"""

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

GAIA_SYSTEM_PROMPT = """You are a general AI assistant. I will ask you a question. Report your thoughts, and finish your answer with the following template: FINAL ANSWER: [YOUR FINAL ANSWER].

YOUR FINAL ANSWER should be a number OR as few words as possible OR a comma separated list of numbers and/or strings.

If you are asked for a number, don't use comma to write your number neither use units such as $ or percent sign unless specified otherwise.

If you are asked for a string, don't use articles, neither abbreviations (e.g. for cities), and write the digits in plain text unless specified otherwise.

If you are asked for a comma separated list, apply the above rules depending of whether the element to be put in the list is a number or a string."""


class GAIAEvaluator(BaseEvaluator):
    """GAIA evaluator using quasi-exact match."""
    
    def __init__(
        self,
        dataset: BaseDataset,
    ):
        """
        Initialize GAIA evaluator.
        
        Args:
            dataset: GAIA dataset
        """
        super().__init__("GAIA")
        self.dataset = dataset
    
    def evaluate(
        self,
        agent: Any,
        max_samples: Optional[int] = None,
        **kwargs,
    ) -> EvaluationReport:
        """
        Run GAIA evaluation on agent.
        
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
        
        category_metrics = self._compute_level_metrics(results)
        
        report = EvaluationReport(
            benchmark_name="GAIA",
            evaluation_time=datetime.now().isoformat(),
            total_samples=len(results),
            correct_samples=sum(1 for r in results if r.is_correct),
            results=results,
            overall_metrics=overall_metrics,
            category_metrics=category_metrics,
            metadata={
                "level": self.dataset.level,
            },
        )
        
        return report
    
    def _evaluate_single(
        self,
        agent: Any,
        sample: Dict[str, Any],
    ) -> EvaluationResult:
        """Evaluate a single sample."""
        task_id = sample.get("task_id", "")
        question = sample.get("Question", "")
        level = sample.get("Level", 1)
        final_answer = sample.get("Final answer", "")
        
        try:
            prompt = self._build_prompt(question)
            response = agent.run(prompt)
            
            predicted_answer = self._extract_answer(response)
            
            is_correct = self._quasi_exact_match(predicted_answer, final_answer)
            
            return EvaluationResult(
                sample_id=task_id,
                input_data={"question": question, "level": level},
                expected_output=final_answer,
                actual_output=predicted_answer,
                is_correct=is_correct,
                metrics=EvaluationMetrics(accuracy=1.0 if is_correct else 0.0),
            )
            
        except Exception as e:
            return EvaluationResult(
                sample_id=task_id,
                input_data={"question": question, "level": level},
                expected_output=final_answer,
                actual_output=None,
                is_correct=False,
                metrics=EvaluationMetrics(accuracy=0.0),
                error_message=str(e),
            )
    
    def _build_prompt(self, question: str) -> str:
        """Build prompt for agent."""
        return f"{GAIA_SYSTEM_PROMPT}\n\nQuestion: {question}"
    
    def _extract_answer(self, response: str) -> str:
        """Extract answer from agent response."""
        match = re.search(r'FINAL ANSWER:\s*(.+)', response, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        
        lines = response.strip().split("\n")
        if lines:
            return lines[-1].strip()
        
        return response.strip()
    
    def _quasi_exact_match(
        self,
        predicted: str,
        ground_truth: str,
    ) -> bool:
        """Quasi-exact match algorithm."""
        pred_normalized = self._normalize(predicted)
        gt_normalized = self._normalize(ground_truth)
        
        return pred_normalized == gt_normalized
    
    def _normalize(self, answer: str) -> str:
        """
        Normalize answer for comparison.
        
        Applies different normalization rules based on answer type:
        - Numbers: remove commas and units
        - Strings: lowercase, remove articles
        - Lists: sort and normalize elements
        """
        if not answer:
            return ""
        
        answer = answer.strip()
        
        is_number = self._is_number(answer)
        
        if is_number:
            answer = re.sub(r'[\$,%€£]', '', answer)
            answer = answer.replace(',', '')
            answer = re.sub(r'\s+', '', answer)
            return answer.lower()
        
        if ',' in answer:
            parts = [p.strip() for p in answer.split(',')]
            normalized_parts = [self._normalize_string(p) for p in parts]
            normalized_parts.sort()
            return ','.join(normalized_parts)
        
        return self._normalize_string(answer)
    
    def _is_number(self, answer: str) -> bool:
        """Check if answer is a number."""
        cleaned = re.sub(r'[\$,%€£]', '', answer)
        cleaned = cleaned.replace(',', '')
        try:
            float(cleaned)
            return True
        except ValueError:
            return False
    
    def _normalize_string(self, text: str) -> str:
        """Normalize string answer."""
        text = text.lower()
        
        articles = ['the ', 'a ', 'an ']
        for article in articles:
            if text.startswith(article):
                text = text[len(article):]
        
        text = re.sub(r'[.\!?,\:;]$', '', text)
        
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _compute_level_metrics(
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
            metrics = self.compute_metrics(lvl_results)
            level_metrics[f"level_{level}"] = metrics
        
        return level_metrics
    
    def compute_difficulty_drop_rate(
        self,
        level_metrics: Dict[str, EvaluationMetrics],
    ) -> Dict[str, float]:
        """Compute difficulty progression drop rate."""
        drop_rates = {}
        
        for i in range(1, 3):
            current_level = f"level_{i}"
            next_level = f"level_{i+1}"
            
            if current_level in level_metrics and next_level in level_metrics:
                current_acc = level_metrics[current_level].accuracy
                next_acc = level_metrics[next_level].accuracy
                
                if current_acc > 0:
                    drop_rate = (current_acc - next_acc) / current_acc
                    drop_rates[f"drop_{i}_to_{i+1}"] = drop_rate
        
        return drop_rates
