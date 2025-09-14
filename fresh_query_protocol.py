#!/usr/bin/env python3
"""
Fresh Query Protocol - Query the FAISS index and compute comprehensive metrics.

This script supports both single-query and batch evaluation modes, computing
precision, recall, MRR, nDCG, diversity, grounding, and other metrics.
"""

import argparse
import json
import logging
import os
import re
import statistics
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


class ProtocolQueryEngine:
    """Main engine for querying the protocol FAISS index."""
    
    def __init__(self, 
                 index_path: str = "/Users/Nigel/Desktop/lichen-workspace/data/indexes/vecs_accurate.faiss",
                 chunks_path: str = "/Users/Nigel/Desktop/lichen-workspace/data/chunks/chunks_accurate.jsonl",
                 stats_path: str = "/Users/Nigel/Desktop/lichen-workspace/data/indexes/vecs_accurate.stats.json",
                 model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        """Initialize the query engine."""
        self.index_path = index_path
        self.chunks_path = chunks_path
        self.stats_path = stats_path
        self.model_name = model_name
        
        # Load components
        self.embedder = None
        self.index = None
        self.chunks = []
        self.stats = {}
        
        self._load_components()
    
    def _load_components(self):
        """Load all required components."""
        print("Loading embedding model...")
        self.embedder = SentenceTransformer(self.model_name)
        
        print("Loading FAISS index...")
        self.index = faiss.read_index(self.index_path)
        
        print("Loading chunks metadata...")
        self._load_chunks()
        
        print("Loading index stats...")
        with open(self.stats_path, 'r') as f:
            self.stats = json.load(f)
        
        print(f"Loaded {len(self.chunks)} chunks with {self.stats['dimension']}D embeddings")
    
    def _load_chunks(self):
        """Load chunks from JSONL file."""
        with open(self.chunks_path, 'r') as f:
            for line in f:
                if line.strip():
                    chunk = json.loads(line.strip())
                    self.chunks.append(chunk)
    
    def embed_query(self, query: str) -> np.ndarray:
        """Embed a query string."""
        return self.embedder.encode([query], convert_to_tensor=False)[0]
    
    def search(self, query: str, k: int = 20) -> Tuple[List[float], List[int], float]:
        """Search the index for a query."""
        start_time = time.perf_counter()
        
        # Embed query
        query_embedding = self.embed_query(query)
        query_embedding = query_embedding.reshape(1, -1)
        
        # Search
        scores, indices = self.index.search(query_embedding, k)
        
        latency_ms = (time.perf_counter() - start_time) * 1000
        
        # Convert L2 distances to similarity scores (assuming L2 distance)
        # FAISS typically returns L2 distances, so we convert to similarity
        similarities = -scores[0]  # Negative distance = similarity
        
        return similarities.tolist(), indices[0].tolist(), latency_ms
    
    def get_chunk_metadata(self, chunk_idx: int) -> Optional[Dict]:
        """Get chunk metadata by index, with bounds checking."""
        if 0 <= chunk_idx < len(self.chunks):
            return self.chunks[chunk_idx]
        return None


class MetricsCalculator:
    """Calculate various retrieval metrics."""
    
    @staticmethod
    def compute_binary_relevance(retrieved_protocol_ids: List[str], 
                                relevant_protocol_ids: List[str]) -> List[int]:
        """Compute binary relevance for retrieved results."""
        relevant_set = set(relevant_protocol_ids)
        return [1 if pid in relevant_set else 0 for pid in retrieved_protocol_ids]
    
    @staticmethod
    def precision_at_k(relevance_scores: List[int], k: int) -> float:
        """Compute precision@k."""
        if k == 0:
            return 0.0
        top_k = relevance_scores[:k]
        return sum(top_k) / k if top_k else 0.0
    
    @staticmethod
    def recall_at_k(relevance_scores: List[int], k: int, total_relevant: int) -> float:
        """Compute recall@k."""
        if total_relevant == 0:
            return 1.0 if k == 0 else 0.0
        top_k = relevance_scores[:k]
        return sum(top_k) / total_relevant
    
    @staticmethod
    def mrr_at_k(relevance_scores: List[int], k: int) -> float:
        """Compute Mean Reciprocal Rank@k."""
        for i, score in enumerate(relevance_scores[:k]):
            if score == 1:
                return 1.0 / (i + 1)
        return 0.0
    
    @staticmethod
    def ndcg_at_k(relevance_scores: List[int], k: int) -> float:
        """Compute nDCG@k with binary relevance."""
        def dcg_at_k(scores: List[int], k: int) -> float:
            if k == 0:
                return 0.0
            top_k = scores[:k]
            dcg = 0.0
            for i, score in enumerate(top_k):
                dcg += score / np.log2(i + 2)  # log2(i+2) because i is 0-indexed
            return dcg
        
        # Binary relevance, so IDCG@k is the same as DCG@k with all 1s
        idcg = dcg_at_k([1] * k, k)
        if idcg == 0:
            return 0.0
        
        dcg = dcg_at_k(relevance_scores, k)
        return dcg / idcg
    
    @staticmethod
    def diversity_top8(chunks: List[Dict]) -> float:
        """Compute diversity as unique protocol_ids in top 8 / 8."""
        if len(chunks) == 0:
            return 0.0
        
        top_8 = chunks[:8]
        unique_protocols = set()
        for chunk in top_8:
            if chunk and 'protocol_id' in chunk:
                unique_protocols.add(chunk['protocol_id'])
        
        return len(unique_protocols) / 8.0
    
    @staticmethod
    def stones_alignment_top10(chunks: List[Dict], target_stones: Optional[List[str]] = None) -> float:
        """Compute stones alignment for top 10 results."""
        if len(chunks) == 0:
            return 0.0
        
        top_10 = chunks[:10]
        
        if target_stones:
            # Mode 1: Intersection with target stones
            target_set = set(target_stones)
            total_target_stones = len(target_set)
            
            if total_target_stones == 0:
                return 0.0
            
            intersection_count = 0
            for chunk in top_10:
                if chunk and 'stones' in chunk:
                    chunk_stones = chunk['stones']
                    if isinstance(chunk_stones, str):
                        chunk_stones = [s.strip() for s in chunk_stones.split(',')]
                    chunk_set = set(chunk_stones)
                    intersection_count += len(target_set.intersection(chunk_set))
            
            alignment = intersection_count / total_target_stones
            return min(alignment, 1.0)  # Clip to [0,1]
        else:
            # Mode 2: Fraction of chunks with stones populated
            chunks_with_stones = 0
            for chunk in top_10:
                if chunk and 'stones' in chunk and chunk['stones']:
                    chunks_with_stones += 1
            
            return chunks_with_stones / len(top_10)
    
    @staticmethod
    def grounding_score_1to5(query: str, chunk: Dict) -> int:
        """Compute grounding score 1-5 based on token overlap."""
        if not chunk:
            return 1
        
        # Extract text from chunk
        chunk_text = ""
        if 'text' in chunk:
            chunk_text += chunk['text']
        if 'title' in chunk:
            chunk_text += " " + chunk['title']
        
        # Tokenize (simple whitespace + punctuation split)
        query_tokens = set(re.findall(r'\b\w+\b', query.lower()))
        chunk_tokens = set(re.findall(r'\b\w+\b', chunk_text.lower()))
        
        if len(query_tokens) == 0:
            return 1
        
        overlap_ratio = len(query_tokens.intersection(chunk_tokens)) / len(query_tokens)
        
        # Map to 1-5 scale
        if overlap_ratio >= 0.60:
            return 5
        elif overlap_ratio >= 0.45:
            return 4
        elif overlap_ratio >= 0.30:
            return 3
        elif overlap_ratio >= 0.15:
            return 2
        else:
            return 1


def format_stones(stones) -> str:
    """Format stones for display."""
    if not stones:
        return ""
    if isinstance(stones, list):
        return ", ".join(stones)
    return str(stones)


def print_human_readable(query: str, results: List[Dict], metrics: Dict, 
                        model_name: str, lane: str, topk: int, show: int = 3):
    """Print human-readable results."""
    print(f"\nQuery: {query}")
    print(f"Lane: {lane}  |  Model: {model_name}  |  TopK: {topk}")
    print()
    
    print("Top 3:")
    for i, result in enumerate(results[:show], 1):
        chunk = result['chunk']
        score = result['score']
        protocol_id = chunk.get('protocol_id', 'N/A') if chunk else 'N/A'
        title = chunk.get('title', 'N/A') if chunk else 'N/A'
        theme_name = chunk.get('theme_name', 'N/A') if chunk else 'N/A'
        stones = format_stones(chunk.get('stones', '')) if chunk else ''
        
        print(f"  {i}) score={score:.3f}  proto={protocol_id}  \"{title}\"  [Theme: {theme_name}]  Stones: {stones}")
    
    print()
    print("Metrics:")
    for key, value in metrics.items():
        if isinstance(value, float):
            print(f"  {key}: {value:.2f}")
        else:
            print(f"  {key}: {value}")


def process_single_query(engine: ProtocolQueryEngine, 
                        query: str, 
                        target_stones: Optional[List[str]] = None,
                        topk: int = 20) -> Dict:
    """Process a single query and return metrics."""
    # Search
    scores, indices, latency_ms = engine.search(query, topk)
    
    # Get chunk metadata
    chunks = []
    for idx in indices:
        chunk = engine.get_chunk_metadata(idx)
        chunks.append(chunk)
    
    # Create results
    results = []
    for i, (score, chunk) in enumerate(zip(scores, chunks)):
        results.append({
            'rank': i + 1,
            'score': score,
            'chunk': chunk
        })
    
    # Calculate metrics
    coverage = 1.0 if len(results) > 0 else 0.0
    diversity = MetricsCalculator.diversity_top8(chunks)
    stones_alignment = MetricsCalculator.stones_alignment_top10(chunks, target_stones)
    
    # Grounding score for top result
    grounding_score = 1
    if chunks and chunks[0]:
        grounding_score = MetricsCalculator.grounding_score_1to5(query, chunks[0])
    
    hallucination_rate = 1.0 if grounding_score < 3 else 0.0
    
    metrics = {
        'precision_at_5': 'NA',
        'recall_at_20': 'NA',
        'mrr_at_10': 'NA',
        'ndcg_at_10': 'NA',
        'coverage': coverage,
        'latency_ms_p95': latency_ms,
        'diversity_avg_top8': diversity,
        'stones_alignment': stones_alignment,
        'grounding_1to5': grounding_score,
        'hallucination_rate': hallucination_rate,
        'lane': 'accurate',
        'num_queries': 1
    }
    
    return {
        'metrics': metrics,
        'results': results,
        'query_mode': 'single'
    }


def process_batch_queries(engine: ProtocolQueryEngine, 
                         queries_data: List[Dict],
                         topk: int = 20) -> Dict:
    """Process batch queries and return aggregated metrics."""
    all_precisions_5 = []
    all_recalls_20 = []
    all_mrrs_10 = []
    all_ndcgs_10 = []
    all_latencies = []
    all_diversities = []
    all_stones_alignments = []
    all_grounding_scores = []
    
    results_preview = []
    
    print(f"Processing {len(queries_data)} queries...")
    
    for i, query_data in enumerate(tqdm(queries_data, desc="Processing queries")):
        query = query_data['query']
        relevant_protocol_ids = query_data.get('relevant_protocol_ids', [])
        target_stones = query_data.get('target_stones', [])
        
        # Search
        scores, indices, latency_ms = engine.search(query, topk)
        all_latencies.append(latency_ms)
        
        # Get chunk metadata
        chunks = []
        retrieved_protocol_ids = []
        for idx in indices:
            chunk = engine.get_chunk_metadata(idx)
            chunks.append(chunk)
            if chunk and 'protocol_id' in chunk:
                retrieved_protocol_ids.append(chunk['protocol_id'])
        
        # Calculate relevance-based metrics
        if relevant_protocol_ids:
            # Debug: print first query's matching
            if i == 0:
                print(f"\nDebug - Query: {query[:50]}...")
                print(f"Debug - Relevant IDs: {relevant_protocol_ids}")
                print(f"Debug - Retrieved IDs (top 5): {retrieved_protocol_ids[:5]}")
                print(f"Debug - Any matches: {set(relevant_protocol_ids).intersection(set(retrieved_protocol_ids))}")
            
            relevance_scores = MetricsCalculator.compute_binary_relevance(
                retrieved_protocol_ids, relevant_protocol_ids)
            
            precision_5 = MetricsCalculator.precision_at_k(relevance_scores, 5)
            recall_20 = MetricsCalculator.recall_at_k(relevance_scores, 20, len(relevant_protocol_ids))
            mrr_10 = MetricsCalculator.mrr_at_k(relevance_scores, 10)
            ndcg_10 = MetricsCalculator.ndcg_at_k(relevance_scores, 10)
            
            all_precisions_5.append(precision_5)
            all_recalls_20.append(recall_20)
            all_mrrs_10.append(mrr_10)
            all_ndcgs_10.append(ndcg_10)
        
        # Calculate other metrics
        diversity = MetricsCalculator.diversity_top8(chunks)
        all_diversities.append(diversity)
        
        stones_alignment = MetricsCalculator.stones_alignment_top10(chunks, target_stones)
        all_stones_alignments.append(stones_alignment)
        
        # Grounding score for top result
        grounding_score = 1
        if chunks and chunks[0]:
            grounding_score = MetricsCalculator.grounding_score_1to5(query, chunks[0])
        all_grounding_scores.append(grounding_score)
        
        # Store preview for first query
        if i == 0:
            for j, (score, chunk) in enumerate(zip(scores[:3], chunks[:3])):
                results_preview.append({
                    'rank': j + 1,
                    'score': score,
                    'protocol_id': chunk.get('protocol_id', 'N/A') if chunk else 'N/A',
                    'title': chunk.get('title', 'N/A') if chunk else 'N/A',
                    'theme_name': chunk.get('theme_name', 'N/A') if chunk else 'N/A',
                    'stones': chunk.get('stones', []) if chunk else []
                })
    
    # Aggregate metrics
    num_queries = len(queries_data)
    coverage = 1.0  # Assuming all queries returned results
    
    precision_at_5 = statistics.mean(all_precisions_5) if all_precisions_5 else 0.0
    recall_at_20 = statistics.mean(all_recalls_20) if all_recalls_20 else 0.0
    mrr_at_10 = statistics.mean(all_mrrs_10) if all_mrrs_10 else 0.0
    ndcg_at_10 = statistics.mean(all_ndcgs_10) if all_ndcgs_10 else 0.0
    
    latency_ms_p95 = np.percentile(all_latencies, 95) if all_latencies else 0.0
    diversity_avg_top8 = statistics.mean(all_diversities)
    stones_alignment = statistics.mean(all_stones_alignments)
    grounding_1to5 = statistics.mean(all_grounding_scores)
    hallucination_rate = sum(1 for score in all_grounding_scores if score < 3) / len(all_grounding_scores)
    
    metrics = {
        'precision_at_5': precision_at_5,
        'recall_at_20': recall_at_20,
        'mrr_at_10': mrr_at_10,
        'ndcg_at_10': ndcg_at_10,
        'coverage': coverage,
        'latency_ms_p95': latency_ms_p95,
        'diversity_avg_top8': diversity_avg_top8,
        'stones_alignment': stones_alignment,
        'grounding_1to5': grounding_1to5,
        'hallucination_rate': hallucination_rate,
        'lane': 'accurate',
        'num_queries': num_queries
    }
    
    return {
        'metrics': metrics,
        'results_preview': results_preview,
        'query_mode': 'batch'
    }


def load_evalset(evalset_path: str) -> List[Dict]:
    """Load evaluation dataset from JSONL file."""
    queries_data = []
    with open(evalset_path, 'r') as f:
        for line in f:
            if line.strip():
                query_data = json.loads(line.strip())
                # Handle both 'gold_doc_ids' and 'relevant_protocol_ids' fields
                if 'gold_doc_ids' in query_data and 'relevant_protocol_ids' not in query_data:
                    query_data['relevant_protocol_ids'] = query_data['gold_doc_ids']
                queries_data.append(query_data)
    return queries_data


def save_results(results: Dict, output_path: str):
    """Save results to JSON file."""
    # Ensure logs directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Query protocol FAISS index with comprehensive metrics")
    
    # Input modes
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--query', type=str, help='Single query string')
    group.add_argument('--evalset', type=str, help='Path to evaluation dataset JSONL file')
    
    # Optional parameters
    parser.add_argument('--target-stones', nargs='*', help='Target stones for single query mode')
    parser.add_argument('--topk', type=int, default=20, help='Number of results to retrieve (default: 20)')
    parser.add_argument('--show', type=int, default=3, help='Number of results to show (default: 3)')
    parser.add_argument('--index-path', type=str, 
                       default='/Users/Nigel/Desktop/lichen-workspace/data/indexes/vecs_accurate.faiss',
                       help='Path to FAISS index file')
    parser.add_argument('--chunks-path', type=str,
                       default='/Users/Nigel/Desktop/lichen-workspace/data/chunks/chunks_accurate.jsonl',
                       help='Path to chunks JSONL file')
    
    args = parser.parse_args()
    
    # Initialize engine
    try:
        engine = ProtocolQueryEngine(
            index_path=args.index_path,
            chunks_path=args.chunks_path
        )
    except Exception as e:
        print(f"Error initializing query engine: {e}")
        return 1
    
    # Process queries
    if args.query:
        # Single query mode
        print(f"Processing single query: {args.query}")
        results = process_single_query(
            engine, 
            args.query, 
            target_stones=args.target_stones,
            topk=args.topk
        )
        
        # Print human-readable output
        print_human_readable(
            args.query, 
            results['results'], 
            results['metrics'],
            engine.model_name, 
            'accurate', 
            args.topk, 
            args.show
        )
        
    else:
        # Batch mode
        try:
            queries_data = load_evalset(args.evalset)
            print(f"Loaded {len(queries_data)} queries from {args.evalset}")
        except Exception as e:
            print(f"Error loading evalset: {e}")
            return 1
        
        results = process_batch_queries(engine, queries_data, args.topk)
        
        # Print summary
        print(f"\nBatch evaluation completed:")
        print(f"Processed {results['metrics']['num_queries']} queries")
        print(f"Average precision@5: {results['metrics']['precision_at_5']:.3f}")
        print(f"Average recall@20: {results['metrics']['recall_at_20']:.3f}")
        print(f"Average MRR@10: {results['metrics']['mrr_at_10']:.3f}")
        print(f"Average nDCG@10: {results['metrics']['ndcg_at_10']:.3f}")
        print(f"95th percentile latency: {results['metrics']['latency_ms_p95']:.1f}ms")
    
    # Prepare final results
    final_results = {
        'metrics': results['metrics'],
        'query_mode': results['query_mode'],
        'topk': args.topk,
        'index_path': args.index_path,
        'model': engine.model_name
    }
    
    if 'results_preview' in results:
        final_results['results_preview'] = results['results_preview']
    
    # Save results
    timestamp = int(time.time())
    output_path = f"/Users/Nigel/Desktop/lichen-workspace/logs/query_results_{timestamp}.json"
    save_results(final_results, output_path)
    
    # Print JSON to stdout
    print(f"\nJSON Results:")
    print(json.dumps(final_results, indent=2))
    print(f"\nResults saved to: {output_path}")
    
    return 0


if __name__ == "__main__":
    exit(main())
