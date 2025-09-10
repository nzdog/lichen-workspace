from typing import List, Optional, Dict, Any
from .contract_types import CaptureData, MemoryItem, GovernanceResult


class MemoryGovernance:
    """Applies Stones-aligned integrity rules to memory operations"""
    
    @staticmethod
    def apply_integrity_linter(capture_data: CaptureData) -> GovernanceResult:
        """
        Apply integrity linter rules to capture data.
        Ensures data quality and consistency.
        """
        # Check for required fields
        required_fields = [
            'tone_label', 'residue_label', 'readiness_state',
            'integration_notes', 'commitments'
        ]
        
        missing_fields = []
        for field in required_fields:
            if not hasattr(capture_data, field) or getattr(capture_data, field) is None:
                missing_fields.append(field)
        
        if missing_fields:
            return GovernanceResult(
                is_allowed=False,
                reason=f"Integrity linter failed: missing required fields: {', '.join(missing_fields)}",
                filtered_data=None
            )
        
        # Check for empty string fields (should be "unspecified" instead)
        empty_fields = []
        for field in required_fields:
            value = getattr(capture_data, field)
            if value == "":
                empty_fields.append(field)
        
        if empty_fields:
            return GovernanceResult(
                is_allowed=False,
                reason=f"Integrity linter failed: empty fields should be 'unspecified': {', '.join(empty_fields)}",
                filtered_data=None
            )
        
        return GovernanceResult(
            is_allowed=True,
            reason="Integrity linter passed: all required fields present and valid",
            filtered_data=capture_data
        )
    
    @staticmethod
    def apply_stones_alignment_filter(capture_data: CaptureData) -> GovernanceResult:
        """
        Apply Stones alignment filter to capture data.
        Ensures alignment with stewardship and walking-with principles.
        """
        # Check for potential misalignment indicators
        misalignment_indicators = [
            "surveillance", "tracking", "monitoring", "extraction",
            "ownership", "possession", "control", "manipulation",
            "deception", "coercion", "pressure", "urgency"
        ]
        
        text_lower = " ".join([
            capture_data.tone_label.lower(),
            capture_data.residue_label.lower(),
            capture_data.integration_notes.lower(),
            capture_data.commitments.lower()
        ])
        
        # Count misalignment indicators
        misalignment_count = sum(1 for indicator in misalignment_indicators 
                               if indicator in text_lower)
        
        if misalignment_count > 0:
            return GovernanceResult(
                is_allowed=False,
                reason=f"Stones alignment failed: {misalignment_count} misalignment indicators detected",
                filtered_data=None
            )
        
        # Check for positive alignment indicators
        alignment_indicators = [
            "stewardship", "care", "respect", "safety", "trust",
            "walking", "accompanying", "supporting", "enabling",
            "honoring", "remembering", "continuity", "wholeness"
        ]
        
        alignment_count = sum(1 for indicator in alignment_indicators 
                             if indicator in text_lower)
        
        # More lenient: allow data with no explicit positive indicators if no misalignment
        # This prevents overly strict filtering of neutral or simple data
        if alignment_count == 0 and misalignment_count == 0:
            return GovernanceResult(
                is_allowed=True,
                reason="Stones alignment passed: neutral data with no misalignment indicators",
                filtered_data=capture_data
            )
        
        return GovernanceResult(
            is_allowed=True,
            reason=f"Stones alignment passed: {alignment_count} positive indicators detected",
            filtered_data=capture_data
        )
    
    @staticmethod
    def apply_coherence_gate(capture_data: CaptureData) -> GovernanceResult:
        """
        Apply coherence gate to capture data.
        Ensures data is coherent and meaningful.
        """
        # Check for reasonable field lengths
        max_lengths = {
            'tone_label': 50,
            'residue_label': 50,
            'readiness_state': 20,
            'integration_notes': 200,
            'commitments': 200
        }
        
        excessive_fields = []
        for field, max_len in max_lengths.items():
            value = getattr(capture_data, field)
            if len(value) > max_len:
                excessive_fields.append(f"{field} ({len(value)} chars, max {max_len})")
        
        if excessive_fields:
            return GovernanceResult(
                is_allowed=False,
                reason=f"Coherence gate failed: excessive field lengths: {', '.join(excessive_fields)}",
                filtered_data=None
            )
        
        # Check for repetitive or nonsensical content
        if capture_data.tone_label == capture_data.residue_label == capture_data.readiness_state:
            if capture_data.tone_label not in ["unspecified", "neutral", "calm"]:
                return GovernanceResult(
                    is_allowed=False,
                    reason="Coherence gate failed: identical values across core fields suggest data quality issues",
                    filtered_data=None
                )
        
        # Check for reasonable content patterns
        if capture_data.tone_label == "unspecified" and capture_data.residue_label == "unspecified":
            # If both core fields are unspecified, integration notes should provide context
            if capture_data.integration_notes == "unspecified":
                return GovernanceResult(
                    is_allowed=False,
                    reason="Coherence gate failed: insufficient context provided for memory capture",
                    filtered_data=None
                )
        
        return GovernanceResult(
            is_allowed=True,
            reason="Coherence gate passed: data is coherent and meaningful",
            filtered_data=capture_data
        )
    
    @staticmethod
    def apply_plain_language_rewriter(capture_data: CaptureData) -> GovernanceResult:
        """
        Apply plain language rewriter to capture data.
        Ensures language is clear and accessible.
        """
        # Check for jargon or overly complex language
        jargon_indicators = [
            "paradigm", "synergy", "leverage", "optimize", "facilitate",
            "methodology", "framework", "infrastructure", "implementation",
            "utilization", "maximization", "minimization"
        ]
        
        text_lower = " ".join([
            capture_data.integration_notes.lower(),
            capture_data.commitments.lower()
        ])
        
        jargon_count = sum(1 for jargon in jargon_indicators if jargon in text_lower)
        
        if jargon_count > 2:
            return GovernanceResult(
                is_allowed=False,
                reason=f"Plain language rewriter failed: {jargon_count} jargon terms detected",
                filtered_data=None
            )
        
        # Check for overly formal language
        formal_indicators = [
            "pursuant to", "in accordance with", "as per", "hereby",
            "aforementioned", "aforementioned", "whereas", "therefore"
        ]
        
        formal_count = sum(1 for formal in formal_indicators if formal in text_lower)
        
        if formal_count > 1:
            return GovernanceResult(
                is_allowed=False,
                reason=f"Plain language rewriter failed: {formal_count} overly formal phrases detected",
                filtered_data=None
            )
        
        return GovernanceResult(
            is_allowed=True,
            reason="Plain language rewriter passed: language is clear and accessible",
            filtered_data=capture_data
        )
    
    @staticmethod
    def apply_governance_chain(capture_data: CaptureData) -> GovernanceResult:
        """
        Apply the complete governance chain to capture data.
        Returns the result of the first failing gate, or success if all pass.
        """
        # Apply gates in order
        gates = [
            ("Integrity Linter", MemoryGovernance.apply_integrity_linter),
            ("Stones Alignment", MemoryGovernance.apply_stones_alignment_filter),
            ("Coherence Gate", MemoryGovernance.apply_coherence_gate),
            ("Plain Language Rewriter", MemoryGovernance.apply_plain_language_rewriter)
        ]
        
        for gate_name, gate_function in gates:
            result = gate_function(capture_data)
            if not result.is_allowed:
                return GovernanceResult(
                    is_allowed=False,
                    reason=f"Governance chain failed at {gate_name}: {result.reason}",
                    filtered_data=None
                )
        
        return GovernanceResult(
            is_allowed=True,
            reason="Governance chain passed: all gates cleared",
            filtered_data=capture_data
        )
    
    @staticmethod
    def validate_memory_item(item: MemoryItem) -> GovernanceResult:
        """
        Validate an existing memory item against governance rules.
        Useful for checking items before retrieval or modification.
        """
        if item.deleted_at:
            return GovernanceResult(
                is_allowed=False,
                reason="Memory item validation failed: item has been deleted",
                filtered_data=None
            )
        
        # Apply governance to the item's capture data
        return MemoryGovernance.apply_governance_chain(item.capture_data)
    
    @staticmethod
    def get_governance_summary(items: List[MemoryItem]) -> Dict[str, Any]:
        """
        Get a summary of governance compliance across memory items.
        Useful for monitoring and debugging.
        """
        total_items = len(items)
        active_items = [item for item in items if not item.deleted_at]
        deleted_items = [item for item in items if item.deleted_at]
        
        # Check governance compliance for active items
        governance_results = []
        for item in active_items:
            result = MemoryGovernance.validate_memory_item(item)
            governance_results.append({
                "item_id": item.item_id,
                "compliant": result.is_allowed,
                "reason": result.reason
            })
        
        compliant_count = sum(1 for result in governance_results if result["compliant"])
        non_compliant_count = len(governance_results) - compliant_count
        
        return {
            "total_items": total_items,
            "active_items": len(active_items),
            "deleted_items": len(deleted_items),
            "governance_compliant": compliant_count,
            "governance_non_compliant": non_compliant_count,
            "compliance_rate": compliant_count / len(active_items) if active_items else 0,
            "governance_details": governance_results
        }
