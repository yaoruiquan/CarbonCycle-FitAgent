"""
BFCL dataset loader.
BFCL 数据集加载器
"""

import json
import os
from typing import Any, Dict, List, Optional


class BFCLDataset:
    """BFCL (Berkeley Function Calling Leaderboard) dataset loader."""
    
    BFCL_CATEGORIES = [
        "simple_python",
        "simple_java", 
        "simple_javascript",
        "multiple",
        "parallel",
        "parallel_multiple",
        "irrelevance",
        "relevance",
    ]
    
    def __init__(
        self,
        data_dir: str = "./data/bfcl",
        category: str = "simple_python",
    ):
        """
        Initialize BFCL dataset loader.
        
        Args:
            data_dir: Directory containing BFCL data files
            category: BFCL category to load
        """
        self.data_dir = data_dir
        self.category = category
        self.data = []
        self.ground_truth = {}
    
    def load(self) -> List[Dict[str, Any]]:
        """
        Load BFCL dataset.
        
        Returns:
            List of test samples
        """
        data_file = os.path.join(
            self.data_dir, 
            f"BFCL_v4_{self.category}.json"
        )
        ground_truth_file = os.path.join(
            self.data_dir,
            "possible_answer",
            f"BFCL_v4_{self.category}.json"
        )
        
        if os.path.exists(data_file):
            with open(data_file, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        
        if os.path.exists(ground_truth_file):
            with open(ground_truth_file, "r", encoding="utf-8") as f:
                self.ground_truth = {item["id"]: item for item in json.load(f)}
        
        return self.data
    
    def get_available_categories(self) -> List[str]:
        """Get available BFCL categories."""
        if os.path.exists(self.data_dir):
            files = os.listdir(self.data_dir)
            categories = [
                f.replace("BFCL_v4_", "").replace(".json", "")
                for f in files
                if f.startswith("BFCL_v4_") and f.endswith(".json")
            ]
            return categories
        return self.BFCL_CATEGORIES
    
    def get_sample(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific sample by ID."""
        for item in self.data:
            if item.get("id") == sample_id:
                return item
        return None
    
    def get_ground_truth(self, sample_id: str) -> Optional[Dict[str, Any]]:
        """Get ground truth for a sample."""
        return self.ground_truth.get(sample_id)
