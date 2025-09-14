"""
AI Room Implementation
Main orchestrator that implements the AI Room Protocol and Contract
"""

import asyncio
from typing import Optional, Dict, Any, Union
from .types import AIRoomInput, AIRoomOutput, AIRoomContext, RAGResult, ConsentPrompt


class AIRoomConfig:
    """Configuration for AI Room policies"""
    
    def __init__(
        self,
        consent_prompt: Optional[ConsentPrompt] = None,
        fallback_enabled: bool = True,
        grounding_threshold: float = 0.25,
        require_citations: bool = True
    ):
        self.consent_prompt = consent_prompt or self._create_default_consent_prompt()
        self.fallback_enabled = fallback_enabled
        self.grounding_threshold = grounding_threshold
        self.require_citations = require_citations

    def _create_default_consent_prompt(self) -> ConsentPrompt:
        """Create default consent/trust seal prompt"""
        return ConsentPrompt(
            text="I'm about to search our knowledge base to provide you with grounded information. This helps ensure my responses are accurate and well-supported. Is it okay to proceed?",
            required=True
        )


class AIRoom:
    """Main AI Room class that orchestrates the protocol flow"""
    
    def __init__(self, config: Optional[AIRoomConfig] = None):
        if config is None:
            config = AIRoomConfig()
        
        self.config = config
        self._session_retrieval_count = {}  # Track retrieval count per session
    
    async def run_ai_room(self, input_data: Union[AIRoomInput, Dict[str, Any]]) -> AIRoomOutput:
        """
        Main entry point that orchestrates the AI Room protocol.
        Implements: Brief Processing → RAG Integration → Consent/Trust Seal → Response Generation → Fallback Handling
        """
        try:
            # Convert dict input to AIRoomInput if needed
            if isinstance(input_data, dict):
                input_data = AIRoomInput(
                    session_state_ref=input_data.get("session_state_ref", ""),
                    payload=input_data.get("payload"),
                    brief=input_data.get("brief"),
                    context=input_data.get("context")
                )
            
            # Extract brief and context
            brief = input_data.brief or input_data.payload or {}
            context = input_data.context or {}
            
            # Create execution context
            ctx = AIRoomContext(
                session_state_ref=input_data.session_state_ref,
                brief=brief,
                context=context,
                is_first_retrieval=self._is_first_retrieval(input_data.session_state_ref)
            )
            
            # Check if this is a fallback response from orchestrator
            if self._is_fallback_response(brief):
                return self._handle_fallback_response(brief)
            
            # Extract query from brief
            query = self._extract_query(brief)
            if not query:
                return AIRoomOutput(
                    display_text="I need a clear task or query to help you with.",
                    next_action="continue"
                )
            
            # Check if we need to show consent prompt for first retrieval
            if ctx.is_first_retrieval and self.config.consent_prompt.required:
                return AIRoomOutput(
                    display_text=self.config.consent_prompt.text,
                    next_action="continue"
                )
            
            # Process RAG integration (this will be handled by orchestrator)
            # The orchestrator will call _run_rag_retrieval and merge results
            # For now, we'll return a placeholder that indicates RAG processing is needed
            return AIRoomOutput(
                display_text="Processing your request with grounded information...",
                next_action="continue",
                meta={
                    "retrieval": {
                        "lane": "fast",
                        "top_k": 0,
                        "used_doc_ids": [],
                        "citations": []
                    },
                    "stones_alignment": 0.0,
                    "grounding_score_1to5": 1,
                    "insufficient_support": True,
                    "rag_processing_required": True
                }
            )
            
        except Exception as e:
            return AIRoomOutput(
                display_text=f"AI Room error: {str(e)}",
                next_action="continue"
            )
    
    def _is_first_retrieval(self, session_state_ref: str) -> bool:
        """Check if this is the first retrieval in the session"""
        if session_state_ref not in self._session_retrieval_count:
            self._session_retrieval_count[session_state_ref] = 0
            return True
        return False
    
    def _is_fallback_response(self, brief: Dict[str, Any]) -> bool:
        """Check if this is a fallback response from the orchestrator"""
        return brief.get("meta", {}).get("fallback") is not None
    
    def _handle_fallback_response(self, brief: Dict[str, Any]) -> AIRoomOutput:
        """Handle fallback response from orchestrator"""
        meta = brief.get("meta", {})
        fallback_type = meta.get("fallback", "unknown")
        
        if fallback_type == "low_grounding":
            display_text = "I cannot provide a confident answer due to insufficient grounding in our knowledge base. Let me pause here to ensure accuracy."
        elif fallback_type == "no_citations":
            display_text = "I cannot provide a confident answer without proper citations to our knowledge base. Let me pause here to ensure accuracy."
        else:
            display_text = "I cannot provide a confident answer at this time. Let me pause here to ensure accuracy."
        
        return AIRoomOutput(
            display_text=display_text,
            next_action="continue",
            meta=meta
        )
    
    def _extract_query(self, brief: Dict[str, Any]) -> str:
        """Extract query from brief"""
        if isinstance(brief, dict):
            return brief.get("task", "") or brief.get("query", "") or brief.get("text", "")
        elif isinstance(brief, str):
            return brief
        return ""
    
    def compose_response_with_rag(self, rag_result: RAGResult, ctx: AIRoomContext) -> AIRoomOutput:
        """
        Compose user-facing response using RAG results.
        This method is called by the orchestrator after RAG processing.
        """
        try:
            # Check if we need to show consent prompt first
            if ctx.is_first_retrieval and self.config.consent_prompt.required:
                return AIRoomOutput(
                    display_text=self.config.consent_prompt.text,
                    next_action="continue",
                    meta={
                        "retrieval": {
                            "lane": rag_result.lane,
                            "top_k": len(rag_result.retrieved_docs),
                            "used_doc_ids": [doc.get("doc", "") for doc in rag_result.retrieved_docs],
                            "citations": rag_result.citations
                        },
                        "stones_alignment": rag_result.stones_alignment,
                        "grounding_score_1to5": int(rag_result.grounding_score * 4) + 1,
                        "insufficient_support": rag_result.insufficient_support,
                        "consent_required": True
                    }
                )
            
            # Compose response with RAG content
            display_text = self._compose_grounded_response(rag_result)
            
            # Build meta information
            meta = {
                "retrieval": {
                    "lane": rag_result.lane,
                    "top_k": len(rag_result.retrieved_docs),
                    "used_doc_ids": [doc.get("doc", "") for doc in rag_result.retrieved_docs],
                    "citations": rag_result.citations
                },
                "stones_alignment": rag_result.stones_alignment,
                "grounding_score_1to5": int(rag_result.grounding_score * 4) + 1,
                "insufficient_support": rag_result.insufficient_support
            }
            
            return AIRoomOutput(
                display_text=display_text,
                next_action="continue",
                meta=meta
            )
            
        except Exception as e:
            return AIRoomOutput(
                display_text=f"Error composing response: {str(e)}",
                next_action="continue"
            )
    
    def _compose_grounded_response(self, rag_result: RAGResult) -> str:
        """Compose grounded response using RAG results"""
        # Start with the generated answer
        response = rag_result.generated_answer
        
        # Add context about grounding if available
        if rag_result.citations:
            citation_count = len(rag_result.citations)
            response += f"\n\nThis response is grounded in {citation_count} source{'s' if citation_count != 1 else ''} from our knowledge base."
        
        # Add Stones alignment note if relevant
        if rag_result.stones_alignment > 0.7:
            response += "\n\nThis guidance aligns with our core principles."
        
        return response


# Global instance for easy access
_ai_room = None

def get_ai_room() -> AIRoom:
    """Get the global AI Room instance."""
    global _ai_room
    if _ai_room is None:
        _ai_room = AIRoom()
    return _ai_room


async def run_ai_room(input_data: Union[AIRoomInput, Dict[str, Any]]) -> AIRoomOutput:
    """Run AI Room with the global instance."""
    ai_room = get_ai_room()
    return await ai_room.run_ai_room(input_data)
