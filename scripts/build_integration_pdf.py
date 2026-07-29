#!/usr/bin/env python3
"""Costruisce il documento di integrazione delle tre librerie Plenora."""

from __future__ import annotations

from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    BaseDocTemplate, Frame, KeepTogether, PageBreak, PageTemplate,
    Paragraph, Spacer, Table, TableStyle,
)

FONTS = Path("C:/Windows/Fonts")

# Constantia per il testo: serif di schermo, generosa nell'x-height, senza il
# tono libresco di Georgia. Calibri per etichette e tabelle: umanista, stretta,
# regge le colonne dense senza gridare.
for name, file_name in [
    ("Body", "constan.ttf"), ("BodyB", "constanb.ttf"), ("BodyI", "constani.ttf"),
    ("UI", "calibri.ttf"), ("UIB", "calibrib.ttf"), ("UIL", "calibril.ttf"),
]:
    pdfmetrics.registerFont(TTFont(name, str(FONTS / file_name)))

INK = colors.HexColor("#14181F")       # nero con deriva blu, non nero puro
PETROL = colors.HexColor("#0E4F54")    # accento: inchiostro da rilievo
SLATE = colors.HexColor("#5A6672")     # testo secondario
AMBER = colors.HexColor("#8A6A1F")     # solo per ciò che non c'è ancora
RULE = colors.HexColor("#D4D9DE")
WASH = colors.HexColor("#F2F5F6")

PAGE_W, PAGE_H = A4
MARGIN = 24 * mm


def style(name, **kwargs):
    base = dict(fontName="Body", fontSize=10.2, leading=15.4, textColor=INK,
                spaceAfter=0, spaceBefore=0)
    base.update(kwargs)
    return ParagraphStyle(name, **base)


S = {
    "title": style("title", fontName="BodyB", fontSize=26, leading=30,
                   textColor=INK, spaceAfter=4),
    "subtitle": style("subtitle", fontName="Body", fontSize=13, leading=19,
                      textColor=SLATE, spaceAfter=18),
    "h1": style("h1", fontName="BodyB", fontSize=17, leading=21, spaceBefore=0,
                spaceAfter=7),
    "h2": style("h2", fontName="BodyB", fontSize=11.6, leading=16,
                textColor=PETROL, spaceBefore=13, spaceAfter=5),
    "eyebrow": style("eyebrow", fontName="UIB", fontSize=7.8, leading=11,
                     textColor=PETROL, spaceAfter=4),
    "body": style("body", alignment=TA_JUSTIFY, spaceAfter=8),
    "lead": style("lead", fontSize=11.4, leading=17.4, textColor=SLATE,
                  alignment=TA_JUSTIFY, spaceAfter=10),
    "bullet": style("bullet", alignment=TA_JUSTIFY, leftIndent=11,
                    bulletIndent=1, spaceAfter=4.5),
    "cell": style("cell", fontName="UI", fontSize=8.6, leading=11.6,
                  alignment=TA_JUSTIFY),
    "cellb": style("cellb", fontName="UIB", fontSize=8.7, leading=12),
    "head": style("head", fontName="UIB", fontSize=7.6, leading=10,
                  textColor=colors.white),
    "note": style("note", fontName="UI", fontSize=8.6, leading=12.6,
                  textColor=SLATE, alignment=TA_JUSTIFY),
    "caption": style("caption", fontName="UI", fontSize=8.2, leading=11.6,
                     textColor=SLATE, spaceBefore=4, spaceAfter=10),
}


def rule(space_before=2, space_after=8, colour=RULE, weight=0.6):
    table = Table([[""]], colWidths=[PAGE_W - 2 * MARGIN], rowHeights=[0.1])
    table.setStyle(TableStyle([
        ("LINEABOVE", (0, 0), (-1, 0), weight, colour),
        ("TOPPADDING", (0, 0), (-1, -1), space_before),
        ("BOTTOMPADDING", (0, 0), (-1, -1), space_after),
    ]))
    return table


