"""
GAIA dataset loader.
GAIA 数据集加载器
"""

import os
from typing import Any, Dict, List, Optional

try:
    from datasets import load_dataset
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False


class GAIADataset:
    """GAIA (General AI Assistants) dataset loader."""
    
    def __init__(
        self,
        dataset_name: str = "gaia-benchmark/GAIA",
        split: str = "validation",
        level: Optional[int] = None,
        data_dir: str = "./data/gaia",
    ):
        """
        Initialize GAIA dataset loader.
        
        Args:
            dataset_name: HuggingFace dataset name
            split: Dataset split (validation or test)
            level: Difficulty level (1, 2, 3) or None for all
            data_dir: Local data directory
        """
        self.dataset_name = dataset_name
        self.split = split
        self.level = level
        self.data_dir = data_dir
        self.data = []
    
    def load(self) -> List[Dict[str, Any]]:
        """
        Load GAIA dataset.
        
        Returns:
            List of test samples
        """
        if not HF_AVAILABLE:
            return self._load_from_local()
        
        try:
            dataset = load_dataset(
                self.dataset_name,
                split=self.split,
            )
            
            data = []
            for item in dataset:
                if self.level is None or item.get("Level") == self.level:
                    data.append(item)
            
            self.data = data
            return data
            
        except Exception:
            return self._load_from_local()
    
    def _load_from_local(self) -> List[Dict[str, Any]]:
        """Load from local files."""
        metadata_file = os.path.join(
            self.data_dir,
            "2023",
            self.split,
            "metadata.jsonl"
        )
        
        if not os.path.exists(metadata_file):
            return []
        
        data = []
        with open(metadata_file, "r", encoding="utf-8") as f:
            for line in f:
                item = eval(line.strip())
                if self.level is None or item.get("Level") == self.level:
                    data.append(item)
        
        self.data = data
        return data
    
    def get_sample(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific sample by ID."""
        for item in self.data:
            if item.get("task_id") == task_id:
                return item
        return None
    
    def get_by_level(self, level: int) -> List[Dict[str, Any]]:
        """Get samples by difficulty level."""
        return [item for item in self.data if item.get("Level") == level]
    
    def get_level_distribution(self) -> Dict[int, int]:
        """Get distribution of samples by level."""
        distribution = {1: 0, 2: 0, 3: 0}
        for item in self.data:
            level = item.get("Level")
            if level in distribution:
                distribution[level] += 1
        return distribution
