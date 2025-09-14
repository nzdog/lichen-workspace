# Router Improvement Plan

## Current Issues Analysis
- **Average relevance: 0.013** (terrible semantic matching)
- **93.3% false positive rate** (routing to irrelevant protocols)
- **Protocol data quality issues** (auto IDs, poor key phrases)
- **Scoring algorithm mismatch** (high confidence ≠ actual relevance)

## Option 1: Targeted Improvements (Recommended)

### A. Better Key Phrase Extraction (High Impact, Low Effort)
```python
# Current: Basic title/theme extraction
# Improved: Extract actual meaningful phrases from protocol content
def extract_better_key_phrases(protocol_data):
    key_phrases = []

    # Theme names (high weight)
    for theme in protocol_data.get('Themes', []):
        if 'Name' in theme:
            key_phrases.append(theme['Name'])

    # Extract key terms from outcomes
    for outcome in protocol_data.get('Overall Outcomes', {}).values():
        # Extract key nouns/phrases using simple NLP
        key_phrases.extend(extract_key_terms(outcome))

    # Extract from "When To Use This Protocol"
    when_to_use = protocol_data.get('When To Use This Protocol', '')
    key_phrases.extend(extract_key_terms(when_to_use))

    return key_phrases
```

### B. Improved Scoring Algorithm (High Impact, Medium Effort)
```python
def score_protocol_improved(query, protocol_entry):
    score = 0.0

    # 1. Exact phrase matches (very high weight)
    exact_matches = count_exact_phrases(query, protocol_entry.key_phrases)
    score += exact_matches * 0.5

    # 2. Semantic embedding similarity (medium weight)
    embed_sim = cosine_similarity(query_embedding, protocol_embedding)
    score += embed_sim * 0.3

    # 3. Stones alignment with synonyms (medium weight)
    stones_overlap = calculate_stones_overlap_with_synonyms(query, protocol_stones)
    score += stones_overlap * 0.15

    # 4. Title relevance (low weight but important)
    title_relevance = calculate_title_relevance(query, protocol_title)
    score += title_relevance * 0.05

    return score
```

### C. Query Intent Classification (Medium Impact, Medium Effort)
```python
def classify_query_intent(query):
    """Classify query into categories to improve routing."""
    intents = []

    # Leadership patterns
    if any(word in query.lower() for word in ['leadership', 'leading', 'leader']):
        intents.append('leadership')

    # Stewardship patterns
    if any(word in query.lower() for word in ['stewardship', 'steward', 'ownership', 'responsibility']):
        intents.append('stewardship')

    # System patterns
    if any(word in query.lower() for word in ['system', 'align', 'rhythm', 'flow']):
        intents.append('system_alignment')

    # Conflict/repair patterns
    if any(word in query.lower() for word in ['conflict', 'repair', 'tension', 'difficult']):
        intents.append('conflict_resolution')

    return intents
```

### D. Relevance Validation Before Routing (High Impact, Low Effort)
```python
def route_with_validation(parsed_query):
    # Get top candidates using current algorithm
    candidates = current_routing_algorithm(parsed_query)

    # Validate relevance of top candidate
    top_relevance = calculate_actual_relevance(parsed_query.text, candidates[0])

    # Only route if relevance meets threshold
    if top_relevance >= 0.2:  # Much higher than current 0.013 average
        return candidates
    else:
        logger.info(f"Router validation failed: relevance {top_relevance:.3f} too low")
        return []  # Fallback to global search
```

## Option 2: Hybrid Approach (Medium Complexity)

### Combine Multiple Routing Methods:
1. **Keyword-based routing** for exact matches
2. **Embedding-based routing** for semantic similarity
3. **Rule-based routing** for specific patterns
4. **Fallback to global search** when confidence is low

```python
def hybrid_route(query):
    # Try exact keyword matching first
    exact_matches = find_exact_keyword_matches(query)
    if exact_matches and confidence > 0.8:
        return exact_matches

    # Try embedding-based routing
    semantic_matches = embedding_route(query)
    if semantic_matches and confidence > 0.4:
        return semantic_matches

    # Try rule-based patterns
    rule_matches = rule_based_route(query)
    if rule_matches:
        return rule_matches

    # Fallback to global search
    return []
```

## Option 3: Completely New Approach

### A. Query Classification + Protocol Tagging
Instead of semantic routing, classify queries into categories and pre-tag protocols:

```python
# Query classification
QUERY_CATEGORIES = {
    'stewardship': ['stewardship', 'ownership', 'responsibility', 'care'],
    'leadership': ['leadership', 'leading', 'authority', 'guidance'],
    'system_rhythm': ['rhythm', 'pace', 'flow', 'alignment'],
    'conflict_repair': ['conflict', 'tension', 'repair', 'difficult']
}

# Protocol tagging
PROTOCOL_CATEGORIES = {
    'auto_1755597150233_0': ['stewardship', 'responsibility'],
    'pacing_adjustment': ['system_rhythm', 'pace'],
    # ... manually curate or auto-generate
}
```

### B. Learning-Based Approach
Train a simple classifier on query-protocol relevance:

1. Generate training data from validation results
2. Train ML model to predict relevance
3. Use model for routing decisions

## Recommendation: Try Option 1 First

**Effort**: 4-6 hours
**Expected Impact**: Improve relevance from 0.013 to 0.15+ (10x improvement)
**Risk**: Low - easy to revert

**Implementation Order**:
1. ✅ Better key phrase extraction (30 min)
2. ✅ Relevance validation before routing (30 min)
3. ✅ Improved scoring algorithm (2 hours)
4. ✅ Query intent classification (1 hour)

**Success Metrics**:
- Average relevance > 0.15
- False positive rate < 50%
- At least 30% of high-confidence routes should be relevant

If Option 1 doesn't achieve these metrics, then consider Option 2 or 3.