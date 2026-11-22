#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gestione Studio per Geometra - versione con finestra grafica
============================================================
App desktop (tkinter) con i campi della scheda di studio:

  Clienti   : anagrafica completa (nascita, codice fiscale / P.IVA,
              indirizzo di residenza, indirizzo immobile, contatti)
  Pratiche  : numero d'ordine, incarico e data, cliente e ruolo
              ("in qualità di"), tipologia immobile, tipologia pratica con dettaglio e
              titolo abilitativo, stato, compenso
  Pagamenti : acconti e saldo con importo, data e riferimenti fattura
  Scadenze  : promemoria collegati alle pratiche
  Stampe    : scheda cliente, scheda pratica, fattura pro forma
  Impostazioni: campi personalizzati per sezione e dati dello studio

Uso:  python3 gestione_studio_gui.py
Database: studio_gui.db (nella stessa cartella)
"""

import html
import os
import sqlite3
import sys
import tempfile
import tkinter as tk
import webbrowser
from datetime import date, datetime
from pathlib import Path
from tkinter import ttk, messagebox, filedialog, font as tkfont

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "studio_gui.db")
CODIFICA = "utf-8"  # sempre UTF-8, su macOS come su Windows


def imposta_utf8():
    """Su Windows la console usa spesso cp1252: forzo UTF-8 sugli stream standard."""
    for nome in ("stdin", "stdout", "stderr"):
        flusso = getattr(sys, nome, None)
        try:
            flusso.reconfigure(encoding=CODIFICA, errors="replace")
        except (AttributeError, ValueError):
            continue


def scrivi_testo(percorso, contenuto):
    """Scrive testo in UTF-8 senza BOM e con fine riga LF, identico su ogni sistema."""
    with open(percorso, "w", encoding=CODIFICA, newline="\n") as f:
        f.write(contenuto)


def leggi_testo(percorso):
    with open(percorso, "r", encoding=CODIFICA) as f:
        return f.read()


def url_file(percorso):
    """URL corretto anche su Windows (file:///C:/...), con gli spazi codificati."""
    return Path(percorso).resolve().as_uri()


# ---------------------------------------------------------------------------
# Aspetto grafico: tema scuro esplicito, uguale su macOS e Windows
# ---------------------------------------------------------------------------

SFONDO = "#1e1f22"
PANEL = "#26282c"
RIGA = "#2b2d31"
CAMPO = "#31343a"
BOTTONE = "#3a3d44"
BOTTONE_HOVER = "#4a4e57"
BOTTONE_PREMUTO = "#2f3238"
BORDO = "#4a4f58"
TESTO = "#e8e8e8"
TESTO_TENUE = "#a3a9b3"
ACCENTO = "#2f6feb"
ACCENTO_TESTO = "#ffffff"
INTESTAZIONE = "#33373d"
TAB = "#2a2d33"
TAB_ATTIVO = "#3a3e46"
SCADUTA_BG = "#5a2a2a"
SCADUTA_FG = "#ffdede"


def usa_schermo_hd():
    """Su Windows evita la finestra sfocata quando il display ha il 150%/200% di zoom."""
    if not sys.platform.startswith("win"):
        return
    try:
        import ctypes
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(1)
        except (AttributeError, OSError):
            ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass


def applica_tema(radice):
    """Tema scuro disegnato da Tk (ttk 'clam'), così l'aspetto non dipende dal sistema."""
    stile = ttk.Style(radice)
    try:
        stile.theme_use("clam")  # tema incluso in Tk: macOS, Windows e Linux
    except tk.TclError:
        pass

    famiglia = tkfont.nametofont("TkDefaultFont").actual("family")
    for nome in ("TkDefaultFont", "TkTextFont", "TkMenuFont", "TkHeadingFont",
                 "TkTooltipFont"):
        try:
            tkfont.nametofont(nome).configure(family=famiglia, size=11)
        except tk.TclError:
            pass

    def cfg(nome, **opzioni):
        try:
            stile.configure(nome, **opzioni)
        except tk.TclError:
            pass

    def mappa(nome, **opzioni):
        try:
            stile.map(nome, **opzioni)
        except tk.TclError:
            pass

    radice.configure(background=SFONDO)

    cfg("TFrame", background=SFONDO)
    cfg("TLabel", background=SFONDO, foreground=TESTO)
    cfg("TSeparator", background=BORDO)
    cfg("TLabelframe", background=SFONDO, bordercolor=BORDO, foreground=TESTO)
    cfg("TLabelframe.Label", background=SFONDO, foreground=TESTO)

    cfg("TButton", background=BOTTONE, foreground=TESTO, bordercolor=BORDO,
        lightcolor=BOTTONE, darkcolor=BOTTONE, focuscolor=ACCENTO, padding=(9, 4),
        relief="flat")
    mappa("TButton",
          background=[("disabled", PANEL), ("pressed", BOTTONE_PREMUTO),
                      ("active", BOTTONE_HOVER)],
          foreground=[("disabled", TESTO_TENUE)])

    cfg("TEntry", fieldbackground=CAMPO, foreground=TESTO, insertcolor=TESTO,
        bordercolor=BORDO, lightcolor=BORDO, darkcolor=BORDO, padding=(4, 3))
    mappa("TEntry", fieldbackground=[("disabled", PANEL)],
          foreground=[("disabled", TESTO_TENUE)])

    cfg("TCombobox", fieldbackground=CAMPO, background=BOTTONE, foreground=TESTO,
        arrowcolor=TESTO, bordercolor=BORDO, lightcolor=BORDO, darkcolor=BORDO,
        padding=(4, 3))
    mappa("TCombobox",
          fieldbackground=[("readonly", CAMPO), ("disabled", PANEL)],
          foreground=[("readonly", TESTO), ("disabled", TESTO_TENUE)],
          background=[("active", BOTTONE_HOVER)],
          selectbackground=[("readonly", CAMPO)],
          selectforeground=[("readonly", TESTO)])

    cfg("TNotebook", background=SFONDO, bordercolor=BORDO, tabmargins=(2, 4, 2, 0))
    cfg("TNotebook.Tab", background=TAB, foreground=TESTO_TENUE, padding=(14, 6),
        bordercolor=BORDO, lightcolor=TAB, darkcolor=TAB)
    mappa("TNotebook.Tab",
          background=[("selected", TAB_ATTIVO), ("active", BOTTONE_HOVER)],
          foreground=[("selected", TESTO), ("active", TESTO)],
          lightcolor=[("selected", TAB_ATTIVO)],
          darkcolor=[("selected", TAB_ATTIVO)])

    cfg("Treeview", background=RIGA, fieldbackground=RIGA, foreground=TESTO,
        bordercolor=BORDO, lightcolor=BORDO, darkcolor=BORDO, rowheight=24)
    mappa("Treeview", background=[("selected", ACCENTO)],
          foreground=[("selected", ACCENTO_TESTO)])
    cfg("Treeview.Heading", background=INTESTAZIONE, foreground=TESTO, relief="flat",
        bordercolor=BORDO, lightcolor=INTESTAZIONE, darkcolor=INTESTAZIONE,
        font=(famiglia, 11, "bold"))
    mappa("Treeview.Heading", background=[("active", BOTTONE_HOVER)],
          foreground=[("active", TESTO)])

    cfg("TCheckbutton", background=SFONDO, foreground=TESTO, focuscolor=ACCENTO,
        padding=(2, 2), indicatorbackground=CAMPO, indicatorforeground=TESTO,
        upperbordercolor=BORDO, lowerbordercolor=BORDO)
    mappa("TCheckbutton", background=[("active", SFONDO)],
          foreground=[("disabled", TESTO_TENUE)],
          indicatorbackground=[("selected", ACCENTO), ("disabled", PANEL)],
          indicatorforeground=[("selected", ACCENTO_TESTO)])

    # interruttore "solo aperte": pulsante a due stati, senza la X del checkbutton
    cfg("Toolbutton", background=BOTTONE, foreground=TESTO_TENUE, bordercolor=BORDO,
        lightcolor=BOTTONE, darkcolor=BOTTONE, focuscolor=ACCENTO, padding=(9, 4),
        relief="flat")
    mappa("Toolbutton",
          background=[("selected", ACCENTO), ("active", BOTTONE_HOVER)],
          foreground=[("selected", ACCENTO_TESTO), ("active", TESTO)])

    cfg("TScrollbar", background=BOTTONE, troughcolor=PANEL, bordercolor=PANEL,
        arrowcolor=TESTO, lightcolor=BOTTONE, darkcolor=BOTTONE)
    mappa("TScrollbar", background=[("active", BOTTONE_HOVER)])

    # tendina dei menu a scelta (è una listbox Tk, non un widget ttk)
    for chiave, valore in (
        ("background", CAMPO), ("foreground", TESTO),
        ("selectBackground", ACCENTO), ("selectForeground", ACCENTO_TESTO),
        ("font", (famiglia, 11)),
    ):
        try:
            radice.option_add(f"*TCombobox*Listbox.{chiave}", valore)
        except tk.TclError:
            pass

    return stile


imposta_utf8()
usa_schermo_hd()

TIPI_CAMPO = ["testo", "numero", "data", "lista", "testo lungo"]
SEZIONI = ["clienti", "pratiche", "scadenze"]
SEZIONI_ETICHETTE = {"clienti": "Clienti", "pratiche": "Pratiche", "scadenze": "Scadenze"}

TIPI_IMMOBILE = ["Fabbricato singolo", "Condominio", "Appartamento",
                 "Villetta", "Fabbricato rurale", "Bottega", "Garage",
                 "Magazzino"]

CATEGORIE = ["Catasto", "Urbanistica", "SCA", "Perizia di stima", "Perizia danni",
             "Perizia superbonus", "Tabelle millesimali", "Altro"]

DETTAGLI = {
    "Catasto": ["Inserimento in mappa", "Frazionamento", "DOCFA",
                "Inserimento in mappa e DOCFA", "Ricorsi", "Allineamento dati"],
    "Urbanistica": ["Nuova costruzione", "Ristrutturazione", "Regolarizzazione",
                    "Sanatoria", "Autorizzazione allo scarico"],
}

TITOLI = ["CILA", "SCIA", "SCIA in sanatoria", "SCIA alternativa al PdC",
          "PdC", "Autorizzazione allo scarico"]

RUOLI_CLIENTE = ["Proprietario", "Comproprietario", "Affittuario",
                 "Amministratore di condominio", "Impresa"]

STATI_PRATICA = ["In attesa", "In corso", "Presentata", "Completata", "Sospesa"]
TIPI_PAGAMENTO = ["Acconto 1", "Acconto 2", "Acconto 3", "Saldo"]

DATI_STUDIO = [("nome", "Studio"), ("indirizzo", "Indirizzo"),
               ("piva", "P.IVA / C.F."), ("telefono", "Telefono"),
               ("email", "Email")]

# Campi fissi (non eliminabili) di ogni sezione, nell'ordine della scheda di studio.
#   tipo: testo | testo lungo | data | numero | lista | cliente | pratica | si_no | dipende
#   tabella: se la colonna compare nella tabella
CAMPI_FISSI = {
    "clienti": [
        {"chiave": "cognome", "etichetta": "Cognome / Ragione sociale *", "tipo": "testo",
         "obbligatorio": True, "tabella": True, "larghezza_tabella": 200},
        {"chiave": "nome", "etichetta": "Nome", "tipo": "testo", "tabella": True},
        {"chiave": "nato_il", "etichetta": "Nato/a il", "tipo": "data", "tabella": True},
        {"chiave": "nato_a", "etichetta": "Nato/a a", "tipo": "testo"},
        {"chiave": "provincia", "etichetta": "Prov. nascita", "tipo": "testo", "larghezza": 10},
        {"chiave": "codice_fiscale", "etichetta": "Codice fiscale / P.IVA", "tipo": "testo",
         "tabella": True, "colonna": "Cod. fiscale / P.IVA"},
        {"chiave": "indirizzo_residenza", "etichetta": "Indirizzo residenza", "tipo": "testo"},
        {"chiave": "indirizzo_immobile", "etichetta": "Indirizzo immobile", "tipo": "testo",
         "tabella": True},
        {"chiave": "citta_immobile", "etichetta": "Città immobile", "tipo": "testo",
         "tabella": True},
        {"chiave": "telefono", "etichetta": "Telefono", "tipo": "testo", "tabella": True,
         "larghezza_tabella": 110},
        {"chiave": "email", "etichetta": "Email", "tipo": "testo", "tabella": True,
         "larghezza_tabella": 160},
        {"chiave": "note", "etichetta": "Note", "tipo": "testo lungo"},
    ],
    "pratiche": [
        {"chiave": "numero_ordine", "etichetta": "Numero d'ordine / pratica", "tipo": "testo",
         "tabella": True, "colonna": "N° ordine", "larghezza_tabella": 110,
         "automatico": True},
        {"chiave": "cliente", "etichetta": "Cliente *", "tipo": "cliente", "obbligatorio": True,
         "tabella": True},
        {"chiave": "in_qualita_di", "etichetta": "In qualità di", "tipo": "lista",
         "opzioni": RUOLI_CLIENTE, "tabella": True, "larghezza_tabella": 150},
        {"chiave": "incarico", "etichetta": "Incarico", "tipo": "testo"},
        {"chiave": "data_incarico", "etichetta": "Data incarico", "tipo": "data", "tabella": True},
        {"chiave": "tipologia_immobile", "etichetta": "Tipologia immobile", "tipo": "lista",
         "opzioni": TIPI_IMMOBILE, "tabella": True, "colonna": "Tipo immobile"},
        {"chiave": "categoria", "etichetta": "Tipologia pratica", "tipo": "lista",
         "opzioni": CATEGORIE, "tabella": True, "colonna": "Tipo pratica"},
        {"chiave": "dettaglio", "etichetta": "Dettaglio", "tipo": "dipende",
         "dipende_da": "categoria", "tabella": True},
        {"chiave": "titolo", "etichetta": "Titolo abilitativo", "tipo": "lista",
         "opzioni": TITOLI},
        {"chiave": "oggetto", "etichetta": "Oggetto / note", "tipo": "testo lungo"},
        {"chiave": "stato", "etichetta": "Stato", "tipo": "lista", "opzioni": STATI_PRATICA,
         "tabella": True},
        {"chiave": "compenso", "etichetta": "Compenso pattuito (€)", "tipo": "numero",
         "tabella": True, "colonna": "Compenso (€)"},
    ],
    "scadenze": [
        {"chiave": "descrizione", "etichetta": "Descrizione *", "tipo": "testo",
         "obbligatorio": True, "tabella": True},
        {"chiave": "data_scadenza", "etichetta": "Data scadenza *", "tipo": "data",
         "obbligatorio": True, "tabella": True},
        {"chiave": "pratica", "etichetta": "Pratica collegata", "tipo": "pratica",
         "tabella": True, "colonna": "Pratica"},
        {"chiave": "completata", "etichetta": "Completata", "tipo": "si_no", "tabella": True},
    ],
}

TABELLE_DATI = {
    "clienti": ["cognome", "nome", "nato_il", "nato_a", "provincia", "codice_fiscale",
                "indirizzo_residenza", "indirizzo_immobile", "citta_immobile", "telefono",
                "email", "note"],
    "pratiche": ["incarico", "data_incarico", "in_qualita_di",
                 "tipologia_immobile", "categoria", "dettaglio", "titolo", "oggetto",
                 "stato", "compenso"],
}

# Campi personalizzati dei vecchi database ormai coperti dai campi fissi
CAMPI_DUPLICATI = {
    "clienti": {"Codice fiscale / P.IVA": "codice_fiscale", "Telefono": "telefono",
                "Email": "email", "Indirizzo": "indirizzo_residenza", "Note": "note"},
    "pratiche": {"Riferimento contratto": "incarico"},
    "scadenze": {},
}

# Vecchie tipologie di pratica -> (categoria, dettaglio)
MIGRA_TIPI = {
    "Accatastamento": ("Catasto", "Inserimento in mappa e DOCFA"),
    "Voltura catastale": ("Catasto", "Allineamento dati"),
    "Rilievo planimetrico": ("Catasto", "Inserimento in mappa"),
    "Frazionamento": ("Catasto", "Frazionamento"),
    "Fusione": ("Catasto", "Allineamento dati"),
    "Verifica conformità catastale": ("Catasto", "Allineamento dati"),
    "Progetto e DOCFA": ("Catasto", "DOCFA"),
    "Altra": ("Altro", ""),
}


# ---------------------------------------------------------------------------
# Modello / database
# ---------------------------------------------------------------------------

def connetti():
    con = sqlite3.connect(DB_FILE)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA foreign_keys = ON")
    return con


def _colonne(con, tabella):
    return {r["name"] for r in con.execute(f"PRAGMA table_info({tabella})")}


def _aggiungi_colonne(con, tabella, definizioni):
    presenti = _colonne(con, tabella)
    for nome, tipo in definizioni:
        if nome not in presenti:
            con.execute(f"ALTER TABLE {tabella} ADD COLUMN {nome} {tipo}")


def inizializza_db():
    con = connetti()
    con.executescript("""
        CREATE TABLE IF NOT EXISTS clienti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cognome TEXT NOT NULL DEFAULT '',
            nome TEXT NOT NULL DEFAULT '',
            nato_il TEXT,
            nato_a TEXT,
            provincia TEXT,
            codice_fiscale TEXT,
            indirizzo_residenza TEXT,
            indirizzo_immobile TEXT,
            citta_immobile TEXT,
            telefono TEXT,
            email TEXT,
            note TEXT
        );
        CREATE TABLE IF NOT EXISTS pratiche (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cliente_id INTEGER REFERENCES clienti(id) ON DELETE CASCADE,
            numero_ordine TEXT,
            incarico TEXT,
            data_incarico TEXT,
            in_qualita_di TEXT,
            tipologia_immobile TEXT,
            categoria TEXT,
            dettaglio TEXT,
            titolo TEXT,
            oggetto TEXT,
            stato TEXT NOT NULL DEFAULT 'In attesa',
            compenso REAL NOT NULL DEFAULT 0,
            data_apertura TEXT,
            data_chiusura TEXT
        );
        CREATE TABLE IF NOT EXISTS pagamenti (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            pratica_id INTEGER NOT NULL REFERENCES pratiche(id) ON DELETE CASCADE,
            tipo TEXT NOT NULL DEFAULT 'Acconto 1',
            importo REAL NOT NULL DEFAULT 0,
            data TEXT,
            fattura_numero TEXT,
            fattura_data TEXT
        );
        CREATE TABLE IF NOT EXISTS scadenze (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            descrizione TEXT NOT NULL,
            data_scadenza TEXT NOT NULL,
            pratica_id INTEGER REFERENCES pratiche(id) ON DELETE SET NULL,
            completata INTEGER NOT NULL DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS campi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sezione TEXT NOT NULL,
            nome TEXT NOT NULL,
            tipo TEXT NOT NULL DEFAULT 'testo',
            opzioni TEXT NOT NULL DEFAULT '',
            ordine INTEGER NOT NULL DEFAULT 0,
            attivo INTEGER NOT NULL DEFAULT 1,
            UNIQUE (sezione, nome)
        );
        CREATE TABLE IF NOT EXISTS valori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            campo_id INTEGER NOT NULL REFERENCES campi(id) ON DELETE CASCADE,
            record_id INTEGER NOT NULL,
            valore TEXT NOT NULL DEFAULT '',
            UNIQUE (campo_id, record_id)
        );
        CREATE TABLE IF NOT EXISTS meta (
            chiave TEXT PRIMARY KEY,
            valore TEXT NOT NULL DEFAULT ''
        );
    """)
    _migra_db(con)
    if not con.execute("SELECT 1 FROM meta WHERE chiave='predefiniti'").fetchone():
        con.execute("INSERT INTO meta (chiave, valore) VALUES ('predefiniti', '1')")
    if not con.execute("SELECT 1 FROM meta WHERE chiave='studio_nome'").fetchone():
        con.execute("INSERT INTO meta (chiave, valore) VALUES ('studio_nome', 'Studio Geometra Russo')")
    con.commit()
    con.close()


def _migra_db(con):
    """Porta i database delle versioni precedenti alla struttura attuale."""
    _aggiungi_colonne(con, "clienti", [
        ("cognome", "TEXT NOT NULL DEFAULT ''"), ("nato_il", "TEXT"),
        ("nato_a", "TEXT"), ("provincia", "TEXT"), ("codice_fiscale", "TEXT"),
        ("indirizzo_residenza", "TEXT"), ("indirizzo_immobile", "TEXT"),
        ("citta_immobile", "TEXT"),
        ("telefono", "TEXT"), ("email", "TEXT"), ("note", "TEXT"),
    ])
    colonne = _colonne(con, "clienti")
    if "cognome_ragione_sociale" in colonne:
        con.execute("UPDATE clienti SET cognome=cognome_ragione_sociale"
                    " WHERE (cognome IS NULL OR cognome='')")
        con.execute("ALTER TABLE clienti DROP COLUMN cognome_ragione_sociale")

    _aggiungi_colonne(con, "pratiche", [
        ("numero_ordine", "TEXT"), ("incarico", "TEXT"), ("data_incarico", "TEXT"),
        ("in_qualita_di", "TEXT"), ("tipologia_immobile", "TEXT"),
        ("categoria", "TEXT"), ("dettaglio", "TEXT"), ("titolo", "TEXT"),
        ("oggetto", "TEXT"), ("stato", "TEXT NOT NULL DEFAULT 'In attesa'"),
        ("compenso", "REAL NOT NULL DEFAULT 0"),
        ("data_apertura", "TEXT"), ("data_chiusura", "TEXT"),
    ])
    colonne = _colonne(con, "pratiche")
    if "tipo" in colonne:
        for vecchio, (categoria, dettaglio) in MIGRA_TIPI.items():
            con.execute(
                "UPDATE pratiche SET categoria=?, dettaglio=?"
                " WHERE (categoria IS NULL OR categoria='') AND tipo=?",
                (categoria, dettaglio, vecchio))
        con.execute("UPDATE pratiche SET categoria='Altro' WHERE categoria IS NULL OR categoria=''")
        con.execute("ALTER TABLE pratiche DROP COLUMN tipo")
    # la vecchia "data apertura" equivale alla data di incarico
    con.execute("UPDATE pratiche SET data_incarico=data_apertura"
                " WHERE (data_incarico IS NULL OR data_incarico='')"
                " AND data_apertura IS NOT NULL")
    con.execute("UPDATE pratiche SET data_apertura=data_incarico"
                " WHERE (data_apertura IS NULL OR data_apertura='')"
                " AND data_incarico IS NOT NULL")

    # i valori dei campi personalizzati che ora sono campi fissi vengono copiati
    for sezione, mappa in CAMPI_DUPLICATI.items():
        for nome, colonna in mappa.items():
            campo = con.execute("SELECT id FROM campi WHERE sezione=? AND nome=?",
                                (sezione, nome)).fetchone()
            if not campo:
                continue
            tabella = sezione
            for r in con.execute(
                "SELECT record_id, valore FROM valori WHERE campo_id=? AND valore<>''",
                (campo["id"],),
            ):
                con.execute(f"UPDATE {tabella} SET {colonna}=?"
                            f" WHERE id=? AND ({colonna} IS NULL OR {colonna}='')",
                            (r["valore"], r["record_id"]))
            # il campo resta nel database ma non viene più mostrato: niente doppioni
            con.execute("UPDATE campi SET attivo=0 WHERE id=?", (campo["id"],))

    # i vecchi ruoli separati diventano un unico campo "In qualità di"
    presenti = _colonne(con, "pratiche")
    for colonna, ruolo in (("proprietario", "Proprietario"),
                           ("comproprietario", "Comproprietario"),
                           ("affittuario", "Affittuario"),
                           ("amministratore", "Amministratore di condominio"),
                           ("impresa", "Impresa")):
        if colonna not in presenti:
            continue
        con.execute(f"UPDATE pratiche SET in_qualita_di=?"
                    f" WHERE (in_qualita_di IS NULL OR in_qualita_di='')"
                    f" AND {colonna} IS NOT NULL AND {colonna}<>''", (ruolo,))
        try:  # colonna non più usata: la tolgo dal database
            con.execute(f"ALTER TABLE pratiche DROP COLUMN {colonna}")
        except sqlite3.OperationalError:
            pass

    con.execute("UPDATE pratiche SET numero_ordine=CAST(id AS TEXT)")

    con.execute("UPDATE scadenze SET completata=0 WHERE completata IS NULL")


def campi_sezione(con, sezione, solo_attivi=True):
    q = "SELECT * FROM campi WHERE sezione=?"
    if solo_attivi:
        q += " AND attivo=1"
    q += " ORDER BY ordine, id"
    return con.execute(q, (sezione,)).fetchall()


def valori_record(con, campo_ids, record_id):
    """Restituisce {campo_id: valore} per un record di una sezione."""
    out = {cid: "" for cid in campo_ids}
    if not campo_ids:
        return out
    segnaposti = ",".join("?" * len(campo_ids))
    for r in con.execute(
        f"SELECT campo_id, valore FROM valori WHERE campo_id IN ({segnaposti}) AND record_id=?",
        (*campo_ids, record_id),
    ):
        out[r["campo_id"]] = r["valore"]
    return out


def salva_valori(con, campo_ids_valori, record_id):
    for campo_id, valore in campo_ids_valori.items():
        con.execute(
            "INSERT INTO valori (campo_id, record_id, valore) VALUES (?,?,?)"
            " ON CONFLICT(campo_id, record_id) DO UPDATE SET valore=excluded.valore",
            (campo_id, record_id, valore),
        )


def elimina_valori(con, sezione, record_ids):
    """Rimuove i valori dei campi personalizzati dei record eliminati."""
    for rid in record_ids:
        con.execute("DELETE FROM valori WHERE record_id=? AND campo_id IN"
                    " (SELECT id FROM campi WHERE sezione=?)", (rid, sezione))


def dati_studio(con):
    valori = {}
    for chiave, _ in DATI_STUDIO:
        riga = con.execute("SELECT valore FROM meta WHERE chiave=?",
                           (f"studio_{chiave}",)).fetchone()
        valori[chiave] = riga["valore"] if riga else ""
    return valori


def salva_dati_studio(con, valori):
    for k, v in valori.items():
        con.execute("INSERT INTO meta (chiave, valore) VALUES (?,?)"
                    " ON CONFLICT(chiave) DO UPDATE SET valore=excluded.valore",
                    (f"studio_{k}", v))


def etichetta_cliente(c):
    nome = " ".join(x for x in (c["cognome"], c["nome"]) if x)
    return f"{nome or 'Senza nome'} (#{c['id']})"


def etichetta_pratica(p):
    numero = p["numero_ordine"] or f"#{p['id']}"
    pezzi = [numero]
    if p["categoria"]:
        pezzi.append(p["categoria"])
    if p["dettaglio"]:
        pezzi.append(p["dettaglio"])
    return " — ".join(pezzi)


def formatta_data(iso):
    """Accetta 'AAAA-MM-GG' o 'GG/MM/AAAA' e restituisce 'GG/MM/AAAA'."""
    if not iso:
        return ""
    testo = str(iso).strip()
    for formato in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(testo, formato).strftime("%d/%m/%Y")
        except ValueError:
            continue
    return testo


def valida_data(testo, obbligatorio=False):
    testo = (testo or "").strip()
    if not testo:
        if obbligatorio:
            raise ValueError("Campo data vuoto")
        return None
    return datetime.strptime(testo, "%d/%m/%Y").date().isoformat()


def mostra_valore(testo):
    """Mostra in formato italiano i valori personalizzati salvati come data ISO."""
    testo = str(testo or "")
    if len(testo) == 10 and testo[4] == "-" and testo[7] == "-":
        return formatta_data(testo)
    return testo


def euro(valore):
    try:
        return f"€ {float(valore or 0):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (TypeError, ValueError):
        return "€ 0,00"


# ---------------------------------------------------------------------------
# Widget per i campi data / testo lungo
# ---------------------------------------------------------------------------

def _metti_oggi(entry):
    entry.delete(0, "end")
    entry.insert(0, date.today().strftime("%d/%m/%Y"))


class TestoLungo(ttk.Frame):
    def __init__(self, padre, default=""):
        super().__init__(padre)
        self.text = tk.Text(self, width=18, height=3, wrap="word",
                            background=CAMPO, foreground=TESTO, insertbackground=TESTO,
                            selectbackground=ACCENTO, selectforeground=ACCENTO_TESTO,
                            relief="flat", highlightthickness=1,
                            highlightbackground=BORDO, highlightcolor=ACCENTO)
        barra = ttk.Scrollbar(self, command=self.text.yview)
        self.text.configure(yscrollcommand=barra.set)
        self.text.pack(side="left", fill="both", expand=True)
        barra.pack(side="right", fill="y")
        self.set(default)

    def get(self):
        return self.text.get("1.0", "end").strip()

    def set(self, valore):
        self.text.delete("1.0", "end")
        if valore:
            self.text.insert("1.0", str(valore))


class CampoData(ttk.Frame):
    def __init__(self, padre, default=""):
        super().__init__(padre)
        self.entry = ttk.Entry(self, width=10)
        self.entry.pack(side="left")
        ttk.Button(self, text="Oggi", width=5,
                   command=lambda: _metti_oggi(self.entry)).pack(side="left", padx=4)
        self.set(default)

    def get(self):
        return self.entry.get()

    def set(self, valore):
        self.entry.delete(0, "end")
        if valore:
            self.entry.insert(0, str(valore))


# ---------------------------------------------------------------------------
# Maschera generata a partire dai campi della sezione
# ---------------------------------------------------------------------------

class MascheraDialog(tk.Toplevel):
    """Maschera di inserimento/modifica costruita dai campi fissi + personalizzati."""

    def __init__(self, master, titolo, campi, iniziali=None, elenchi=None):
        super().__init__(master, background=SFONDO)
        self.title(titolo)
        self.transient(master)
        self.grab_set()
        self.resizable(False, False)
        self.result = None
        self._campi = campi
        self._elenchi = elenchi or {}
        self.widgets = {}
        iniziali = iniziali or {}

        padre = ttk.Frame(self, padding=12)
        padre.pack(fill="both", expand=True)

        for riga, campo in enumerate(campi):
            ttk.Label(padre, text=campo["etichetta"] + ":").grid(
                row=riga, column=0, sticky="ne", padx=(0, 8), pady=4)
            w = self._crea_widget(padre, campo, iniziali.get(campo["chiave"]))
            w.grid(row=riga, column=1, sticky="ew", pady=4)
            self.widgets[campo["chiave"]] = w

        for campo in campi:
            if campo["tipo"] == "dipende":
                self._collega_dipendente(campo)

        pulsanti = ttk.Frame(padre)
        pulsanti.grid(row=len(campi), column=0, columnspan=2, sticky="e", pady=(10, 0))
        ttk.Button(pulsanti, text="Salva", command=self._salva).pack(side="left", padx=4)
        ttk.Button(pulsanti, text="Annulla", command=self.destroy).pack(side="left")

        self.bind("<Return>", self._invio)
        self.bind("<Escape>", lambda e: self.destroy())
        self.wait_visibility()
        self.focus_set()
        self.wait_window()

    def _crea_widget(self, padre, campo, valore):
        tipo = campo["tipo"]
        if tipo == "testo":
            w = ttk.Entry(padre, width=campo.get("larghezza", 18))
        elif tipo == "numero":
            w = ttk.Entry(padre, width=8)
        elif tipo == "data":
            w = CampoData(padre, formatta_data(valore))
            return w
        elif tipo == "testo lungo":
            return TestoLungo(padre, valore or "")
        elif tipo == "si_no":
            w = ttk.Combobox(padre, values=["No", "Sì"], width=17, state="readonly")
            w.set("Sì" if valore else "No")
            return w
        elif tipo == "cliente":
            w = ttk.Combobox(padre, values=self._elenchi.get("cliente", []),
                             width=17, state="readonly")
            if valore in w["values"]:
                w.set(valore)
            elif w["values"]:
                w.current(0)
            return w
        elif tipo == "pratica":
            valori = list(self._elenchi.get("pratica", []))
            w = ttk.Combobox(padre, values=valori, width=17, state="readonly")
            if valore in valori:
                w.set(valore)
            elif campo.get("obbligatorio"):
                w.set(next((v for v in valori if v != "(nessuna)"), "(nessuna)"))
            elif valori:
                w.set("(nessuna)")
            return w
        elif tipo == "dipende":
            genitore = self.widgets.get(campo.get("dipende_da"))
            opzioni = DETTAGLI.get(genitore.get() if genitore is not None else "", [])
            w = ttk.Combobox(padre, values=opzioni, width=17, state="readonly")
            if valore in opzioni:
                w.set(valore)
            return w
        else:  # lista
            opzioni = list(campo.get("opzioni", []))
            if "" not in opzioni:
                opzioni.insert(0, "")  # prima voce sempre vuota
            w = ttk.Combobox(padre, values=opzioni, width=17, state="readonly")
            if valore not in (None, "") and valore in opzioni:
                w.set(valore)
            elif campo.get("obbligatorio") and len(opzioni) > 1:
                w.current(1)
            else:
                w.current(0)  # nessuna scelta: resta lo spazio vuoto
            return w
        if valore not in (None, ""):
            w.insert(0, str(valore))
        return w

    def _collega_dipendente(self, campo):
        genitore = self.widgets.get(campo["dipende_da"])
        figlio = self.widgets.get(campo["chiave"])
        if genitore is None or figlio is None:
            return

        def aggiorna(_evento=None):
            opzioni = DETTAGLI.get(genitore.get(), [])
            figlio.configure(values=opzioni)
            if figlio.get() not in opzioni:
                figlio.set("")

        genitore.bind("<<ComboboxSelected>>", aggiorna)

    def _invio(self, _evento=None):
        if isinstance(self.focus_get(), tk.Text):
            return  # in un campo di testo lungo Invio va a capo
        self._salva()

    def _salva(self):
        self.result = {chiave: w.get() for chiave, w in self.widgets.items()}
        self.destroy()


# ---------------------------------------------------------------------------
# Utilità comuni alle schede
# ---------------------------------------------------------------------------

def normalizza_dati(campi, dati):
    """Converte date in ISO, numeri in float e verifica gli obbligatori.

    Restituisce (dati_normalizzati, messaggio_errore)."""
    out = {}
    for campo in campi:
        chiave = campo["chiave"]
        valore = str(dati.get(chiave, "") or "").strip()
        etichetta = campo["etichetta"].rstrip(" *")
        if campo.get("obbligatorio") and not valore:
            return None, f"Il campo '{etichetta}' è obbligatorio."
        tipo = campo["tipo"]
        if tipo == "data":
            try:
                out[chiave] = valida_data(valore) or ""
            except ValueError:
                return None, f"'{etichetta}' non è una data valida (usa GG/MM/AAAA)."
        elif tipo == "numero":
            if not valore:
                out[chiave] = valore if campo.get("custom") else 0.0
            else:
                try:
                    numero = float(valore.replace(",", "."))
                except ValueError:
                    return None, f"'{etichetta}' deve essere un numero."
                out[chiave] = valore if campo.get("custom") else numero
        elif tipo == "si_no":
            out[chiave] = 1 if valore == "Sì" else 0
        else:
            out[chiave] = valore
    return out, None


def separa_custom(campi, dati):
    """Divide i valori dei campi fissi da quelli personalizzati (campo_id)."""
    fissi, custom = {}, {}
    for campo in campi:
        if campo.get("custom"):
            custom[campo["custom"]] = str(dati.get(campo["chiave"], "") or "")
        else:
            fissi[campo["chiave"]] = dati.get(campo["chiave"])
    return fissi, custom


# ---------------------------------------------------------------------------
# Scheda Clienti
# ---------------------------------------------------------------------------

class SchedaClienti(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.notebook)
        self.app = app
        self._costruisci()
        self.ricarica()

    def _costruisci(self):
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill="x")
        ttk.Button(barra, text="Nuovo cliente", command=self.nuovo).pack(side="left", padx=2)
        ttk.Button(barra, text="Modifica", command=self.modifica).pack(side="left", padx=2)
        ttk.Button(barra, text="Elimina", command=self.elimina).pack(side="left", padx=2)
        ttk.Button(barra, text="Stampa scheda", command=self.stampa).pack(side="left", padx=2)
        self.cerca = tk.StringVar()
        ttk.Label(barra, text="cerca:").pack(side="left", padx=(20, 4))
        ttk.Entry(barra, textvariable=self.cerca, width=24).pack(side="left")
        self.cerca.trace_add("write", lambda *a: self.ricarica())

        self.albero = ttk.Treeview(self, show="headings")
        barra_sc = ttk.Scrollbar(self, command=self.albero.yview)
        self.albero.configure(yscrollcommand=barra_sc.set)
        self.albero.pack(side="left", fill="both", expand=True)
        barra_sc.pack(side="left", fill="y")
        self.albero.bind("<Double-1>", lambda e: self.modifica())

    def ricarica(self):
        con = self.app.con
        colonne, testi = self.app.colonne_sezione("clienti")
        self.albero["columns"] = colonne
        for col, testo, larghezza in zip(colonne, testi, self.app.larghezze_sezione("clienti")):
            self.albero.heading(col, text=testo)
            self.albero.column(col, width=larghezza, minwidth=70, stretch=True)
        for i in self.albero.get_children():
            self.albero.delete(i)
        campi = campi_sezione(con, "clienti")
        filtro = self.cerca.get().strip().lower()
        for c in con.execute("SELECT * FROM clienti ORDER BY cognome, nome"):
            v = valori_record(con, [k["id"] for k in campi], c["id"])
            riga = []
            for col in colonne:
                if col.startswith("fisso_"):
                    riga.append(self._valore(col[6:], c))
                else:
                    riga.append(mostra_valore(v.get(int(col[5:]))))
            if filtro and filtro not in " ".join(map(str, riga)).lower():
                continue
            self.albero.insert("", "end", iid=str(c["id"]), values=riga)

    @staticmethod
    def _valore(chiave, c):
        if chiave == "nato_il":
            return formatta_data(c["nato_il"])
        return c[chiave] or ""

    def _maschera(self, iniziali=None):
        campi = self.app.campi_form("clienti")
        return MascheraDialog(self, "Cliente", campi, iniziali), campi

    def nuovo(self):
        dlg, campi = self._maschera()
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        fissi, custom = separa_custom(campi, dati)
        con = self.app.con
        colonne = TABELLE_DATI["clienti"]
        cur = con.execute(
            f"INSERT INTO clienti ({','.join(colonne)}) VALUES ({','.join('?' * len(colonne))})",
            [fissi.get(k, "") for k in colonne])
        salva_valori(con, custom, cur.lastrowid)
        con.commit()
        self.ricarica()
        self.app.schede["pratiche"].ricarica()

    def _id_selezionato(self):
        sel = self.albero.selection()
        if not sel:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima un cliente dalla tabella.")
            return None
        return int(sel[0])

    def modifica(self):
        cliente_id = self._id_selezionato()
        if not cliente_id:
            return
        con = self.app.con
        c = con.execute("SELECT * FROM clienti WHERE id=?", (cliente_id,)).fetchone()
        campi = self.app.campi_form("clienti")
        v = valori_record(con, [k["id"] for k in campi_sezione(con, "clienti")], cliente_id)
        iniziali = {k: c[k] for k in c.keys()}
        for k in campi_sezione(con, "clienti"):
            iniziali[f"campo_{k['id']}"] = v.get(k["id"]) or ""
        dlg = MascheraDialog(self, "Cliente", campi, iniziali)
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        fissi, custom = separa_custom(campi, dati)
        colonne = TABELLE_DATI["clienti"]
        con.execute(f"UPDATE clienti SET {','.join(k + '=?' for k in colonne)} WHERE id=?",
                    [fissi.get(k, "") for k in colonne] + [cliente_id])
        salva_valori(con, custom, cliente_id)
        con.commit()
        self.ricarica()
        self.app.schede["pratiche"].ricarica()

    def elimina(self):
        cliente_id = self._id_selezionato()
        if not cliente_id:
            return
        if not messagebox.askyesno(
                "Conferma", "Eliminare il cliente, le sue pratiche, i pagamenti e le scadenze?"):
            return
        con = self.app.con
        pratiche = [r["id"] for r in con.execute(
            "SELECT id FROM pratiche WHERE cliente_id=?", (cliente_id,))]
        segnaposti = ",".join("?" * len(pratiche)) or "NULL"
        scadenze = [r["id"] for r in con.execute(
            f"SELECT id FROM scadenze WHERE pratica_id IN ({segnaposti})", pratiche)]
        con.execute("DELETE FROM clienti WHERE id=?", (cliente_id,))
        if scadenze:
            con.execute(f"DELETE FROM scadenze WHERE id IN ({','.join('?' * len(scadenze))})",
                        scadenze)
        elimina_valori(con, "clienti", [cliente_id])
        elimina_valori(con, "pratiche", pratiche)
        elimina_valori(con, "scadenze", scadenze)
        con.commit()
        self.app.riempi_tabelle()

    def stampa(self):
        cliente_id = self._id_selezionato()
        if not cliente_id:
            return
        apri_stampa(html_scheda_cliente(self.app.con, cliente_id),
                    f"scheda_cliente_{cliente_id}.html")


