from typing import Dict, Any, Optional, List, Union
from .contract_types import (
    MemoryRoomInput, MemoryRoomOutput, MemoryItem, MemorySession,
    MemoryScope, UserAction, CaptureData, MemoryQuery
)
from .capture import MemoryCapture
from .control import UserControl
from .continuity import MemoryContinuity
from .governance import MemoryGovernance
from .completion import MemoryCompletion


class MemoryRoom:
    """Main orchestrator for Memory Room operations"""
    
    def __init__(self):
        self.sessions: Dict[str, MemorySession] = {}
    
    def run_memory_room(self, input_data: MemoryRoomInput) -> MemoryRoomOutput:
        """
        Main entry point for Memory Room operations.
        Routes input to appropriate handler based on payload content.
        """
        try:
            # Parse input to determine operation
            operation = self._parse_input_operation(input_data)
            
            if operation == "capture":
                return self._handle_capture(input_data)
            elif operation == "user_control":
                return self._handle_user_control(input_data)
            elif operation == "retrieve":
                return self._handle_retrieve(input_data)
            elif operation == "summary":
                return self._handle_summary(input_data)
            else:
                return self._handle_default(input_data)
                
        except Exception as e:
            # Return structured error response
            error_text = f"Memory Room Error: {str(e)}"
            return MemoryRoomOutput(
                display_text=error_text,
                next_action="continue"
            )
    
    def _parse_input_operation(self, input_data: MemoryRoomInput) -> str:
        """Parse input to determine the operation type"""
        payload = input_data.payload
        
        if not payload:
            return "default"
        
        if isinstance(payload, dict):
            # Check for explicit operation
            if "operation" in payload:
                return payload["operation"]
            
            # Check for user control actions
            if "action" in payload and payload["action"] in ["pin", "edit", "delete", "unpin"]:
                return "user_control"
            
            # Check for retrieval requests
            if "scope" in payload or "query" in payload:
                return "retrieve"
            
            # Check for memory data (capture)
            if any(key in payload for key in ["tone_label", "residue_label", "readiness_state"]):
                return "capture"
            
            # Check for summary request
            if "summary" in payload:
                return "summary"
        
        return "default"
    
    def _handle_capture(self, input_data: MemoryRoomInput) -> MemoryRoomOutput:
        """Handle memory capture operations"""
        # Extract capture data from payload
        capture_data = MemoryCapture.extract_from_payload(
            input_data.payload, input_data.session_state_ref
        )
        
        # Apply governance chain
        governance_result = MemoryGovernance.apply_governance_chain(capture_data)
        
        if not governance_result.is_allowed:
            return MemoryRoomOutput(
                display_text=f"Memory capture failed: {governance_result.reason}",
                next_action="continue"
            )
        
        # Create memory item
        memory_item = MemoryCapture.create_memory_item(capture_data)
        
        # Store in session
        session = self._get_or_create_session(input_data.session_state_ref)
        session.items.append(memory_item)
        session.last_accessed = memory_item.created_at
        
        # Format response
        summary = MemoryCapture.format_capture_summary(capture_data)
        response_text = f"Memory captured successfully:\n\n{summary}"
        
        # Append completion marker
        response_text = MemoryCompletion.append_completion_marker(response_text)
        
        return MemoryRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_user_control(self, input_data: MemoryRoomInput) -> MemoryRoomOutput:
        """Handle user control operations (pin, edit, delete)"""
        payload = input_data.payload
        session = self._get_or_create_session(input_data.session_state_ref)
        
        if not isinstance(payload, dict) or "action" not in payload:
            return MemoryRoomOutput(
                display_text="User control operation requires 'action' field",
                next_action="continue"
            )
        
        action = payload["action"]
        item_id = payload.get("item_id")
        
        if not item_id:
            return MemoryRoomOutput(
                display_text="User control operation requires 'item_id' field",
                next_action="continue"
            )
        
        # Execute user control operation
        if action == "pin":
            result = UserControl.pin_item(session.items, item_id)
        elif action == "edit":
            field_name = payload.get("field_name")
            new_value = payload.get("new_value")
            if not field_name or new_value is None:
                return MemoryRoomOutput(
                    display_text="Edit operation requires 'field_name' and 'new_value'",
                    next_action="continue"
                )
            result = UserControl.edit_item(session.items, item_id, field_name, new_value)
        elif action == "delete":
            result = UserControl.delete_item(session.items, item_id)
        elif action == "unpin":
            result = UserControl.unpin_item(session.items, item_id)
        else:
            return MemoryRoomOutput(
                display_text=f"Unknown user control action: {action}",
                next_action="continue"
            )
        
        # Format response
        if result.success:
            response_text = MemoryCompletion.format_operation_result(
                action, True, result.message, len(result.affected_items)
            )
        else:
            response_text = MemoryCompletion.format_operation_result(
                action, False, result.message, 0
            )
        
        # Append completion marker
        response_text = MemoryCompletion.append_completion_marker(response_text)
        
        return MemoryRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_retrieve(self, input_data: MemoryRoomInput) -> MemoryRoomOutput:
        """Handle memory retrieval operations"""
        payload = input_data.payload
        session = self._get_or_create_session(input_data.session_state_ref)
        
        # Parse query parameters
        scope_str = payload.get("scope", "session") if isinstance(payload, dict) else "session"
        try:
            scope = MemoryScope(scope_str)
        except ValueError:
            scope = MemoryScope.SESSION
        
        # Get memory items
        items = MemoryContinuity.get_memory(
            items=session.items,
            scope=scope,
            session_id=input_data.session_state_ref,
            protocol_id=payload.get("protocol_id") if isinstance(payload, dict) else None,
            include_deleted=payload.get("include_deleted", False) if isinstance(payload, dict) else False,
            limit=payload.get("limit") if isinstance(payload, dict) else None
        )
        
        # Get summary
        summary = MemoryContinuity.get_memory_summary(
            session.items, scope, input_data.session_state_ref,
            payload.get("protocol_id") if isinstance(payload, dict) else None
        )
        
        # Format response
        response_parts = [
            f"# Memory Retrieval - {scope.value.title()} Scope",
            "",
            f"**Query Summary**: {summary['summary']}",
            f"**Total Items**: {summary['total_items']}",
            f"**Pinned Items**: {summary['pinned_items']}",
            f"**Recent Items**: {summary['recent_items']}",
            ""
        ]
        
        if items:
            response_parts.append("## Retrieved Items")
            for item in items[:10]:  # Limit to first 10 for display
                response_parts.append(
                    f"- **{item.capture_data.tone_label}** | "
                    f"{item.capture_data.residue_label} | "
                    f"{item.capture_data.readiness_state}"
                )
                if item.is_pinned:
                    response_parts[-1] += " 📌"
            
            if len(items) > 10:
                response_parts.append(f"\n... and {len(items) - 10} more items")
        else:
            response_parts.append("No items found for the specified scope.")
        
        response_text = "\n".join(response_parts)
        
        # Append completion marker
        response_text = MemoryCompletion.append_completion_marker(response_text)
        
        return MemoryRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_summary(self, input_data: MemoryRoomInput) -> MemoryRoomOutput:
        """Handle memory summary requests"""
        session = self._get_or_create_session(input_data.session_state_ref)
        
        # Get governance summary
        governance_summary = MemoryGovernance.get_governance_summary(session.items)
        
        # Format memory summary
        response_text = MemoryCompletion.format_memory_summary(
            input_data.session_state_ref, session.items, governance_summary
        )
        
        # Append completion marker
        response_text = MemoryCompletion.append_completion_marker(response_text)
        
        return MemoryRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _handle_default(self, input_data: MemoryRoomInput) -> MemoryRoomOutput:
        """Handle default case - show available operations"""
        session = self._get_or_create_session(input_data.session_state_ref)
        
        response_parts = [
            "# Memory Room - Available Operations",
            "",
            "## Current Session Status",
            f"**Session ID**: {input_data.session_state_ref}",
            f"**Memory Items**: {len(session.items)}",
            f"**Active Items**: {len([item for item in session.items if not item.deleted_at])}",
            "",
            "## Available Operations",
            "1. **Capture Memory**: Send data with tone_label, residue_label, etc.",
            "2. **Pin Item**: `{'action': 'pin', 'item_id': 'id'}`",
            "3. **Edit Item**: `{'action': 'edit', 'item_id': 'id', 'field_name': 'field', 'new_value': 'value'}`",
            "4. **Delete Item**: `{'action': 'delete', 'item_id': 'id'}`",
            "5. **Retrieve Memory**: `{'scope': 'session|protocol|global'}`",
            "6. **Get Summary**: `{'summary': true}`",
            "",
            "## Memory Room Features",
            "✅ Minimal capture policy enforced",
            "✅ User control operations supported", 
            "✅ Continuity across rooms enabled",
            "✅ Stones-aligned governance applied"
        ]
        
        response_text = "\n".join(response_parts)
        
        # Append completion marker
        response_text = MemoryCompletion.append_completion_marker(response_text)
        
        return MemoryRoomOutput(
            display_text=response_text,
            next_action="continue"
        )
    
    def _get_or_create_session(self, session_id: str) -> MemorySession:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = MemorySession(session_id=session_id)
        return self.sessions[session_id]
    
    def get_memory_for_room(
        self,
        room_id: str,
        session_id: str,
        protocol_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get memory context for a downstream room"""
        session = self._get_or_create_session(session_id)
        return MemoryContinuity.get_context_for_room(
            session.items, room_id, session_id, protocol_id
        )
    
    def get_session_stats(self, session_id: str) -> Dict[str, Any]:
        """Get statistics for a specific session"""
        session = self._get_or_create_session(session_id)
        
        active_items = [item for item in session.items if not item.deleted_at]
        deleted_items = [item for item in session.items if item.deleted_at]
        pinned_items = [item for item in active_items if item.is_pinned]
        
        return {
            "session_id": session_id,
            "total_items": len(session.items),
            "active_items": len(active_items),
            "deleted_items": len(deleted_items),
            "pinned_items": len(pinned_items),
            "created_at": session.created_at.isoformat(),
            "last_accessed": session.last_accessed.isoformat()
        }


def run_memory_room(input_data: Union[MemoryRoomInput, Dict[str, Any]]) -> Dict[str, Any]:
    """Standalone function to run Memory Room operations"""
    from rooms.memory_room.contract_types import MemoryRoomInput
    from dataclasses import asdict
    inp = MemoryRoomInput.from_obj(input_data)
    room = MemoryRoom()
    result = room.run_memory_room(inp)
    return asdict(result)