def grid(rows, widths, header=True, zebra=True):
    data = []
    for index, row in enumerate(rows):
        rendered = []
        for cell in row:
            if index == 0 and header:
                rendered.append(Paragraph(cell, S["head"]))
            else:
                rendered.append(Paragraph(cell, S["cell"]))
        data.append(rendered)
    table = Table(data, colWidths=widths, repeatRows=1 if header else 0)
    commands = [
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("TOPPADDING", (0, 0), (-1, -1), 3.0),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3.0),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -2), 0.4, RULE),
    ]
    if header:
        commands += [("BACKGROUND", (0, 0), (-1, 0), PETROL),
                     ("BOTTOMPADDING", (0, 0), (-1, 0), 5),
                     ("TOPPADDING", (0, 0), (-1, 0), 5)]
    if zebra:
        start = 1 if header else 0
        for index in range(start, len(rows)):
            if (index - start) % 2 == 1:
                commands.append(("BACKGROUND", (0, index), (-1, index), WASH))
    table.setStyle(TableStyle(commands))
    return table


def callout(title, body, colour=AMBER):
    inner = [[Paragraph(title, S["cellb"])], [Paragraph(body, S["note"])]]
    table = Table(inner, colWidths=[PAGE_W - 2 * MARGIN - 8])
    table.setStyle(TableStyle([
        ("LEFTPADDING", (0, 0), (-1, -1), 11),
        ("RIGHTPADDING", (0, 0), (-1, -1), 11),
        ("TOPPADDING", (0, 0), (-1, 0), 9),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 2),
        ("TOPPADDING", (0, 1), (-1, 1), 0),
        ("BOTTOMPADDING", (0, 1), (-1, 1), 9),
        ("BACKGROUND", (0, 0), (-1, -1), WASH),
        ("LINEBEFORE", (0, 0), (0, -1), 2.2, colour),
    ]))
    return KeepTogether([Spacer(1, 4), table, Spacer(1, 10)])


def bullets(items):
    return [Paragraph(text, S["bullet"], bulletText="—") for text in items]


def decorate(canvas, document):
    canvas.saveState()
    if document.page > 1:
        canvas.setFont("UIL", 7.6)
        canvas.setFillColor(SLATE)
        canvas.drawString(MARGIN, PAGE_H - MARGIN + 9 * mm,
                          "Plenora · Integrazione delle tre librerie")
        canvas.drawRightString(PAGE_W - MARGIN, PAGE_H - MARGIN + 9 * mm,
                               f"{document.page}")
        canvas.setStrokeColor(RULE)
        canvas.setLineWidth(0.5)
        canvas.line(MARGIN, PAGE_H - MARGIN + 7 * mm,
                    PAGE_W - MARGIN, PAGE_H - MARGIN + 7 * mm)
    canvas.restoreState()


# ---------------------------------------------------------------- contenuto

W = PAGE_W - 2 * MARGIN
story = []

# --- copertina ---------------------------------------------------------------
story += [
    Spacer(1, 26 * mm),
    Paragraph("PLENORA", S["eyebrow"]),
    Paragraph("Le tre librerie", S["title"]),
    Paragraph("Come si dividono il lavoro, come si parlano,<br/>e cosa sanno fare",
              S["subtitle"]),
    rule(space_after=14),
    Paragraph(
        "Le tre librerie sostituiscono il livello che legge, trasforma e scrive i dati "
        "di Plenora. Non affiancano il codice esistente: prendono il suo posto. Questo "
        "documento spiega come si incastrano e cosa mettono a disposizione, senza "
        "entrare nel codice.", S["lead"]),
    Spacer(1, 4),
    Paragraph(
        "È scritto per chi deve decidere e per chi deve coordinare, non per chi "
        "implementa. Dove qualcosa non è ancora pronto, è detto.", S["body"]),
    Spacer(1, 20 * mm),
]

