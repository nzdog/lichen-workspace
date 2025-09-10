from typing import Dict, Any, Optional
from .contract_types import CaptureData, MemoryItem
import uuid


class MemoryCapture:
    """Handles minimal capture of memory signals"""
    
    @staticmethod
    def create_capture_data(
        tone_label: Optional[str] = None,
        residue_label: Optional[str] = None,
        readiness_state: Optional[str] = None,
        integration_notes: Optional[str] = None,
        commitments: Optional[str] = None,
        session_id: str = "unspecified",
        protocol_id: Optional[str] = None
    ) -> CaptureData:
        """
        Create capture data with defaults for missing values.
        No interpretation, no analysis, no heuristics.
        """
        return CaptureData(
            tone_label=tone_label or "unspecified",
            residue_label=residue_label or "unspecified",
            readiness_state=readiness_state or "unspecified",
            integration_notes=integration_notes or "unspecified",
            commitments=commitments or "unspecified",
            session_id=session_id,
            protocol_id=protocol_id
        )
    
    @staticmethod
    def extract_from_payload(payload: Any, session_id: str) -> CaptureData:
        """
        Extract memory signals from input payload.
        Returns structured data with defaults for missing fields.
        """
        if not payload:
            return MemoryCapture.create_capture_data(session_id=session_id)
        
        # Extract fields if they exist in payload
        tone_label = payload.get('tone_label') if isinstance(payload, dict) else None
        residue_label = payload.get('residue_label') if isinstance(payload, dict) else None
        readiness_state = payload.get('readiness_state') if isinstance(payload, dict) else None
        integration_notes = payload.get('integration_notes') if isinstance(payload, dict) else None
        commitments = payload.get('commitments') if isinstance(payload, dict) else None
        protocol_id = payload.get('protocol_id') if isinstance(payload, dict) else None
        
        return MemoryCapture.create_capture_data(
            tone_label=tone_label,
            residue_label=residue_label,
            readiness_state=readiness_state,
            integration_notes=integration_notes,
            commitments=commitments,
            session_id=session_id,
            protocol_id=protocol_id
        )
    
    @staticmethod
    def create_memory_item(
        capture_data: CaptureData,
        item_id: Optional[str] = None
    ) -> MemoryItem:
        """Create a new memory item from capture data"""
        return MemoryItem(
            item_id=item_id or str(uuid.uuid4()),
            capture_data=capture_data
        )
    
    @staticmethod
    def validate_capture_data(capture_data: CaptureData) -> bool:
        """Validate that capture data has required fields"""
        required_fields = [
            'tone_label', 'residue_label', 'readiness_state',
            'integration_notes', 'commitments', 'session_id'
        ]
        
        for field_name in required_fields:
            if not hasattr(capture_data, field_name):
                return False
            if getattr(capture_data, field_name) is None:
                return False
        
        return True
    
    @staticmethod
    def format_capture_summary(capture_data: CaptureData) -> str:
        """Format capture data into a human-readable summary"""
        summary_parts = [
            f"Tone: {capture_data.tone_label}",
            f"Residue: {capture_data.residue_label}",
            f"Readiness: {capture_data.readiness_state}",
            f"Integration: {capture_data.integration_notes}",
            f"Commitments: {capture_data.commitments}"
        ]
        
        if capture_data.protocol_id:
            summary_parts.append(f"Protocol: {capture_data.protocol_id}")
        
        return " | ".join(summary_parts)
    
    @staticmethod
    def get_capture_statistics(capture_data_list: list[CaptureData]) -> Dict[str, any]:
        """Get summary statistics from capture data"""
        if not capture_data_list:
            return {
                "total_items": 0,
                "tone_distribution": {},
                "residue_distribution": {},
                "readiness_distribution": {},
                "protocol_distribution": {}
            }
        
        tone_counts = {}
        residue_counts = {}
        readiness_counts = {}
        protocol_counts = {}
        
        for data in capture_data_list:
            # Count tones
            tone_counts[data.tone_label] = tone_counts.get(data.tone_label, 0) + 1
            
            # Count residues
            residue_counts[data.residue_label] = residue_counts.get(data.residue_label, 0) + 1
            
            # Count readiness states
            readiness_counts[data.readiness_state] = readiness_counts.get(data.readiness_state, 0) + 1
            
            # Count protocols
            if data.protocol_id:
                protocol_counts[data.protocol_id] = protocol_counts.get(data.protocol_id, 0) + 1
        
        return {
            "total_items": len(capture_data_list),
            "tone_distribution": tone_counts,
            "residue_distribution": residue_counts,
            "readiness_distribution": readiness_counts,
            "protocol_distribution": protocol_counts
        }
