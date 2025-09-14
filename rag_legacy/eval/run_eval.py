"""
Command-line interface for running RAG evaluation harness.
"""

import argparse
import json
import os
import time
import yaml
import glob
import logging
from datetime import datetime
from typing import List, Dict, Any, Set

from config import LANE_TARGETS, evaluate_metric_band
from metrics import (
    precision_at_k, recall_at_k, mrr_at_k, ndcg_at_k,
    diversity_unique_docs_topk, p95, simple_grounding_score, stones_alignment_score
)
from adapter import retrieve, generate, expected_stones_for_query


def check_semantic_alignment(answer: str, stone_info: Dict[str, Any], assertions: List[str]) -> Dict[str, Any]:
    """
    Check semantic alignment of answer against Stone meaning and assertions.
    
    Args:
        answer: Generated answer text
        stone_info: Stone information from registry
        assertions: List of assertion strings
        
    Returns:
        Dictionary with alignment results
    """
    result = {
        "passed": True,
        "failed_assertions": [],
        "must_have_matches": [],
        "red_flag_matches": []
    }
    
    answer_lower = answer.lower()
    
    # Check for must_have phrases (positive alignment)
    must_haves = stone_info.get('must_haves', [])
    for must_have in must_haves:
        # Simple keyword matching - could be enhanced with embeddings
        must_have_lower = must_have.lower()
        if any(word in answer_lower for word in must_have_lower.split()):
            result["must_have_matches"].append(must_have)
    
    # Check for red_flag phrases (negative alignment)
    red_flags = stone_info.get('red_flags', [])
    for red_flag in red_flags:
        red_flag_lower = red_flag.lower()
        if any(word in answer_lower for word in red_flag_lower.split()):
            result["red_flag_matches"].append(red_flag)
            result["passed"] = False
    
    # Check if assertions require stone meaning reference
    requires_stone_meaning = any("must_reference_stone_meaning" in assertion for assertion in assertions)
    if requires_stone_meaning:
        # Must have at least one must_have match
        if not result["must_have_matches"]:
            result["failed_assertions"].append("must_reference_stone_meaning")
            result["passed"] = False
    
    return result


def load_evalset(evalset_path: str) -> List[Dict[str, Any]]:
    """Load evaluation dataset from JSON file."""
    with open(evalset_path, 'r') as f:
        return json.load(f)


def load_evalset_jsonl(evalset_path: str) -> List[Dict[str, Any]]:
    """Load evaluation dataset from JSONL file."""
    evalset = []
    with open(evalset_path, 'r') as f:
        for line in f:
            line = line.strip()
            if line:
                evalset.append(json.loads(line))
    return evalset


def load_stones_registry(stones_path: str = "stones.yaml") -> Dict[str, Dict[str, Any]]:
    """Load the canonical Stones registry."""
    try:
        with open(stones_path, 'r') as f:
            data = yaml.safe_load(f)
            stones = {}
            for stone in data.get('stones', []):
                stones[stone['slug']] = stone
            return stones
    except Exception as e:
        print(f"Warning: Could not load stones registry from {stones_path}: {e}")
        return {}


