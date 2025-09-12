"""
Pure control flow orchestrator for the Hallway Protocol.
"""

import os
import time
import uuid
from typing import Dict, Any, List, Optional

# Global warmup counter for performance budget tracking
_warmup_counter = 0
_warmup_threshold = 3

from .types import ExecutionContext, FinalOutput, StepStatus, StepResult
from .steps import run_step
from .logging import emit_event
from .errors import BudgetExceededError
from .rag_observability import log_rag_turn


def _is_warmup_query() -> bool:
    """
    Check if this is a warm-up query and increment counter.
    
    Returns:
        True if this is a warm-up query (first 3 queries per process)
    """
    global _warmup_counter
    _warmup_counter += 1
    return _warmup_counter <= _warmup_threshold


def _get_timing_ms(start_time: float) -> float:
    """
    Get high precision timing in milliseconds.
    
    Args:
        start_time: Start time from time.perf_counter()
        
    Returns:
        Elapsed time in milliseconds with microsecond precision
    """
    return (time.perf_counter() - start_time) * 1000.0


async def run_hallway(ctx: ExecutionContext) -> FinalOutput:
    """
    Execute the hallway protocol with pure control flow.

    Args:
        ctx: Execution context with all necessary state and dependencies

    Returns:
        Final output with results and audit trail
    """
    emit_event(ctx, phase="start", rooms_planned=len(ctx.rooms_to_run))

    try:
        for room_id in ctx.rooms_to_run:
            # Check budgets before each step
            if _exceeded_budgets(ctx):
                emit_event(ctx, phase="halt", reason="budget_exceeded", room_id=room_id)
                break

            emit_event(ctx, phase="step_start", room_id=room_id)

            # Execute the step
            step_result = await run_step(room_id, ctx)
            
            # Add RAG retrieval stage for AI Room
            if room_id == "ai_room":
                rag_result = await _run_rag_retrieval(ctx)
                if rag_result:
                    # Merge RAG results into the step result
                    step_result.outputs.update(rag_result)
            
            ctx.add_step(step_result)

            emit_event(
                ctx,
                phase="step_done",
                room_id=room_id,
                status=step_result.status.name,
                duration_ms=step_result.metrics.get("duration_ms", 0)
            )

            # Handle step result based on status
            if step_result.status == StepStatus.FAIL:
                emit_event(ctx, phase="halt", reason="step_failed", room_id=room_id)
                break

            elif step_result.status == StepStatus.HALT:
                # Honor stop_on_decline policy
                stop_on_decline = ctx.policy.get("stop_on_decline", True)
                if stop_on_decline:
                    emit_event(ctx, phase="halt", reason="step_halted", room_id=room_id, halt_reason=step_result.halt_reason)
                    break
                else:
                    # Continue to next room if policy allows
                    emit_event(ctx, phase="decline_continue", reason="step_halted", room_id=room_id, halt_reason=step_result.halt_reason)

            elif step_result.status == StepStatus.RETRY:
                # Implement retry logic if needed
                retry_count = step_result.metrics.get("retry_count", 0)
                max_retries = ctx.policy.get("max_retries", 3)

                if retry_count < max_retries:
                    emit_event(ctx, phase="retry", room_id=room_id, attempt=retry_count + 1)
                    # Could implement retry here, for now just continue
                else:
                    emit_event(ctx, phase="halt", reason="max_retries_exceeded", room_id=room_id)
                    break

            elif step_result.status == StepStatus.FALLBACK:
                # Implement fallback logic
                emit_event(ctx, phase="fallback", room_id=room_id)
                _handle_fallback(ctx, step_result)

            # For OK status, just continue to next room

            # Update state if room provided new session state
            if "session_state_ref" in step_result.outputs:
                ctx.state["session_state_ref"] = step_result.outputs["session_state_ref"]

        # Build final output
        final_output = _build_final_output(ctx)
        emit_event(ctx, phase="end", success=True, total_steps=len(ctx.events))

        return final_output

    except Exception as e:
        emit_event(ctx, phase="error", error=str(e))
        ctx.ports.log.error({
            "event": "orchestrator_error",
            "run_id": ctx.run_id,
            "error": str(e)
        })
        raise