# ---------------------------------------------------------------------------
# Scheda Pratiche
# ---------------------------------------------------------------------------

class SchedaPratiche(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.notebook)
        self.app = app
        self._costruisci()
        self.ricarica()

    def _costruisci(self):
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill="x")
        ttk.Button(barra, text="Nuova pratica", command=self.nuovo).pack(side="left", padx=2)
        ttk.Button(barra, text="Modifica", command=self.modifica).pack(side="left", padx=2)
        ttk.Button(barra, text="Elimina", command=self.elimina).pack(side="left", padx=2)
        ttk.Button(barra, text="Stampa scheda", command=self.stampa).pack(side="left", padx=2)
        ttk.Button(barra, text="Fattura pro forma",
                   command=self.fattura).pack(side="left", padx=2)

        filtri = ttk.Frame(self, padding=(6, 0, 6, 6))
        filtri.pack(fill="x")
        self.cerca = tk.StringVar()
        ttk.Label(filtri, text="cerca:").pack(side="left")
        ttk.Entry(filtri, textvariable=self.cerca, width=22).pack(side="left", padx=(4, 14))
        self.categoria_filtro = tk.StringVar(value="Tutte")
        ttk.Label(filtri, text="Tipologia:").pack(side="left")
        ttk.Combobox(filtri, textvariable=self.categoria_filtro, width=16, state="readonly",
                     values=["Tutte"] + CATEGORIE).pack(side="left", padx=4)
        self.stato_filtro = tk.StringVar(value="Tutti")
        ttk.Label(filtri, text="Stato:").pack(side="left", padx=(12, 0))
        ttk.Combobox(filtri, textvariable=self.stato_filtro, width=12, state="readonly",
                     values=["Tutti"] + STATI_PRATICA).pack(side="left", padx=4)
        for var in (self.cerca, self.categoria_filtro, self.stato_filtro):
            var.trace_add("write", lambda *a: self.ricarica())

        self.albero = ttk.Treeview(self, show="headings")
        barra_sc = ttk.Scrollbar(self, command=self.albero.yview)
        self.albero.configure(yscrollcommand=barra_sc.set)
        self.albero.pack(side="left", fill="both", expand=True)
        barra_sc.pack(side="left", fill="y")
        self.albero.bind("<Double-1>", lambda e: self.modifica())

    def ricarica(self):
        con = self.app.con
        colonne, testi = self.app.colonne_sezione("pratiche")
        self.albero["columns"] = colonne
        for col, testo, larghezza in zip(colonne, testi, self.app.larghezze_sezione("pratiche")):
            self.albero.heading(col, text=testo)
            self.albero.column(col, width=larghezza, minwidth=70, stretch=True)
        for i in self.albero.get_children():
            self.albero.delete(i)
        campi = campi_sezione(con, "pratiche")
        q = ("SELECT p.*, c.cognome, c.nome AS nome_cliente FROM pratiche p"
             " LEFT JOIN clienti c ON c.id=p.cliente_id")
        condizioni, args = [], []
        if self.categoria_filtro.get() != "Tutte":
            condizioni.append("p.categoria=?")
            args.append(self.categoria_filtro.get())
        if self.stato_filtro.get() != "Tutti":
            condizioni.append("p.stato=?")
            args.append(self.stato_filtro.get())
        if condizioni:
            q += " WHERE " + " AND ".join(condizioni)
        q += " ORDER BY p.id DESC"
        filtro = self.cerca.get().strip().lower()
        for p in con.execute(q, args):
            v = valori_record(con, [k["id"] for k in campi], p["id"])
            riga = []
            for col in colonne:
                if col.startswith("fisso_"):
                    riga.append(self._valore(col[6:], p))
                else:
                    riga.append(mostra_valore(v.get(int(col[5:]))))
            if filtro and filtro not in " ".join(map(str, riga)).lower():
                continue
            self.albero.insert("", "end", iid=str(p["id"]), values=riga)

    @staticmethod
    def _valore(chiave, p):
        if chiave == "cliente":
            return " ".join(x for x in (p["cognome"], p["nome_cliente"]) if x)
        if chiave == "data_incarico":
            return formatta_data(p["data_incarico"])
        if chiave == "compenso":
            return euro(p["compenso"])
        return p[chiave] or ""

    def _maschera(self, iniziali=None):
        campi = self.app.campi_form("pratiche")
        elenchi = {"cliente": [lab for _, lab in self.app.etichette_clienti()]}
        return MascheraDialog(self, "Pratica", campi, iniziali, elenchi), campi

    def nuovo(self):
        if not self.app.etichette_clienti():
            messagebox.showinfo("Nessun cliente",
                                "Inserisci prima un cliente nella scheda Clienti.")
            return
        dlg, campi = self._maschera()
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        fissi, custom = separa_custom(campi, dati)
        cliente_id = self.app.id_cliente_da_etichetta(fissi.pop("cliente"))
        if cliente_id is None:
            messagebox.showwarning("Dato non valido", "Seleziona il cliente.")
            return
        self._scrivi(dati=fissi, custom=custom, cliente_id=cliente_id, pratica_id=None)

    def _scrivi(self, dati, custom, cliente_id, pratica_id):
        con = self.app.con
        if not str(dati.get("stato") or "").strip():
            dati["stato"] = "In attesa"
        colonne = TABELLE_DATI["pratiche"]
        valori = [dati.get(k, "") for k in colonne]
        stato = dati.get("stato") or "In attesa"
        if pratica_id is None:
            cur = con.execute(
                f"INSERT INTO pratiche (cliente_id, {','.join(colonne)}, data_apertura)"
                f" VALUES (?, {','.join('?' * len(colonne))}, ?)",
                [cliente_id, *valori, dati.get("data_incarico") or None])
            pratica_id = cur.lastrowid
        else:
            chiusura = "data_chiusura=COALESCE(data_chiusura, ?)" if stato == "Completata" \
                else "data_chiusura=NULL"
            if stato == "Completata":
                con.execute(
                    f"UPDATE pratiche SET cliente_id=?, {','.join(k + '=?' for k in colonne)},"
                    f" data_apertura=?, {chiusura} WHERE id=?",
                    [cliente_id, *valori, dati.get("data_incarico") or None,
                     date.today().isoformat(), pratica_id])
            else:
                con.execute(
                    f"UPDATE pratiche SET cliente_id=?, {','.join(k + '=?' for k in colonne)},"
                    f" data_apertura=?, {chiusura} WHERE id=?",
                    [cliente_id, *valori, dati.get("data_incarico") or None, pratica_id])
        con.execute("UPDATE pratiche SET numero_ordine=? WHERE id=?",
                    (str(pratica_id), pratica_id))
        salva_valori(con, custom, pratica_id)
        con.commit()
        self.app.riempi_tabelle()

    def _id_selezionato(self):
        sel = self.albero.selection()
        if not sel:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima una pratica dalla tabella.")
            return None
        return int(sel[0])

    def modifica(self):
        pratica_id = self._id_selezionato()
        if not pratica_id:
            return
        con = self.app.con
        p = con.execute("SELECT * FROM pratiche WHERE id=?", (pratica_id,)).fetchone()
        cliente = con.execute("SELECT * FROM clienti WHERE id=?", (p["cliente_id"],)).fetchone()
        campi = self.app.campi_form("pratiche")
        v = valori_record(con, [k["id"] for k in campi_sezione(con, "pratiche")], pratica_id)
        iniziali = {k: p[k] for k in p.keys()}
        iniziali["cliente"] = etichetta_cliente(cliente) if cliente else ""
        for k in campi_sezione(con, "pratiche"):
            iniziali[f"campo_{k['id']}"] = v.get(k["id"]) or ""
        elenchi = {"cliente": [lab for _, lab in self.app.etichette_clienti()]}
        dlg = MascheraDialog(self, "Pratica", campi, iniziali, elenchi)
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        fissi, custom = separa_custom(campi, dati)
        cliente_id = self.app.id_cliente_da_etichetta(fissi.pop("cliente"))
        if cliente_id is None:
            messagebox.showwarning("Dato non valido", "Seleziona il cliente.")
            return
        self._scrivi(dati=fissi, custom=custom, cliente_id=cliente_id, pratica_id=pratica_id)

    def elimina(self):
        pratica_id = self._id_selezionato()
        if not pratica_id:
            return
        if not messagebox.askyesno("Conferma", "Eliminare la pratica, i suoi pagamenti e le scadenze collegate?"):
            return
        con = self.app.con
        scadenze = [r["id"] for r in con.execute(
            "SELECT id FROM scadenze WHERE pratica_id=?", (pratica_id,))]
        con.execute("DELETE FROM pratiche WHERE id=?", (pratica_id,))
        con.execute("DELETE FROM scadenze WHERE pratica_id=?", (pratica_id,))
        elimina_valori(con, "pratiche", [pratica_id])
        elimina_valori(con, "scadenze", scadenze)
        con.commit()
        self.app.riempi_tabelle()

    def stampa(self):
        pratica_id = self._id_selezionato()
        if not pratica_id:
            return
        apri_stampa(html_scheda_pratica(self.app.con, pratica_id),
                    f"scheda_pratica_{pratica_id}.html")

    def fattura(self):
        pratica_id = self._id_selezionato()
        if not pratica_id:
            return
        apri_stampa(html_fattura_pro_forma(self.app.con, pratica_id),
                    f"pro_forma_pratica_{pratica_id}.html")