def load_prompts_from_yaml(prompts_dir: str, stones_registry: Dict[str, Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Load evaluation prompts from YAML files in the prompts directory."""
    prompts = []
    
    # Find all YAML files in the prompts directory
    yaml_files = glob.glob(os.path.join(prompts_dir, "*.yaml"))
    print(f"Found {len(yaml_files)} YAML files in {prompts_dir}")
    
    for yaml_file in yaml_files:
        try:
            with open(yaml_file, 'r') as f:
                data = yaml.safe_load(f)
                if 'prompts' in data:
                    print(f"Loading {len(data['prompts'])} prompts from {yaml_file}")
                    for prompt in data['prompts']:
                        # Validate and fix stone_meaning if needed
                        if stones_registry and 'stone' in prompt:
                            stone_slug = prompt['stone']
                            if stone_slug in stones_registry:
                                expected_meaning = stones_registry[stone_slug]['meaning'].strip()
                                if 'stone_meaning' not in prompt or prompt['stone_meaning'].strip() != expected_meaning:
                                    print(f"Warning: Fixing stone_meaning for {prompt.get('query_id', 'unknown')} in {yaml_file}")
                                    prompt['stone_meaning'] = expected_meaning
                            else:
                                print(f"Warning: Unknown stone '{stone_slug}' in {prompt.get('query_id', 'unknown')} in {yaml_file}")
                        prompts.append(prompt)
                else:
                    print(f"No 'prompts' key found in {yaml_file}")
        except Exception as e:
            print(f"Warning: Could not load {yaml_file}: {e}")
    
    print(f"Total prompts loaded: {len(prompts)}")
    return prompts


def evaluate_lane(evalset: List[Dict[str, Any]], lane: str, outdir: str, stones_registry: Dict[str, Dict[str, Any]] = None, debug_retrieval: bool = False, use_router: bool = True) -> Dict[str, Any]:
    """
    Evaluate a single lane (fast or accurate) and return aggregate metrics.
    
    Args:
        evalset: List of evaluation items
        lane: Lane to evaluate (fast/accurate)
        outdir: Output directory for results
        stones_registry: Stones registry for semantic alignment
        debug_retrieval: Enable debug logging
        use_router: Whether to use protocol router for retrieval
    """
    records = []
    retriever_latencies = []
    
    # Setup debug logging if requested
    debug_logger = None
    if debug_retrieval:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_path = f"logs/retrieval_{timestamp}.log"
        os.makedirs("logs", exist_ok=True)
        
        debug_logger = logging.getLogger(f"retrieval_debug_{lane}")
        debug_logger.setLevel(logging.INFO)
        handler = logging.FileHandler(log_path)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)
        debug_logger.addHandler(handler)
        
        debug_logger.info(f"Starting {lane} lane evaluation with debug logging")
    
    # Process each evaluation item
    for i, item in enumerate(evalset):
        query_id = item.get("query_id") or item.get("id", "unknown")
        query = item.get("query") or item.get("prompt", "")
        gold_doc_ids = set(item.get("gold_doc_ids", []))
        expected_stones = item.get("expected_stones", [])
        # If no expected_stones but we have a stone field, use that
        if not expected_stones and "stone" in item:
            expected_stones = [item["stone"]]
        top_k_for_generation = item.get("top_k_for_generation", 8)
        
        # Debug logging for first 3 queries
        if debug_logger and i < 3:
            debug_logger.info(f"Query {i+1}: {query}")
            debug_logger.info(f"Expected gold docs: {list(gold_doc_ids)}")
        
        # Measure retriever latency
        start_time = time.time()
        retrieval_results = retrieve(query, lane, use_router=use_router)
        latency_ms = (time.time() - start_time) * 1000
        retriever_latencies.append(latency_ms)
        
        # Debug logging for retrieval results
        if debug_logger and i < 3:
            debug_logger.info(f"Retrieval results: {len(retrieval_results)} docs")
            for j, result in enumerate(retrieval_results[:5]):
                router_info = ""
                if "router_decision" in result:
                    router_decision = result["router_decision"]
                    router_info = f", router: {router_decision['route']} (conf: {router_decision['confidence']:.2f})"
                debug_logger.info(f"  {j+1}. doc={result.get('doc', 'unknown')}, score={result.get('score', 0.0):.3f}{router_info}, text={result.get('text', '')[:80]}...")
        
        # Extract ranked document IDs
        ranked_doc_ids = [result["doc"] for result in retrieval_results]
        
        # Calculate diversity
        diversity_top8 = diversity_unique_docs_topk(retrieval_results, 8)
        
        # Calculate coverage
        coverage = len(gold_doc_ids & set(ranked_doc_ids)) > 0 if gold_doc_ids else True
        
        # Build generation context
        context_texts = [result["text"] for result in retrieval_results[:top_k_for_generation]]
        
        # Generate answer
        generation_result = generate(query, context_texts, lane)
        answer = generation_result["answer"]
        hallucinations = generation_result["hallucinations"]
        
        # Calculate grounding score
        grounding_score = simple_grounding_score(answer, context_texts)
        
        # Calculate Stones alignment
        if not expected_stones:
            expected_stones = expected_stones_for_query(query)
        stones_alignment = stones_alignment_score(expected_stones, answer)
        
        # Check semantic alignment if stones registry is available
        semantic_alignment = None
        if stones_registry and 'stone' in item:
            stone_slug = item['stone']
            if stone_slug in stones_registry:
                stone_info = stones_registry[stone_slug]
                semantic_alignment = check_semantic_alignment(answer, stone_info, item.get('assertions', []))
        
        # Extract router information
        router_decision = None
        if retrieval_results and "router_decision" in retrieval_results[0]:
            router_decision = retrieval_results[0]["router_decision"]
        
        # Create record
        record = {
            "query_id": query_id,
            "query": query,
            "lane": lane,
            "use_router": use_router,
            "ranked_doc_ids": ranked_doc_ids,
            "gold_doc_ids": list(gold_doc_ids),
            "expected_stones": expected_stones,
            "diversity_top8": diversity_top8,
            "coverage": coverage,
            "latency_ms": latency_ms,
            "answer": answer,
            "hallucinations": hallucinations,
            "grounding_score": grounding_score,
            "stones_alignment": stones_alignment
        }
        
        # Add stone field if available
        if 'stone' in item:
            record["stone"] = item["stone"]
        
        # Add semantic alignment if available
        if semantic_alignment:
            record["semantic_alignment"] = semantic_alignment
        
        # Add router decision if available
        if router_decision:
            record["router_decision"] = router_decision
        
        records.append(record)
    
    # Calculate aggregate metrics
    all_ranked_docs = [record["ranked_doc_ids"] for record in records]
    all_gold_sets = [set(record["gold_doc_ids"]) for record in records]
    
    precision_5 = sum(precision_at_k(ranked_docs, gold_docs, 5) 
                     for ranked_docs, gold_docs in zip(all_ranked_docs, all_gold_sets)) / len(records)
    
    recall_20 = sum(recall_at_k(ranked_docs, gold_docs, 20) 
                   for ranked_docs, gold_docs in zip(all_ranked_docs, all_gold_sets)) / len(records)
    
    mrr_10 = mrr_at_k(all_ranked_docs, all_gold_sets, 10)
    
    ndcg_10 = sum(ndcg_at_k(ranked_docs, gold_docs, 10) 
                 for ranked_docs, gold_docs in zip(all_ranked_docs, all_gold_sets)) / len(records)
    
    latency_p95 = p95(retriever_latencies)
    diversity_avg = sum(record["diversity_top8"] for record in records) / len(records)
    coverage_fraction = sum(record["coverage"] for record in records) / len(records)
    stones_alignment_avg = sum(record["stones_alignment"] for record in records) / len(records)
    grounding_avg = sum(record["grounding_score"] for record in records) / len(records)
    hallucination_rate = sum(record["hallucinations"] for record in records) / len(records)
    
    # Calculate per-Stone metrics
    stone_metrics = {}
    if stones_registry:
        for stone_slug, stone_info in stones_registry.items():
            stone_records = [r for r in records if r.get('semantic_alignment') and r.get('stone') == stone_slug]
            if stone_records:
                passed = sum(1 for r in stone_records if r['semantic_alignment']['passed'])
                failed = len(stone_records) - passed
                
                # Find most common failed assertion
                failed_assertions = []
                for r in stone_records:
                    if not r['semantic_alignment']['passed']:
                        failed_assertions.extend(r['semantic_alignment']['failed_assertions'])
                
                top_failed_assertion = max(set(failed_assertions), key=failed_assertions.count) if failed_assertions else None
                
                stone_metrics[stone_slug] = {
                    "stone": stone_slug,
                    "prompts": len(stone_records),
                    "passed": passed,
                    "failed": failed,
                    "top_failed_assertion": top_failed_assertion
                }
    
    # Create summary
    summary = {
        "lane": lane,
        "num_queries": len(records),
        "precision_at_5": precision_5,
        "recall_at_20": recall_20,
        "mrr_at_10": mrr_10,
        "ndcg_at_10": ndcg_10,
        "coverage": coverage_fraction,
        "latency_ms_p95": latency_p95,
        "diversity_avg_top8": diversity_avg,
        "stones_alignment": stones_alignment_avg,
        "grounding_1to5": grounding_avg,
        "hallucination_rate": hallucination_rate
    }
    
    # Add stone metrics if available
    if stone_metrics:
        summary["stone_metrics"] = list(stone_metrics.values())
    
    # Save records and summary
    os.makedirs(outdir, exist_ok=True)
    
    records_path = os.path.join(outdir, f"records_{lane}.jsonl")
    with open(records_path, 'w') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
    
    summary_path = os.path.join(outdir, f"summary_{lane}.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    
    return summary


def print_dashboard(summary: Dict[str, Any], lane: str):
    """Print a formatted dashboard for the evaluation results."""
    targets = LANE_TARGETS[lane]
    
    print(f"\n{'='*60}")
    print(f"RAG EVAL DASHBOARD — lane: {lane.upper()}")
    print(f"{'='*60}")
    
    # Define metrics with their properties
    metrics = [
        ("Precision@5", summary["precision_at_5"], targets.precision_at_5, True),
        ("Recall@20", summary["recall_at_20"], targets.recall_at_20, True),
        ("MRR@10", summary["mrr_at_10"], targets.mrr_at_10, True),
        ("nDCG@10", summary["ndcg_at_10"], targets.ndcg_at_10, True),
        ("Coverage", summary["coverage"], targets.coverage, True),
        ("Latency p95 (ms)", summary["latency_ms_p95"], targets.latency_ms_p95, False),
        ("Diversity (uniq docs in top-8)", summary["diversity_avg_top8"], targets.diversity_min_unique_docs_top8, True),
        ("Stones Alignment (0–1)", summary["stones_alignment"], targets.stones_alignment, True),
        ("Grounding (1–5)", summary["grounding_1to5"], targets.grounding_score_1to5, True),
        ("Hallucination rate", summary["hallucination_rate"], targets.hallucination_rate, False)
    ]
    
    green_count = 0
    amber_count = 0
    red_count = 0
    
    for name, actual, target, higher_is_better in metrics:
        band = evaluate_metric_band(actual, target, higher_is_better)
        
        if band == "GREEN":
            color = "🟢"
            green_count += 1
        elif band == "AMBER":
            color = "🟡"
            amber_count += 1
        else:
            color = "🔴"
            red_count += 1
        
        # Format the values appropriately
        if name == "Latency p95 (ms)":
            actual_str = f"{actual:.1f}"
            target_str = f"{target:.1f}"
        elif name in ["Precision@5", "Recall@20", "MRR@10", "nDCG@10", "Coverage", "Stones Alignment (0–1)", "Hallucination rate"]:
            actual_str = f"{actual:.3f}"
            target_str = f"{target:.3f}"
        elif name == "Diversity (uniq docs in top-8)":
            actual_str = f"{actual:.1f}"
            target_str = f"{target:.1f}"
        else:  # Grounding
            actual_str = f"{actual:.1f}"
            target_str = f"{target:.1f}"
        
        print(f"{color} {name:<30} {actual_str:>8} (target: {target_str})")
    
    print(f"{'='*60}")
    print(f"Summary → GREEN: {green_count} | AMBER: {amber_count} | RED: {red_count}")
    print(f"{'='*60}")


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(description="Run RAG evaluation harness")
    parser.add_argument("--evalset", default="eval/evalset.json", 
                       help="Path to evaluation dataset JSON file (legacy)")
    parser.add_argument("--prompts-dir", default="prompts", 
                       help="Directory containing YAML prompt files")
    parser.add_argument("--outdir", default="eval/out", 
                       help="Output directory for results")
    parser.add_argument("--use-yaml", action="store_true", default=False,
                       help="Use YAML prompts directory instead of JSON/JSONL evalset")
    parser.add_argument("--debug-retrieval", action="store_true", default=False,
                       help="Enable debug logging for retrieval operations")
    parser.add_argument("--router", action="store_true", default=False,
                       help="Use protocol router for retrieval")
    parser.add_argument("--no-router", action="store_true", default=False,
                       help="Disable protocol router for retrieval")
    
    args = parser.parse_args()
    
    # Load stones registry
    stones_registry = load_stones_registry()
    if stones_registry:
        print(f"Loaded {len(stones_registry)} stones from registry")
    
    # Load evaluation dataset
    if args.use_yaml or (not args.use_yaml and args.evalset == "eval/evalset.json"):
        print(f"Loading prompts from YAML files in {args.prompts_dir}...")
        evalset = load_prompts_from_yaml(args.prompts_dir, stones_registry)
        print(f"Loaded {len(evalset)} prompts from YAML files")
    else:
        print(f"Loading evalset from {args.evalset}...")
        # Detect file format and use appropriate loader
        if args.evalset.endswith('.jsonl'):
            evalset = load_evalset_jsonl(args.evalset)
            print(f"Loaded {len(evalset)} prompts from JSONL file")
        else:
            evalset = load_evalset(args.evalset)
            print(f"Loaded {len(evalset)} prompts from JSON file")
    
    if not evalset:
        print("Error: No evaluation prompts loaded!")
        return
    
    # Determine router usage
    use_router = True  # Default to using router
    if args.no_router:
        use_router = False
    elif args.router:
        use_router = True
    
    router_mode = "with router" if use_router else "without router"
    print(f"\nRunning evaluation {router_mode}")
    
    # Evaluate both lanes
    for lane in ["fast", "accurate"]:
        print(f"\nEvaluating {lane} lane {router_mode}...")
        summary = evaluate_lane(evalset, lane, args.outdir, stones_registry, args.debug_retrieval, use_router)
        print_dashboard(summary, lane)
    
    print(f"\nEvaluation complete. Results saved to {args.outdir}/")


if __name__ == "__main__":
    main()