def _exceeded_budgets(ctx: ExecutionContext) -> bool:
    """Check if any budget limits have been exceeded."""
    for k, limit in ctx.budgets.items():
        if ctx.usage.get(k, 0.0) > float(limit):
            return True
    return False


def _handle_fallback(ctx: ExecutionContext, step_result: StepResult) -> None:
    """Handle fallback logic for a step."""
    # For now, just log the fallback
    # This could be extended to modify the execution plan
    ctx.ports.log.info({
        "event": "fallback_handled",
        "run_id": ctx.run_id,
        "room_id": step_result.room_id,
        "reason": step_result.halt_reason
    })


def _build_final_output(ctx: ExecutionContext) -> FinalOutput:
    """Build the final output from execution context."""
    # Collect all step outputs that are marked as successful
    final_outputs = {}

    # Include final session state
    if "session_state_ref" in ctx.state:
        final_outputs["final_state_ref"] = ctx.state["session_state_ref"]

    # Include any other accumulated outputs
    for key, value in ctx.state.items():
        if not key.startswith("_") and key not in ["payloads", "session_state_ref"]:
            final_outputs[key] = value

    # Build audit trail
    steps = []
    step_count = 0
    for event in ctx.events:
        if event.get("phase") == "step_done":
            step_count += 1
            steps.append({
                "step": step_count,
                "room_id": event.get("room_id"),
                "status": event.get("status"),
                "duration_ms": event.get("duration_ms", 0),
                "timestamp": event.get("timestamp")
            })

    # Determine completion status
    completed = not any(
        event.get("phase") == "halt" or event.get("phase") == "error"
        for event in ctx.events
    )

    final_outputs["contract_version"] = "0.2.0"
    final_outputs["steps"] = steps
    final_outputs["completed"] = completed
    final_outputs["exit_summary"] = {
        "completed": completed,
        "decline": None if completed else _extract_decline_reason(ctx),
        "auditable_hash_chain": _build_audit_chain(steps)
    }

    return FinalOutput(
        run_id=ctx.run_id,
        outputs=final_outputs,
        events=ctx.events
    )


def _extract_decline_reason(ctx: ExecutionContext) -> Optional[Dict[str, Any]]:
    """Extract decline reason from context events."""
    for event in ctx.events:
        if event.get("phase") == "halt":
            return {
                "reason": event.get("reason", "unknown"),
                "message": f"Execution halted: {event.get('reason', 'unknown')}",
                "details": {
                    "room_id": event.get("room_id"),
                    "event": event
                }
            }
    return None


def _build_audit_chain(steps: List[Dict[str, Any]]) -> List[str]:
    """Build audit hash chain from steps."""
    # Simple implementation - in production would use proper cryptographic hashes
    import hashlib

    chain = []
    prev_hash = "genesis"

    for step in steps:
        # Create deterministic hash from step data
        step_data = f"{prev_hash}:{step.get('room_id')}:{step.get('status')}:{step.get('timestamp')}"
        step_hash = hashlib.sha256(step_data.encode()).hexdigest()[:16]
        chain.append(step_hash)
        prev_hash = step_hash

    return chain