# ---------------------------------------------------------------------------
# Scheda Pagamenti (acconti e saldo)
# ---------------------------------------------------------------------------

CAMPI_PAGAMENTO = [
    {"chiave": "pratica", "etichetta": "Pratica *", "tipo": "pratica", "obbligatorio": True},
    {"chiave": "tipo", "etichetta": "Tipo", "tipo": "lista", "opzioni": TIPI_PAGAMENTO,
     "obbligatorio": True},
    {"chiave": "importo", "etichetta": "Importo (€) *", "tipo": "numero", "obbligatorio": True},
    {"chiave": "data", "etichetta": "Data", "tipo": "data"},
    {"chiave": "fattura_numero", "etichetta": "Fattura n°", "tipo": "testo"},
    {"chiave": "fattura_data", "etichetta": "Fattura del", "tipo": "data"},
]


class SchedaPagamenti(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.notebook)
        self.app = app
        self._costruisci()
        self.ricarica()

    def _costruisci(self):
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill="x")
        ttk.Button(barra, text="Nuovo pagamento", command=self.nuovo).pack(side="left", padx=2)
        ttk.Button(barra, text="Modifica", command=self.modifica).pack(side="left", padx=2)
        ttk.Button(barra, text="Elimina", command=self.elimina).pack(side="left", padx=2)
        self.cerca = tk.StringVar()
        ttk.Label(barra, text="cerca:").pack(side="left", padx=(20, 4))
        ttk.Entry(barra, textvariable=self.cerca, width=22).pack(side="left")
        self.cerca.trace_add("write", lambda *a: self.ricarica())

        self.riepilogo = ttk.Label(self, padding=(10, 6), text="")
        self.riepilogo.pack(side="bottom", fill="x")

        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True)
        colonne = ("pratica", "tipo", "importo", "data", "fattura", "fattura_data")
        testi = ("Pratica", "Tipo", "Importo", "Data", "Fattura n°", "Fattura del")
        larghezze = (330, 140, 130, 130, 130, 130)
        self.albero = ttk.Treeview(corpo, columns=colonne, show="headings")
        for col, testo, larghezza in zip(colonne, testi, larghezze):
            self.albero.heading(col, text=testo)
            self.albero.column(col, width=larghezza, minwidth=90, stretch=True)
        barra_sc = ttk.Scrollbar(corpo, command=self.albero.yview)
        self.albero.configure(yscrollcommand=barra_sc.set)
        self.albero.pack(side="left", fill="both", expand=True)
        barra_sc.pack(side="left", fill="y")
        self.albero.bind("<Double-1>", lambda e: self.modifica())

    def ricarica(self):
        con = self.app.con
        for i in self.albero.get_children():
            self.albero.delete(i)
        filtro = self.cerca.get().strip().lower()
        q = ("SELECT g.*, p.numero_ordine, p.categoria, p.dettaglio, p.compenso,"
             " c.cognome, c.nome"
             " FROM pagamenti g JOIN pratiche p ON p.id=g.pratica_id"
             " LEFT JOIN clienti c ON c.id=p.cliente_id"
             " ORDER BY g.data DESC, g.id DESC")
        tot = 0.0
        for g in con.execute(q):
            pratica = etichetta_pratica(g)
            cliente = " ".join(x for x in (g["cognome"], g["nome"]) if x)
            riga = (f"{pratica} ({cliente})", g["tipo"], euro(g["importo"]),
                    formatta_data(g["data"]), g["fattura_numero"] or "",
                    formatta_data(g["fattura_data"]))
            if filtro and filtro not in " ".join(map(str, riga)).lower():
                continue
            tot += g["importo"] or 0
            self.albero.insert("", "end", iid=str(g["id"]), values=riga)
        compensi = con.execute("SELECT COALESCE(SUM(compenso),0) FROM pratiche").fetchone()[0]
        self.riepilogo.configure(
            text=f"Visualizzati: {len(self.albero.get_children())} pagamenti — "
                 f"totale {euro(tot)}   |   Compensi pattuiti {euro(compensi)} — "
                 f"da incassare {euro(compensi - con.execute('SELECT COALESCE(SUM(importo),0) FROM pagamenti').fetchone()[0])}")

    def _elenchi(self):
        return {"pratica": ["(nessuna)"] + [lab for _, lab in self.app.etichette_pratiche()]}

    def nuovo(self):
        if not self.app.etichette_pratiche():
            messagebox.showinfo("Nessuna pratica", "Inserisci prima una pratica.")
            return
        campi = [dict(c) for c in CAMPI_PAGAMENTO]
        dlg = MascheraDialog(self, "Pagamento", campi, None, self._elenchi())
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        pratica_id = self.app.id_pratica_da_etichetta(dati["pratica"])
        if pratica_id is None:
            messagebox.showwarning("Dato non valido", "Seleziona la pratica.")
            return
        con = self.app.con
        con.execute("INSERT INTO pagamenti (pratica_id, tipo, importo, data, fattura_numero,"
                    " fattura_data) VALUES (?,?,?,?,?,?)",
                    (pratica_id, dati["tipo"], dati["importo"], dati["data"] or None,
                     dati["fattura_numero"], dati["fattura_data"] or None))
        con.commit()
        self.ricarica()

    def _id_selezionato(self):
        sel = self.albero.selection()
        if not sel:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima un pagamento.")
            return None
        return int(sel[0])

    def _iniziali(self, pagamento_id):
        con = self.app.con
        g = con.execute("SELECT * FROM pagamenti WHERE id=?", (pagamento_id,)).fetchone()
        p = con.execute("SELECT * FROM pratiche WHERE id=?", (g["pratica_id"],)).fetchone()
        return {"pratica": etichetta_pratica(p) if p else "(nessuna)", "tipo": g["tipo"],
                "importo": f"{g['importo']:.2f}".replace(".", ","), "data": formatta_data(g["data"]),
                "fattura_numero": g["fattura_numero"] or "",
                "fattura_data": formatta_data(g["fattura_data"])}

    def modifica(self):
        pagamento_id = self._id_selezionato()
        if not pagamento_id:
            return
        campi = [dict(c) for c in CAMPI_PAGAMENTO]
        dlg = MascheraDialog(self, "Pagamento", campi, self._iniziali(pagamento_id),
                             self._elenchi())
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        pratica_id = self.app.id_pratica_da_etichetta(dati["pratica"])
        if pratica_id is None:
            messagebox.showwarning("Dato non valido", "Seleziona la pratica.")
            return
        con = self.app.con
        con.execute("UPDATE pagamenti SET pratica_id=?, tipo=?, importo=?, data=?,"
                    " fattura_numero=?, fattura_data=? WHERE id=?",
                    (pratica_id, dati["tipo"], dati["importo"], dati["data"] or None,
                     dati["fattura_numero"], dati["fattura_data"] or None, pagamento_id))
        con.commit()
        self.ricarica()

    def elimina(self):
        pagamento_id = self._id_selezionato()
        if not pagamento_id:
            return
        if not messagebox.askyesno("Conferma", "Eliminare il pagamento?"):
            return
        con = self.app.con
        con.execute("DELETE FROM pagamenti WHERE id=?", (pagamento_id,))
        con.commit()
        self.ricarica()


