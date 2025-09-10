"""
Mapping Module
Implements Scenario Mapping theme from Protocol Room Protocol
"""

from typing import List, Optional
from .room_types import ScenarioMapping, Protocols, Scenarios


# Static scenario mapping registry - deterministic only, no AI or heuristics
SCENARIO_REGISTRY: List[ScenarioMapping] = [
    ScenarioMapping(Scenarios.OVERWHELM, Protocols.RESOURCING_MINI_WALK, 9),
    ScenarioMapping(Scenarios.URGENCY, Protocols.CLEARING_ENTRY, 8),
    ScenarioMapping(Scenarios.BOUNDARY_VIOLATION, Protocols.BOUNDARY_SETTING, 9),
    ScenarioMapping(Scenarios.COMMUNICATION_BREAKDOWN, Protocols.DEEP_LISTENING, 8),
    ScenarioMapping(Scenarios.DECISION_FATIGUE, Protocols.INTEGRATION_PAUSE, 7),
    ScenarioMapping(Scenarios.TEAM_CONFLICT, Protocols.DEEP_LISTENING, 8),
    ScenarioMapping(Scenarios.PERSONAL_CRISIS, Protocols.RESOURCING_MINI_WALK, 9),
    ScenarioMapping(Scenarios.GROWTH_EDGE, Protocols.PACING_ADJUSTMENT, 7),
    
    # Additional mappings for common scenarios
    ScenarioMapping("stress", Protocols.RESOURCING_MINI_WALK, 8),
    ScenarioMapping("confusion", Protocols.CLEARING_ENTRY, 9),
    ScenarioMapping("exhaustion", Protocols.INTEGRATION_PAUSE, 8),
    ScenarioMapping("stuck", Protocols.CLEARING_ENTRY, 8),
    ScenarioMapping("transition", Protocols.PACING_ADJUSTMENT, 7),
    ScenarioMapping("conflict", Protocols.DEEP_LISTENING, 8),
    ScenarioMapping("growth", Protocols.PACING_ADJUSTMENT, 7),
    ScenarioMapping("integration", Protocols.INTEGRATION_PAUSE, 9)
]


def map_scenario_to_protocol(scenario_label: str) -> Optional[str]:
    """
    Deterministic scenario to protocol mapping.
    Uses static registry only - no AI, no heuristics.
    """
    scenario_lower = scenario_label.lower().strip()
    
    # Exact match first
    for mapping in SCENARIO_REGISTRY:
        if mapping.scenario_label.lower() == scenario_lower:
            return mapping.protocol_id
    
    # Partial match for common variations
    for mapping in SCENARIO_REGISTRY:
        if scenario_lower in mapping.scenario_label.lower() or mapping.scenario_label.lower() in scenario_lower:
            return mapping.protocol_id
    
    # Default mapping for unknown scenarios
    return Protocols.DEFAULT


def get_scenario_mapping(scenario_label: str) -> Optional[ScenarioMapping]:
    """
    Get full scenario mapping information.
    Returns None if no mapping found.
    """
    scenario_lower = scenario_label.lower().strip()
    
    for mapping in SCENARIO_REGISTRY:
        if mapping.scenario_label.lower() == scenario_lower:
            return mapping
    
    return None


def list_scenario_mappings() -> List[ScenarioMapping]:
    """List all available scenario mappings"""
    return SCENARIO_REGISTRY.copy()


def get_related_protocols(protocol_id: str) -> List[str]:
    """
    Get list of protocols that might be related.
    Deterministic selection based on static relationships.
    """
    related = []
    
    if protocol_id == Protocols.RESOURCING_MINI_WALK:
        related = [Protocols.CLEARING_ENTRY, Protocols.INTEGRATION_PAUSE]
    elif protocol_id == Protocols.CLEARING_ENTRY:
        related = [Protocols.RESOURCING_MINI_WALK, Protocols.PACING_ADJUSTMENT]
    elif protocol_id == Protocols.PACING_ADJUSTMENT:
        related = [Protocols.CLEARING_ENTRY, Protocols.INTEGRATION_PAUSE]
    elif protocol_id == Protocols.INTEGRATION_PAUSE:
        related = [Protocols.RESOURCING_MINI_WALK, Protocols.PACING_ADJUSTMENT]
    else:
        related = [Protocols.CLEARING_ENTRY, Protocols.RESOURCING_MINI_WALK]
    
    return related
