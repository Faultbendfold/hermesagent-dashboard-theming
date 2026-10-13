#!/bin/sh
# install.sh -- put this repository's dashboard themes into a Hermes home.
#
#   ./install.sh                          copy the themes, then say what to do next
#   ./install.sh --activate light-clean   copy, then select the theme in config
#   ./install.sh --list                   list the themes in this repository
#   ./install.sh --dest DIR               install into DIR instead of $HERMES_HOME/dashboard-themes
#   ./install.sh --hermes-home DIR        use DIR as the Hermes home (default: $HERMES_HOME, else ~/.hermes)
#   ./install.sh --force                  replace an existing theme file (the old one is kept as .bak)
#   ./install.sh --dry-run                show what would happen, change nothing
#   ./install.sh --status                 show the theme directory and the active theme
#
# Hermes reads user themes from "$HERMES_HOME/dashboard-themes/*.yaml". The
# directory is read once per page load, so a plain page reload is enough to see
# a theme appear -- no rebuild, no restart.
#
# Nothing here is destructive: a file that already exists and differs is left
# alone unless --force is given, and --force writes a timestamped .bak first.
# Revert any time with:  hermes config set dashboard.theme default

set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
src="$here/themes"

hermes_home=${HERMES_HOME:-$HOME/.hermes}
dest=""
activate=""
force=0
list_only=0
dry_run=0
status_only=0

usage() {
    sed -n '2,25p' "$0" | sed 's/^# \{0,1\}//'
}

while [ $# -gt 0 ]; do
    case "$1" in
        --dest)          dest=$2; shift 2 ;;
        --dest=*)        dest=${1#*=}; shift ;;
        --hermes-home)   hermes_home=$2; shift 2 ;;
        --hermes-home=*) hermes_home=${1#*=}; shift ;;
        --activate)      activate=$2; shift 2 ;;
        --activate=*)    activate=${1#*=}; shift ;;
        --force)         force=1; shift ;;
        --dry-run)       dry_run=1; shift ;;
        --status)        status_only=1; shift ;;
        --list)          list_only=1; shift ;;
        -h|--help)       usage; exit 0 ;;
        *) echo "install.sh: unknown argument: $1" >&2; usage >&2; exit 2 ;;
    esac
done

if [ ! -d "$src" ]; then
    echo "install.sh: no themes/ directory next to this script ($src)" >&2
    exit 2
fi

theme_name() { sed -n 's/^name:[[:space:]]*//p' "$1" | head -1 | tr -d '"'"'"; }
theme_label() { sed -n 's/^label:[[:space:]]*//p' "$1" | head -1 | tr -d '"'"'"; }

if [ "$status_only" -eq 1 ]; then
    sdir=${dest:-$hermes_home/dashboard-themes}
    echo "HERMES_HOME: $hermes_home"
    echo "theme dir:   $sdir"
    if [ -d "$sdir" ]; then
        echo "installed:"
        for f in "$sdir"/*.yaml; do
            [ -e "$f" ] || continue
            printf '  %-24s %s\n' "$(theme_name "$f")" "$(theme_label "$f")"
        done
    else
        echo "installed:   (the directory does not exist yet)"
    fi
    if command -v hermes >/dev/null 2>&1; then
        echo "active:      $(hermes config get dashboard.theme 2>/dev/null || echo '(could not read)')"
    else
        echo "active:      (hermes is not on PATH here -- run: hermes config get dashboard.theme)"
    fi
    exit 0
fi

if [ "$list_only" -eq 1 ]; then
    echo "themes in $src:"
    for f in "$src"/*.yaml; do
        [ -e "$f" ] || continue
        printf '  %-24s %s\n' "$(theme_name "$f")" "$(theme_label "$f")"
    done
    exit 0
fi

[ -n "$dest" ] || dest="$hermes_home/dashboard-themes"
mkdir -p "$dest"

echo "source:  $src"
echo "target:  $dest"
echo

copied=0
skipped=0
for f in "$src"/*.yaml; do
    [ -e "$f" ] || continue
    base=$(basename "$f")
    target="$dest/$base"
    replaced=0
    if [ "$dry_run" -eq 1 ]; then
        if [ ! -e "$target" ]; then
            echo "  + $base  would be written"
        elif cmp -s "$f" "$target"; then
            echo "  = $base  already identical, nothing to do"
        else
            echo "  ~ $base  would be replaced (the old one kept as .bak)"
        fi
        continue
    fi
    if [ -e "$target" ]; then
        if cmp -s "$f" "$target"; then
            echo "  = $base  (identical, left as is)"
            skipped=$((skipped + 1))
            continue
        fi
        if [ "$force" -ne 1 ]; then
            echo "  ! $base  exists and differs -- skipped (--force replaces it, keeping a .bak)"
            skipped=$((skipped + 1))
            continue
        fi
        bak="$target.bak-$(date +%Y%m%d-%H%M%S)"
        cp "$target" "$bak"
        echo "  ~ $base  replaced (previous kept as $(basename "$bak"))"
        replaced=1
    fi
    cp "$f" "$target"
    if [ "$replaced" -eq 0 ]; then
        echo "  + $base"
    fi
    copied=$((copied + 1))
done

echo
if [ "$dry_run" -eq 1 ]; then
    echo "dry run: nothing was written"
    exit 0
fi
echo "copied: $copied   skipped: $skipped"

if [ -n "$activate" ]; then
    if [ ! -f "$dest/$activate.yaml" ]; then
        echo "note: $dest/$activate.yaml does not exist -- activating anyway"
    fi
    if command -v hermes >/dev/null 2>&1; then
        hermes config set dashboard.theme "$activate"
        echo "active theme: $(hermes config get dashboard.theme 2>/dev/null || echo "$activate")"
    else
        echo "hermes is not on PATH here. On the machine that runs Hermes, run:"
        echo "    hermes config set dashboard.theme $activate"
    fi
fi

echo
echo "next:"
echo "  1. reload the dashboard page completely (the theme list is read once per page load),"
echo "     or pick the theme in the sidebar's theme control"
if [ -z "$activate" ]; then
    echo "  2. or activate one now:  hermes config set dashboard.theme <name>"
fi
echo "  revert with:             hermes config set dashboard.theme default"
