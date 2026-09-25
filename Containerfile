# ============================================================================
#
# Pred tým, ako sa čohokoľvek chytíš, rozmysli si to.
#
# Ak si si to náhodou stále nerozmyslel, skús to znova.
#
# Ak si si fakt naozaj istý, že sa toho chceš chytať a nemáš fakt nič
# lepšie zo životom, tak aspoň updatni counter...
#
# hours_wasted_so_far = 17
#
# Úprimnú sústrasť.
#                                                           - Andrej
#
# PS: plne zdieľam tvoju nenávisť k celému degesovi, texu a fksákom.
#
# ============================================================================
#
# One file, two images:
#
#   podman build --target light -t dgs:light .    Markdown + TeX tiers
#   podman build --target full  -t dgs:full  .    + LaTeX and PDF
#
# Ordering here is by rate of change, not by subject: every layer that costs
# minutes sits *below* every layer a source edit touches. That is also why
# `full` descends from `tex` and not from `light` -- a stage has one parent, so
# the two final stages duplicate their tails, and that duplication is the whole
# price of keeping the twenty-minute FontPro layer underneath `COPY . .`.
#
# `source/` is never baked: it is 657 MB of separate, private repositories.
# Bind-mount it at run time. See install.md.

ARG DEBIAN_TAG=trixie-slim
ARG PYTHON_VERSION=3.14

# assets/fonts/FontPro, pinned. `.containerignore` excludes `.git/`, so
# `git submodule update --init` cannot run inside a build; the commit is fetched
# as a tarball instead, which is the same pin without 52 MB of history.
# `core/tests/test_containerfile.py` fails if this drifts from the gitlink.
ARG FONTPRO_COMMIT=165b4a7d11ad34b64d7457ee6d51af4875e0bf14


# === common ==================================================================
FROM docker.io/library/debian:${DEBIAN_TAG} AS common

# TERM: Makefile:41-46 calls `$(shell tput ...)` at parse time whether or not
#   there is a tty; with no TERM that writes "tput: No value for $TERM" to stderr
#   on every single make invocation.
# LANG: not cosmetic. Real venues are gdańsk-senior, toruń-senior, wrocław-junior,
#   košice-junior; under the default POSIX locale zip (module.mk:429), rsync
#   (:504), tar and make mangle or refuse those paths. C.UTF-8 lives inside glibc,
#   so this needs no `locales` package and no locale-gen.
# HOME: writable by any uid, so a forced `--user` still works.
# PATH: the venv first. Makefile:112 and :140 call a bare `python` and Debian has
#   no /usr/bin/python; this is what satisfies them, and it is also what makes
#   capabilities.py's probe_python_launcher take its `via: python` branch.
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONUNBUFFERED=1 \
    TERM=xterm \
    LANG=C.UTF-8 \
    HOME=/home/dgs \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin

RUN install -d -m 0777 /home/dgs