facts = [
    ["", "Ruolo", "Cosa mette a disposizione"],
    ["<b>IO-tools</b>", "Il confine con i file",
     "10 formati, tutti in lettura e scrittura"],
    ["<b>data-tools</b>", "Il motore di trasformazione",
     "77 operazioni geometriche, 70 su tabelle"],
    ["<b>database-tools</b>", "Il confine con i database",
     "PostgreSQL e SQL Server, lettura e scrittura"],
]
story += [grid(facts, [30 * mm, 42 * mm, W - 72 * mm]),
          Paragraph("Conteggi rilevati dal codice delle tre librerie, non dichiarati "
                    "dalla documentazione.", S["caption"])]

story.append(PageBreak())

# --- 1. il disegno -----------------------------------------------------------
story += [
    Paragraph("IL DISEGNO", S["eyebrow"]),
    Paragraph("Tre confini, un formato solo in mezzo", S["h1"]),
    rule(),
    Paragraph(
        "Un ETL fa sempre le stesse tre cose: prende dati da qualche parte, li "
        "trasforma, li deposita da qualche altra parte. Plenora separa queste tre cose "
        "in tre librerie distinte, ognuna responsabile di un confine.", S["body"]),
    Paragraph(
        "<b>IO-tools</b> è il confine con i file. Sa aprire uno shapefile, un GeoPackage, "
        "un Excel, un DXF di AutoCAD, e sa riscriverli. È l'unico dei tre che tocca "
        "formati di terzi.", S["body"]),
    Paragraph(
        "<b>data-tools</b> è il motore. Non sa nulla di file né di database: riceve una "
        "tabella, applica una sequenza di operazioni descritta in un piano, restituisce "
        "una tabella.", S["body"]),
    Paragraph(
        "<b>database-tools</b> è il confine con i database. Conosce PostgreSQL e SQL "
        "Server, le loro peculiarità sui tipi geometrici, le transazioni, gli indici "
        "spaziali.", S["body"]),
]

story += [
    Paragraph("Il pezzo che tiene insieme tutto", S["h2"]),
    Paragraph(
        "In mezzo ai tre passa sempre la stessa cosa: una tabella in memoria, nel "
        "formato Apache Arrow, accompagnata da un'etichetta che dice cosa contiene. "
        "L'etichetta è la parte che conta.", S["body"]),
    Paragraph(
        "Un dato patrimoniale non è solo una geometria: è una geometria <i>in un certo "
        "sistema di riferimento</i>, con o senza quota, con gli assi in un certo ordine. "
        "Se una di queste informazioni si perde per strada, il dato resta apparentemente "
        "valido ma è sbagliato — e nessuno se ne accorge finché non lo si sovrappone a "
        "una mappa. L'etichetta trasporta esattamente queste informazioni, e il contratto "
        "fra le tre librerie stabilisce che nessuna può perderla o riempirla a caso.",
        S["body"]),
]

story += [
    Paragraph("Chi parla con chi", S["h2"]),
    Paragraph(
        "Nessuna delle tre chiama direttamente le altre. Il backend Python le orchestra "
        "e si passa le tabelle. Questo significa che non servono sei collegamenti fra "
        "le librerie: ognuna deve solo saper leggere e scrivere lo stesso formato. Se "
        "ciascuna lo rispetta, qualunque combinazione funziona — file verso database, "
        "database verso file, o entrambi passando dal motore.", S["body"]),
]

story.append(callout(
    "Perché questo disegno, e non un blocco unico",
    "Tre librerie separate costano di più in coordinamento, ma ognuna si può sostituire, "
    "verificare e correggere senza toccare le altre. Un formato di file nuovo si aggiunge "
    "in IO-tools e gli altri due non se ne accorgono. Un provider di database nuovo non "
    "richiede di ricompilare il motore. È la stessa ragione per cui i tre repository sono "
    "distinti: chi ospita un test ne controlla l'esito, e un componente non può essere "
    "giudice di sé stesso.", PETROL))

story.append(PageBreak())

