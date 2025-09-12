"""
Configuration for RAG evaluation harness with lane targets and thresholds.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class LaneTargets:
    """Target metrics for a RAG evaluation lane."""
    precision_at_5: float
    recall_at_20: float
    mrr_at_10: float
    ndcg_at_10: float
    coverage: float
    latency_ms_p95: float
    diversity_min_unique_docs_top8: float
    stones_alignment: float
    grounding_score_1to5: float
    hallucination_rate: float
    answer_consistency: float


# Threshold constants for tolerance bands
GREEN_TOL = 0.00
AMBER_TOL = 0.10

# Lane targets
FAST = LaneTargets(
    precision_at_5=0.40,
    recall_at_20=0.70,
    mrr_at_10=0.35,
    ndcg_at_10=0.55,
    coverage=0.95,
    latency_ms_p95=300,
    diversity_min_unique_docs_top8=3,
    stones_alignment=0.70,
    grounding_score_1to5=4.0,
    hallucination_rate=0.02,
    answer_consistency=0.85
)

ACCURATE = LaneTargets(
    precision_at_5=0.60,
    recall_at_20=0.85,
    mrr_at_10=0.50,
    ndcg_at_10=0.70,
    coverage=0.95,
    latency_ms_p95=800,
    diversity_min_unique_docs_top8=3,
    stones_alignment=0.80,
    grounding_score_1to5=4.5,
    hallucination_rate=0.01,
    answer_consistency=0.85
)

# Lane configuration mapping
LANE_TARGETS: Dict[str, LaneTargets] = {
    "fast": FAST,
    "accurate": ACCURATE
}


def get_lane_targets(lane: str) -> LaneTargets:
    """Get the target metrics for a specific lane."""
    if lane not in LANE_TARGETS:
        raise ValueError(f"Unknown lane: {lane}. Available lanes: {list(LANE_TARGETS.keys())}")
    return LANE_TARGETS[lane]


def evaluate_metric_band(actual: float, target: float, higher_is_better: bool = True) -> str:
    """
    Determine if a metric meets GREEN, AMBER, or RED criteria.
    
    Args:
        actual: The actual metric value
        target: The target threshold
        higher_is_better: True if higher values are better (e.g., precision), False for latency
        
    Returns:
        "GREEN", "AMBER", or "RED"
    """
    if higher_is_better:
        if actual >= target:
            return "GREEN"
        elif actual >= target * (1 - AMBER_TOL):
            return "AMBER"
        else:
            return "RED"
    else:
        if actual <= target:
            return "GREEN"
        elif actual <= target * (1 + AMBER_TOL):
            return "AMBER"
        else:
            return "RED"
