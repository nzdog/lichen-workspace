# mvp_build/utils/redaction.py
import os, re, logging

EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.\w+')
PHONE_RE = re.compile(r'(\+?\d[\d\s\-\(\)]{7,}\d)')
BIG_JSON_RE = re.compile(r'\{[^{}]{200,}\}', re.DOTALL)

def redact_text(text: str) -> str:
    if not isinstance(text, str):
        text = str(text)
    text = EMAIL_RE.sub('[REDACTED_EMAIL]', text)
    text = PHONE_RE.sub('[REDACTED_PHONE]', text)
    # Mask large JSON-like blobs (e.g., protocol dumps)
    text = BIG_JSON_RE.sub('{...[REDACTED_JSON]...}', text)
    return text

def safe_log(logger: logging.Logger, level: int, msg: str, *args, **kwargs):
    """Use this instead of logger.info(...) etc. in prod paths."""
    if os.getenv('LOG_REDACTION') == '1':
        msg = redact_text(msg)
    return logger.log(level, msg, *args, **kwargs)