# ---------------------------------------------------------------------------
# Scheda Scadenze
# ---------------------------------------------------------------------------

class SchedaScadenze(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.notebook)
        self.app = app
        self._costruisci()
        self.ricarica()

    def _costruisci(self):
        barra = ttk.Frame(self, padding=6)
        barra.pack(fill="x")
        ttk.Button(barra, text="Nuova scadenza", command=self.nuovo).pack(side="left", padx=2)
        ttk.Button(barra, text="Modifica", command=self.modifica).pack(side="left", padx=2)
        ttk.Button(barra, text="Segna completata", command=self.completa).pack(side="left", padx=2)
        ttk.Button(barra, text="Elimina", command=self.elimina).pack(side="left", padx=2)
        self.solo_aperte = tk.BooleanVar(value=True)
        ttk.Checkbutton(barra, text="solo aperte", variable=self.solo_aperte,
                        style="Toolbutton",
                        command=self.ricarica).pack(side="left", padx=(20, 0))

        self.albero = ttk.Treeview(self, show="headings")
        barra_sc = ttk.Scrollbar(self, command=self.albero.yview)
        self.albero.configure(yscrollcommand=barra_sc.set)
        self.albero.pack(side="left", fill="both", expand=True)
        barra_sc.pack(side="left", fill="y")
        self.albero.tag_configure("scaduta", background=SCADUTA_BG,
                                  foreground=SCADUTA_FG)
        self.albero.bind("<Double-1>", lambda e: self.modifica())

    def ricarica(self):
        con = self.app.con
        colonne, testi = self.app.colonne_sezione("scadenze")
        self.albero["columns"] = colonne
        for col, testo, larghezza in zip(colonne, testi, self.app.larghezze_sezione("scadenze")):
            self.albero.heading(col, text=testo)
            self.albero.column(col, width=larghezza, minwidth=70, stretch=True)
        for i in self.albero.get_children():
            self.albero.delete(i)
        campi = campi_sezione(con, "scadenze")
        q = ("SELECT s.*, p.numero_ordine, p.categoria, p.dettaglio, c.cognome, c.nome"
             " FROM scadenze s"
             " LEFT JOIN pratiche p ON p.id=s.pratica_id"
             " LEFT JOIN clienti c ON c.id=p.cliente_id")
        if self.solo_aperte.get():
            q += " WHERE s.completata=0"
        q += " ORDER BY s.data_scadenza, s.id"
        oggi = date.today().isoformat()
        for s in con.execute(q):
            v = valori_record(con, [k["id"] for k in campi], s["id"])
            pratica = ""
            if s["pratica_id"]:
                pratica = " ".join(x for x in (etichetta_pratica(s),
                                               " ".join(y for y in (s["cognome"], s["nome"]) if y))
                                   if x)
            riga, scaduta = [], False
            for col in colonne:
                if col.startswith("fisso_"):
                    chiave = col[6:]
                    if chiave == "data_scadenza":
                        riga.append(formatta_data(s["data_scadenza"]))
                        scaduta = s["data_scadenza"] <= oggi and not s["completata"]
                    elif chiave == "completata":
                        riga.append("Sì" if s["completata"] else "No")
                    elif chiave == "pratica":
                        riga.append(pratica)
                    else:
                        riga.append(s[chiave] or "")
                else:
                    riga.append(mostra_valore(v.get(int(col[5:]))))
            self.albero.insert("", "end", iid=str(s["id"]), values=riga,
                               tags=("scaduta",) if scaduta else ())

    def _maschera(self, iniziali=None):
        campi = self.app.campi_form("scadenze")
        elenchi = {"pratica": ["(nessuna)"] + [lab for _, lab in self.app.etichette_pratiche()]}
        return MascheraDialog(self, "Scadenza", campi, iniziali, elenchi), campi

    def nuovo(self):
        dlg, campi = self._maschera()
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        fissi, custom = separa_custom(campi, dati)
        self._scrivi(fissi, custom, None)

    def _scrivi(self, fissi, custom, scadenza_id):
        con = self.app.con
        pratica_id = self.app.id_pratica_da_etichetta(fissi.pop("pratica"))
        valori = (fissi["descrizione"], fissi["data_scadenza"], pratica_id,
                  int(fissi.get("completata") or 0))
        if scadenza_id is None:
            cur = con.execute("INSERT INTO scadenze (descrizione, data_scadenza, pratica_id,"
                              " completata) VALUES (?,?,?,?)", valori)
            scadenza_id = cur.lastrowid
        else:
            con.execute("UPDATE scadenze SET descrizione=?, data_scadenza=?, pratica_id=?,"
                        " completata=? WHERE id=?", (*valori, scadenza_id))
        salva_valori(con, custom, scadenza_id)
        con.commit()
        self.ricarica()

    def _id_selezionato(self):
        sel = self.albero.selection()
        if not sel:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima una scadenza dalla tabella.")
            return None
        return int(sel[0])

    def modifica(self):
        scadenza_id = self._id_selezionato()
        if not scadenza_id:
            return
        con = self.app.con
        s = con.execute("SELECT * FROM scadenze WHERE id=?", (scadenza_id,)).fetchone()
        campi = self.app.campi_form("scadenze")
        v = valori_record(con, [k["id"] for k in campi_sezione(con, "scadenze")], scadenza_id)
        iniziali = {k: s[k] for k in s.keys()}
        iniziali["pratica"] = "(nessuna)"
        if s["pratica_id"]:
            p = con.execute("SELECT * FROM pratiche WHERE id=?", (s["pratica_id"],)).fetchone()
            if p:
                iniziali["pratica"] = etichetta_pratica(p)
        for k in campi_sezione(con, "scadenze"):
            iniziali[f"campo_{k['id']}"] = v.get(k["id"]) or ""
        elenchi = {"pratica": ["(nessuna)"] + [lab for _, lab in self.app.etichette_pratiche()]}
        dlg = MascheraDialog(self, "Scadenza", campi, iniziali, elenchi)
        if not dlg.result:
            return
        dati, errore = normalizza_dati(campi, dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return
        fissi, custom = separa_custom(campi, dati)
        self._scrivi(fissi, custom, scadenza_id)

    def completa(self):
        scadenza_id = self._id_selezionato()
        if not scadenza_id:
            return
        con = self.app.con
        con.execute("UPDATE scadenze SET completata=1 WHERE id=?", (scadenza_id,))
        con.commit()
        self.ricarica()

    def elimina(self):
        scadenza_id = self._id_selezionato()
        if not scadenza_id:
            return
        if not messagebox.askyesno("Conferma", "Eliminare la scadenza?"):
            return
        con = self.app.con
        con.execute("DELETE FROM scadenze WHERE id=?", (scadenza_id,))
        elimina_valori(con, "scadenze", [scadenza_id])
        con.commit()
        self.ricarica()


# ---------------------------------------------------------------------------
# Scheda Impostazioni (campi personalizzati e dati dello studio)
# ---------------------------------------------------------------------------

class SchedaImpostazioni(ttk.Frame):
    def __init__(self, app):
        super().__init__(app.notebook)
        self.app = app
        self.sezione = tk.StringVar(value=SEZIONI_ETICHETTE["clienti"])

        alto = ttk.Frame(self, padding=6)
        alto.pack(fill="x")
        ttk.Label(alto, text="Sezione:").pack(side="left")
        ttk.Combobox(alto, textvariable=self.sezione, width=12, state="readonly",
                     values=[SEZIONI_ETICHETTE[s] for s in SEZIONI]).pack(side="left", padx=6)
        ttk.Button(alto, text="Dati studio…", command=self.dati_studio).pack(side="right")
        self.sezione.trace_add("write", lambda *a: self.ricarica())

        corpo = ttk.Frame(self)
        corpo.pack(fill="both", expand=True)

        self.albero = ttk.Treeview(corpo, columns=("ord", "nome", "tipo", "attivo"),
                                   show="headings", height=12)
        for col, testo, w in (("ord", "#", 40), ("nome", "Nome campo", 240),
                              ("tipo", "Tipo", 100), ("attivo", "Attivo", 70)):
            self.albero.heading(col, text=testo)
            self.albero.column(col, width=w)
        self.albero.pack(side="left", fill="both", expand=True, padx=(6, 0))

        barra = ttk.Frame(corpo, padding=6)
        barra.pack(side="left", fill="y")
        ttk.Button(barra, text="Aggiungi campo", command=self.aggiungi).pack(fill="x", pady=2)
        ttk.Button(barra, text="Modifica campo", command=self.modifica).pack(fill="x", pady=2)
        ttk.Button(barra, text="Attiva / Disattiva", command=self.inverti).pack(fill="x", pady=2)
        ttk.Button(barra, text="Elimina campo", command=self.elimina).pack(fill="x", pady=2)
        ttk.Button(barra, text="Sposta su", command=lambda: self.sposta(-1)).pack(fill="x", pady=2)
        ttk.Button(barra, text="Sposta giù", command=lambda: self.sposta(1)).pack(fill="x", pady=2)
        ttk.Separator(barra).pack(fill="x", pady=8)
        ttk.Label(barra, justify="left",
                  text="I campi fissi seguono\nla scheda di studio.\nQui aggiungi quelli\n"
                       "extra: tabelle e\nmaschere si aggiornano\nda sole.").pack()

        self.ricarica()

    def _sezione_corrente(self):
        return [k for k, v in SEZIONI_ETICHETTE.items() if v == self.sezione.get()][0]

    def ricarica(self):
        con = self.app.con
        for i in self.albero.get_children():
            self.albero.delete(i)
        for n, k in enumerate(con.execute(
                "SELECT * FROM campi WHERE sezione=? ORDER BY ordine, id",
                (self._sezione_corrente(),)).fetchall(), 1):
            self.albero.insert("", "end", iid=str(k["id"]),
                               values=(n, k["nome"], k["tipo"], "Sì" if k["attivo"] else "No"))

    def dati_studio(self):
        studio = dati_studio(self.app.con)
        campi = [{"chiave": k, "etichetta": et, "tipo": "testo"} for k, et in DATI_STUDIO]
        dlg = MascheraDialog(self, "Dati studio", campi, studio)
        if not dlg.result:
            return
        salva_dati_studio(self.app.con, dlg.result)
        self.app.con.commit()
        messagebox.showinfo("Dati studio", "Dati salvati: saranno usati nelle stampe.")

    def _chiedi_campo(self, titolo, iniziali=None):
        dlg = MascheraDialog(self, titolo, [
            {"chiave": "nome", "etichetta": "Nome campo *", "tipo": "testo", "obbligatorio": True},
            {"chiave": "tipo", "etichetta": "Tipo", "tipo": "lista", "opzioni": TIPI_CAMPO,
             "obbligatorio": True},
            {"chiave": "opzioni", "etichetta": "Opzioni (solo 'lista', separate da ;)",
             "tipo": "testo"},
            {"chiave": "attivo", "etichetta": "Attivo", "tipo": "si_no"},
        ], iniziali or {"tipo": "testo", "attivo": 1})
        if not dlg.result:
            return None
        dati, errore = normalizza_dati([
            {"chiave": "nome", "etichetta": "Nome campo *", "tipo": "testo", "obbligatorio": True},
            {"chiave": "tipo", "etichetta": "Tipo", "tipo": "lista", "obbligatorio": True},
        ], dlg.result)
        if errore:
            messagebox.showwarning("Dato non valido", errore)
            return None
        if dati["tipo"] == "lista" and not dlg.result["opzioni"].strip():
            messagebox.showwarning("Dato mancante",
                                   "Per un campo 'lista' servono le opzioni separate da ';'.")
            return None
        return {"nome": dati["nome"], "tipo": dati["tipo"],
                "opzioni": dlg.result["opzioni"].strip(), "attivo": dlg.result["attivo"]}

    def aggiungi(self):
        sezione = self._sezione_corrente()
        campo = self._chiedi_campo("Nuovo campo")
        if not campo:
            return
        con = self.app.con
        ordine = con.execute("SELECT COALESCE(MAX(ordine), -1) + 1 FROM campi WHERE sezione=?",
                             (sezione,)).fetchone()[0]
        try:
            con.execute("INSERT INTO campi (sezione, nome, tipo, opzioni, ordine, attivo)"
                        " VALUES (?,?,?,?,?,?)",
                        (sezione, campo["nome"], campo["tipo"], campo["opzioni"], ordine,
                         campo["attivo"]))
            con.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicato", "Esiste già un campo con questo nome in questa sezione.")
            return
        self.ricarica()
        self.app.riempi_tabelle()

    def _campo_selezionato(self):
        sel = self.albero.selection()
        if not sel:
            messagebox.showinfo("Nessuna selezione", "Seleziona prima un campo.")
            return None
        return int(sel[0])

    def modifica(self):
        campo_id = self._campo_selezionato()
        if not campo_id:
            return
        con = self.app.con
        k = con.execute("SELECT * FROM campi WHERE id=?", (campo_id,)).fetchone()
        campo = self._chiedi_campo("Modifica campo", {
            "nome": k["nome"], "tipo": k["tipo"], "opzioni": k["opzioni"], "attivo": k["attivo"]})
        if not campo:
            return
        try:
            con.execute("UPDATE campi SET nome=?, tipo=?, opzioni=?, attivo=? WHERE id=?",
                        (campo["nome"], campo["tipo"], campo["opzioni"], campo["attivo"], campo_id))
            con.commit()
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicato", "Esiste già un campo con questo nome in questa sezione.")
            return
        self.ricarica()
        self.app.riempi_tabelle()

    def inverti(self):
        campo_id = self._campo_selezionato()
        if not campo_id:
            return
        con = self.app.con
        con.execute("UPDATE campi SET attivo = 1 - attivo WHERE id=?", (campo_id,))
        con.commit()
        self.ricarica()
        self.app.riempi_tabelle()

    def elimina(self):
        campo_id = self._campo_selezionato()
        if not campo_id:
            return
        if not messagebox.askyesno("Conferma",
                                   "Eliminare il campo e i suoi valori nei record già inseriti?"):
            return
        con = self.app.con
        con.execute("DELETE FROM campi WHERE id=?", (campo_id,))
        con.commit()
        self.ricarica()
        self.app.riempi_tabelle()

    def sposta(self, direzione):
        campo_id = self._campo_selezionato()
        if not campo_id:
            return
        con = self.app.con
        posizioni = [r["id"] for r in con.execute(
            "SELECT id FROM campi WHERE sezione=? ORDER BY ordine, id",
            (self._sezione_corrente(),))]
        i = posizioni.index(campo_id)
        j = i + direzione
        if not 0 <= j < len(posizioni):
            return
        posizioni[i], posizioni[j] = posizioni[j], posizioni[i]
        for ordine, cid in enumerate(posizioni):
            con.execute("UPDATE campi SET ordine=? WHERE id=?", (ordine, cid))
        con.commit()
        self.ricarica()
        self.app.riempi_tabelle()


# ---------------------------------------------------------------------------
# Stampe (schede e fattura pro forma)
# ---------------------------------------------------------------------------

STILE_STAMPA = """
  body { font-family: "Helvetica Neue", Arial, sans-serif; color: #222; margin: 32px; }
  h1 { font-size: 20px; margin: 0 0 4px; }
  h2 { font-size: 15px; margin: 26px 0 8px; border-bottom: 1px solid #bbb; padding-bottom: 4px; }
  .studio { color: #555; font-size: 13px; margin-bottom: 18px; white-space: pre-line; }
  table { border-collapse: collapse; width: 100%; font-size: 13px; }
  th, td { text-align: left; padding: 6px 8px; border-bottom: 1px solid #e3e3e3;
           vertical-align: top; }
  th { width: 34%; color: #555; font-weight: 600; }
  .num { text-align: right; white-space: nowrap; }
  tfoot td { font-weight: 600; border-top: 1px solid #999; }
  .nota { margin-top: 22px; font-size: 12px; color: #666; }
  @media print { body { margin: 12mm; } }
"""


def _documento(titolo, corpo):
    return (f"<!DOCTYPE html><html lang=\"it\"><head>"
            f"<meta charset=\"utf-8\"><meta http-equiv=\"Content-Type\" "
            f"content=\"text/html; charset=utf-8\">"
            f"<title>{html.escape(titolo)}</title><style>{STILE_STAMPA}</style></head>"
            f"<body>{corpo}</body></html>")


def _intestazione_studio(con, titolo):
    studio = dati_studio(con)
    riga = "<br>".join(html.escape(x) for x in (
        studio.get("indirizzo", ""),
        " · ".join(x for x in (studio.get("piva", ""), studio.get("telefono", ""),
                               studio.get("email", "")) if x)) if x)
    return (f"<h1>{html.escape(titolo)}</h1>"
            f"<div class=\"studio\">{html.escape(studio.get('nome') or '')}<br>{riga}</div>")


def _tabella_dati(coppie):
    righe = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{html.escape(str(v or ''))}</td></tr>"
                    for k, v in coppie)
    return f"<table>{righe}</table>"


