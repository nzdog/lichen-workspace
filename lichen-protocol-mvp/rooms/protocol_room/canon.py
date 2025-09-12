"""
Canon Module
Implements Canon Fidelity theme from Protocol Room Protocol
"""

from typing import Dict, Optional, List
from .types import ProtocolText, Protocols


# Static canon store - in production this would be a database or file system
CANON_STORE: Dict[str, ProtocolText] = {
    Protocols.RESOURCING_MINI_WALK: ProtocolText(
        protocol_id=Protocols.RESOURCING_MINI_WALK,
        title="Resourcing Mini Walk",
        description="A brief protocol to help founders reconnect with their resources and center",
        full_text="""# Resourcing Mini Walk

## Purpose
To help founders reconnect with their inner resources and find their center when feeling overwhelmed or scattered.

## Steps
1. **Grounding Breath** (2 minutes)
   - Sit comfortably with feet on the ground
   - Take 3 deep breaths, feeling the earth support you
   - Notice where you feel most grounded in your body

2. **Resource Inventory** (3 minutes)
   - Name 3 personal strengths that have served you well
   - Identify 2 supportive relationships in your life
   - Recall 1 recent success or win, no matter how small

3. **Centering Practice** (2 minutes)
   - Place your hands on your heart or belly
   - Feel the rhythm of your breath
   - Say to yourself: "I am resourceful and capable"

## Completion
When you feel more centered and connected to your resources, you're ready to proceed.

## Notes
This protocol is designed for quick resourcing when time is limited. For deeper work, consider the full Resourcing Walk.""",
        theme_text="Quick grounding and resource reconnection for overwhelmed founders",
        scenario_text="When feeling scattered or overwhelmed, take 7 minutes to reconnect with your resources through grounding breath, resource inventory, and centering practice."
    ),
    
    Protocols.CLEARING_ENTRY: ProtocolText(
        protocol_id=Protocols.CLEARING_ENTRY,
        title="Clearing Entry",
        description="A foundational protocol to clear mental clutter and create space for new insights",
        full_text="""# Clearing Entry

## Purpose
To clear mental clutter, emotional residue, and create clean space for new insights and decisions.

## Steps
1. **Mental Decluttering** (5 minutes)
   - Write down all the thoughts, concerns, and to-dos swirling in your mind
   - Don't organize or prioritize yet - just get it all out
   - Notice what feels most urgent or heavy

2. **Emotional Clearing** (5 minutes)
   - Identify the primary emotion you're carrying
   - Where do you feel it in your body?
   - What would it look like to release it? (breath, movement, sound)

3. **Space Creation** (3 minutes)
   - Imagine clearing a physical space in your mind
   - What would you like to fill this clean space with?
   - Set an intention for what comes next

## Completion
When you feel mentally clearer and emotionally lighter, you're ready for the next step.

## Notes
This protocol works best when done before major decisions or creative work. It's the foundation for many other protocols.""",
        theme_text="Clear mental clutter and emotional residue to create space for new insights",
        scenario_text="When your mind feels cluttered or you're carrying emotional weight, take 13 minutes to declutter thoughts, clear emotions, and create clean mental space."
    ),
    
    Protocols.PACING_ADJUSTMENT: ProtocolText(
        protocol_id=Protocols.PACING_ADJUSTMENT,
        title="Pacing Adjustment",
        description="A protocol to help founders find their optimal rhythm and pace",
        full_text="""# Pacing Adjustment

## Purpose
To help founders identify and adjust their pace to match their current capacity and the demands of their situation.

## Steps
1. **Pace Assessment** (3 minutes)
   - Rate your current pace from 1 (too slow) to 10 (too fast)
   - What's driving your current pace?
   - How does this pace feel in your body?

2. **Capacity Check** (3 minutes)
   - What's your current energy level?
   - What external pressures are affecting your pace?
   - What would an ideal pace feel like?

3. **Pace Adjustment** (4 minutes)
   - Choose one small change to adjust your pace
   - How will you implement this change?
   - What support do you need to maintain this pace?

## Completion
When you have a clear sense of your optimal pace and a plan to adjust, you're ready to proceed.

## Notes
Pacing is crucial for sustainable growth. This protocol helps founders find their rhythm.""",
        theme_text="Assess and adjust your pace to match your capacity and situation",
        scenario_text="When your pace feels off or unsustainable, take 10 minutes to assess your current pace, check your capacity, and make one small adjustment."
    ),
    
    Protocols.INTEGRATION_PAUSE: ProtocolText(
        protocol_id=Protocols.INTEGRATION_PAUSE,
        title="Integration Pause",
        description="A protocol to help founders integrate insights and experiences",
        full_text="""# Integration Pause

## Purpose
To help founders pause and integrate insights, experiences, and learning before moving forward.

## Steps
1. **Reflection** (4 minutes)
   - What have you learned or experienced recently?
   - What insights are you carrying?
   - What feels unresolved or incomplete?

2. **Integration** (4 minutes)
   - How do these insights connect to your larger journey?
   - What patterns or themes are emerging?
   - What would integration look like for you?

3. **Forward Movement** (2 minutes)
   - What's the next small step?
   - How will you carry these insights forward?
   - What support do you need?

## Completion
When you feel your recent experiences are integrated and you're ready to move forward, you're complete.

## Notes
Integration is essential for sustainable growth. This protocol helps founders honor their learning.""",
        theme_text="Pause to integrate insights and experiences before moving forward",
        scenario_text="When you have new insights or experiences to integrate, take 10 minutes to reflect on what you've learned, integrate it into your journey, and plan your next step."
    )
}


def fetch_protocol_text(protocol_id: str) -> Optional[ProtocolText]:
    """
    Fetch exact protocol text from canon store.
    No editing, no paraphrasing, no distortion.
    Returns the protocol exactly as authored.
    """
    return CANON_STORE.get(protocol_id)


def get_protocol_by_depth(protocol_id: str, depth: str) -> Optional[str]:
    """
    Get protocol text at the specified depth.
    Returns exact text without modification.
    """
    protocol = fetch_protocol_text(protocol_id)
    if not protocol:
        return None
    
    if depth == "full":
        return protocol.full_text
    elif depth == "theme":
        return protocol.theme_text
    elif depth == "scenario":
        return protocol.scenario_text
    else:
        return protocol.full_text  # Default to full text


def list_available_protocols() -> List[str]:
    """List all available protocol IDs in the canon"""
    return list(CANON_STORE.keys())
