#!/usr/bin/env python3
"""
Cross-Contract Dependency Validator for Lichen Protocol
Validates that all dependencies in contract_registry.json are satisfied
"""

import json
import os
import sys
from pathlib import Path

# ANSI color codes for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def load_registry():
    """Load the contract registry"""
    registry_path = Path('contracts/contract_registry.json')
    
    if not registry_path.exists():
        print(f"{RED}❌ Contract registry not found at {registry_path}{RESET}")
        sys.exit(1)
    
    with open(registry_path) as f:
        return json.load(f)

def validate_file_paths(registry):
    """Check that all file paths in registry exist"""
    print(f"{BLUE}📁 Validating file paths...{RESET}")
    errors = []
    
    for contract_type in ['rooms', 'gates', 'services', 'rag', 'rag_build']:
        for contract_name, contract_info in registry['contracts'][contract_type].items():
            if contract_type in ['rag', 'rag_build']:
                # RAG and RAG build contracts are just name -> path mappings
                file_path = Path(contract_info.lstrip('./'))
            else:
                # Other contracts have version and path fields
                file_path = Path('contracts') / contract_info['path'].lstrip('./')
            
            if file_path.exists():
                print(f"{GREEN}✅ {contract_name}: {file_path}{RESET}")
            else:
                error_msg = f"{contract_name}: Missing file {file_path}"
                errors.append(error_msg)
                print(f"{RED}❌ {error_msg}{RESET}")
    
    return errors

def validate_gate_dependencies(registry):
    """Check that all gate dependencies exist"""
    print(f"{BLUE}🔗 Validating gate dependencies...{RESET}")
    errors = []
    
    available_gates = set(registry['contracts']['gates'].keys())
    print(f"{BLUE}Available gates: {', '.join(sorted(available_gates))}{RESET}")
    
    for room_name, room_info in registry['contracts']['rooms'].items():
        print(f"\n{BLUE}Checking {room_name}:{RESET}")
        
        dependencies = room_info.get('dependencies', [])
        
        for dep in dependencies:
            if dep in available_gates:
                print(f"{GREEN}  ✅ {dep}{RESET}")
            else:
                error_msg = f"{room_name} depends on missing gate: {dep}"
                errors.append(error_msg)
                print(f"{RED}  ❌ {error_msg}{RESET}")
    
    return errors

def validate_version_consistency(registry):
    """Check that all contracts use consistent versioning"""
    print(f"{BLUE}📋 Validating version consistency...{RESET}")
    errors = []
    
    versions = {}
    for contract_type in ['rooms', 'gates', 'services', 'rag', 'rag_build']:
        for contract_name, contract_info in registry['contracts'][contract_type].items():
            if contract_type in ['rag', 'rag_build']:
                # RAG and RAG build contracts don't have version info, skip version consistency check
                continue
            else:
                version = contract_info['version']
                if version not in versions:
                    versions[version] = []
                versions[version].append(f"{contract_type}/{contract_name}")
    
    for version, contracts in versions.items():
        print(f"{GREEN}✅ Version {version}: {len(contracts)} contracts{RESET}")
        if len(versions) > 1:
            print(f"  {', '.join(contracts[:3])}{'...' if len(contracts) > 3 else ''}")
    
    if len(versions) > 1:
        error_msg = f"Multiple versions found: {list(versions.keys())}"
        errors.append(error_msg)
        print(f"{YELLOW}⚠️  {error_msg}{RESET}")
    
    return errors

def main():
    """Main validation function"""
    print(f"{BLUE}🔍 Lichen Protocol Contract Dependency Validator{RESET}")
    print(f"{BLUE}=" * 50 + f"{RESET}")
    
    # Load registry
    registry = load_registry()
    print(f"{GREEN}✅ Contract registry loaded{RESET}")
    
    # Run all validations
    all_errors = []
    
    all_errors.extend(validate_file_paths(registry))
    all_errors.extend(validate_gate_dependencies(registry))
    all_errors.extend(validate_version_consistency(registry))
    
    # Summary
    print(f"\n{BLUE}📊 Validation Summary:{RESET}")
    
    if not all_errors:
        print(f"{GREEN}🎉 All validations passed! Contract system is consistent.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}❌ Found {len(all_errors)} issues:{RESET}")
        for i, error in enumerate(all_errors, 1):
            print(f"{RED}  {i}. {error}{RESET}")
        sys.exit(1)

if __name__ == "__main__":
    main()
