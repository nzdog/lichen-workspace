from typing import Dict, Any, Optional, Tuple, List
from .contract_types import IntegrationData, DeclineReason, DeclineResponse


class IntegrationEnforcement:
    """Enforces integration capture requirements before closure"""
    
    @staticmethod
    def validate_integration_presence(payload: Any) -> Tuple[bool, Optional[IntegrationData], Optional[DeclineResponse]]:
        """
        Validate that required integration data is present.
        Returns: (is_valid, integration_data, decline_response)
        """
        if not payload:
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message="Integration data is required before closure",
                details="Payload is empty or missing",
                required_fields=["integration_notes", "session_context"]
            )
            return False, None, decline
        
        if not isinstance(payload, dict):
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message="Integration data must be provided as structured data",
                details="Payload is not a dictionary",
                required_fields=["integration_notes", "session_context"]
            )
            return False, None, decline
        
        # Check for required integration fields
        required_fields = ["integration_notes", "session_context"]
        missing_fields = []
        
        for field in required_fields:
            if field not in payload or not payload[field]:
                missing_fields.append(field)
        
        if missing_fields:
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message=f"Missing required integration fields: {', '.join(missing_fields)}",
                details="Integration data must include integration_notes and session_context",
                required_fields=missing_fields
            )
            return False, None, decline
        
        # Create integration data object
        integration_data = IntegrationData(
            integration_notes=payload["integration_notes"],
            session_context=payload["session_context"],
            key_insights=payload.get("key_insights", []),
            shifts_noted=payload.get("shifts_noted", [])
        )
        
        return True, integration_data, None
    
    @staticmethod
    def validate_integration_quality(integration_data: IntegrationData) -> Tuple[bool, Optional[DeclineResponse]]:
        """
        Validate the quality of integration data.
        Returns: (is_valid, decline_response)
        """
        # Check for minimum content length
        if len(integration_data.integration_notes.strip()) < 10:
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message="Integration notes must provide meaningful content",
                details="Integration notes are too brief for meaningful integration",
                required_fields=["integration_notes"]
            )
            return False, decline
        
        if len(integration_data.session_context.strip()) < 5:
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message="Session context must provide meaningful context",
                details="Session context is too brief for meaningful integration",
                required_fields=["session_context"]
            )
            return False, decline
        
        # Check for reasonable content (not just placeholder text)
        placeholder_indicators = ["unspecified", "none", "n/a", "placeholder", "to be filled"]
        integration_lower = integration_data.integration_notes.lower()
        context_lower = integration_data.session_context.lower()
        
        if any(indicator in integration_lower for indicator in placeholder_indicators):
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message="Integration notes must contain actual content, not placeholders",
                details="Integration notes appear to contain placeholder text",
                required_fields=["integration_notes"]
            )
            return False, decline
        
        if any(indicator in context_lower for indicator in placeholder_indicators):
            decline = DeclineResponse(
                reason=DeclineReason.MISSING_INTEGRATION,
                message="Session context must contain actual content, not placeholders",
                details="Session context appears to contain placeholder text",
                required_fields=["session_context"]
            )
            return False, decline
        
        return True, None
    
    @staticmethod
    def format_integration_summary(integration_data: IntegrationData) -> str:
        """Format integration data into a human-readable summary"""
        summary_parts = [
            "## Integration Summary",
            f"**Session Context**: {integration_data.session_context}",
            f"**Integration Notes**: {integration_data.integration_notes}",
            ""
        ]
        
        if integration_data.key_insights:
            summary_parts.append("**Key Insights**:")
            for insight in integration_data.key_insights:
                summary_parts.append(f"- {insight}")
            summary_parts.append("")
        
        if integration_data.shifts_noted:
            summary_parts.append("**Shifts Noted**:")
            for shift in integration_data.shifts_noted:
                summary_parts.append(f"- {shift}")
            summary_parts.append("")
        
        summary_parts.append(f"**Integration Timestamp**: {integration_data.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return "\n".join(summary_parts)
    
    @staticmethod
    def get_integration_requirements() -> List[str]:
        """Get list of required integration fields"""
        return ["integration_notes", "session_context"]
    
    @staticmethod
    def get_optional_integration_fields() -> List[str]:
        """Get list of optional integration fields"""
        return ["key_insights", "shifts_noted"]
    
    @staticmethod
    def validate_integration_completeness(integration_data: IntegrationData) -> bool:
        """Check if integration data is complete for closure"""
        # Basic validation
        if not integration_data.integration_notes or not integration_data.session_context:
            return False
        
        # Quality validation
        is_valid, _ = IntegrationEnforcement.validate_integration_quality(integration_data)
        return is_valid