# --- 2. IO-tools -------------------------------------------------------------
story += [
    Paragraph("PRIMA LIBRERIA", S["eyebrow"]),
    Paragraph("IO-tools — il confine con i file", S["h1"]),
    rule(),
    Paragraph(
        "Dieci formati, tutti sia in lettura sia in scrittura. Questo permette la "
        "conversione diretta fra due qualsiasi di essi: un DXF diventa un GeoPackage, "
        "un Excel diventa un GeoJSON, senza passare da un database.", S["body"]),
]

formats = [
    ["Formato", "Che cos'è", "Fedeltà", "Motore"],
    ["<b>geoparquet</b>", "Colonnare compresso, standard per grandi volumi",
     "Senza perdita", "Rust"],
    ["<b>geojson</b>", "Scambio via web, leggibile a occhio",
     "Senza perdita", "Rust"],
    ["<b>ipc</b>", "Il formato di scambio interno fra le tre librerie",
     "Senza perdita", "Rust"],
    ["<b>gpkg</b>", "GeoPackage OGC, più livelli in un file",
     "Condizionata", "Rust"],
    ["<b>shp</b>", "Shapefile, lo storico di settore",
     "Condizionata", "Rust"],
    ["<b>filegdb</b>", "File Geodatabase Esri, più livelli",
     "Condizionata", "GDAL"],
    ["<b>kml</b>", "Google Earth e derivati", "Condizionata", "Rust"],
    ["<b>csv</b>", "Tabellare puro", "Condizionata", "Rust"],
    ["<b>xls</b>", "Excel", "Condizionata", "Rust"],
    ["<b>dxf</b>", "Disegno AutoCAD", "Approssimante", "Rust"],
]
story += [grid(formats, [24 * mm, W - 66 * mm, 24 * mm, 18 * mm])]

story += [
    Paragraph("Cosa vuol dire «fedeltà»", S["h2"]),
    Paragraph(
        "È la dichiarazione, fatta dalla libreria stessa, di quanto un formato riesce a "
        "conservare. <b>Senza perdita</b>: ciò che entra riesce identico. "
        "<b>Condizionata</b>: dipende dai dati — uno shapefile tronca i nomi delle "
        "colonne a dieci caratteri, un CSV non ha tipi. <b>Approssimante</b>: il formato "
        "non può rappresentare tutto — il DXF è un disegno tecnico, non un archivio di "
        "dati, e alcune informazioni non hanno dove andare.", S["body"]),
    Paragraph(
        "La dichiarazione non è un'etichetta di comodo: quando una conversione perde "
        "qualcosa, la libreria emette un rapporto di perdita che elenca cosa non è "
        "passato. Non lo nasconde e non lo indovina.", S["body"]),
]

story += [
    Paragraph("Cosa si può chiedere alla libreria", S["h2"]),
]
commands = [
    ["Funzione", "A cosa serve"],
    ["<b>catalog</b>", "Elenca i formati riconosciuti e cosa sa fare ciascuno"],
    ["<b>inspect</b>", "Apre un file e riferisce cosa contiene, senza leggerlo tutto"],
    ["<b>layers</b>", "Elenca i livelli di un file che ne contiene più d'uno"],
    ["<b>read</b>", "Legge i dati e li consegna nel formato di scambio interno"],
    ["<b>convert</b>", "Converte da un formato all'altro, con rapporto di perdita"],
]
story += [grid(commands, [26 * mm, W - 26 * mm])]

story.append(callout(
    "Un limite da conoscere",
    "Le conversioni verso un formato che ammette un solo livello, partendo da un file "
    "che ne contiene diversi, vengono rifiutate: la libreria chiede di scegliere quale "
    "livello convertire invece di sceglierlo al posto di chi la usa. È un rifiuto "
    "voluto, non una funzione mancante."))

story.append(PageBreak())

