"""
Canon Module
Implements Canon Fidelity theme from Protocol Room Protocol
"""

import json
from pathlib import Path
from typing import Dict, Optional, List, Any

from .types import ProtocolText, Protocols


def _get_protocols_directory() -> Path:
    """Get the absolute path to the protocols directory"""
    # canon.py is in: lichen-protocol-mvp/rooms/protocol_room/canon.py
    # protocols directory is: lichen-protocol-mvp/protocols/
    # So we need to go up 2 levels: protocol_room -> rooms -> lichen-protocol-mvp, then into protocols
    return Path(__file__).resolve().parent.parent.parent / "protocols"


def _load_protocol_json(protocol_id: str) -> Optional[Dict[str, Any]]:
    """Load a protocol JSON file from the filesystem"""
    protocols_dir = _get_protocols_directory()
    protocol_file = protocols_dir / f"{protocol_id}.json"
    
    if not protocol_file.exists():
        return None
    
    try:
        with open(protocol_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"ERROR: Failed to load protocol {protocol_id} from {protocol_file}: {e}")
        return None


def _format_protocol_for_display(protocol_data: Dict[str, Any]) -> str:
    """Format protocol JSON data into display text"""
    lines = [
        f"# {protocol_data.get('Title', 'Unknown Protocol')}",
        "",
        f"**Purpose:** {protocol_data.get('Overall Purpose', 'No purpose specified')}",
        "",
        f"**When to Use:** {protocol_data.get('When To Use This Protocol', 'No guidance provided')}",
        "",
        "## Overall Outcomes",
    ]
    
    outcomes = protocol_data.get('Overall Outcomes', {})
    for level, description in outcomes.items():
        lines.append(f"- **{level}:** {description}")
    
    lines.append("")
    lines.append("## Themes")
    
    themes = protocol_data.get('Themes', [])
    for theme in themes:
        lines.append(f"### {theme.get('Name', 'Unnamed Theme')}")
        lines.append(f"**Purpose:** {theme.get('Purpose of This Theme', 'No purpose specified')}")
        lines.append(f"**Why This Matters:** {theme.get('Why This Matters', 'No explanation provided')}")
        
        # Add guiding questions if available
        guiding_questions = theme.get('Guiding Questions', [])
        if guiding_questions:
            lines.append("**Guiding Questions:**")
            for question in guiding_questions:
                lines.append(f"- {question}")
        
        lines.append("")
    
    # Add completion prompts if available
    completion_prompts = protocol_data.get('Completion Prompts', [])
    if completion_prompts:
        lines.append("## Completion Prompts")
        for prompt in completion_prompts:
            lines.append(f"- {prompt}")
        lines.append("")
    
    return "\n".join(lines)


def _format_themes_only(protocol_data: Dict[str, Any]) -> str:
    """Format only the Themes section for theme-level depth"""
    lines = ["## Themes"]
    
    themes = protocol_data.get('Themes', [])
    for theme in themes:
        lines.append(f"### {theme.get('Name', 'Unnamed Theme')}")
        lines.append(f"**Purpose:** {theme.get('Purpose of This Theme', 'No purpose specified')}")
        lines.append(f"**Why This Matters:** {theme.get('Why This Matters', 'No explanation provided')}")
        
        # Add guiding questions if available
        guiding_questions = theme.get('Guiding Questions', [])
        if guiding_questions:
            lines.append("**Guiding Questions:**")
            for question in guiding_questions:
                lines.append(f"- {question}")
        
        lines.append("")
    
    return "\n".join(lines)


def _format_scenario_only(protocol_data: Dict[str, Any]) -> str:
    """Format only the scenario information for scenario-level depth"""
    lines = [
        f"# {protocol_data.get('Title', 'Unknown Protocol')}",
        "",
        f"**Purpose:** {protocol_data.get('Overall Purpose', 'No purpose specified')}",
        "",
        f"**When to Use:** {protocol_data.get('When To Use This Protocol', 'No guidance provided')}",
    ]
    
    return "\n".join(lines)


def fetch_protocol_text(protocol_id: str) -> Optional[ProtocolText]:
    """
    Fetch exact protocol text from filesystem.
    No editing, no paraphrasing, no distortion.
    Returns the protocol exactly as authored.
    """
    protocol_data = _load_protocol_json(protocol_id)
    if not protocol_data:
        return None
    
    protocols_dir = _get_protocols_directory()
    protocol_file = protocols_dir / f"{protocol_id}.json"
    print(f"DEBUG canon.py loading {protocol_id} from {protocol_file}")
    
    # Create ProtocolText object from JSON data
    return ProtocolText(
        protocol_id=protocol_id,
        title=protocol_data.get('Title', 'Unknown Protocol'),
        description=protocol_data.get('Overall Purpose', 'No description available'),
        full_text=_format_protocol_for_display(protocol_data),
        theme_text=_format_themes_only(protocol_data),
        scenario_text=_format_scenario_only(protocol_data)
    )


def get_protocol_by_depth(protocol_id: str, depth: str) -> Optional[str]:
    """
    Get protocol text at the specified depth.
    Returns exact text without modification.
    """
    print(f"DEBUG canon.py loading protocol by depth: {protocol_id} at depth {depth}")
    
    protocol_data = _load_protocol_json(protocol_id)
    if not protocol_data:
        return None
    
    protocols_dir = _get_protocols_directory()
    protocol_file = protocols_dir / f"{protocol_id}.json"
    print(f"DEBUG canon.py loading {protocol_id} from {protocol_file}")
    
    if depth == "full":
        return _format_protocol_for_display(protocol_data)
    elif depth == "theme":
        return _format_themes_only(protocol_data)
    elif depth == "scenario":
        return _format_scenario_only(protocol_data)
    else:
        return _format_protocol_for_display(protocol_data)  # Default to full text


def list_available_protocols() -> List[str]:
    """List all available protocol IDs in the canon"""
    protocols_dir = _get_protocols_directory()
    print(f"DEBUG canon.py listing all available protocols from {protocols_dir}")
    
    if not protocols_dir.exists():
        print(f"ERROR: Protocols directory does not exist: {protocols_dir}")
        return []
    
    protocol_files = list(protocols_dir.glob("*.json"))
    protocol_ids = [f.stem for f in protocol_files]
    
    print(f"DEBUG canon.py found {len(protocol_ids)} protocols: {protocol_ids}")
    return protocol_ids