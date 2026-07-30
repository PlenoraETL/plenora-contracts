# Ambiente riproducibile per la qualifica di sistema.
#
# Un container solo con i tre componenti: non sono servizi, sono processi che
# leggono un file e ne scrivono un altro. Isolarli in container separati
# costringerebbe a spostare file attraverso volumi condivisi e aggiungerebbe un
# modo di fallire che non riguarda il contratto — un permesso sbagliato su un
# volume non dice nulla su `axis_order`.
#
# Nessun database: il roundtrip di plenora-database-tools e' `arrow_to_contract`
# e `inspect-dataset` lavora offline. I container PostgreSQL e SQL Server
# servono alla direzione inversa, che e' un altro lavoro.
#
# Nessuna GDAL: in plenora-IO-tools la dipendenza `gdal` e' opzionale dietro la
# feature `gdal-backend`, che non e' di default.

FROM rust:1.92.0-bookworm

# `proj` con feature `bundled_proj`, che plenora-data-tools richiede sotto
# `--features proj-backend`, compila PROJ dai sorgenti: non serve una PROJ di
# sistema, ma serve di che costruirla. La prima build e' lunga: non e' bloccata.
#
# `sqlite3` e' l'eseguibile, non solo la libreria: il CMakeLists di PROJ lo
# invoca per costruire il proprio database delle griglie, e senza di esso la
# configurazione fallisce con `sqlite3 binary not found`. `libtiff` e `libcurl`
# servono alle griglie di trasformazione; `libclang` a bindgen, che `proj-sys`
# usa per generare i binding.
#
# `libgeos` serve alle operazioni topologiche di data-tools dietro la feature
# `geos-backend`: senza, `make_valid` e le altre che riparano geometrie non
# valide rifiutano con `richiede la capability geos, non compilata`.
RUN apt-get update \
 && apt-get install --yes --no-install-recommends \
      build-essential \
      cmake \
      pkg-config \
      sqlite3 \
      libsqlite3-dev \
      libtiff-dev \
      libcurl4-openssl-dev \
      libgeos-dev \
      libclang-dev \
      clang \
      python3 \
      python3-pip \
      git \
      ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Il corpus e' generato con PyArrow e non dai componenti che deve verificare:
# un difetto nel writer e il difetto speculare nel reader si annullerebbero.
# Versione fissata: un corpus generato da una PyArrow diversa non e' lo stesso
# corpus, e l'evidenza deve essere riproducibile (C2.2 dei criteri di RC).
RUN pip3 install --break-system-packages --no-cache-dir "pyarrow==23.0.1" \
 && python3 -c "import pyarrow; print('pyarrow', pyarrow.__version__)"

WORKDIR /work
ENV CARGO_TERM_COLOR=never

ENTRYPOINT ["/bin/bash", "/work/plenora-contracts/conformance/run-in-container.sh"]
