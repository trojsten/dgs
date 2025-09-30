orig=${2}
lang=${3}

find $1 -type f -path "*/$orig/*" | while read src; do
    dest=$(echo "$src" | sed "s#/$orig/#/$lang/#")
    echo "$src -> $dest"
    mkdir -p "$(dirname "$dest")"
    cp "$src" "$dest"
done