async def _run_rag_retrieval(ctx: ExecutionContext) -> Optional[Dict[str, Any]]:
    """
    Run RAG retrieval stage for AI Room.
    
    Args:
        ctx: Execution context
        
    Returns:
        Dict with RAG results or None if RAG is not applicable
    """
    try:
        from .adapters.rag_adapter import get_rag_adapter
        
        # Get RAG adapter
        rag_adapter = get_rag_adapter()
        
        if not rag_adapter.enabled:
            # Track warmup for disabled RAG events too
            is_warmup = _is_warmup_query()
            
            # Log disabled RAG event
            turn_id = str(uuid.uuid4())
            payloads = ctx.state.get("payloads", {})
            ai_room_payload = payloads.get("ai_room", {})
            brief = ai_room_payload.get("brief", {})
            query = ""
            if isinstance(brief, dict):
                query = brief.get("task", "") or brief.get("query", "")
            else:
                query = str(brief) if brief else ""
            
            expected_stones = brief.get("stones", []) if isinstance(brief, dict) else []
            
            log_rag_turn(
                request_id=turn_id,
                lane="disabled",
                query=query,
                topk=0,
                stages={"retrieve_ms": 0.0, "rerank_ms": 0.0, "synth_ms": 0.0, "total_ms": 0.0},
                grounding_score=None,
                stones=expected_stones,
                citations=[],
                flags={"rag_enabled": False, "fallback": "flags.disabled", "warmup": is_warmup}
            )
            
            # Return fallback response when RAG is disabled
            return {
                "meta": {
                    "retrieval": {
                        "lane": "disabled",
                        "top_k": 0,
                        "used_doc_ids": [],
                        "citations": []
                    },
                    "stones_alignment": 0.0,
                    "grounding_score_1to5": 1,
                    "insufficient_support": True,
                    "reason": "flags.disabled"
                }
            }
        
        # Extract query from context
        # Look for brief or query in the payload
        payloads = ctx.state.get("payloads", {})
        ai_room_payload = payloads.get("ai_room", {})
        
        # Try to extract query from brief
        brief = ai_room_payload.get("brief", {})
        if isinstance(brief, dict):
            query = brief.get("task", "") or brief.get("query", "")
        else:
            query = str(brief) if brief else ""
        
        if not query:
            return None
        
        # Generate turn ID for this RAG operation
        turn_id = str(uuid.uuid4())
        
        # Determine lane from request meta or default
        lane = ai_room_payload.get("meta", {}).get("rag_lane", rag_adapter.default_lane)
        
        # Track if this is a warm-up query for performance budgets
        is_warmup = _is_warmup_query()
        
        # Run retrieval with high precision timing
        retrieve_start = time.perf_counter()
        retrieval_results = rag_adapter.retrieve(query, lane)
        retrieve_ms = _get_timing_ms(retrieve_start)
        
        if not retrieval_results:
            # Log empty result with new schema
            latency_metrics = {
                "retrieve_ms": round(retrieve_ms, 3),
                "rerank_ms": 0.0,
                "synth_ms": 0.0,
                "total_ms": round(retrieve_ms, 3)
            }
            
            log_rag_turn(
                request_id=turn_id,
                lane=lane,
                query=query,
                topk=0,
                stages=latency_metrics,
                grounding_score=1.0,
                stones=expected_stones,
                citations=[],
                flags={"rag_enabled": True, "fallback": None, "warmup": is_warmup}
            )
            
            return {
                "meta": {
                    "retrieval": {
                        "lane": lane,
                        "top_k": 0,
                        "used_doc_ids": [],
                        "citations": []
                    },
                    "stones_alignment": 0.0,
                    "grounding_score_1to5": 1,
                    "insufficient_support": True
                }
            }
        
        # Extract context texts for generation
        context_texts = [result.get("text", "") for result in retrieval_results]
        
        # Run generation with high precision timing
        synth_start = time.perf_counter()
        generation_result = rag_adapter.generate(query, context_texts, lane)
        synth_ms = _get_timing_ms(synth_start)
        
        # Calculate Stones alignment
        expected_stones = brief.get("stones", []) if isinstance(brief, dict) else []
        stones_alignment = rag_adapter.stones_align(generation_result["answer"], expected_stones)
        
        # Check if support is sufficient
        insufficient_support = not rag_adapter.is_sufficient_support(
            lane, stones_alignment, generation_result["hallucinations"]
        )
        
        # Calculate grounding score (1-5 scale based on citations and alignment)
        grounding_score_1to5 = 1
        if generation_result["citations"]:
            grounding_score_1to5 += 1
        if stones_alignment > 0.5:
            grounding_score_1to5 += 1
        if stones_alignment > 0.7:
            grounding_score_1to5 += 1
        if generation_result["hallucinations"] == 0:
            grounding_score_1to5 += 1
        
        # Convert to 0-1 scale for guardrail checks
        grounding_score_normalized = (grounding_score_1to5 - 1) / 4.0
        
        # Load minimum grounding threshold from config
        from .gates import GroundingGate
        gate = GroundingGate()
        min_grounding_threshold = gate.min_grounding
        
        # Check grounding threshold guardrail
        if grounding_score_normalized < min_grounding_threshold:
            # Log refusal event
            refusal_latency = {
                "retrieve_ms": round(retrieve_ms, 3),
                "rerank_ms": 0.0,
                "synth_ms": round(synth_ms, 3),
                "total_ms": round(retrieve_ms + synth_ms, 3)
            }
            
            log_rag_turn(
                request_id=turn_id,
                lane=lane,
                query=query,
                topk=len(retrieval_results),
                stages=refusal_latency,
                grounding_score=grounding_score_normalized,
                stones=expected_stones,
                citations=[],
                flags={"rag_enabled": True, "fallback": "low_grounding", "refusal": "low_grounding", "warmup": is_warmup}
            )
            
            # Return fallback refusal payload
            return {
                "text": "Cannot answer confidently: insufficient grounding.",
                "citations": [],
                "meta": {
                    "profile": lane,
                    "fallback": "low_grounding",
                    "grounding_score": grounding_score_normalized
                }
            }
        
        # Check citations requirement guardrail
        citations = generation_result.get("citations", [])
        if not citations:
            # Log refusal event for missing citations
            refusal_latency = {
                "retrieve_ms": round(retrieve_ms, 3),
                "rerank_ms": 0.0,
                "synth_ms": round(synth_ms, 3),
                "total_ms": round(retrieve_ms + synth_ms, 3)
            }
            
            log_rag_turn(
                request_id=turn_id,
                lane=lane,
                query=query,
                topk=len(retrieval_results),
                stages=refusal_latency,
                grounding_score=grounding_score_normalized,
                stones=expected_stones,
                citations=[],
                flags={"rag_enabled": True, "fallback": "no_citations", "refusal": "no_citations", "warmup": is_warmup}
            )
            
            # Return fallback refusal payload
            return {
                "text": "Cannot answer confidently: insufficient grounding.",
                "citations": [],
                "meta": {
                    "profile": lane,
                    "fallback": "no_citations",
                    "grounding_score": grounding_score_normalized
                }
            }
        
        # Extract document IDs
        used_doc_ids = list(set(result.get("doc", "") for result in retrieval_results if result.get("doc")))
        
        # Log RAG turn for observability with new schema
        latency_metrics = {
            "retrieve_ms": round(retrieve_ms, 3),
            "rerank_ms": 0.0,  # Not implemented in current adapter
            "synth_ms": round(synth_ms, 3),
            "total_ms": round(retrieve_ms + synth_ms, 3)
        }
        
        log_rag_turn(
            request_id=turn_id,
            lane=lane,
            query=query,
            topk=len(retrieval_results),
            stages=latency_metrics,
            grounding_score=grounding_score_normalized,
            stones=expected_stones,
            citations=citations,
            flags={"rag_enabled": True, "fallback": None, "warmup": is_warmup},
            trace={"used_doc_ids": used_doc_ids}
        )
        
        # Log RAG metrics (existing event system)
        emit_event(ctx, phase="rag_retrieval", 
                  query=query, lane=lane, top_k=len(retrieval_results),
                  doc_ids=used_doc_ids, stones_alignment=stones_alignment,
                  grounding_score=grounding_score_normalized, hallucinations=generation_result["hallucinations"],
                  latency_ms_retriever=retrieve_ms, latency_ms_generator=synth_ms)
        
        return {
            "meta": {
                "retrieval": {
                    "lane": lane,
                    "top_k": len(retrieval_results),
                    "used_doc_ids": used_doc_ids,
                    "citations": generation_result["citations"]
                },
                "stones_alignment": stones_alignment,
                "grounding_score_1to5": grounding_score_1to5,
                "insufficient_support": insufficient_support
            },
            "rag_context": {
                "query": query,
                "retrieved_docs": retrieval_results,
                "generated_answer": generation_result["answer"],
                "hallucinations": generation_result["hallucinations"]
            }
        }
        
    except Exception as e:
        # Log error but don't fail the entire step
        emit_event(ctx, phase="rag_error", error=str(e))
        return {
            "meta": {
                "retrieval": {
                    "lane": "unknown",
                    "top_k": 0,
                    "used_doc_ids": [],
                    "citations": []
                },
                "stones_alignment": 0.0,
                "grounding_score_1to5": 1,
                "insufficient_support": True
            },
            "rag_error": str(e)
        }
