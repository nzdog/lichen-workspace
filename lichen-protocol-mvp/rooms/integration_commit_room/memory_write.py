from typing import List, Optional, Dict, Any, Tuple
from .contract_types import IntegrationData, Commitment, MemoryWriteResult, DeclineReason, DeclineResponse


class MemoryWrite:
    """Handles atomic writes to the Memory Room"""
    
    def __init__(self):
        # In-memory storage for MVP (simulates Memory Room interface)
        self.memory_storage = {}
        self.write_history = []
    
    def write_integration_and_commitments(
        self,
        session_id: str,
        integration_data: IntegrationData,
        commitments: List[Commitment]
    ) -> MemoryWriteResult:
        """
        Write integration and commitment data atomically to memory.
        If any part fails, nothing is persisted.
        """
        try:
            # Validate inputs
            if not session_id:
                return MemoryWriteResult(
                    success=False,
                    reason="Session ID is required for memory write",
                    error_details="session_id cannot be empty"
                )
            
            if not integration_data:
                return MemoryWriteResult(
                    success=False,
                    reason="Integration data is required for memory write",
                    error_details="integration_data cannot be None"
                )
            
            if not commitments:
                return MemoryWriteResult(
                    success=False,
                    reason="At least one commitment is required for memory write",
                    error_details="commitments list cannot be empty"
                )
            
            # Prepare memory data
            memory_data = {
                "session_id": session_id,
                "timestamp": integration_data.timestamp.isoformat(),
                "integration": {
                    "integration_notes": integration_data.integration_notes,
                    "session_context": integration_data.session_context,
                    "key_insights": integration_data.key_insights,
                    "shifts_noted": integration_data.shifts_noted
                },
                "commitments": []
            }
            
            # Prepare commitment data
            for commitment in commitments:
                commitment_data = {
                    "text": commitment.text,
                    "context": commitment.context,
                    "pace_state": commitment.pace_state.value,
                    "session_ref": commitment.session_ref,
                    "timestamp": commitment.timestamp.isoformat(),
                    "commitment_id": commitment.commitment_id
                }
                memory_data["commitments"].append(commitment_data)
            
            # Simulate atomic write (in-memory for MVP)
            # In a real implementation, this would be a database transaction
            
            # Store in memory
            if session_id not in self.memory_storage:
                self.memory_storage[session_id] = []
            
            self.memory_storage[session_id].append(memory_data)
            
            # Record write history
            write_record = {
                "session_id": session_id,
                "timestamp": integration_data.timestamp.isoformat(),
                "integration_written": True,
                "commitments_written": len(commitments),
                "success": True
            }
            self.write_history.append(write_record)
            
            return MemoryWriteResult(
                success=True,
                reason=f"Successfully wrote integration and {len(commitments)} commitments to memory",
                integration_written=True,
                commitments_written=len(commitments)
            )
            
        except Exception as e:
            # Log the error (in production, this would go to a proper logging system)
            error_msg = f"Memory write failed: {str(e)}"
            
            # Record failed write attempt
            write_record = {
                "session_id": session_id,
                "timestamp": integration_data.timestamp.isoformat() if integration_data else None,
                "integration_written": False,
                "commitments_written": 0,
                "success": False,
                "error": error_msg
            }
            self.write_history.append(write_record)
            
            return MemoryWriteResult(
                success=False,
                reason="Memory write operation failed",
                error_details=error_msg
            )
    
    def read_integration_and_commitments(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Read integration and commitment data from memory"""
        if session_id not in self.memory_storage:
            return None
        
        # Return the most recent entry for the session
        session_data = self.memory_storage[session_id]
        if not session_data:
            return None
        
        return session_data[-1]  # Most recent entry
    
    def get_write_history(self, session_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get write history, optionally filtered by session"""
        if session_id:
            return [record for record in self.write_history if record["session_id"] == session_id]
        return self.write_history
    
    def validate_memory_data(
        self,
        integration_data: IntegrationData,
        commitments: List[Commitment]
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that data is ready for memory write.
        Returns: (is_valid, error_message)
        """
        # Check integration data
        if not integration_data.integration_notes or not integration_data.session_context:
            return False, "Integration data missing required fields"
        
        # Check commitments
        if not commitments:
            return False, "No commitments provided for memory write"
        
        for i, commitment in enumerate(commitments):
            if not commitment.text or not commitment.context or not commitment.pace_state:
                return False, f"Commitment {i+1} missing required fields"
        
        return True, None
    
    def simulate_memory_failure(self, session_id: str) -> bool:
        """
        Simulate a memory write failure for testing purposes.
        Returns True if failure should be simulated.
        """
        # Simulate failure for specific session IDs (testing scenario)
        return session_id == "test-failure-session"
    
    def clear_memory_storage(self):
        """Clear in-memory storage (for testing)"""
        self.memory_storage.clear()
        self.write_history.clear()
    
    def get_memory_statistics(self) -> Dict[str, Any]:
        """Get statistics about memory storage"""
        total_sessions = len(self.memory_storage)
        total_writes = len(self.write_history)
        successful_writes = sum(1 for record in self.write_history if record.get("success", False))
        failed_writes = total_writes - successful_writes
        
        total_commitments = 0
        for session_data in self.memory_storage.values():
            for entry in session_data:
                total_commitments += len(entry.get("commitments", []))
        
        return {
            "total_sessions": total_sessions,
            "total_writes": total_writes,
            "successful_writes": successful_writes,
            "failed_writes": failed_writes,
            "total_commitments": total_commitments,
            "success_rate": successful_writes / total_writes if total_writes > 0 else 0
        }
