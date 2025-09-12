# Redaction System

The redaction system provides comprehensive protection for sensitive information in logs and data outputs. It automatically detects and redacts emails, phone numbers, names, API keys, and other sensitive data before writing to logs.

## Features

- **Comprehensive Pattern Matching**: Detects emails, phone numbers, names, SSNs, credit cards, API keys, and URLs
- **Environment Control**: Configurable via `REDACT_LOGS` environment flag
- **JSONL Support**: Specialized redaction for JSONL log files
- **Recursive Processing**: Handles nested dictionaries and lists
- **Performance Optimized**: Uses compiled regex patterns for efficiency

## Usage

### Basic Usage

```python
from hallway.redaction import redact_text, redact_dict, redact_jsonl_line

# Redact text
original = "Contact john@example.com or call (555) 123-4567"
redacted = redact_text(original)
# Result: "Contact [EMAIL_REDACTED] or call [PHONE_REDACTED]"

# Redact dictionary
data = {
    "user": "john@example.com",
    "phone": "(555) 123-4567",
    "name": "John Smith"
}
redacted_data = redact_dict(data)

# Redact JSONL line
jsonl_line = '{"user": "john@example.com", "query": "test"}\n'
redacted_line = redact_jsonl_line(jsonl_line)
```

### Advanced Usage

```python
from hallway.redaction import get_redactor

# Get redactor instance
redactor = get_redactor()

# Check if redaction is enabled
if redactor.redaction_enabled:
    print("Redaction is active")

# Get redaction statistics
stats = redactor.get_redaction_stats()
print(f"Patterns: {stats['patterns_count']}")
```

## Environment Configuration

### REDACT_LOGS Flag

Control redaction behavior with the `REDACT_LOGS` environment variable:

```bash
# Enable redaction (default)
export REDACT_LOGS=1

# Disable redaction
export REDACT_LOGS=0
```

The flag is documented in `config/rag.yaml`:

```yaml
# Environment variables:
#   REDACT_LOGS: "1" (default) or "0" to disable log redaction
```

## Redaction Patterns

The system includes patterns for:

### Email Addresses
- Pattern: `\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b`
- Example: `john@example.com` → `[EMAIL_REDACTED]`

### Phone Numbers
- **US Format**: `\+?1?[-.\s]?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b`
- **International**: `\+[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}[-.\s]?[0-9]{1,4}\b`
- Example: `(555) 123-4567` → `[PHONE_REDACTED]`

### Names
- Pattern: `\b[A-Z][a-z]+ [A-Z][a-z]+\b`
- Example: `John Smith` → `[NAME_REDACTED]`

### Social Security Numbers
- Pattern: `\b[0-9]{3}[-.\s]?[0-9]{2}[-.\s]?[0-9]{4}\b`
- Example: `123-45-6789` → `[SSN_REDACTED]`

### Credit Card Numbers
- Pattern: `\b[0-9]{4}[-.\s]?[0-9]{4}[-.\s]?[0-9]{4}[-.\s]?[0-9]{4}\b`
- Example: `4532-1234-5678-9012` → `[CARD_REDACTED]`

### API Keys and Tokens
- Pattern: `\b[A-Za-z0-9]{20,}\b`
- Example: `sk-1234567890abcdef1234567890abcdef` → `[API_KEY_REDACTED]`

### URLs
- Pattern: `https?://[^\s]+`
- Example: `https://api.example.com/v1/data` → `[URL_REDACTED]`

## Integration

### RAG Observability

The redaction system is automatically integrated with RAG observability logging:

```python
# In rag_observability.py
from .redaction import get_redactor

# Before writing logs
redactor = get_redactor()
redacted_event = redactor.redact_dict(event)
```

### Custom Integration

To integrate redaction into your own logging system:

```python
from hallway.redaction import get_redactor

def log_data(data):
    redactor = get_redactor()
    redacted_data = redactor.redact_dict(data)
    
    # Write redacted data to logs
    with open("log.jsonl", "a") as f:
        f.write(json.dumps(redacted_data) + "\n")
```

## Security Considerations

### What Gets Redacted

- ✅ Email addresses
- ✅ Phone numbers (US and international formats)
- ✅ Names (basic patterns)
- ✅ Social Security Numbers
- ✅ Credit card numbers
- ✅ API keys and tokens
- ✅ URLs (to prevent data leakage)

### What Doesn't Get Redacted

- ❌ IP addresses (may be needed for debugging)
- ❌ Timestamps (needed for log analysis)
- ❌ System identifiers (needed for operations)
- ❌ Generic text content

### Limitations

1. **Pattern Accuracy**: Some patterns may have false positives or negatives
2. **Context Awareness**: The system doesn't understand context (e.g., legitimate vs. sensitive data)
3. **Custom Patterns**: Additional patterns may be needed for specific use cases

## Testing

The redaction system includes comprehensive tests:

```bash
# Run redaction tests
python3 test_redaction.py
```

Test coverage includes:
- Pattern matching accuracy
- Environment flag behavior
- JSONL redaction
- Integration with observability logging

## Performance

- **Compiled Regex**: Patterns are compiled once for efficiency
- **Lazy Evaluation**: Redaction only occurs when enabled
- **Minimal Overhead**: Fast pattern matching with word boundaries

## Troubleshooting

### Redaction Not Working

1. Check environment flag: `echo $REDACT_LOGS`
2. Verify pattern matching: Test with known sensitive data
3. Check integration: Ensure redaction is called before logging

### False Positives

1. Review pattern specificity
2. Add custom patterns for your use case
3. Consider context-aware redaction for complex scenarios

### Performance Issues

1. Profile pattern matching performance
2. Consider reducing pattern complexity
3. Implement caching for repeated data

## Future Enhancements

- **Machine Learning**: Context-aware redaction using ML models
- **Custom Patterns**: User-defined redaction patterns
- **Audit Logging**: Track what was redacted for compliance
- **Pattern Updates**: Dynamic pattern updates without restarts
