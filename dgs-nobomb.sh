#!/bin/bash
find $1 -name "*.md" -exec dos2unix {} \;
