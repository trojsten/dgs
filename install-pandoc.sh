#!/bin/bash
# Install pandoc and pandoc-crossref as a matched pair, into ~/.local/bin, without root.
#
# Called by `install.sh` and by `.github/workflows/python-app.yml`, so that the version lives in
# exactly one place. Everything else about the pair is a consequence, not a second choice:
#
# - **Only the filter is pinned.** pandoc-crossref is compiled against one pandoc and says so if
#   run through another: "pandoc-crossref was compiled with pandoc X but is being run through Y.
#   This is not supported. Strange things may (and likely will) happen silently." So ask the
#   filter which pandoc it wants and install exactly that one. Bumping the pair is editing the
#   line below and nothing else.
# - **pandoc does not come from apt.** Debian bookworm ships 2.17, and the repository needs a
#   pandoc that emits `\pandocbounded` for an attribute-less image (>= 3.2, which
#   `core/builder/convertor.py` refuses on purpose) and `keepaspectratio` on a sized one --
#   `core/tests/test_convertor.py::TestImages` fails against anything older. A stale pandoc
#   otherwise builds green and silently different.
# - **Nothing here needs sudo.** Both are single static binaries from upstream and live in
#   `$BIN_DIR`, so a version bump touches nothing outside your home directory and needs no
#   package manager's permission. This is also why the pandoc *tarball* is used and not the
#   .deb: the .deb owns /usr/bin/pandoc and would have to be installed as root.
# - **The filter is also linked into pandoc's data directory.** `pandoc --filter pandoc-crossref`
#   looks in `<user data directory>/filters` *before* it consults PATH, so the link makes the
#   matched copy win even on a machine where a stale pandoc-crossref sits earlier in PATH --
#   which is exactly the state this repository was built in for two years.
# - **The install is verified, not assumed.** A mismatched pair only warns, on stderr, in the
#   middle of a build. The check at the bottom fails the install instead.
set -euo pipefail

PANDOC_CROSSREF_VERSION="${PANDOC_CROSSREF_VERSION:-v0.3.25a}"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"

case "$(uname -m)" in
    x86_64 | amd64)  crossref_arch=X64;   pandoc_arch=amd64 ;;
    aarch64 | arm64) crossref_arch=ARM64; pandoc_arch=arm64 ;;
    *) echo "install-pandoc: unsupported architecture $(uname -m)" >&2; exit 1 ;;
esac

work=$(mktemp -d)
trap 'rm -rf "$work"' EXIT
mkdir -p "$BIN_DIR"

echo "install-pandoc: pandoc-crossref ${PANDOC_CROSSREF_VERSION} (${crossref_arch})"
curl -fsSL \
    "https://github.com/lierdakil/pandoc-crossref/releases/download/${PANDOC_CROSSREF_VERSION}/pandoc-crossref-Linux-${crossref_arch}.tar.xz" \
    | tar -xJ -C "$work"

# The extracted binary, not one already on PATH: what it reports has to be what we are about to
# install, or we would install a pandoc to match somebody else's filter.
PANDOC_VERSION=$("$work/pandoc-crossref" --version \
    | sed -n 's/.*built with Pandoc v\([0-9][0-9.]*\).*/\1/p')
if [ -z "$PANDOC_VERSION" ]; then
    echo "install-pandoc: could not read the pandoc version out of pandoc-crossref --version" >&2
    exit 1
fi
echo "install-pandoc: it was built with pandoc ${PANDOC_VERSION}, installing that"

curl -fsSL \
    "https://github.com/jgm/pandoc/releases/download/${PANDOC_VERSION}/pandoc-${PANDOC_VERSION}-linux-${pandoc_arch}.tar.gz" \
    | tar -xz -C "$work"
install -m755 "$work/pandoc-${PANDOC_VERSION}/bin/pandoc" "$BIN_DIR/pandoc"
install -m755 "$work/pandoc-crossref" "$BIN_DIR/pandoc-crossref"

# Ask the pandoc just installed where its data directory is, rather than guessing at
# XDG_DATA_HOME and pandoc's older ~/.pandoc fallback.
data_dir=$("$BIN_DIR/pandoc" --version | sed -n 's/^User data directory: //p')
if [ -n "$data_dir" ]; then
    mkdir -p "$data_dir/filters"
    ln -sf "$BIN_DIR/pandoc-crossref" "$data_dir/filters/pandoc-crossref"
    echo "install-pandoc: linked into $data_dir/filters"
fi

# One reference through the filter, which exercises both halves: the pair agrees (no warning) and
# the filter is actually reached (the reference resolved rather than staying literal). Run through
# the installed pandoc by path, since $BIN_DIR may not be on PATH in this shell yet.
printf 'x [-@eq:d]\n\n$$E=mc^2$$ {#eq:d}\n' > "$work/check.md"
"$BIN_DIR/pandoc" --filter pandoc-crossref --to latex "$work/check.md" > "$work/check.out" 2>&1 || {
    cat "$work/check.out" >&2
    echo "install-pandoc: pandoc could not run the filter" >&2
    exit 1
}
if grep -q 'WARNING' "$work/check.out"; then
    cat "$work/check.out" >&2
    echo "install-pandoc: pandoc and pandoc-crossref disagree -- see the warning above" >&2
    exit 1
fi
if ! grep -q 'ref{eq:d}' "$work/check.out"; then
    cat "$work/check.out" >&2
    echo "install-pandoc: pandoc-crossref did not resolve a reference" >&2
    exit 1
fi

echo "install-pandoc: $("$BIN_DIR/pandoc" --version | head -1) with $("$BIN_DIR/pandoc-crossref" --version | head -1)"

# A build shells out to `pandoc` by name, so an install nothing can reach is worth saying out
# loud. Not fatal: the caller may be adding the directory to PATH itself, as the workflow does.
# Compared canonically rather than by matching $BIN_DIR against PATH: an entry may carry a
# trailing slash -- this machine's does -- and `command -v` then hands back a doubled one.
resolved=$(command -v pandoc || true)
if [ -z "$resolved" ]; then
    echo "install-pandoc: WARNING $BIN_DIR is not on your PATH -- add it, or the build will not" \
         "find pandoc at all" >&2
elif [ "$(readlink -f "$resolved")" != "$(readlink -f "$BIN_DIR/pandoc")" ]; then
    echo "install-pandoc: WARNING PATH resolves pandoc to $resolved, not $BIN_DIR/pandoc" >&2
fi
