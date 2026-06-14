#!/usr/bin/env bash
# UI helpers for the interactive installer.
# - `say "$T_STRING"` for normal info messages
# - `explain "$T_STRING"` for longer explanations (can be skipped by experienced users)
# - `confirm "$T_QUESTION"` for yes/no prompts
# - `warn`, `err` for warnings/errors

# Color codes (only if tty)
if [[ -t 1 ]]; then
    C_RESET='\033[0m'
    C_BOLD='\033[1m'
    C_DIM='\033[2m'
    C_BLUE='\033[34m'
    C_GREEN='\033[32m'
    C_YELLOW='\033[33m'
    C_RED='\033[31m'
else
    C_RESET= C_BOLD= C_DIM= C_BLUE= C_GREEN= C_YELLOW= C_RED=
fi

print_header() {
    echo -e "${C_BLUE}${T_HEADER}${C_RESET}"
}

print_done_banner() {
    echo -e "${C_GREEN}${T_DONE_BANNER}${C_RESET}"
}

# Print a normal message with optional %s arguments.
say() {
    local fmt="$1"; shift
    # shellcheck disable=SC2059
    printf "${fmt}\n" "$@"
}

# Print a longer explanation. Users in `--quiet` mode skip these.
explain() {
    if [[ "${QUIET:-0}" == "1" ]]; then return; fi
    local fmt="$1"; shift
    # shellcheck disable=SC2059
    printf "${C_DIM}${fmt}${C_RESET}\n" "$@"
}

warn() {
    local fmt="$1"; shift
    # shellcheck disable=SC2059
    printf "${C_YELLOW}${fmt}${C_RESET}\n" "$@" >&2
}

err() {
    local fmt="$1"; shift
    # shellcheck disable=SC2059
    printf "${C_RED}${fmt}${C_RESET}\n" "$@" >&2
}

# Yes/no confirmation. Returns 0 for yes, 1 for no.
# In `--quiet` mode, returns the default (yes).
# Translation strings T_YES_NO_HINT and T_YES_NO_RETRY come from lib/i18n/*.sh.
confirm() {
    local prompt="$1"
    if [[ "${QUIET:-0}" == "1" ]]; then
        return 0
    fi
    local hint="${T_YES_NO_HINT:-[Y/n]}"
    local retry="${T_YES_NO_RETRY:-Answer with 'y' (yes) or 'n' (no).}"
    local answer
    while true; do
        printf "${C_BOLD}%s${C_RESET} %s " "$prompt" "$hint"
        read -r answer
        case "${answer,,}" in
            ""|o|oui|y|yes) return 0 ;;
            n|non|no) return 1 ;;
            *) echo "$retry" ;;
        esac
    done
}