RUN apt-get update && apt-get install -y --no-install-recommends \
        ca-certificates curl git make xz-utils tar ncurses-bin \
    && rm -rf /var/lib/apt/lists/*

# uv is needed at *run* time, not only here: tools/editor/app.py hardcodes
# ["uv", "run", "python", "core/markdown-check.py", ...] for /api/lint, and that
# route answers 500 without it.
# Pinned inline rather than through an ARG: `COPY --from=` with a variable image
# reference works, but this is the one line whose failure mode is "silently a
# different uv", and it is cheaper to read it here than to chase a build-arg.
COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /uvx /usr/local/bin/

# The venv lives OUTSIDE /dgs. That is what lets you bind-mount a whole working
# copy over /dgs and still have the interpreter, the packages and the dgs.cls
# symlink resolve.
ENV UV_PYTHON_INSTALL_DIR=/opt/python \
    UV_PYTHON_PREFERENCE=only-managed \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy \
    UV_NO_PROGRESS=1

# pyproject.toml wants >= 3.14 and trixie ships 3.13, so uv fetches a standalone
# build. `only-managed` above stops it quietly settling for 3.13.
ARG PYTHON_VERSION
RUN uv python install ${PYTHON_VERSION}

# pandoc >= 3.2 as a matched pair with pandoc-crossref. The repository's own
# script rather than a reimplementation: it pins the filter, asks the binary
# which pandoc it was built against, installs exactly that one, and fails if the
# pair still disagrees -- a mismatch otherwise only warns and builds green.
# BIN_DIR (install-pandoc.sh:30) keeps it out of $HOME; it needs no root.
# apt's pandoc is 3.1.11.1, below the >= 3.2 floor convertor.py requires.
COPY install-pandoc.sh /tmp/install-pandoc.sh
RUN BIN_DIR=/usr/local/bin /tmp/install-pandoc.sh && rm /tmp/install-pandoc.sh


# === tex =====================================================================
# Everything the PDF tier needs, installed by apt so each package's postinst
# runs. NEVER `COPY --from=` a TeX tree into a stage: restoring the files without
# the postinst leaves binaries with no /var/lib/texmf configuration, and FontPro
# then dies inside updmap-sys after twenty minutes of work.
# .github/workflows/python-app.yml:43-51 is the post-mortem. `FROM tex` below
# inherits the whole filesystem and dpkg state, and is a different thing.
FROM common AS tex

# --no-install-recommends silently drops dvisvgm and ghostscript, which is why
# both are named: Makefile:208 runs pdfcrop (ghostscript) and :226 dvisvgm.
#
# texlive-full is 5-6 GB and drags in CJK, ConTeXt, asymptote and the doc tree.
# This list is about 2.4 GB. texlive-fonts-extra is 1.7 GB of that and is not
# optional: MnSymbol (dgs.cls:93), esvect (:100), ifsym and skull (fonts.tex:51)
# live in no smaller package.
RUN apt-get update && apt-get install -y --no-install-recommends \
        texlive-latex-base texlive-latex-recommended texlive-latex-extra \
        texlive-xetex texlive-pictures texlive-science texlive-plain-generic \
        texlive-fonts-recommended texlive-fonts-extra \
        texlive-extra-utils texlive-font-utils \
        texlive-lang-czechslovak texlive-lang-english texlive-lang-european \
        texlive-lang-german texlive-lang-french texlive-lang-polish \
        texlive-lang-spanish texlive-lang-portuguese texlive-lang-cyrillic \
        lcdf-typetools fontconfig \
        ghostscript dvisvgm librsvg2-bin poppler-utils gnuplot-nox \
        pdftk-java zip rsync \
    && rm -rf /var/lib/apt/lists/*

# FontPro fails deep inside a TeX run when a tool is absent, twenty minutes in.
# Fail here instead, by name. The first eleven are python-app.yml:61-71 verbatim;
# the rest is what the makefiles reach for beyond the obvious.
RUN missing=""; \
    for tool in tex fontinst vptovf pltotf otfinfo otftotfm cfftot1 kpsewhich \
                mktexlsr updmap-sys perl \
                xelatex texfot pdfcrop pdfjam pdftk pdftoppm dvisvgm \
                rsvg-convert gnuplot zip rsync fc-cache; do \
        command -v "$tool" >/dev/null || missing="$missing $tool"; \
    done; \
    [ -z "$missing" ] || { echo "missing tools:$missing" >&2; exit 1; }; \
    kpsewhich -var-value=TEXMFLOCAL

# The OTFs alone, not the repository: they have not changed in years, so the
# twenty-minute layer below survives every source edit.
COPY assets/fonts/MinionPro/*.otf /tmp/fontpro/otf/

ARG FONTPRO_COMMIT
# The last three lines are a second, easily-missed font install. Makefile:232,274
# pass gnuplot `font 'Minion Pro, 12'` -- a family name, resolved through
# fontconfig, not kpathsea. FontPro installs nothing fontconfig reads, so without
# them every gnuplot figure silently comes out in DejaVu. Verified on the host:
# `fc-match 'Minion Pro'` answers there only because somebody once copied the OTFs
# into ~/.local/share/fonts by hand; install.sh never does it. fc-match always
# answers *something*, so the grep is the actual assertion.
#
# No `|| true` anywhere. The old Dockerfile had it on all three FontPro steps,
# which is exactly why the image it pushed had no MinionPro in it and still
# reported a clean build. Every command here is fatal, and the kpsewhich and
# fc-match lines at the end mean a *successful-looking* run cannot pass either.
RUN set -eux; \
    echo '=== FontPro: fetch, pinned at '"${FONTPRO_COMMIT}"; \
    curl -fsSL "https://codeload.github.com/sebschub/FontPro/tar.gz/${FONTPRO_COMMIT}" \
      | tar -xz --strip-components=1 -C /tmp/fontpro; \
    cd /tmp/fontpro; \
    echo '=== FontPro: makeall MinionPro -- this is the twenty minutes'; \
    ./scripts/makeall MinionPro; \
    echo '=== FontPro: install into TEXMFLOCAL'; \
    yes | ./scripts/install; \
    mktexlsr; \
    echo '=== FontPro: enable the map'; \
    yes | updmap-sys --enable Map=MinionPro.map; \
    kpsewhich MinionPro.sty; \
    kpsewhich MinionPro.map; \
    echo '=== Minion Pro as a *fontconfig* font, which is a separate thing'; \
    install -d /usr/local/share/fonts/minionpro; \
    cp otf/*.otf /usr/local/share/fonts/minionpro/; \
    fc-cache -f >/dev/null; \
    fc-match 'Minion Pro' file | grep -qi minionpro; \
    cd /; rm -rf /tmp/fontpro


# === light ===================================================================
FROM common AS light
WORKDIR /dgs

# Dependencies before the tree, so a source edit does not re-resolve them.
# pyproject.toml declares no [build-system], so uv treats dgs as a virtual
# project: `uv sync` wants these two files and never installs dgs itself -- the
# code is reached through cwd, which is why everything must run from /dgs.
# --dev because flask is in the dev group; --locked so a stale lock is an error.
COPY pyproject.toml uv.lock ./
# `quickjs` (dev group) is the one dependency with no cp314 wheel, so uv builds it from C.
# The compiler is installed, used and purged inside a single RUN, so it never reaches a layer:
# ~250 MB of toolchain for one 300 KB .so would otherwise sit in both images forever.
# gcc and libc6-dev rather than build-essential -- module.c is plain C and `make` is already here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && uv sync --locked --dev \
    && apt-get purge -y gcc libc6-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# uv is locked down only now: everything above needed the network.
ENV UV_NO_SYNC=1 UV_FROZEN=1 UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never

# make writes here. Sticky-writable rather than chowned to a uid the image
# cannot know, so a forced `--user` still works.
RUN install -d -m 1777 build render output

# The image checks itself, so a broken one is never tagged. Not capabilities.py:
# its main() exits 0 only when *every* tier is available, which is the wrong
# question here -- `light` must fail if it lost pandoc and equally if it somehow
# grew a TeX distribution.
RUN python tools/editor/expect-tiers.py markdown tex

EXPOSE 5000
# No ENTRYPOINT, so `podman run dgs:light make <target>` works as typed.
CMD ["python", "tools/editor/app.py", "--host", "0.0.0.0", "--port", "5000"]


# === full ====================================================================
# Deliberately a near-copy of light's tail. `full` must descend from `tex`,
# because apt's postinst state cannot be copied and a stage has one parent.
FROM tex AS full
WORKDIR /dgs

COPY pyproject.toml uv.lock ./
# `quickjs` (dev group) is the one dependency with no cp314 wheel, so uv builds it from C.
# The compiler is installed, used and purged inside a single RUN, so it never reaches a layer:
# ~250 MB of toolchain for one 300 KB .so would otherwise sit in both images forever.
# gcc and libc6-dev rather than build-essential -- module.c is plain C and `make` is already here.
RUN apt-get update \
    && apt-get install -y --no-install-recommends gcc libc6-dev \
    && uv sync --locked --dev \
    && apt-get purge -y gcc libc6-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

COPY . .

# TEXMFLOCAL, not TEXMFHOME: the latter is $HOME-relative and evaporates the
# moment anyone changes the runtime user. A symlink rather than a copy, so the
# class TeX finds is always this /dgs -- including when /dgs is mounted over.
RUN install -d "$(kpsewhich -var-value=TEXMFLOCAL)/tex/latex" \
    && ln -s /dgs/core/latex/dgs.cls \
             "$(kpsewhich -var-value=TEXMFLOCAL)/tex/latex/dgs.cls" \
    && mktexlsr \
    && kpsewhich dgs.cls

ENV UV_NO_SYNC=1 UV_FROZEN=1 UV_OFFLINE=1 UV_PYTHON_DOWNLOADS=never

# `_minted/` because -shell-escape is unconditional (Makefile:84, 217-222) even
# though nothing in core/latex loads minted today.
RUN install -d -m 1777 build render output _minted

RUN python tools/editor/expect-tiers.py markdown tex latex pdf

LABEL org.opencontainers.image.source="https://github.com/TrojstenSK/dgs"
EXPOSE 5000
CMD ["python", "tools/editor/app.py", "--host", "0.0.0.0", "--port", "5000"]
