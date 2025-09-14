# tests/test_redaction_canary.py
import os
import logging
from mvp_build.utils.redaction import redact_text, safe_log

def test_redaction_env_flags_present():
    assert os.getenv('PII_REDACTION') == '1'
    assert os.getenv('LOG_REDACTION') == '1'

def test_redacts_email_and_phone_and_big_json(caplog):
    os.environ['LOG_REDACTION'] = '1'
    logger = logging.getLogger('canary')
    logger.setLevel(logging.INFO)

    raw = (
        "Founder email: alice@example.com, phone: +1 (415) 555-1212\n"
        + '{"Title":"The Leadership I’m Actually Carrying","Overall Purpose":"Reveal the true weight",'
        + '"Why This Matters":"Unacknowledged burdens distort leadership and drain energy.",'
        + '"Themes":[{"Name":"Name the Weight Behind the Role","Outcomes":{"Poor":{"Present pattern":"Ignore hidden weight."}}}]}'
    )

    with caplog.at_level(logging.INFO):
        safe_log(logger, logging.INFO, raw)

    logged = "\n".join(rec.message for rec in caplog.records)
    assert 'alice@example.com' not in logged
    assert '415' not in logged
    assert '[REDACTED_EMAIL]' in logged
    assert '[REDACTED_PHONE]' in logged
    assert '[REDACTED_JSON]' in logged

def test_redaction_off_allows_raw(caplog):
    os.environ['LOG_REDACTION'] = '0'
    logger = logging.getLogger('canary2')
    logger.setLevel(logging.INFO)
    sample = "email bob@demo.co"
    with caplog.at_level(logging.INFO):
        safe_log(logger, logging.INFO, sample)
    logged = "\n".join(rec.message for rec in caplog.records)
    assert 'bob@demo.co' in logged  # sanity: off means raw