def _cliente_row(con, cliente_id):
    return con.execute("SELECT * FROM clienti WHERE id=?", (cliente_id,)).fetchone()


def _campi_cliente(c):
    return [
        ("Cognome / Ragione sociale", c["cognome"]),
        ("Nome", c["nome"]),
        ("Nato/a il", formatta_data(c["nato_il"])),
        ("Nato/a a", " ".join(x for x in (c["nato_a"], f"({c['provincia']})" if c["provincia"] else "") if x)),
        ("Codice fiscale / P.IVA", c["codice_fiscale"]),
        ("Indirizzo residenza", c["indirizzo_residenza"]),
        ("Indirizzo immobile", c["indirizzo_immobile"]),
        ("Città immobile", c["citta_immobile"]),
        ("Telefono", c["telefono"]),
        ("Email", c["email"]),
        ("Note", c["note"]),
    ]


def html_scheda_cliente(con, cliente_id):
    c = _cliente_row(con, cliente_id)
    corpo = _intestazione_studio(con, "Scheda cliente")
    corpo += _tabella_dati(_campi_cliente(c))
    pratiche = con.execute("SELECT * FROM pratiche WHERE cliente_id=? ORDER BY id DESC",
                           (cliente_id,)).fetchall()
    corpo += "<h2>Pratiche</h2>"
    if pratiche:
        righe = ""
        for p in pratiche:
            righe += ("<tr>"
                      f"<td>{html.escape(p['numero_ordine'] or '#%d' % p['id'])}</td>"
                      f"<td>{html.escape(etichetta_pratica(p))}</td>"
                      f"<td>{html.escape(p['stato'] or '')}</td>"
                      f"<td>{html.escape(formatta_data(p['data_incarico']))}</td>"
                      f"<td class=\"num\">{html.escape(euro(p['compenso']))}</td></tr>")
        corpo += ("<table><thead><tr><th>N°</th><th>Pratica</th><th>Stato</th><th>Incarico</th>"
                  "<th class=\"num\">Compenso</th></tr></thead>"
                  f"<tbody>{righe}</tbody></table>")
    else:
        corpo += "<p>Nessuna pratica registrata.</p>"
    corpo += "<p class=\"nota\">Documento generato dal gestionale dello studio.</p>"
    return _documento("Scheda cliente", corpo)


