#!/bin/bash

DIR=$(dirname $0)

ln -s $PWD/core/tex/dgs.cls `kpsewhich -var-value=TEXMFHOME`/tex/latex/dgs.cls
