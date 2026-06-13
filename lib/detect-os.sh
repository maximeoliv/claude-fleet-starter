#!/usr/bin/env bash
# Detect the operating system.
# Returns a normalized string: "synology-dsm", "debian", "ubuntu", "macos",
# "arch", "fedora", or "unknown".

detect_os() {
    # macOS
    if [[ "$(uname)" == "Darwin" ]]; then
        echo "macos"
        return
    fi

    # Synology DSM (special)
    if [[ -f /etc/synoinfo.conf ]]; then
        local v
        v="$(grep -oE 'majorversion="[0-9]+"' /etc/synoinfo.conf | head -1 | sed 's/[^0-9]//g')"
        echo "synology-dsm-${v:-?}"
        return
    fi

    # /etc/os-release for modern Linux distros
    if [[ -f /etc/os-release ]]; then
        # shellcheck disable=SC1091
        . /etc/os-release
        case "${ID,,}" in
            debian|ubuntu|fedora|arch|pop|linuxmint|raspbian)
                echo "${ID,,}"
                return
                ;;
        esac
        # ID_LIKE fallback
        for like in ${ID_LIKE:-}; do
            case "$like" in
                debian|fedora|arch) echo "$like"; return ;;
            esac
        done
    fi

    echo "unknown"
}

# Quick helper: is this a Debian-family system?
is_debian_like() {
    local os="$1"
    case "$os" in
        debian|ubuntu|pop|linuxmint|raspbian) return 0 ;;
        *) return 1 ;;
    esac
}
