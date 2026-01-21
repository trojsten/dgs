FROM debian:trixie-slim AS builder

ENV DEBIAN_FRONTEND=noninteractive

RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates wget xz-utils && \
    rm -rf /var/lib/apt/lists/*

RUN wget https://github.com/lierdakil/pandoc-crossref/releases/download/v0.3.16.0a/pandoc-crossref-Linux.tar.xz && \
    tar -xf pandoc-crossref-Linux.tar.xz && \
    mv ./pandoc-crossref "/usr/local/bin/pandoc-crossref" && \
    rm pandoc-crossref-Linux.tar.xz


FROM debian:trixie-slim

ENV DEBIAN_FRONTEND=noninteractive


RUN --mount=target=/var/lib/apt/lists,type=cache,sharing=locked \
    --mount=target=/var/cache/apt,type=cache,sharing=locked \
    rm -f /etc/apt/apt.conf.d/docker-clean && \
    apt-get update && \
    apt-get install -y --no-install-recommends ca-certificates make git pandoc texlive-xetex texlive-full texlive-fonts-extra texlive-science python3.13 pipenv librsvg2-bin lcdf-typetools && \
    rm -rf /tmp

RUN useradd --create-home dgs && mkdir /app && chown dgs:dgs /app
WORKDIR /app

COPY --from=builder /usr/local/bin/pandoc-crossref /usr/local/bin/pandoc-crossref
COPY --chown=dgs:dgs . /app/
RUN cd /app/assets/fonts && \
    git clone --depth 1 https://github.com/sebschub/FontPro.git && \
    cd FontPro && \
    mkdir otf && \
    cp ../../fonts/MinionPro/*.otf otf/ && \
    ./scripts/makeall MinionPro && \
    yes | ./scripts/install && \
    yes | updmap-sys --enable Map=MinionPro.map && \
    cd /app && \
    rm -rf /app/assets/fonts/FontPro


USER dgs

ENV TEXHOME=/home/dgs/texmf

COPY Pipfile Pipfile.lock /app/
RUN pipenv install --deploy && pipenv --clear

RUN mkdir -p $TEXHOME/tex/latex/
RUN ln -s /app/core/latex/dgs.cls $TEXHOME/tex/latex/dgs.cls

ENTRYPOINT ["pipenv", "run"]
