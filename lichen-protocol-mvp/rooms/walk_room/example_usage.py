#!/usr/bin/env python3
"""
Example Usage of Walk Room
Demonstrates basic and advanced usage patterns
"""

from .walk_room import run_walk_room
from .contract_types import WalkRoomInput


def basic_walk_example():
    """Demonstrate basic walk flow"""
    print("=== Basic Walk Example ===")
    
    # Start a new walk
    start_input = WalkRoomInput(
        session_state_ref='basic-example',
        payload={
            'protocol_id': 'grounding_protocol',
            'title': 'Grounding Protocol',
            'steps': [
                {
                    'title': 'Grounding Breath',
                    'content': 'Take 3 deep breaths, focusing on the sensation of breathing',
                    'description': 'Begin with grounding breath practice to center yourself',
                    'estimated_time': 2
                },
                {
                    'title': 'Resource Inventory',
                    'content': 'List 3 personal resources that are currently available to you',
                    'description': 'Identify your current resources and strengths',
                    'estimated_time': 3
                },
                {
                    'title': 'Centering Practice',
                    'content': 'Find your center point and connect with your core',
                    'description': 'Connect with your center and feel grounded',
                    'estimated_time': 2
                }
            ]
        }
    )
    
    print("Starting walk...")
    result = run_walk_room(start_input)
    print(f"First step: {result.display_text[:100]}...")
    print(f"Next action: {result.next_action}")
    print()


def pacing_examples():
    """Demonstrate different pacing scenarios"""
    print("=== Pacing Examples ===")
    
    # Start walk
    start_input = WalkRoomInput(
        session_state_ref='pacing-example',
        payload={
            'protocol_id': 'pacing_demo',
            'steps': [
                {'title': 'Step 1', 'description': 'First step'},
                {'title': 'Step 2', 'description': 'Second step'}
            ]
        }
    )
    
    run_walk_room(start_input)
    
    # Test different paces
    paces = ['NOW', 'HOLD', 'LATER', 'SOFT_HOLD']
    
    for pace in paces:
        pace_input = WalkRoomInput(
            session_state_ref='pacing-example',
            payload={'pace': pace}
        )
        
        result = run_walk_room(pace_input)
        print(f"Pace '{pace}' → next_action: {result.next_action}")
    
    print()


def step_progression_example():
    """Demonstrate step progression through a walk"""
    print("=== Step Progression Example ===")
    
    # Start walk
    start_input = WalkRoomInput(
        session_state_ref='progression-example',
        payload={
            'protocol_id': 'progression_demo',
            'steps': [
                {'title': 'Step 1', 'description': 'First step'},
                {'title': 'Step 2', 'description': 'Second step'},
                {'title': 'Step 3', 'description': 'Third step'}
            ]
        }
    )
    
    run_walk_room(start_input)
    
    # Progress through steps
    for step_num in range(3):
        print(f"--- Step {step_num + 1} ---")
        
        # Get current step
        current_input = WalkRoomInput(
            session_state_ref='progression-example',
            payload={}
        )
        
        result = run_walk_room(current_input)
        print(f"Current: {result.display_text[:80]}...")
        
        # Set pace
        pace_input = WalkRoomInput(
            session_state_ref='progression-example',
            payload={'pace': 'NOW'}
        )
        
        result = run_walk_room(pace_input)
        print(f"Pace set: {result.next_action}")
        
        # Advance if not last step
        if step_num < 2:
            advance_input = WalkRoomInput(
                session_state_ref='progression-example',
                payload={'action': 'advance_step'}
            )
            
            run_walk_room(advance_input)
            print("Advanced to next step")
        
        print()
    
    # Complete walk
    complete_input = WalkRoomInput(
        session_state_ref='progression-example',
        payload={'action': 'confirm_completion'}
    )
    
    result = run_walk_room(complete_input)
    print("=== Walk Complete ===")
    print(f"Summary: {result.display_text[:200]}...")
    print(f"Next action: {result.next_action}")
    print()


def diagnostics_example():
    """Demonstrate diagnostic capture"""
    print("=== Diagnostics Example ===")
    
    # Start walk
    start_input = WalkRoomInput(
        session_state_ref='diagnostics-example',
        payload={
            'protocol_id': 'diagnostics_demo',
            'steps': [
                {'title': 'Step 1', 'description': 'First step'},
                {'title': 'Step 2', 'description': 'Second step'}
            ]
        }
    )
    
    run_walk_room(start_input)
    
    # Set pace with diagnostics
    pace_input = WalkRoomInput(
        session_state_ref='diagnostics-example',
        payload={'pace': 'HOLD'}
    )
    
    result = run_walk_room(pace_input)
    print(f"Step 1 pace: HOLD → {result.next_action}")
    
    # Advance to next step
    advance_input = WalkRoomInput(
        session_state_ref='diagnostics-example',
        payload={'action': 'advance_step'}
    )
    
    run_walk_room(advance_input)
    
    # Set pace for second step
    pace_input2 = WalkRoomInput(
        session_state_ref='diagnostics-example',
        payload={'pace': 'NOW'}
    )
    
    result = run_walk_room(pace_input2)
    print(f"Step 2 pace: NOW → {result.next_action}")
    
    # Get walk status to see diagnostics
    status_input = WalkRoomInput(
        session_state_ref='diagnostics-example',
        payload={'action': 'get_walk_status'}
    )
    
    result = run_walk_room(status_input)
    print("Walk status:")
    print(result.display_text)
    print()


def error_handling_example():
    """Demonstrate error handling"""
    print("=== Error Handling Example ===")
    
    # Try to get status without session
    input_data = WalkRoomInput(
        session_state_ref='nonexistent-session',
        payload={'action': 'get_walk_status'}
    )
    
    result = run_walk_room(input_data)
    print(f"Error handling: {result.display_text}")
    print(f"Next action: {result.next_action}")
    print()
    
    # Try invalid pace
    start_input = WalkRoomInput(
        session_state_ref='error-example',
        payload={
            'protocol_id': 'error_demo',
            'steps': [{'title': 'Step 1', 'description': 'First step'}]
        }
    )
    
    run_walk_room(start_input)
    
    invalid_pace_input = WalkRoomInput(
        session_state_ref='error-example',
        payload={'pace': 'INVALID_PACE'}
    )
    
    result = run_walk_room(invalid_pace_input)
    print(f"Invalid pace handling: {result.display_text}")
    print()


def main():
    """Run all examples"""
    print("Walk Room Examples")
    print("=" * 50)
    print()
    
    basic_walk_example()
    pacing_examples()
    step_progression_example()
    diagnostics_example()
    error_handling_example()
    
    print("All examples completed!")


if __name__ == "__main__":
    main()
