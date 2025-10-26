# Copy Náboj files from one language to another (typically sk/en to <lang> before it is distributed to branches for translation)
#
# Usage ./copy-naboj.sh source/naboj/phys/28/problems/sk en

orig=${2}
lang=${3}

find $1 -type f -path "*/$orig/*" | while read src; do
    dest=$(echo "$src" | sed "s#/$orig/#/$lang/#")
    echo "$src -> $dest"
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
done