# --- 3. data-tools -----------------------------------------------------------
story += [
    Paragraph("SECONDA LIBRERIA", S["eyebrow"]),
    Paragraph("data-tools — il motore di trasformazione", S["h1"]),
    rule(),
    Paragraph(
        "Riceve una tabella e un piano — la descrizione, in un file, delle operazioni da "
        "applicare e del loro ordine — e restituisce una tabella. Il piano è un dato, "
        "non codice: si può salvare, versionare, rieseguire identico, confrontare con "
        "quello di ieri.", S["body"]),
    Paragraph(
        "Le operazioni disponibili sono centoquarantasette, divise in due famiglie.",
        S["body"]),
]

story += [Paragraph("Operazioni geometriche — 77", S["h2"])]
geo = [
    ["Famiglia", "Esempi di cosa sa fare"],
    ["<b>Misura</b>",
     "area, perimetro, lunghezza, distanza, e le versioni geodetiche che tengono conto "
     "della curvatura terrestre"],
    ["<b>Costruzione</b>",
     "buffer, centroide, involucro convesso e concavo, inviluppo, punto sulla superficie, "
     "griglie, Voronoi, Delaunay"],
    ["<b>Combinazione</b>",
     "unione, intersezione, differenza, differenza simmetrica, ritaglio, sovrapposizione, "
     "dissoluzione per attributo"],
    ["<b>Relazione</b>",
     "contiene, interseca, tocca, attraversa, è dentro, è disgiunto — undici predicati "
     "topologici, più la giunzione spaziale"],
    ["<b>Correzione</b>",
     "riparazione di geometrie non valide, pulizia topologica, semplificazione, infittimento, diagnostica"],
    ["<b>Riproiezione</b>",
     "trasformazione fra sistemi di riferimento, rotazione, scala, traslazione, "
     "trasformazione affine"],
    ["<b>Analisi</b>",
     "vicino più prossimo, raggruppamento per densità, conteggio di punti nei poligoni, "
     "distanze di Hausdorff e Fréchet"],
]
story += [grid(geo, [30 * mm, W - 30 * mm])]

story += [Paragraph("Operazioni su tabelle — 70", S["h2"])]
tab = [
    ["Famiglia", "Esempi di cosa sa fare"],
    ["<b>Selezione</b>",
     "filtro, ordinamento, limite, primi N, campionamento, distinti, scelta e "
     "riordino delle colonne"],
    ["<b>Unione</b>",
     "giunzioni interne ed esterne, semi e anti, incrociate, temporali, approssimate "
     "per somiglianza; unione, intersezione, differenza fra tabelle"],
    ["<b>Rimodellamento</b>",
     "pivot, spivot, trasposizione, appiattimento di JSON, esplosione di liste, "
     "concatenazione"],
    ["<b>Calcolo</b>",
     "espressioni e formule, aggregazioni, finestre mobili, funzioni di finestra, "
     "numerazione, classificazione in intervalli"],
    ["<b>Testo e date</b>",
     "estrazione, sostituzione, riempimento, normalizzazione; somma e differenza di date, conversione di fuso"],
    ["<b>Verifica</b>",
     "controlli su schema, unicità, chiavi esterne, cardinalità, valori nulli, "
     "intervalli, espressioni regolari, metadati"],
    ["<b>Qualità</b>",
     "deduplicazione, riconciliazione fra tabelle, confronto strutturale, statistiche, "
     "impronta stabile, mascheramento di dati sensibili"],
]
story += [grid(tab, [30 * mm, W - 30 * mm])]

story.append(callout(
    "La famiglia che conta di più per Plenora",
    "Le operazioni di verifica non trasformano nulla: controllano e basta. Su dati "
    "patrimoniali servono a fermare una lavorazione prima che produca un archivio "
    "sbagliato — un vincolo di unicità violato, una chiave che non trova corrispondenza, "
    "un valore fuori intervallo. Farlo dentro il piano, e non a valle con una query, "
    "significa che il controllo è versionato insieme alla trasformazione e viene "
    "rieseguito ogni volta.", PETROL))

story.append(PageBreak())

