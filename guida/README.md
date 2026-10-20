# Guida dello sviluppatore

Come si usano le librerie Plenora **dall'esterno**: i comandi, le funzioni,
ciò che accettano e ciò che rifiutano. L'interno è una scatola nera: questa
guida descrive il comportamento osservabile e si ferma lì. La fonte di verità
restano i cataloghi pubblici e gli schemi di questo repository: dove la guida
e un catalogo dicessero cose diverse, ha ragione il catalogo.

| capitolo | che cosa copre |
| --- | --- |
| [Fondamenta comuni](fondamenta.md) | la busta CLI v2, gli exit code, le categorie d'errore, la scoperta delle capacità: uguali per tutte le librerie |
| [IO](io.md) | leggere e scrivere file: CSV, DXF, Shapefile, GeoParquet, FileGDB, GeoJSON, IPC (6 operazioni) |
| [data](data.md) | trasformare tabelle Arrow con un piano dichiarativo (5 operazioni) |
| [database](database.md) | leggere, scrivere e interrogare PostgreSQL/PostGIS, MySQL, SQL Server, Oracle, DB2 (13 operazioni) |
| [storage](storage.md) | trasferire file su local, S3, Azure, GCS, FTP/FTPS, SFTP, SMB, WebDAV (7 operazioni) |
| [rest](rest.md) | chiamare API HTTP: generare, arricchire, scaricare, caricare (5 operazioni) |
| [Farle parlare insieme](insieme.md) | le catene fra librerie: che cosa passa fra un hop e l'altro, e che cosa aspettarsi quando qualcosa rifiuta |

Ogni capitolo di libreria ha la stessa forma: **le operazioni** (dal catalogo
pubblico, con ingressi, uscite e side effect), **la CLI** (invocazione,
busta, exit code), **l'SDK Python** (installazione, funzioni, eccezioni), e
**i rifiuti e i limiti** (che cosa la libreria non fa, dichiaratamente).
