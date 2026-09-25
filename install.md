# Installing DGS

You do not need all of this. The toolchain comes in three tiers, and the editor tells you which
ones you have — an unavailable tier is greyed with the reason and the command that fixes it.

To see where you stand at any point:

```
uv run python tools/editor/capabilities.py
```

| tier | what you can do | what it needs |
|---|---|---|
| — | open, edit and **save** files; the whole `/audit` page | Python and the dependencies below |
| Rendered Markdown | see what your Jinja tags expand to | GNU make |
| TeX | see what pandoc makes of it | + `pandoc` and `pandoc-crossref` |
| PDF | compile and read the page | + TeX Live, `dgs.cls`, and the MinionPro fonts |

The expensive half is the last row. If you are translating or writing problems, the first three
are enough, and they cost a `pip install` and five minutes.

## 0. Or skip all of it: containers

Everything below is what it takes to install DGS on a machine. If you would rather not, there is
an image:

```
./dgs-container build          # or: podman pull ghcr.io/trojstensk/dgs:full
./dgs-container editor         # browser at localhost:5001
./dgs-container make output/naboj/phys/29/languages/sk/booklet.pdf
```

`DGS_TARGET=light` gets you a much smaller image with the Markdown and TeX tiers but no PDF —
enough to write and translate, and it skips the twenty-minute font build entirely.

You need `sudo apt install podman` and nothing else; rootless works out of the box on Debian 13.
Your working copy is mounted at `/dgs`, so edits are live and nothing is baked into the image —
including `source/`, which stays on your disk where it belongs.

`./dgs-container check` proves an image is what it says it is.

## 1. Python

```
uv sync --dev
```

`--dev` matters: **`flask` is in the `dev` dependency group**, so a plain `uv sync` or
`pip install .` installs the pipeline but not the editor. Without uv:

```
python -m venv .venv && . .venv/bin/activate
pip install -e . && pip install flask
```

`pyproject.toml` asks for Python 3.14.

## 2. Sources

**A fresh clone has an empty `source/`.** The content lives in separate repositories which are
*not* submodules of this one — `source/` is gitignored and the index holds no gitlinks for it — so
there is no `git submodule` step and never really was. Clone what you need:

```
git clone git@github.com:TrojstenSK/naboj-physics   source/naboj/phys
git clone git@github.com:TrojstenSK/naboj-chemistry source/naboj/chem
git clone git@github.com:TrojstenSK/fks            source/seminar/FKS
```

The full list per module is in `modules/<module>/editor.yaml` under `sources:`, which is also what
the editor shows on its front page when it finds nothing to edit — so you do not have to remember
any of this.

The URLs are SSH and the repositories are private, so you need a GitHub key and access. One module
is enough: `source/naboj/phys` alone gives you every Náboj physics problem.

## 3. TeX tier: pandoc

```
./install-pandoc.sh
```

pandoc and pandoc-crossref have to be a **matched pair**, which is why this is a script and not an
apt line: the filter is not packaged by Debian, and a mismatched pair does not fail — it warns on
stderr and builds green. The script pins the filter, asks the binary which pandoc it was built
against, installs that one, and verifies the result with a probe document.

**The trap:** it installs into `$HOME/.local/bin` and only *warns* if that is not on your `PATH`,
so the install goes green and nothing works. There is a second half the script cannot warn about —
the editor shells out to make with **its own** environment, so a `PATH` exported in `~/.zshrc` is
invisible to an editor started from a desktop launcher or a systemd unit. The symptom is a TeX tab
greyed out on a machine where `pandoc` works fine in the terminal. `capabilities.py` reports the
PATH the server would actually use.

Note that `pandoc` from apt is too old: the repository needs one that emits `\pandocbounded`.

## 4. PDF tier: TeX Live and the fonts

```
./install.sh
```

It installs the apt packages itself, including `lcdf-typetools` — FontPro's scripts call
`otfinfo`, `otftotfm` and `cfftot1` and die without it. Beyond that it does three things:

- symlinks `core/latex/dgs.cls` into your `TEXMFHOME`, because the class reaches its pieces by
  paths relative to the repository root. It symlinks **`$PWD`**, so with two clones on one machine
  TeX quietly uses whichever one you ran it from; `capabilities.py` says which.
- builds **MinionPro** through [FontPro](https://github.com/sebschub/FontPro) from the OTFs in
  `assets/fonts/MinionPro/`, because `MinionPro.sty` is not in TeX Live. This is the twenty-minute
  step and it calls `sudo`. FontPro is the repository's one submodule, pinned at a known-good
  commit and fetched over HTTPS, so this needs no GitHub key — `git submodule update --init
  assets/fonts/FontPro` if you want it on its own.
- runs `updmap` so the font map is found.

It does **not** install the Python side. Do step 1 as well.

## 5. Running the editor

```
uv run python tools/editor/app.py --port 5001
```

From the repository root, always: several `core` modules open their data by a repository-relative
path — `core/i18n/__init__.py` reads `core/i18n/default.yaml` at import time — so it will not work
from anywhere else. The app `chdir`s there itself, but the working copy it picks is the one the
file lives in. Port 5000 is the default and is often taken.

`uv` is not required to run it. Without uv the editor calls `make` directly, with the directory of
the interpreter running it prepended to `PATH` — so an editor started from an activated venv works
with no uv installed at all.

## What each tier actually fails on

Worth knowing, because two of them fail quietly:

- **A missing `build/core/i18n/<lang>.yaml`** does not break the TeX tier; it silently changes it.
  pandoc-crossref falls back to English prefixes, so a Slovak booklet says `eq.~\ref{…}` where it
  should say `rovnica~\ref{…}`. The `.tex` rules depend on `build/core/i18n.stamp` so make builds
  it for you; if you ever bypass make, build it first.
- **A font present but lacking a glyph** is not a compile error. xelatex writes
  `Missing character:` into the log, exits 0, and ships a hole in the page. `core/tests/test_latex.py`
  exists to catch that.
- A missing font *file*, or a missing `MinionPro.sty`, is loud and stops the build.