# --- 4. database-tools -------------------------------------------------------
story += [
    Paragraph("TERZA LIBRERIA", S["eyebrow"]),
    Paragraph("database-tools — il confine con i database", S["h1"]),
    rule(),
    Paragraph(
        "Due database supportati, PostgreSQL con PostGIS e SQL Server. Entrambi in "
        "lettura e scrittura.", S["body"]),
    Paragraph(
        "Il problema che questa libreria risolve non è «mandare una query»: è che due "
        "database trattano le geometrie in modo diverso, ammettono transazioni diverse, "
        "hanno limiti diversi su quanto si può scrivere in un colpo solo. Scrivere codice "
        "che li tratta allo stesso modo produce, prima o poi, un archivio corrotto in "
        "uno dei due.", S["body"]),
]

story += [Paragraph("Le operazioni", S["h2"])]
ops = [
    ["Operazione", "A cosa serve"],
    ["<b>Elenco schemi</b>", "Cosa contiene il database"],
    ["<b>Elenco oggetti</b>", "Quali tabelle e viste ci sono in uno schema"],
    ["<b>Descrizione</b>", "Che colonne ha una tabella, di che tipo, con quale sistema di riferimento"],
    ["<b>Lettura</b>", "Estrae righe, con selezione di colonne, filtro, ordinamento e limite"],
    ["<b>Scrittura</b>", "Deposita righe: creazione, aggiunta, aggiornamento, sostituzione, cancellazione per chiave"],
]
story += [grid(ops, [34 * mm, W - 34 * mm])]

story += [
    Paragraph("Interrogare prima di agire", S["h2"]),
    Paragraph(
        "Prima di scrivere, la libreria chiede al database che cosa sa fare: se regge "
        "la scrittura massiva, se ammette transazioni con punti di ripristino, se ha "
        "supporto per geometrie o geografie, se può creare un indice spaziale. Poi si "
        "adatta.", S["body"]),
    Paragraph(
        "Questo evita il difetto più comune: dare per scontata una capacità, scoprire a "
        "metà lavorazione che manca, e restare con un archivio scritto per metà. Se una "
        "capacità richiesta non c'è, il rifiuto arriva prima di toccare i dati.",
        S["body"]),
]

story += [
    Paragraph("Cosa succede quando qualcosa va storto", S["h2"]),
    Paragraph(
        "Ogni errore dichiara quattro cose: di che genere è, in quale fase è successo, "
        "che effetto ha avuto sul database, e se ha senso riprovare.", S["body"]),
]
errors = [
    ["Ciò che l'errore dichiara", "Perché serve"],
    ["<b>La fase</b>",
     "Validazione, connessione, preparazione, scrittura, conferma, ripristino: dice a "
     "che punto della lavorazione ci si è fermati"],
    ["<b>L'effetto sul database</b>",
     "Nessuno, annullato, parziale, confermato, o ignoto. È l'informazione che decide "
     "se si può ripartire da capo o serve prima verificare"],
    ["<b>Se riprovare</b>",
     "Mai, sicuro, solo con una chiave di idempotenza, solo dopo un recupero, o dopo "
     "un'attesa"],
]
story += [grid(errors, [40 * mm, W - 40 * mm])]
story += [Paragraph(
    "«Parziale» e «ignoto» sono le risposte scomode, e sono proprio quelle che non "
    "vanno nascoste: un sistema che dice sempre «errore, riprova» invita a duplicare "
    "i dati.", S["note"]), Spacer(1, 8)]

story.append(PageBreak())

# --- 5. stato ----------------------------------------------------------------
story += [
    Paragraph("STATO", S["eyebrow"]),
    Paragraph("Cosa funziona e cosa manca", S["h1"]),
    rule(),
    Paragraph(
        "Le tre librerie sono complete come singoli componenti. Quello che non è ancora "
        "dimostrato è che funzionino <i>insieme</i> su tutti i casi difficili.", S["body"]),
]

