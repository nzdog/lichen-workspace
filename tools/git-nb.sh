#!/bin/bash
#
# Git Branch Naming Helper (git-nb)
# 
# Creates branch names following convention:
# <type>/<area>-p<phase>-<scope>[-i<issue>]
#
# Usage:
#   git nb                                    # Interactive mode
#   git nb <type> <area> <phase> <scope> [issue]  # Command-line mode
#
# Examples:
#   git nb feature rag 2 "staging-observability" 7
#   git nb fix ai-room 3 "citation-ui" 42
#   git nb chore eval 1 "cleanup-old-data"
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Valid branch types
VALID_TYPES=("feature" "fix" "hotfix" "chore" "docs" "perf" "test" "spike" "release")

# Common areas (suggestions)
COMMON_AREAS=("rag" "ai-room" "canon" "indexer" "eval" "hallway" "protocol" "ui" "api" "config")

# Function to print colored output
print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# Function to normalize text to kebab-case
normalize_scope() {
    echo "$1" | tr '[:upper:]' '[:lower:]' | sed 's/[^a-z0-9]/-/g' | sed 's/--*/-/g' | sed 's/^-\|-$//g'
}

# Function to validate branch type
validate_type() {
    local type="$1"
    for valid_type in "${VALID_TYPES[@]}"; do
        if [[ "$type" == "$valid_type" ]]; then
            return 0
        fi
    done
    return 1
}

# Function to validate phase number
validate_phase() {
    local phase="$1"
    if [[ "$phase" =~ ^[0-9]+$ ]] && [[ "$phase" -gt 0 ]]; then
        return 0
    fi
    return 1
}

# Function to validate issue number
validate_issue() {
    local issue="$1"
    if [[ "$issue" =~ ^[0-9]+$ ]] && [[ "$issue" -gt 0 ]]; then
        return 0
    fi
    return 1
}

# Function to check if repo is clean
check_repo_status() {
    if ! git rev-parse --git-dir > /dev/null 2>&1; then
        print_error "Not in a git repository"
        exit 1
    fi
    
    # Check if there are any commits
    if ! git rev-parse HEAD > /dev/null 2>&1; then
        print_error "Repository has no commits yet. Make an initial commit first."
        exit 1
    fi
    
    # Check for uncommitted changes
    if ! git diff-index --quiet HEAD --; then
        print_warning "You have uncommitted changes."
        echo "Do you want to continue anyway? (y/N)"
        read -r response
        if [[ ! "$response" =~ ^[Yy]$ ]]; then
            print_info "Aborted. Commit or stash your changes first."
            exit 1
        fi
    fi
}

# Function to show type options
show_type_options() {
    echo "Valid types:"
    for i in "${!VALID_TYPES[@]}"; do
        echo "  $((i+1)). ${VALID_TYPES[$i]}"
    done
}

# Function to show area suggestions
show_area_suggestions() {
    echo "Common areas:"
    for area in "${COMMON_AREAS[@]}"; do
        echo "  - $area"
    done
}

# Function to get user input with validation
get_type() {
    local type="$1"
    
    if [[ -n "$type" ]]; then
        if validate_type "$type"; then
            echo "$type"
            return
        else
            print_error "Invalid type: $type"
        fi
    fi
    
    while true; do
        show_type_options
        echo -n "Enter type (1-${#VALID_TYPES[@]} or name): "
        read -r input
        
        # Check if it's a number
        if [[ "$input" =~ ^[0-9]+$ ]] && [[ "$input" -ge 1 ]] && [[ "$input" -le ${#VALID_TYPES[@]} ]]; then
            echo "${VALID_TYPES[$((input-1))]}"
            return
        fi
        
        # Check if it's a valid type name
        if validate_type "$input"; then
            echo "$input"
            return
        fi
        
        print_error "Invalid input. Please try again."
    done
}

get_area() {
    local area="$1"
    
    if [[ -n "$area" ]]; then
        echo "$area"
        return
    fi
    
    show_area_suggestions
    echo -n "Enter area: "
    read -r input
    
    if [[ -n "$input" ]]; then
        echo "$input"
    else
        print_error "Area cannot be empty"
        exit 1
    fi
}

get_phase() {
    local phase="$1"
    
    if [[ -n "$phase" ]]; then
        if validate_phase "$phase"; then
            echo "$phase"
            return
        else
            print_error "Invalid phase: $phase (must be a positive integer)"
        fi
    fi
    
    while true; do
        echo -n "Enter phase number (p1, p2, p3, ...): "
        read -r input
        
        if validate_phase "$input"; then
            echo "$input"
            return
        fi
        
        print_error "Phase must be a positive integer. Please try again."
    done
}

get_scope() {
    local scope="$1"
    
    if [[ -n "$scope" ]]; then
        echo "$(normalize_scope "$scope")"
        return
    fi
    
    echo -n "Enter scope (2-5 words, kebab-case): "
    read -r input
    
    if [[ -n "$input" ]]; then
        echo "$(normalize_scope "$input")"
    else
        print_error "Scope cannot be empty"
        exit 1
    fi
}

get_issue() {
    local issue="$1"
    
    if [[ -n "$issue" ]]; then
        if validate_issue "$issue"; then
            echo "$issue"
            return
        else
            print_error "Invalid issue number: $issue (must be a positive integer)"
            exit 1
        fi
    fi
    
    echo -n "Enter GitHub issue/PR number (optional, press Enter to skip): "
    read -r input
    
    if [[ -n "$input" ]]; then
        if validate_issue "$input"; then
            echo "$input"
        else
            print_error "Invalid issue number. Skipping issue number."
            echo ""
        fi
    else
        echo ""
    fi
}

# Function to build branch name
build_branch_name() {
    local type="$1"
    local area="$2"
    local phase="$3"
    local scope="$4"
    local issue="$5"
    
    local branch_name="${type}/${area}-p${phase}-${scope}"
    
    if [[ -n "$issue" ]]; then
        branch_name="${branch_name}-i${issue}"
    fi
    
    echo "$branch_name"
}

# Function to create and checkout branch
create_branch() {
    local branch_name="$1"
    
    print_info "Creating branch: $branch_name"
    
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        print_error "Branch '$branch_name' already exists"
        exit 1
    fi
    
    if git checkout -b "$branch_name"; then
        print_success "Created and switched to branch: $branch_name"
    else
        print_error "Failed to create branch: $branch_name"
        exit 1
    fi
}

# Main function
main() {
    print_info "Git Branch Naming Helper"
    echo "Convention: <type>/<area>-p<phase>-<scope>[-i<issue>]"
    echo ""
    
    # Check repository status
    check_repo_status
    
    # Parse command line arguments
    local type="$1"
    local area="$2"
    local phase="$3"
    local scope="$4"
    local issue="$5"
    
    # Get branch components
    type=$(get_type "$type")
    area=$(get_area "$area")
    phase=$(get_phase "$phase")
    scope=$(get_scope "$scope")
    issue=$(get_issue "$issue")
    
    # Build branch name
    local branch_name
    branch_name=$(build_branch_name "$type" "$area" "$phase" "$scope" "$issue")
    
    echo ""
    print_info "Branch name: $branch_name"
    echo ""
    
    # Confirm and create
    echo "Create this branch? (Y/n)"
    read -r response
    if [[ "$response" =~ ^[Nn]$ ]]; then
        print_info "Aborted."
        exit 0
    fi
    
    create_branch "$branch_name"
}

# Run main function with all arguments
main "$@"
