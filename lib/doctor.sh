#!/usr/bin/env bash
# Pre-flight checks for the kit installer.

doctor_check_basic() {
    local missing=()
    for cmd in curl bash tmux git; do
        if ! command -v "$cmd" >/dev/null 2>&1; then
            missing+=("$cmd")
        fi
    done

    if (( ${#missing[@]} > 0 )); then
        err "Outils manquants: ${missing[*]}"
        err "Installe-les avec: apt-get install ${missing[*]} (Debian/Ubuntu/Pop), brew install ${missing[*]} (macOS), ou via Container Manager (Synology)"
        return 1
    fi
    return 0
}