def html_scheda_pratica(con, pratica_id):
    p = con.execute("SELECT * FROM pratiche WHERE id=?", (pratica_id,)).fetchone()
    c = _cliente_row(con, p["cliente_id"]) if p["cliente_id"] else None
    corpo = _intestazione_studio(con, "Scheda pratica")
    corpo += _tabella_dati([
        ("Numero d'ordine / pratica", p["numero_ordine"]),
        ("Incarico", p["incarico"]),
        ("Data incarico", formatta_data(p["data_incarico"])),
        ("Tipologia pratica", p["categoria"]),
        ("Dettaglio", p["dettaglio"]),
        ("Titolo abilitativo", p["titolo"]),
        ("Tipologia immobile", p["tipologia_immobile"]),
        ("In qualità di", p["in_qualita_di"]),
        ("Stato", p["stato"]),
        ("Oggetto / note", p["oggetto"]),
        ("Compenso pattuito", euro(p["compenso"])),
    ])
    if c:
        corpo += "<h2>Cliente</h2>" + _tabella_dati(_campi_cliente(c))
    scadenze = con.execute("SELECT * FROM scadenze WHERE pratica_id=? ORDER BY data_scadenza",
                           (pratica_id,)).fetchall()
    if scadenze:
        corpo += "<h2>Scadenze</h2>" + _tabella_dati([
            (formatta_data(s["data_scadenza"]),
             f"{s['descrizione']} — {'completata' if s['completata'] else 'aperta'}")
            for s in scadenze])
    corpo += "<p class=\"nota\">Documento generato dal gestionale dello studio.</p>"
    return _documento("Scheda pratica", corpo)


