#!/usr/bin/env python3
"""
Example Usage of Protocol Room
Demonstrates basic and advanced usage patterns
"""

from .protocol_room import run_protocol_room
from .types import ProtocolRoomInput


def basic_protocol_request_example():
    """Example: Basic protocol request by ID"""
    print("=== Basic Protocol Request ===")
    
    input_data = ProtocolRoomInput(
        session_state_ref='example-session-1',
        payload={
            'protocol_id': 'clearing_entry',
            'depth': 'full'
        }
    )
    
    result = run_protocol_room(input_data)
    print(f"Protocol: {result.display_text[:100]}...")
    print(f"Next Action: {result.next_action}")
    print()


def scenario_based_protocol_example():
    """Example: Protocol selection based on scenario"""
    print("=== Scenario-Based Protocol Selection ===")
    
    input_data = ProtocolRoomInput(
        session_state_ref='example-session-2',
        payload={
            'scenario': 'overwhelm',
            'depth': 'scenario'
        }
    )
    
    result = run_protocol_room(input_data)
    print(f"Protocol: {result.display_text[:100]}...")
    print(f"Next Action: {result.next_action}")
    print()


def depth_selection_example():
    """Example: Different depth selections"""
    print("=== Depth Selection Examples ===")
    
    depths = ['full', 'theme', 'scenario']
    
    for depth in depths:
        input_data = ProtocolRoomInput(
            session_state_ref=f'example-session-{depth}',
            payload={
                'protocol_id': 'pacing_adjustment',
                'depth': depth
            }
        )
        
        result = run_protocol_room(input_data)
        print(f"{depth.upper()}: {result.display_text[:80]}...")
    
    print()


def readiness_based_depth_example():
    """Example: Depth selection based on readiness level"""
    print("=== Readiness-Based Depth Selection ===")
    
    readiness_levels = ['NOW', 'HOLD', 'LATER', 'SOFT_HOLD']
    
    for readiness in readiness_levels:
        input_data = ProtocolRoomInput(
            session_state_ref=f'example-session-{readiness}',
            payload={
                'protocol_id': 'integration_pause',
                'readiness_level': readiness
            }
        )
        
        result = run_protocol_room(input_data)
        print(f"{readiness}: {result.display_text[:80]}...")
    
    print()


def time_based_depth_example():
    """Example: Depth selection based on available time"""
    print("=== Time-Based Depth Selection ===")
    
    time_scenarios = [3, 10, 20]  # minutes
    
    for time_available in time_scenarios:
        input_data = ProtocolRoomInput(
            session_state_ref=f'example-session-{time_available}min',
            payload={
                'protocol_id': 'resourcing_mini_walk',
                'time_available': time_available
            }
        )
        
        result = run_protocol_room(input_data)
        print(f"{time_available}min: {result.display_text[:80]}...")
    
    print()


def diagnostic_integration_example():
    """Example: Integration with diagnostic signals"""
    print("=== Diagnostic Integration Example ===")
    
    input_data = ProtocolRoomInput(
        session_state_ref='example-session-diagnostic',
        payload={
            'suggested_protocol_id': 'clearing_entry',
            'readiness_level': 'HOLD',
            'depth': 'theme'
        }
    )
    
    result = run_protocol_room(input_data)
    print(f"Diagnostic-Guided: {result.display_text[:100]}...")
    print(f"Next Action: {result.next_action}")
    print()


def main():
    """Run all examples"""
    print("Protocol Room Usage Examples\n")
    
    basic_protocol_request_example()
    scenario_based_protocol_example()
    depth_selection_example()
    readiness_based_depth_example()
    time_based_depth_example()
    diagnostic_integration_example()
    
    print("All examples completed successfully!")


if __name__ == "__main__":
    main()
