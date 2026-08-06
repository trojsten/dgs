FROM debian:trixie-slim

# ====================================================================
#
# Pred tým, ako sa čohokoľvek chytíš, rozmysli si to.
#
# Ak si si to náhodou stále nerozmyslel, skús to znova.
#
# Ak si si fakt naozaj istý, že sa toho chceš chytať a nemáš fakt nič
# lepšie zo životom, tak aspoň updatni counter...
#
# hours_wasted_so_far = 13.5
#
# Úprimnú sústrasť.
#                                                           - Andrej
#
# PS: plne zdieľam tvoju nenávisť k celému degesovi, texu a fksákom.
#
# ====================================================================

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    wget \
    curl \
    xz-utils \
    tar \
    git \
    make \
    librsvg2-bin \
    lcdf-typetools \
    pandoc \
    python3 \
    pipenv \
    poppler-utils \
    texlive-full \
    texlive-fonts-extra \
    texlive-science \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/lierdakil/pandoc-crossref/releases/download/v0.3.16.0a/pandoc-crossref-Linux.tar.xz \
    && tar -xf pandoc-crossref-Linux.tar.xz \
    && mv ./pandoc-crossref /usr/local/bin/pandoc-crossref \
    && chmod +x /usr/local/bin/pandoc-crossref \
    && rm pandoc-crossref-Linux.tar.xz

WORKDIR /app

COPY . .

RUN git clone https://github.com/sebschub/FontPro.git /tmp/FontPro \
    && cd /tmp/FontPro \
    && mkdir otf \
    && cp /app/assets/fonts/MinionPro/*.otf otf/ 2>/dev/null || true \
    && ./scripts/makeall MinionPro || true \
    && yes | ./scripts/install || true \
    && yes | updmap-sys --enable Map=MinionPro.map || true \
    && rm -rf /tmp/FontPro

RUN TEXHOME=$(kpsewhich -var-value=TEXMFHOME) \
    && mkdir -p "$TEXHOME/tex/latex/" \
    && ln -s /app/core/latex/dgs.cls "$TEXHOME/tex/latex/dgs.cls"

RUN pipenv install --dev && pipenv --clear

ENTRYPOINT ["pipenv", "run"]