def html_fattura_pro_forma(con, pratica_id):
    p = con.execute("SELECT * FROM pratiche WHERE id=?", (pratica_id,)).fetchone()
    c = _cliente_row(con, p["cliente_id"]) if p["cliente_id"] else None
    pagamenti = con.execute("SELECT * FROM pagamenti WHERE pratica_id=? ORDER BY data, id",
                            (pratica_id,)).fetchall()
    pagato = sum(g["importo"] or 0 for g in pagamenti)
    saldo = (p["compenso"] or 0) - pagato
    corpo = _intestazione_studio(con, "Fattura pro forma")
    corpo += (f"<p><strong>Numero pratica:</strong> {html.escape(p['numero_ordine'] or '#%d' % p['id'])}"
              f" &nbsp; <strong>Data:</strong> {html.escape(date.today().strftime('%d/%m/%Y'))}</p>")
    if c:
        corpo += "<h2>Cliente</h2>" + _tabella_dati(_campi_cliente(c)[:7])
    descrizione = " ".join(x for x in ("Prestazione professionale", p["categoria"], p["dettaglio"]) if x)
    if p["oggetto"]:
        descrizione += f" — {p['oggetto']}"
    corpo += ("<h2>Prestazione</h2><table><thead><tr><th>Descrizione</th>"
              "<th class=\"num\">Importo</th></tr></thead><tbody>"
              f"<tr><td>{html.escape(descrizione)}</td>"
              f"<td class=\"num\">{html.escape(euro(p['compenso']))}</td></tr></tbody></table>")
    corpo += "<h2>Acconti e saldo</h2>"
    if pagamenti:
        righe = ""
        for g in pagamenti:
            riferimento = " ".join(x for x in (
                g["fattura_numero"] and f"fattura n° {g['fattura_numero']}",
                g["fattura_data"] and f"del {formatta_data(g['fattura_data'])}") if x)
            righe += (f"<tr><td>{html.escape(g['tipo'])}</td>"
                      f"<td>{html.escape(formatta_data(g['data']))}</td>"
                      f"<td>{html.escape(riferimento)}</td>"
                      f"<td class=\"num\">{html.escape(euro(g['importo']))}</td></tr>")
        corpo += ("<table><thead><tr><th>Tipo</th><th>Data</th><th>Riferimento</th>"
                  "<th class=\"num\">Importo</th></tr></thead>"
                  f"<tbody>{righe}</tbody></table>")
    else:
        corpo += "<p>Nessun acconto registrato.</p>"
    corpo += ("<h2>Totali</h2>" + _tabella_dati([
        ("Compenso pattuito", euro(p["compenso"])),
        ("Totale acconti versati", euro(pagato)),
        ("Saldo da versare", euro(saldo)),
    ]))
    corpo += ("<p class=\"nota\">Documento pro forma, non valido ai fini fiscali. "
              "Generato dal gestionale dello studio.</p>")
    return _documento("Fattura pro forma", corpo)


