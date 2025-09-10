#!/usr/bin/env python3
"""
Example Usage of Entry Room
Demonstrates basic and advanced usage patterns
"""

import asyncio
from entry_room.entry_room import (
    EntryRoom, run_entry_room, EntryRoomInput, EntryRoomConfig
)
from entry_room.completion import CustomCompletionPolicy
from entry_room.pace import SimplePacePolicy


async def basic_usage_example():
    """Basic usage example"""
    print("=== Basic Usage Example ===")
    
    # Create input
    input_data = EntryRoomInput(
        session_state_ref='example-session-123',
        payload='I have concerns about the project timeline and quality.'
    )
    
    # Create a consent policy that allows proceeding
    from entry_room.consent import ExplicitConsentPolicy
    consent_policy = ExplicitConsentPolicy(require_explicit_consent=False)
    
    # Run entry room with custom consent policy
    config = EntryRoomConfig(consent=consent_policy)
    result = await run_entry_room(input_data, config)
    
    print(f"Display Text: {result.display_text}")
    print(f"Next Action: {result.next_action}")
    print()


async def advanced_configuration_example():
    """Advanced configuration example"""
    print("=== Advanced Configuration Example ===")
    
    # Create custom policies
    custom_completion = CustomCompletionPolicy('[COMPLETE]')
    custom_pace = SimplePacePolicy('HOLD')
    
    # Create a consent policy that allows proceeding
    from entry_room.consent import ExplicitConsentPolicy
    consent_policy = ExplicitConsentPolicy(require_explicit_consent=False)
    
    # Create configuration
    config = EntryRoomConfig(
        completion=custom_completion,
        pace=custom_pace,
        diagnostics_default=False,
        consent=consent_policy
    )
    
    # Create input
    input_data = EntryRoomInput(
        session_state_ref='advanced-session-456',
        payload="""I have several concerns:
1. First concern about timing
2. Second concern about quality
3. Third concern about resources"""
    )
    
    # Run entry room with custom config
    result = await run_entry_room(input_data, config)
    
    print(f"Display Text: {result.display_text}")
    print(f"Next Action: {result.next_action}")
    print()


async def class_based_usage_example():
    """Class-based usage example"""
    print("=== Class-Based Usage Example ===")
    
    # Create a consent policy that allows proceeding
    from entry_room.consent import ExplicitConsentPolicy
    consent_policy = ExplicitConsentPolicy(require_explicit_consent=False)
    
    # Create entry room instance with custom consent policy
    config = EntryRoomConfig(consent=consent_policy)
    room = EntryRoom(config)
    
    # Create input
    input_data = EntryRoomInput(
        session_state_ref='class-session-789',
        payload='Simple single idea payload'
    )
    
    # Run entry room
    result = await room.run_entry_room(input_data)
    
    print(f"Display Text: {result.display_text}")
    print(f"Next Action: {result.next_action}")
    print()


async def main():
    """Main function to run all examples"""
    print("Entry Room Implementation Examples")
    print("=" * 40)
    print()
    
    await basic_usage_example()
    await advanced_configuration_example()
    await class_based_usage_example()
    
    print("All examples completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