state = [
    ["", "Stato", "Nota"],
    ["<b>Le tre librerie, prese una per una</b>", "Verificate internamente",
     "Test propri e analisi in ogni repository"],
    ["<b>Revisione indipendente</b>", "Non svolta",
     "Nessuna delle tre è stata revisionata da chi non l'ha scritta"],
    ["<b>La catena completa</b>", "Una prova sola",
     "Un caso semplice, su Linux, con un verificatore non terzo — poi rimosso"],
    ["<b>I casi difficili</b>", "Mai provati",
     "Quote, ordine degli assi, sistemi di riferimento in conflitto"],
    ["<b>Il percorso inverso</b>", "Mai provato",
     "Dal database verso i file non è mai stato eseguito"],
]
story += [grid(state, [58 * mm, 32 * mm, W - 90 * mm])]

story += [
    Paragraph("Che cosa sono «i casi difficili»", S["h2"]),
    Paragraph(
        "Sono le situazioni in cui un dato si degrada senza che nessuno se ne accorga. "
        "Una geometria con la quota che esce senza quota. Un sistema di riferimento con "
        "latitudine e longitudine invertite. Un identificativo numerico grande che perde "
        "precisione. Nessuno di questi produce un errore: producono un archivio "
        "plausibile e sbagliato.", S["body"]),
    Paragraph(
        "Su dati patrimoniali è la categoria di guasto che costa di più, perché si "
        "scopre tardi e non si sa da quando. Per questo esiste un quarto repository, "
        "<b>plenora-contracts</b>, che contiene le regole che tutte e tre devono "
        "rispettare e una batteria di tredici casi costruiti apposta per farle "
        "sbagliare. I dati di prova sono generati da uno strumento esterno alle tre "
        "librerie: se li producesse una di loro, un suo difetto potrebbe annullarsi con "
        "il difetto speculare e la prova passerebbe lo stesso.", S["body"]),
]

story.append(callout(
    "Il pezzo che manca per chiudere",
    "Due delle tre librerie possono essere verificate oggi. La terza deve prima esporre "
    "un comando che, letta una tabella, dichiari che cosa ci ha capito — senza bisogno di "
    "un database acceso. È un lavoro contenuto, in corso, e sblocca l'intera verifica."))

story += [
    Paragraph("Cosa significa, in pratica", S["h2"]),
    Paragraph(
        "Le tre librerie si parlano: la prova che passino dati dall'una all'altra "
        "conservando il contratto esiste. Quello che manca è la conferma che reggano "
        "anche quando i dati sono scomodi. Non è un dubbio sul disegno, che è già "
        "quello giusto: è la differenza fra «funziona» e «è dimostrato che funziona», "
        "e su un archivio patrimoniale la seconda è quella che conta.", S["body"]),
]

story += [
    Spacer(1, 10),
    rule(space_after=6),
    Paragraph(
        "Le funzioni e i conteggi riportati sono stati rilevati leggendo il codice delle "
        "tre librerie, non la loro documentazione. Le affermazioni sullo stato "
        "corrispondono a quanto le librerie stesse dichiarano nei propri registri di "
        "rilascio. Nessuna prova è stata eseguita per redigere questo documento.",
        S["note"]),
]

# ---------------------------------------------------------------- build

output = Path(__file__).resolve().parents[1] / "docs" / "PLENORA-INTEGRAZIONE-TRE-LIBRERIE.pdf"
output.parent.mkdir(parents=True, exist_ok=True)

document = BaseDocTemplate(
    str(output), pagesize=A4,
    leftMargin=MARGIN, rightMargin=MARGIN,
    topMargin=MARGIN, bottomMargin=MARGIN,
    title="Plenora — Integrazione delle tre librerie",
    author="Plenora", subject="Documento di integrazione",
)
frame = Frame(MARGIN, MARGIN, W, PAGE_H - 2 * MARGIN, id="main",
              leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
document.addPageTemplates([PageTemplate(id="page", frames=[frame], onPage=decorate)])
document.build(story)
print(f"{output}  ({output.stat().st_size // 1024} KB)")