def apri_stampa(contenuto, nome_file):
    """Salva il documento e lo apre nel browser (da lì si stampa o si salva in PDF)."""
    cartella = tempfile.mkdtemp(prefix="gestione_studio_")
    percorso = os.path.join(cartella, nome_file)
    scrivi_testo(percorso, contenuto)
    if not webbrowser.open(url_file(percorso)):
        percorso = filedialog.asksaveasfilename(
            title="Salva il documento", defaultextension=".html",
            initialfile=nome_file, filetypes=[("Pagina HTML", "*.html")])
        if percorso:
            scrivi_testo(percorso, contenuto)
            messagebox.showinfo("Documento salvato", percorso)


# ---------------------------------------------------------------------------
# Applicazione principale
# ---------------------------------------------------------------------------

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestione Studio Geometra")
        self.geometry("1180x660")
        applica_tema(self)
        inizializza_db()
        self.con = connetti()

        barra = ttk.Frame(self, padding=4)
        barra.pack(fill="x")
        ttk.Button(barra, text="Ricarica tabelle",
                   command=self.riempi_tabelle).pack(side="left")
        ttk.Button(barra, text="Esci", command=self._chiudi).pack(side="right")

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True)
        self.schede = {
            "clienti": SchedaClienti(self),
            "pratiche": SchedaPratiche(self),
            "pagamenti": SchedaPagamenti(self),
            "scadenze": SchedaScadenze(self),
            "impostazioni": SchedaImpostazioni(self),
        }
        for testo, chiave in (("Clienti", "clienti"), ("Pratiche", "pratiche"),
                              ("Pagamenti", "pagamenti"), ("Scadenze", "scadenze"),
                              ("Impostazioni campi", "impostazioni")):
            self.notebook.add(self.schede[chiave], text=testo)
        self.notebook.bind("<<NotebookTabChanged>>", self._cambio_scheda)
        self.protocol("WM_DELETE_WINDOW", self._chiudi)

    def _cambio_scheda(self, _evento=None):
        scheda = self.notebook.select()
        for s in self.schede.values():
            if str(s) == scheda and hasattr(s, "ricarica"):
                s.ricarica()

    # -- campi -------------------------------------------------------------

    def campi_form(self, sezione):
        """Campi fissi della sezione + campi personalizzati attivi."""
        campi = [dict(c) for c in CAMPI_FISSI[sezione] if not c.get("automatico")]
        for k in campi_sezione(self.con, sezione):
            opzioni = ([o.strip() for o in k["opzioni"].split(";") if o.strip()]
                       if k["tipo"] == "lista" else [])
            campi.append({"chiave": f"campo_{k['id']}", "etichetta": k["nome"],
                          "tipo": k["tipo"], "opzioni": opzioni, "custom": k["id"]})
        return campi

    def colonne_sezione(self, sezione):
        colonne, testi = [], []
        for campo in CAMPI_FISSI[sezione]:
            if campo.get("tabella"):
                colonne.append("fisso_" + campo["chiave"])
                testi.append(campo.get("colonna") or campo["etichetta"].rstrip(" *"))
        for k in campi_sezione(self.con, sezione):
            colonne.append(f"campo{k['id']}")
            testi.append(k["nome"])
        return colonne, testi

    def larghezze_sezione(self, sezione):
        larghezze = []
        for campo in CAMPI_FISSI[sezione]:
            if campo.get("tabella"):
                testo = campo.get("colonna") or campo["etichetta"].rstrip(" *")
                larghezze.append(campo.get("larghezza_tabella")
                                 or self.larghezza_colonna(testo))
        for k in campi_sezione(self.con, sezione):
            larghezze.append(self.larghezza_colonna(k["nome"]))
        return larghezze

    @staticmethod
    def larghezza_colonna(testo):
        """Larghezza che contiene l'intestazione senza tagliarla."""
        return max(100, min(230, 8 * len(str(testo)) + 24))

    # -- elenchi per le maschere -------------------------------------------

    def etichette_clienti(self):
        return [(c["id"], etichetta_cliente(c)) for c in self.con.execute(
            "SELECT * FROM clienti ORDER BY cognome, nome")]

    def etichette_pratiche(self):
        return [(p["id"], etichetta_pratica(p)) for p in self.con.execute(
            "SELECT * FROM pratiche ORDER BY id DESC")]

    def id_cliente_da_etichetta(self, etichetta):
        return next((cid for cid, lab in self.etichette_clienti() if lab == etichetta), None)

    def id_pratica_da_etichetta(self, etichetta):
        if not etichetta or etichetta == "(nessuna)":
            return None
        return next((pid for pid, lab in self.etichette_pratiche() if lab == etichetta), None)

    # -- aggiornamenti -----------------------------------------------------

    def riempi_tabelle(self):
        for chiave in ("clienti", "pratiche", "pagamenti", "scadenze"):
            self.schede[chiave].ricarica()

    def _chiudi(self):
        self.con.close()
        self.destroy()


def main():
    app = App()
    app.mainloop()


if __name__ == "__main__":
    main()
