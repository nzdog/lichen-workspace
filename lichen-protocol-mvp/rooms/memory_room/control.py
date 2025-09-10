from typing import List, Optional, Tuple
from datetime import datetime
from .contract_types import MemoryItem, UserAction, MemoryOperationResult


class UserControl:
    """Handles user control operations on memory items"""
    
    @staticmethod
    def pin_item(
        items: List[MemoryItem],
        item_id: str
    ) -> MemoryOperationResult:
        """
        Pin a memory item. Returns structured result.
        No state mutation on failure.
        """
        item = UserControl._find_item_by_id(items, item_id)
        if not item:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot pin: item {item_id} not found",
                error_details="Item does not exist"
            )
        
        if item.deleted_at:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot pin: item {item_id} is deleted",
                error_details="Item has been deleted"
            )
        
        # Pin the item
        item.is_pinned = True
        item.updated_at = datetime.now()
        
        return MemoryOperationResult(
            success=True,
            message=f"Item {item_id} pinned successfully",
            affected_items=[item]
        )
    
    @staticmethod
    def edit_item(
        items: List[MemoryItem],
        item_id: str,
        field_name: str,
        new_value: str
    ) -> MemoryOperationResult:
        """
        Edit a field in a memory item. Returns structured result.
        No state mutation on failure.
        """
        item = UserControl._find_item_by_id(items, item_id)
        if not item:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot edit: item {item_id} not found",
                error_details="Item does not exist"
            )
        
        if item.deleted_at:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot edit: item {item_id} is deleted",
                error_details="Item has been deleted"
            )
        
        # Validate field name
        valid_fields = [
            'tone_label', 'residue_label', 'readiness_state',
            'integration_notes', 'commitments'
        ]
        
        if field_name not in valid_fields:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot edit: invalid field '{field_name}'",
                error_details=f"Valid fields are: {', '.join(valid_fields)}"
            )
        
        # Edit the field
        setattr(item.capture_data, field_name, new_value)
        item.updated_at = datetime.now()
        
        return MemoryOperationResult(
            success=True,
            message=f"Field '{field_name}' updated to '{new_value}'",
            affected_items=[item]
        )
    
    @staticmethod
    def delete_item(
        items: List[MemoryItem],
        item_id: str
    ) -> MemoryOperationResult:
        """
        Soft delete a memory item. Returns structured result.
        No state mutation on failure.
        """
        item = UserControl._find_item_by_id(items, item_id)
        if not item:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot delete: item {item_id} not found",
                error_details="Item does not exist"
            )
        
        if item.deleted_at:
            return MemoryOperationResult(
                success=False,
                message=f"Item {item_id} is already deleted",
                error_details="Item was previously deleted"
            )
        
        # Soft delete the item
        item.deleted_at = datetime.now()
        item.updated_at = datetime.now()
        
        return MemoryOperationResult(
            success=True,
            message=f"Item {item_id} deleted successfully",
            affected_items=[item]
        )
    
    @staticmethod
    def unpin_item(
        items: List[MemoryItem],
        item_id: str
    ) -> MemoryOperationResult:
        """
        Unpin a memory item. Returns structured result.
        No state mutation on failure.
        """
        item = UserControl._find_item_by_id(items, item_id)
        if not item:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot unpin: item {item_id} not found",
                error_details="Item does not exist"
            )
        
        if item.deleted_at:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot unpin: item {item_id} is deleted",
                error_details="Item has been deleted"
            )
        
        if not item.is_pinned:
            return MemoryOperationResult(
                success=False,
                message=f"Item {item_id} is not pinned",
                error_details="Item was not pinned"
            )
        
        # Unpin the item
        item.is_pinned = False
        item.updated_at = datetime.now()
        
        return MemoryOperationResult(
            success=True,
            message=f"Item {item_id} unpinned successfully",
            affected_items=[item]
        )
    
    @staticmethod
    def get_item_details(
        items: List[MemoryItem],
        item_id: str
    ) -> MemoryOperationResult:
        """
        Get detailed information about a memory item.
        Returns structured result.
        """
        item = UserControl._find_item_by_id(items, item_id)
        if not item:
            return MemoryOperationResult(
                success=False,
                message=f"Cannot retrieve: item {item_id} not found",
                error_details="Item does not exist"
            )
        
        return MemoryOperationResult(
            success=True,
            message=f"Item {item_id} retrieved successfully",
            affected_items=[item]
        )
    
    @staticmethod
    def list_user_actions() -> List[str]:
        """Get list of available user actions"""
        return [action.value for action in UserAction]
    
    @staticmethod
    def validate_user_action(action: str) -> bool:
        """Validate that a user action is supported"""
        valid_actions = [action.value for action in UserAction]
        return action in valid_actions
    
    @staticmethod
    def _find_item_by_id(
        items: List[MemoryItem],
        item_id: str
    ) -> Optional[MemoryItem]:
        """Find a memory item by ID"""
        for item in items:
            if item.item_id == item_id:
                return item
        return None
    
    @staticmethod
    def get_pinned_items(items: List[MemoryItem]) -> List[MemoryItem]:
        """Get all pinned items"""
        return [item for item in items if item.is_pinned and not item.deleted_at]
    
    @staticmethod
    def get_active_items(items: List[MemoryItem]) -> List[MemoryItem]:
        """Get all non-deleted items"""
        return [item for item in items if not item.deleted_at]
    
    @staticmethod
    def get_deleted_items(items: List[MemoryItem]) -> List[MemoryItem]:
        """Get all deleted items"""
        return [item for item in items if item.deleted_at]
