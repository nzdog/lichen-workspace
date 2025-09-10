from typing import List, Optional, Dict, Any
from .contract_types import MemoryItem, MemoryScope, MemoryQuery


class MemoryContinuity:
    """Handles memory retrieval for downstream room access"""
    
    @staticmethod
    def get_memory(
        items: List[MemoryItem],
        scope: MemoryScope,
        session_id: Optional[str] = None,
        protocol_id: Optional[str] = None,
        include_deleted: bool = False,
        limit: Optional[int] = None
    ) -> List[MemoryItem]:
        """
        Retrieve memory items based on scope and filters.
        Returns scoped memory for downstream room access.
        """
        # Filter items based on scope
        if scope == MemoryScope.SESSION:
            filtered_items = MemoryContinuity._filter_by_session(items, session_id)
        elif scope == MemoryScope.PROTOCOL:
            filtered_items = MemoryContinuity._filter_by_protocol(items, protocol_id)
        elif scope == MemoryScope.GLOBAL:
            filtered_items = MemoryContinuity._filter_global(items)
        else:
            return []
        
        # Apply deletion filter
        if not include_deleted:
            filtered_items = [item for item in filtered_items if not item.deleted_at]
        
        # Apply limit if specified
        if limit and limit > 0:
            filtered_items = filtered_items[:limit]
        
        return filtered_items
    
    @staticmethod
    def query_memory(
        items: List[MemoryItem],
        query: MemoryQuery
    ) -> List[MemoryItem]:
        """
        Execute a memory query with structured parameters.
        Returns filtered memory items.
        """
        return MemoryContinuity.get_memory(
            items=items,
            scope=query.scope,
            session_id=query.session_id,
            protocol_id=query.protocol_id,
            include_deleted=query.include_deleted,
            limit=query.limit
        )
    
    @staticmethod
    def get_memory_summary(
        items: List[MemoryItem],
        scope: MemoryScope,
        session_id: Optional[str] = None,
        protocol_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get a summary of memory items for a given scope.
        Useful for downstream room context.
        """
        filtered_items = MemoryContinuity.get_memory(
            items, scope, session_id, protocol_id, include_deleted=False
        )
        
        if not filtered_items:
            return {
                "scope": scope.value,
                "total_items": 0,
                "pinned_items": 0,
                "recent_items": 0,
                "summary": "No memory items found"
            }
        
        # Count pinned items
        pinned_count = sum(1 for item in filtered_items if item.is_pinned)
        
        # Count recent items (last 24 hours)
        from datetime import datetime, timedelta
        recent_cutoff = datetime.now() - timedelta(hours=24)
        recent_count = sum(1 for item in filtered_items 
                          if item.updated_at > recent_cutoff)
        
        # Get summary text
        summary = MemoryContinuity._generate_summary_text(filtered_items, scope)
        
        return {
            "scope": scope.value,
            "total_items": len(filtered_items),
            "pinned_items": pinned_count,
            "recent_items": recent_count,
            "summary": summary
        }
    
    @staticmethod
    def get_context_for_room(
        items: List[MemoryItem],
        room_id: str,
        session_id: str,
        protocol_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get memory context specifically formatted for a downstream room.
        Returns relevant memory signals and summary.
        """
        # Get session-scoped memory
        session_memory = MemoryContinuity.get_memory(
            items, MemoryScope.SESSION, session_id
        )
        
        # Get protocol-scoped memory if available
        protocol_memory = []
        if protocol_id:
            protocol_memory = MemoryContinuity.get_memory(
                items, MemoryScope.PROTOCOL, protocol_id=protocol_id
            )
        
        # Get global context
        global_memory = MemoryContinuity.get_memory(
            items, MemoryScope.GLOBAL
        )
        
        # Format for room consumption
        context = {
            "room_id": room_id,
            "session_id": session_id,
            "protocol_id": protocol_id,
            "session_context": MemoryContinuity._format_room_context(session_memory),
            "protocol_context": MemoryContinuity._format_room_context(protocol_memory),
            "global_context": MemoryContinuity._format_room_context(global_memory),
            "summary": MemoryContinuity._generate_room_summary(
                session_memory, protocol_memory, global_memory
            )
        }
        
        return context
    
    @staticmethod
    def _filter_by_session(
        items: List[MemoryItem],
        session_id: Optional[str]
    ) -> List[MemoryItem]:
        """Filter items by session ID"""
        if not session_id:
            return []
        return [item for item in items if item.capture_data.session_id == session_id]
    
    @staticmethod
    def _filter_by_protocol(
        items: List[MemoryItem],
        protocol_id: Optional[str]
    ) -> List[MemoryItem]:
        """Filter items by protocol ID"""
        if not protocol_id:
            return []
        return [item for item in items if item.capture_data.protocol_id == protocol_id]
    
    @staticmethod
    def _filter_global(items: List[MemoryItem]) -> List[MemoryItem]:
        """Filter items for global scope (all active items)"""
        return [item for item in items if not item.deleted_at]
    
    @staticmethod
    def _generate_summary_text(
        items: List[MemoryItem],
        scope: MemoryScope
    ) -> str:
        """Generate human-readable summary text for memory items"""
        if not items:
            return f"No {scope.value} memory items found"
        
        # Count by type
        tone_counts = {}
        residue_counts = {}
        readiness_counts = {}
        
        for item in items:
            tone = item.capture_data.tone_label
            residue = item.capture_data.residue_label
            readiness = item.capture_data.readiness_state
            
            tone_counts[tone] = tone_counts.get(tone, 0) + 1
            residue_counts[residue] = residue_counts.get(residue, 0) + 1
            readiness_counts[readiness] = readiness_counts.get(readiness, 0) + 1
        
        # Build summary
        summary_parts = [f"{len(items)} {scope.value} memory items"]
        
        if tone_counts:
            dominant_tone = max(tone_counts, key=tone_counts.get)
            summary_parts.append(f"dominant tone: {dominant_tone}")
        
        if residue_counts:
            dominant_residue = max(residue_counts, key=residue_counts.get)
            summary_parts.append(f"dominant residue: {dominant_residue}")
        
        pinned_count = sum(1 for item in items if item.is_pinned)
        if pinned_count > 0:
            summary_parts.append(f"{pinned_count} pinned items")
        
        return ", ".join(summary_parts)
    
    @staticmethod
    def _format_room_context(items: List[MemoryItem]) -> Dict[str, Any]:
        """Format memory items for room consumption"""
        if not items:
            return {"count": 0, "items": [], "summary": "No items"}
        
        # Get recent items (last 5)
        recent_items = sorted(items, key=lambda x: x.updated_at, reverse=True)[:5]
        
        # Format for room consumption
        formatted_items = []
        for item in recent_items:
            formatted_items.append({
                "id": item.item_id,
                "tone": item.capture_data.tone_label,
                "residue": item.capture_data.residue_label,
                "readiness": item.capture_data.readiness_state,
                "is_pinned": item.is_pinned,
                "updated_at": item.updated_at.isoformat()
            })
        
        return {
            "count": len(items),
            "items": formatted_items,
            "summary": MemoryContinuity._generate_summary_text(items, MemoryScope.SESSION)
        }
    
    @staticmethod
    def _generate_room_summary(
        session_memory: List[MemoryItem],
        protocol_memory: List[MemoryItem],
        global_memory: List[MemoryItem]
    ) -> str:
        """Generate overall summary for room context"""
        total_items = len(session_memory) + len(protocol_memory) + len(global_memory)
        
        if total_items == 0:
            return "No memory context available"
        
        summary_parts = [f"Total memory context: {total_items} items"]
        
        if session_memory:
            summary_parts.append(f"Session: {len(session_memory)} items")
        
        if protocol_memory:
            summary_parts.append(f"Protocol: {len(protocol_memory)} items")
        
        if global_memory:
            summary_parts.append(f"Global: {len(global_memory)} items")
        
        return ", ".join(summary_parts)
