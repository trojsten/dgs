#!/bin/bash

DIR=$(dirname $0)

# No `pandoc` here on purpose: it comes from upstream as a matched pair with pandoc-crossref,
# which apt does not package at all. See the comments in install-pandoc.sh.
#
# `lcdf-typetools` is not optional: FontPro's scripts call otfinfo, otftotfm and cfftot1,
# and die without them. CI has always installed it; this script used to forget.
sudo apt install texlive-full texlive-fonts-extra texlive-science librsvg2-bin gnuplot \
                lcdf-typetools
"$DIR/install-pandoc.sh"

TEXHOME=`kpsewhich -var-value=TEXMFHOME`
mkdir -p $TEXHOME/tex/latex/
ln -s $PWD/core/latex/dgs.cls $TEXHOME/tex/latex/dgs.cls

# FontPro is a submodule pinned at a known-good commit, so check it out rather than cloning by
# hand: `rm -rf` and a fresh clone silently took whatever upstream happened to be that day. It is
# the only submodule in this repository -- the content under `source/` is not one, and each
# module lists its own repositories in `modules/<module>/editor.yaml`.
git -C "$DIR" submodule update --init assets/fonts/FontPro

cd "$DIR/assets/fonts/FontPro"
mkdir -p otf
cp ../MinionPro/*.otf otf/
./scripts/makeall MinionPro
yes | sudo ./scripts/install
yes | updmap-user --enable Map=MinionPro.map

