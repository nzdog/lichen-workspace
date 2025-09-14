#!/usr/bin/env python3
"""
Model Swap Dry Run Tool

Performs A/B comparison between current and proposed embedding/reranker models
for RAG lanes. Generates detailed reports with overlap, rank correlation,
and latency metrics.

Usage:
    python tools/model_swap_dry_run.py --lane fast --new-embed sentence-transformers/all-MiniLM-L12-v2 --queries eval/data/test_queries.jsonl --k 10 --outdir /tmp/model_swap_results
"""

import argparse
import json
import time
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import logging

# Add the lichen-protocol-mvp directory to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "lichen-protocol-mvp"))

from hallway.adapters.rag_adapter import RAGAdapter
from hallway.adapters.model_config import ModelConfig

logger = logging.getLogger(__name__)


class ModelSwapDryRun:
    """Model swap dry run comparison tool."""
    
    def __init__(self, lane: str, new_embed: Optional[str] = None, new_reranker: Optional[str] = None):
        """
        Initialize the dry run tool.
        
        Args:
            lane: Lane to test (fast/accurate)
            new_embed: Proposed embedding model ID
            new_reranker: Proposed reranker model ID
        """
        self.lane = lane
        self.new_embed = new_embed
        self.new_reranker = new_reranker
        
        # Initialize RAG adapter for current models
        self.rag_adapter = RAGAdapter()
        self.model_config = ModelConfig()
        
        # Get current model IDs
        self.current_embed, self.current_reranker = self.rag_adapter.get_active_model_ids(lane)
        
        logger.info(f"Current {lane} models: embed={self.current_embed}, reranker={self.current_reranker}")
        logger.info(f"Proposed {lane} models: embed={new_embed}, reranker={new_reranker}")
    
    def load_queries(self, queries_path: str) -> List[Dict[str, Any]]:
        """Load test queries from JSONL file."""
        queries = []
        with open(queries_path, 'r') as f:
            for line in f:
                if line.strip():
                    queries.append(json.loads(line))
        return queries
    
    def run_query_comparison(self, query: str, k: int) -> Dict[str, Any]:
        """
        Run a single query comparison between current and proposed models.
        
        Args:
            query: Query text
            k: Number of results to retrieve
            
        Returns:
            Dict with comparison results
        """
        # Run with current models
        start_time = time.time()
        current_results = self.rag_adapter.retrieve(query, self.lane)
        current_latency = (time.time() - start_time) * 1000
        
        # Run with proposed models (simulate by temporarily overriding config)
        proposed_results = self._run_with_proposed_models(query, k)
        proposed_latency = proposed_results.get("latency_ms", 0)
        
        # Calculate metrics
        current_doc_ids = [r.get("doc", "") for r in current_results[:k]]
        proposed_doc_ids = [r.get("doc", "") for r in proposed_results.get("results", [])[:k]]
        
        overlap_at_k = self._calculate_overlap(current_doc_ids, proposed_doc_ids)
        rank_correlation = self._calculate_rank_correlation(current_results[:k], proposed_results.get("results", [])[:k])
        
        return {
            "query": query,
            "current": {
                "results": current_results[:k],
                "latency_ms": current_latency,
                "embed_model": self.current_embed,
                "reranker_model": self.current_reranker
            },
            "proposed": {
                "results": proposed_results.get("results", [])[:k],
                "latency_ms": proposed_latency,
                "embed_model": self.new_embed,
                "reranker_model": self.new_reranker
            },
            "metrics": {
                "overlap_at_k": overlap_at_k,
                "rank_correlation": rank_correlation,
                "latency_delta_ms": proposed_latency - current_latency
            }
        }
    
    def _run_with_proposed_models(self, query: str, k: int) -> Dict[str, Any]:
        """
        Simulate running with proposed models by temporarily overriding environment variables.
        
        Args:
            query: Query text
            k: Number of results to retrieve
            
        Returns:
            Dict with results and timing
        """
        # Store original environment variables
        original_env = {}
        env_keys = [
            f"RAG_{self.lane.upper()}_EMBED",
            f"RAG_{self.lane.upper()}_RERANK"
        ]
        
        for key in env_keys:
            original_env[key] = os.getenv(key)
        
        try:
            # Set proposed models in environment
            if self.new_embed:
                os.environ[f"RAG_{self.lane.upper()}_EMBED"] = self.new_embed
            if self.new_reranker:
                os.environ[f"RAG_{self.lane.upper()}_RERANK"] = self.new_reranker
            
            # Create new adapter instance with proposed models
            proposed_adapter = RAGAdapter()
            
            # Run retrieval
            start_time = time.time()
            results = proposed_adapter.retrieve(query, self.lane)
            latency = (time.time() - start_time) * 1000
            
            return {
                "results": results,
                "latency_ms": latency
            }
            
        finally:
            # Restore original environment variables
            for key, value in original_env.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value
    
    def _calculate_overlap(self, list_a: List[str], list_b: List[str]) -> float:
        """Calculate overlap@k between two lists of document IDs."""
        if not list_a or not list_b:
            return 0.0
        
        set_a = set(list_a)
        set_b = set(list_b)
        intersection = set_a.intersection(set_b)
        
        return len(intersection) / max(len(set_a), len(set_b))
    
    def _calculate_rank_correlation(self, results_a: List[Dict], results_b: List[Dict]) -> float:
        """
        Calculate simple rank correlation between two result lists.
        
        This is a simplified version - in practice you might want to use
        Kendall's tau or Spearman's rank correlation.
        """
        if not results_a or not results_b:
            return 0.0
        
        # Create rank maps for each result set
        rank_map_a = {r.get("doc", ""): i for i, r in enumerate(results_a)}
        rank_map_b = {r.get("doc", ""): i for i, r in enumerate(results_b)}
        
        # Find common documents
        common_docs = set(rank_map_a.keys()).intersection(set(rank_map_b.keys()))
        
        if len(common_docs) < 2:
            return 0.0
        
        # Calculate simple rank correlation
        ranks_a = [rank_map_a[doc] for doc in common_docs]
        ranks_b = [rank_map_b[doc] for doc in common_docs]
        
        # Simple correlation: 1 - (sum of squared rank differences) / (max possible difference)
        rank_diffs = [(a - b) ** 2 for a, b in zip(ranks_a, ranks_b)]
        max_possible_diff = len(common_docs) * (len(common_docs) - 1) ** 2
        
        if max_possible_diff == 0:
            return 1.0
        
        correlation = 1.0 - (sum(rank_diffs) / max_possible_diff)
        return max(0.0, min(1.0, correlation))
    
    def run_comparison(self, queries: List[Dict[str, Any]], k: int) -> Dict[str, Any]:
        """
        Run comparison across all queries.
        
        Args:
            queries: List of query objects
            k: Number of results to retrieve per query
            
        Returns:
            Dict with aggregated results
        """
        results = []
        total_current_latency = 0
        total_proposed_latency = 0
        total_overlap = 0
        total_correlation = 0
        
        logger.info(f"Running comparison on {len(queries)} queries with k={k}")
        
        for i, query_obj in enumerate(queries):
            query_text = query_obj.get("query", "")
            if not query_text:
                continue
            
            logger.info(f"Processing query {i+1}/{len(queries)}: {query_text[:50]}...")
            
            comparison = self.run_query_comparison(query_text, k)
            results.append(comparison)
            
            # Aggregate metrics
            total_current_latency += comparison["current"]["latency_ms"]
            total_proposed_latency += comparison["proposed"]["latency_ms"]
            total_overlap += comparison["metrics"]["overlap_at_k"]
            total_correlation += comparison["metrics"]["rank_correlation"]
        
        # Calculate aggregates
        num_queries = len(results)
        aggregates = {
            "num_queries": num_queries,
            "avg_current_latency_ms": total_current_latency / num_queries if num_queries > 0 else 0,
            "avg_proposed_latency_ms": total_proposed_latency / num_queries if num_queries > 0 else 0,
            "avg_latency_delta_ms": (total_proposed_latency - total_current_latency) / num_queries if num_queries > 0 else 0,
            "avg_overlap_at_k": total_overlap / num_queries if num_queries > 0 else 0,
            "avg_rank_correlation": total_correlation / num_queries if num_queries > 0 else 0
        }
        
        return {
            "metadata": {
                "lane": self.lane,
                "current_models": {
                    "embed_model": self.current_embed,
                    "reranker_model": self.current_reranker
                },
                "proposed_models": {
                    "embed_model": self.new_embed,
                    "reranker_model": self.new_reranker
                },
                "k": k,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ")
            },
            "aggregates": aggregates,
            "query_results": results
        }
    
    def generate_report(self, results: Dict[str, Any], outdir: str) -> None:
        """Generate JSON and Markdown reports."""
        outdir_path = Path(outdir)
        outdir_path.mkdir(parents=True, exist_ok=True)
        
        # Generate JSON report
        json_path = outdir_path / "report.json"
        with open(json_path, 'w') as f:
            json.dump(results, f, indent=2)
        
        # Generate Markdown report
        md_path = outdir_path / "report.md"
        self._generate_markdown_report(results, md_path)
        
        # Generate CSV for quick analysis
        csv_path = outdir_path / "query_results.csv"
        self._generate_csv_report(results, csv_path)
        
        logger.info(f"Reports generated in {outdir_path}")
        logger.info(f"  - JSON: {json_path}")
        logger.info(f"  - Markdown: {md_path}")
        logger.info(f"  - CSV: {csv_path}")
    
    def _generate_markdown_report(self, results: Dict[str, Any], output_path: Path) -> None:
        """Generate human-readable Markdown report."""
        metadata = results["metadata"]
        aggregates = results["aggregates"]
        
        with open(output_path, 'w') as f:
            f.write(f"# Model Swap Dry Run Report\n\n")
            f.write(f"**Lane:** {metadata['lane']}\n")
            f.write(f"**Timestamp:** {metadata['timestamp']}\n")
            f.write(f"**K:** {metadata['k']}\n\n")
            
            f.write("## Model Configuration\n\n")
            f.write("### Current Models\n")
            f.write(f"- **Embedding:** {metadata['current_models']['embed_model']}\n")
            f.write(f"- **Reranker:** {metadata['current_models']['reranker_model'] or 'None'}\n\n")
            
            f.write("### Proposed Models\n")
            f.write(f"- **Embedding:** {metadata['proposed_models']['embed_model'] or 'No change'}\n")
            f.write(f"- **Reranker:** {metadata['proposed_models']['reranker_model'] or 'No change'}\n\n")
            
            f.write("## Aggregate Metrics\n\n")
            f.write("| Metric | Current | Proposed | Delta |\n")
            f.write("|--------|---------|----------|-------|\n")
            
            # Latency comparison
            current_lat = aggregates["avg_current_latency_ms"]
            proposed_lat = aggregates["avg_proposed_latency_ms"]
            lat_delta = aggregates["avg_latency_delta_ms"]
            lat_delta_str = f"{lat_delta:+.1f}ms"
            if lat_delta > 0:
                lat_delta_str = f"🔴 {lat_delta_str}"
            elif lat_delta < 0:
                lat_delta_str = f"🟢 {lat_delta_str}"
            else:
                lat_delta_str = f"⚪ {lat_delta_str}"
            
            f.write(f"| Avg Latency | {current_lat:.1f}ms | {proposed_lat:.1f}ms | {lat_delta_str} |\n")
            
            # Overlap
            overlap = aggregates["avg_overlap_at_k"]
            overlap_str = f"{overlap:.1%}"
            if overlap >= 0.8:
                overlap_str = f"🟢 {overlap_str}"
            elif overlap >= 0.6:
                overlap_str = f"🟡 {overlap_str}"
            else:
                overlap_str = f"🔴 {overlap_str}"
            
            f.write(f"| Overlap@{metadata['k']} | - | - | {overlap_str} |\n")
            
            # Rank correlation
            correlation = aggregates["avg_rank_correlation"]
            corr_str = f"{correlation:.3f}"
            if correlation >= 0.8:
                corr_str = f"🟢 {corr_str}"
            elif correlation >= 0.6:
                corr_str = f"🟡 {corr_str}"
            else:
                corr_str = f"🔴 {corr_str}"
            
            f.write(f"| Rank Correlation | - | - | {corr_str} |\n\n")
            
            f.write("## Summary\n\n")
            f.write(f"Processed {aggregates['num_queries']} queries.\n\n")
            
            # Recommendations
            f.write("### Recommendations\n\n")
            if lat_delta > 100:
                f.write("⚠️ **High latency increase detected** - consider impact on user experience\n\n")
            elif lat_delta < -50:
                f.write("✅ **Latency improvement detected** - good for user experience\n\n")
            
            if overlap < 0.6:
                f.write("⚠️ **Low result overlap** - models may produce very different results\n\n")
            elif overlap > 0.8:
                f.write("✅ **High result overlap** - models produce similar results\n\n")
            
            if correlation < 0.6:
                f.write("⚠️ **Low rank correlation** - ranking order may be significantly different\n\n")
            elif correlation > 0.8:
                f.write("✅ **High rank correlation** - ranking order is similar\n\n")
    
    def _generate_csv_report(self, results: Dict[str, Any], output_path: Path) -> None:
        """Generate CSV report for quick analysis."""
        import csv
        
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            
            # Header
            writer.writerow([
                "query", "current_latency_ms", "proposed_latency_ms", "latency_delta_ms",
                "overlap_at_k", "rank_correlation", "current_embed", "proposed_embed"
            ])
            
            # Data rows
            for query_result in results["query_results"]:
                writer.writerow([
                    query_result["query"][:100],  # Truncate long queries
                    f"{query_result['current']['latency_ms']:.1f}",
                    f"{query_result['proposed']['latency_ms']:.1f}",
                    f"{query_result['metrics']['latency_delta_ms']:+.1f}",
                    f"{query_result['metrics']['overlap_at_k']:.3f}",
                    f"{query_result['metrics']['rank_correlation']:.3f}",
                    query_result["current"]["embed_model"],
                    query_result["proposed"]["embed_model"]
                ])


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Model swap dry run comparison tool")
    parser.add_argument("--lane", required=True, choices=["fast", "accurate"], 
                       help="RAG lane to test")
    parser.add_argument("--new-embed", help="Proposed embedding model ID")
    parser.add_argument("--new-reranker", help="Proposed reranker model ID")
    parser.add_argument("--queries", required=True, help="Path to JSONL file with test queries")
    parser.add_argument("--k", type=int, default=10, help="Number of results to retrieve (default: 10)")
    parser.add_argument("--outdir", required=True, help="Output directory for reports")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose logging")
    
    args = parser.parse_args()
    
    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(level=log_level, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Validate arguments
    if not args.new_embed and not args.new_reranker:
        logger.error("At least one of --new-embed or --new-reranker must be specified")
        sys.exit(1)
    
    if not Path(args.queries).exists():
        logger.error(f"Queries file not found: {args.queries}")
        sys.exit(1)
    
    try:
        # Initialize dry run tool
        dry_run = ModelSwapDryRun(args.lane, args.new_embed, args.new_reranker)
        
        # Load queries
        queries = dry_run.load_queries(args.queries)
        if not queries:
            logger.error("No queries found in file")
            sys.exit(1)
        
        # Run comparison
        results = dry_run.run_comparison(queries, args.k)
        
        # Generate reports
        dry_run.generate_report(results, args.outdir)
        
        # Print summary
        aggregates = results["aggregates"]
        print(f"\n=== Model Swap Dry Run Summary ===")
        print(f"Lane: {args.lane}")
        print(f"Queries processed: {aggregates['num_queries']}")
        print(f"Avg latency delta: {aggregates['avg_latency_delta_ms']:+.1f}ms")
        print(f"Avg overlap@{args.k}: {aggregates['avg_overlap_at_k']:.1%}")
        print(f"Avg rank correlation: {aggregates['avg_rank_correlation']:.3f}")
        print(f"Reports saved to: {args.outdir}")
        
    except Exception as e:
        logger.error(f"Dry run failed: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
