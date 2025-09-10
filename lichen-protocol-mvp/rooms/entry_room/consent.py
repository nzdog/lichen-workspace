"""
Consent Module
Implements Consent Anchor theme from Entry Room Protocol
"""

from .types import ConsentPolicy, EntryRoomContext


class DefaultConsentPolicy(ConsentPolicy):
    """Default consent policy implementation"""
    
    async def enforce_consent(self, ctx: EntryRoomContext) -> str:
        """
        Enforces explicit consent before proceeding.
        Returns consent status or short-circuits with hold/later.
        """
        # Default implementation: check if consent has been granted
        if ctx.consent_granted:
            return "YES"
        
        # No consent granted - return HOLD to request consent
        return "HOLD"


class ExplicitConsentPolicy(ConsentPolicy):
    """Explicit consent policy that requires clear consent signals"""
    
    def __init__(self, require_explicit_consent: bool = True):
        self.require_explicit_consent = require_explicit_consent
    
    async def enforce_consent(self, ctx: EntryRoomContext) -> str:
        """
        Explicit consent policy that requires clear consent signals.
        Can be configured for different consent models.
        """
        if not self.require_explicit_consent:
            return "YES"  # Skip consent requirement
        
        if ctx.consent_granted:
            return "YES"
        
        # No explicit consent - return HOLD
        return "HOLD"


class GraduatedConsentPolicy(ConsentPolicy):
    """Graduated consent policy that offers multiple consent levels"""
    
    async def enforce_consent(self, ctx: EntryRoomContext) -> str:
        """
        Graduated consent policy that offers multiple consent levels.
        Can handle different types of consent (immediate, deferred, etc.).
        """
        # This policy could implement more sophisticated consent logic
        # For now, use the basic consent check
        
        if ctx.consent_granted:
            return "YES"
        
        # Could implement logic to determine if this should be HOLD or LATER
        # based on context, user preferences, etc.
        return "HOLD"


def generate_consent_request() -> str:
    """Utility function to generate consent request message"""
    return "Before we proceed, I need your explicit consent to continue. Please confirm that you're ready to proceed with this session."


def is_consent_required(ctx: EntryRoomContext) -> bool:
    """Utility function to check if consent is required"""
    return not ctx.consent_granted
