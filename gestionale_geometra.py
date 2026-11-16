import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
from datetime import datetime, date, timedelta
from tk_date_entry import DateEntry
import os
import subprocess
import re
import tempfile
import webbrowser
import sys

class GestionaleGeometra:
    def __init__(self, root):
        self.root = root
        self.root.title("Studio Geometra - Gestione Studio")
        self.root.geometry("1300x920") 
        
        # --- FIX FONT PER WINDOWS E MAC ---
        self.FONT_BASE = "Segoe UI" if sys.platform == "win32" else "Helvetica"
        
        # Colori del tema scuro
        self.COLORE_SFONDO = "#2b2b2b"
        self.COLORE_TESTO = "#ffffff"
        self.COLORE_CAMPI = "#3c3f41"
        
        self.root.configure(bg=self.COLORE_SFONDO)
        
        self.imposta_tema_scuro()
        
        # Variabili di stato
        self.id_pratica_selezionata = None
        self.id_cliente_selezionato = None
        self.cliente_corrente = ""
        self.mappa_clienti = {}
        self.mappa_stampe = {}
        
        # --- FIX PERCORSO DATABASE ---
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        else:
            application_path = os.path.dirname(os.path.abspath(__file__))
            
        db_path = os.path.join(application_path, 'studio_geometra.db')
        
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row 
        self.cursor = self.conn.cursor()
        
        self.crea_tabelle()
        self.migrazione_database() 
        
        self.crea_interfaccia()
        
        # Carica i dati iniziali
        self.carica_pratiche()
        self.carica_clienti_tendina()
        self.carica_tabella_clienti()
        self.carica_tendina_stampe()
        
        self.root.after(500, self.avviso_scadenze)

    def imposta_tema_scuro(self):
        stile = ttk.Style()
        stile.theme_use('clam')
        
        stile.configure("TEntry", fieldbackground=self.COLORE_CAMPI, foreground=self.COLORE_TESTO, insertcolor=self.COLORE_TESTO, font=(self.FONT_BASE, 10))
        stile.configure("TCombobox", fieldbackground=self.COLORE_CAMPI, foreground=self.COLORE_TESTO, selectbackground=self.COLORE_CAMPI, selectforeground=self.COLORE_TESTO, font=(self.FONT_BASE, 10))
        
        stile.configure("Treeview", background=self.COLORE_CAMPI, foreground=self.COLORE_TESTO, fieldbackground=self.COLORE_CAMPI, rowheight=25, font=(self.FONT_BASE, 10))
        stile.map("Treeview", background=[('selected', '#1565C0')]) 
        
        stile.configure("Treeview.Heading", background=self.COLORE_SFONDO, foreground=self.COLORE_TESTO, font=(self.FONT_BASE, 10, 'bold'))
        stile.map("Treeview.Heading", background=[('active', '#444444')])
        
        stile.configure("TNotebook", background=self.COLORE_SFONDO, borderwidth=0)
        stile.configure("TNotebook.Tab", background="#444444", foreground="white", padding=[15, 5], font=(self.FONT_BASE, 10, 'bold'))
        stile.map("TNotebook.Tab", background=[("selected", self.COLORE_CAMPI)], foreground=[("selected", "white")])

    def crea_tabelle(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS clienti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                cognome TEXT,
                nato_a TEXT,
                prov TEXT,
                cf_piva TEXT,
                ind_residenza TEXT,
                ind_immobile TEXT
            )
        ''')
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS pratiche (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                cliente_id INTEGER,
                in_qualita_di TEXT,
                tipologia_immobile TEXT,
                tipologia_pratica TEXT,
                tipo TEXT,
                tipo_dettaglio TEXT,
                stato TEXT,
                data_ingresso TEXT,
                data_apertura TEXT,
                scadenza TEXT,
                acc1_importo TEXT, acc1_data TEXT, acc1_fattura TEXT, acc1_data_fattura TEXT,
                acc2_importo TEXT, acc2_data TEXT, acc2_fattura TEXT, acc2_data_fattura TEXT,
                acc3_importo TEXT, acc3_data TEXT, acc3_fattura TEXT, acc3_data_fattura TEXT,
                saldo_importo TEXT, saldo_data TEXT, saldo_fattura TEXT, saldo_data_fattura TEXT,
                FOREIGN KEY(cliente_id) REFERENCES clienti(id)
            )
        ''')
        self.conn.commit()

    def migrazione_database(self):
        self.cursor.execute("PRAGMA table_info(clienti)")
        colonne_clienti = [info[1] for info in self.cursor.fetchall()]
        nuove_colonne_clienti = ['cognome', 'nato_a', 'prov', 'ind_residenza', 'ind_immobile']
        for col in nuove_colonne_clienti:
            if col not in colonne_clienti:
                self.cursor.execute(f"ALTER TABLE clienti ADD COLUMN {col} TEXT")
        
        self.cursor.execute("PRAGMA table_info(pratiche)")
        colonne_pratiche = [info[1] for info in self.cursor.fetchall()]
        
        if 'data_ingresso' not in colonne_pratiche:
            self.cursor.execute("ALTER TABLE pratiche ADD COLUMN data_ingresso TEXT")

        colonne_base = ['in_qualita_di', 'tipologia_immobile', 'tipologia_pratica', 'tipo_dettaglio']
        for col in colonne_base:
            if col not in colonne_pratiche:
                self.cursor.execute(f"ALTER TABLE pratiche ADD COLUMN {col} TEXT")
        
        colonne_pagamenti = [
            'acc1_importo', 'acc1_data', 'acc1_fattura', 'acc1_data_fattura',
            'acc2_importo', 'acc2_data', 'acc2_fattura', 'acc2_data_fattura',
            'acc3_importo', 'acc3_data', 'acc3_fattura', 'acc3_data_fattura',
            'saldo_importo', 'saldo_data', 'saldo_fattura', 'saldo_data_fattura'
        ]
        for col in colonne_pagamenti:
            if col not in colonne_pratiche:
                self.cursor.execute(f"ALTER TABLE pratiche ADD COLUMN {col} TEXT")
                
        self.conn.commit()

    def crea_pulsante(self, parent, testo, comando, colore_bg, colore_hover):
        lbl = tk.Label(parent, text=testo, bg=colore_bg, fg="white", 
                       font=(self.FONT_BASE, 10, 'bold'), padx=15, pady=8, cursor="hand2")
        lbl.bind("<Button-1>", lambda e: comando())
        lbl.bind("<Enter>", lambda e: lbl.config(bg=colore_hover))
        lbl.bind("<Leave>", lambda e: lbl.config(bg=colore_bg))
        return lbl

    def crea_interfaccia(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.tab_pratiche = tk.Frame(self.notebook, bg=self.COLORE_SFONDO)
        self.notebook.add(self.tab_pratiche, text="Gestione Pratiche")
        self.crea_interfaccia_pratiche(self.tab_pratiche)

        self.tab_clienti = tk.Frame(self.notebook, bg=self.COLORE_SFONDO)
        self.notebook.add(self.tab_clienti, text="Anagrafica Clienti")
        self.crea_interfaccia_clienti(self.tab_clienti)
        
        self.tab_stampe = tk.Frame(self.notebook, bg=self.COLORE_SFONDO)
        self.notebook.add(self.tab_stampe, text="Stampe e Fatture")
        self.crea_interfaccia_stampe(self.tab_stampe)

    # ==========================================
    # INTERFACCIA STAMPE E FATTURE
    # ==========================================
    def crea_interfaccia_stampe(self, parent):
        # --- SEZIONE 1: STAMPA PRATICA ---
        frame_stampa_pratica = tk.LabelFrame(parent, text=" 1. Stampa Riepilogo Pratica ", padx=15, pady=15, bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10, 'bold'))
        frame_stampa_pratica.pack(fill="x", padx=20, pady=10)
        
        tk.Label(frame_stampa_pratica, text="Seleziona la pratica:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).pack(side="left", padx=5)
        self.combo_stampe = ttk.Combobox(frame_stampa_pratica, width=60, style="TCombobox")
        self.combo_stampe.pack(side="left", padx=10)
        
        self.btn_genera_pdf = self.crea_pulsante(frame_stampa_pratica, "Genera Stampa Pratica", self.genera_stampa_pdf, "#1565C0", "#0D47A1")
        self.btn_genera_pdf.pack(side="left", padx=10)

        # --- SEZIONE 2: FATTURA PRO-FORMA ---
        self.frame_fattura = tk.LabelFrame(parent, text=" 2. Fattura Pro-Forma ", padx=15, pady=15, bg=self.COLORE_SFONDO, fg="#F9A825", font=(self.FONT_BASE, 10, 'bold'))
        self.frame_fattura.pack(fill="both", expand=True, padx=20, pady=10)

        frame_sel_fattura = tk.Frame(self.frame_fattura, bg=self.COLORE_SFONDO)
        frame_sel_fattura.pack(fill="x", pady=5)
        
        tk.Label(frame_sel_fattura, text="Seleziona la pratica per estrapolare i dati:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).pack(side="left")
        self.combo_fattura = ttk.Combobox(frame_sel_fattura, width=50, style="TCombobox")
        self.combo_fattura.pack(side="left", padx=10)
        self.combo_fattura.bind("<<ComboboxSelected>>", self.auto_compila_fattura)
        
        grid_fattura = tk.Frame(self.frame_fattura, bg=self.COLORE_SFONDO)
        grid_fattura.pack(fill="x", pady=10)

        tk.Label(grid_fattura, text="Professionista:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=0, sticky="nw", pady=5)
        self.entry_fatt_prof = tk.Text(grid_fattura, width=60, height=4, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_fatt_prof.insert("1.0", "Geom. Massimiliano Russo, iscritto al Collegio dei Geometri e G.L. della Provincia di Catania al n° 2938 con studio a Giarre (CT) in via F.lli Cairoli n° 41 - C.F. RSSMSM72S01E017Y P. IVA 03684780871")
        self.entry_fatt_prof.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        tk.Label(grid_fattura, text="Committente:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=1, column=0, sticky="nw", pady=5)
        self.entry_fatt_comm = tk.Text(grid_fattura, width=60, height=3, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_fatt_comm.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tk.Label(grid_fattura, text="Oggetto prestazione:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.entry_fatt_ogg = tk.Entry(grid_fattura, width=70, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_fatt_ogg.grid(row=2, column=1, padx=5, pady=5, sticky="w")

        frame_compensi = tk.Frame(grid_fattura, bg=self.COLORE_SFONDO)
        frame_compensi.grid(row=3, column=0, columnspan=2, sticky="w", pady=10)
        
        tk.Label(frame_compensi, text="Compenso (€):", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=0, sticky="w")
        self.entry_compenso = tk.Entry(frame_compensi, width=12, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_compenso.grid(row=0, column=1, padx=5)
        
        tk.Label(frame_compensi, text="CNG 5% (€):", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=2, sticky="w", padx=(15,0))
        self.entry_cng = tk.Entry(frame_compensi, width=12, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cng.grid(row=0, column=3, padx=5)

        tk.Label(frame_compensi, text="Bollo (€):", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=4, sticky="w", padx=(15,0))
        self.entry_bollo = tk.Entry(frame_compensi, width=8, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_bollo.insert(0, "2.00")
        self.entry_bollo.grid(row=0, column=5, padx=5)
        
        self.crea_pulsante(frame_compensi, "Calcola Totali", self.calcola_cng, "#555555", "#777777").grid(row=0, column=6, padx=10)

        tk.Label(frame_compensi, text="Totale (€):", bg=self.COLORE_SFONDO, fg="#F9A825", font=(self.FONT_BASE, 10, 'bold')).grid(row=0, column=7, sticky="w", padx=(15,0))
        self.entry_totale = tk.Entry(frame_compensi, width=15, bg=self.COLORE_CAMPI, fg="#F9A825", relief="flat", font=(self.FONT_BASE, 10, 'bold'))
        self.entry_totale.grid(row=0, column=8, padx=5)

        tk.Label(grid_fattura, text="Modalità Pagamento:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.entry_fatt_pag = tk.Entry(grid_fattura, width=70, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_fatt_pag.insert(0, "Bonifico Bancario - IBAN: IT00 X000 0000 0000 0000 0000 000")
        self.entry_fatt_pag.grid(row=4, column=1, padx=5, pady=5, sticky="w")

        tk.Label(grid_fattura, text="Annotazioni Fiscali:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=5, column=0, sticky="w", pady=5)
        self.entry_fatt_note = tk.Entry(grid_fattura, width=70, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_fatt_note.insert(0, "Operazione senza IVA ai sensi dell'art. 10, n. 20) D.P.R. 633/72")
        self.entry_fatt_note.grid(row=5, column=1, padx=5, pady=5, sticky="w")

        frame_bottoni_fattura = tk.Frame(self.frame_fattura, bg=self.COLORE_SFONDO)
        frame_bottoni_fattura.pack(pady=10)

        self.btn_genera_fattura = self.crea_pulsante(frame_bottoni_fattura, "Genera Fattura Pro-Forma", self.genera_fattura_pdf, "#2E7D32", "#1B5E20")
        self.btn_genera_fattura.pack(side="left", padx=10)

        self.btn_pulisci_fattura = self.crea_pulsante(frame_bottoni_fattura, "Pulisci Campi", self.pulisci_campi_fattura, "#C62828", "#B71C1C")
        self.btn_pulisci_fattura.pack(side="left", padx=10)

    def carica_tendina_stampe(self):
        self.cursor.execute('''
            SELECT p.id, c.nome, c.cognome, p.tipologia_immobile 
            FROM pratiche p JOIN clienti c ON p.cliente_id = c.id
            ORDER BY p.id DESC
        ''')
        pratiche = self.cursor.fetchall()
        self.mappa_stampe = {}
        for p in pratiche:
            nominativo = f"{p['cognome']} {p['nome']}".strip()
            label = f"ID {p['id']} - {nominativo} - {p['tipologia_immobile']}"
            self.mappa_stampe[label] = p['id']
            
        self.combo_stampe['values'] = list(self.mappa_stampe.keys())
        self.combo_fattura['values'] = list(self.mappa_stampe.keys())

    def auto_compila_fattura(self, event=None):
        selezione = self.combo_fattura.get()
        if not selezione or selezione not in self.mappa_stampe:
            return
            
        id_pratica = self.mappa_stampe[selezione]
        
        self.cursor.execute('''
            SELECT p.*, c.* 
            FROM pratiche p JOIN clienti c ON p.cliente_id = c.id 
            WHERE p.id = ?
        ''', (id_pratica,))
        dati = self.cursor.fetchone()
        
        if dati:
            committente = f"{dati['cognome']} {dati['nome']}\n{dati['ind_residenza'] or ''}\nC.F./P.IVA: {dati['cf_piva'] or ''}"
            self.entry_fatt_comm.delete("1.0", tk.END)
            self.entry_fatt_comm.insert("1.0", committente)
            
            tipo_completo = f"{dati['tipo']} {('- ' + dati['tipo_dettaglio']) if dati['tipo_dettaglio'] else ''}"
            oggetto = f"Prestazione relativa a {dati['tipologia_pratica'] or ''} per {tipo_completo} - Immobile in {dati['ind_immobile'] or ''}"
            self.entry_fatt_ogg.delete(0, tk.END)
            self.entry_fatt_ogg.insert(0, oggetto)

    def pulisci_campi_fattura(self):
        self.combo_fattura.set("")
        self.entry_fatt_comm.delete("1.0", tk.END)
        self.entry_fatt_ogg.delete(0, tk.END)
        self.entry_compenso.delete(0, tk.END)
        self.entry_cng.delete(0, tk.END)
        self.entry_bollo.delete(0, tk.END)
        self.entry_bollo.insert(0, "2.00")
        self.entry_totale.delete(0, tk.END)

    def calcola_cng(self):
        try:
            compenso_str = self.entry_compenso.get().replace(',', '.').strip()
            bollo_str = self.entry_bollo.get().replace(',', '.').strip() or "0"
            
            if not compenso_str:
                return
                
            compenso = float(compenso_str)
            bollo = float(bollo_str)
            cng = compenso * 0.05
            totale = compenso + cng + bollo
            
            self.entry_cng.delete(0, tk.END)
            self.entry_cng.insert(0, f"{cng:.2f}")
            
            self.entry_totale.delete(0, tk.END)
            self.entry_totale.insert(0, f"{totale:.2f}")
        except ValueError:
            messagebox.showerror("Errore", "Inserisci importi numerici validi.")

    def genera_fattura_pdf(self):
        prof = self.entry_fatt_prof.get("1.0", "end-1c").replace('\n', '<br>')
        comm = self.entry_fatt_comm.get("1.0", "end-1c").replace('\n', '<br>')
        ogg = self.entry_fatt_ogg.get()
        comp = self.entry_compenso.get()
        cng = self.entry_cng.get()
        bollo = self.entry_bollo.get()
        tot = self.entry_totale.get()
        pag = self.entry_fatt_pag.get()
        note = self.entry_fatt_note.get()

        if not comm or not comp:
            messagebox.showwarning("Attenzione", "Committente e Compenso sono obbligatori!")
            return

        html_content = f"""
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <title>Fattura Pro-Forma</title>
            <style>
                body {{ font-family: 'Helvetica Neue', Helvetica, Arial, sans-serif; color: #333; margin: 40px; font-size: 14px; line-height: 1.5; }}
                .header {{ text-align: right; margin-bottom: 40px; border-bottom: 2px solid #F9A825; padding-bottom: 10px; }}
                .header h1 {{ color: #F9A825; margin: 0; font-size: 28px; text-transform: uppercase; }}
                .header p {{ margin: 5px 0 0 0; font-size: 14px; color: #666; font-weight: bold; }}
                .row {{ display: flex; justify-content: space-between; margin-bottom: 40px; }}
                .box {{ width: 48%; }}
                .box h3 {{ border-bottom: 1px solid #ddd; padding-bottom: 5px; margin-bottom: 10px; font-size: 16px; color: #333; }}
                .box p {{ margin: 0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 30px; }}
                th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
                th {{ background-color: #f9f9f9; font-weight: bold; }}
                .total-row td {{ font-weight: bold; background-color: #f0f0f0; font-size: 16px; color: #F9A825; }}
                .footer {{ margin-top: 60px; font-size: 13px; color: #555; border-top: 1px solid #ddd; padding-top: 15px; }}
                .disclaimer {{ text-align: center; font-weight: bold; margin-top: 50px; font-size: 14px; text-transform: uppercase; letter-spacing: 1px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Fattura Pro-Forma</h1>
                <p>Data: {datetime.now().strftime('%d/%m/%Y')}</p>
            </div>

            <div class="row">
                <div class="box">
                    <h3>Professionista</h3>
                    <p>{prof}</p>
                </div>
                <div class="box">
                    <h3>Committente</h3>
                    <p>{comm}</p>
                </div>
            </div>

            <h3>Oggetto della prestazione</h3>
            <p style="background-color: #f9f9f9; padding: 15px; border-left: 4px solid #F9A825;">{ogg}</p>

            <table>
                <tr>
                    <th>Descrizione</th>
                    <th style="text-align: right; width: 150px;">Importo (€)</th>
                </tr>
                <tr>
                    <td>Compenso Professionale</td>
                    <td style="text-align: right;">{comp}</td>
                </tr>
                <tr>
                    <td>Contributo Previdenziale CNG 5%</td>
                    <td style="text-align: right;">{cng}</td>
                </tr>
                <tr>
                    <td>Bollo</td>
                    <td style="text-align: right;">{bollo}</td>
                </tr>
                <tr class="total-row">
                    <td style="text-align: right;">TOTALE</td>
                    <td style="text-align: right;">€ {tot}</td>
                </tr>
            </table>

            <div class="footer">
                <p><strong>Modalità di pagamento:</strong><br>{pag}</p>
                <p><strong>Annotazioni fiscali:</strong><br>{note}</p>
            </div>
            
            <div class="disclaimer">
                Documento non valido ai fini fiscali
            </div>
        </body>
        </html>
        """

        # FIX CODIFICA: Aggiunto encoding='utf-8' per Windows
        fd, path = tempfile.mkstemp(suffix=".html", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_content)

        try:
            if os.name == 'posix':
                subprocess.run(['open', path])
                messagebox.showinfo("Fattura Pronta", "Il documento è stato aperto nel browser.\nUsa Cmd+P per stamparlo o salvarlo in PDF.")
            else:
                os.startfile(path)
                messagebox.showinfo("Fattura Pronta", "Il documento è stato aperto nel browser.\nUsa Ctrl+P per stamparlo o salvarlo in PDF.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire la fattura:\n{e}")

    # ==========================================
    # STAMPA PRATICA
    # ==========================================
    def genera_stampa_pdf(self):
        selezione = self.combo_stampe.get()
        if not selezione or selezione not in self.mappa_stampe:
            messagebox.showwarning("Attenzione", "Seleziona una pratica dal menu a tendina!")
            return
            
        id_pratica = self.mappa_stampe[selezione]
        
        self.cursor.execute('''
            SELECT p.*, c.* 
            FROM pratiche p 
            JOIN clienti c ON p.cliente_id = c.id 
            WHERE p.id = ?
        ''', (id_pratica,))
        dati = self.cursor.fetchone()
        
        if not dati:
            messagebox.showerror("Errore", "Impossibile trovare i dati della pratica.")
            return

        data_ing = dati['data_ingresso'] if dati['data_ingresso'] else '-'
        if data_ing != '-':
            try:
                data_ing = datetime.strptime(data_ing, '%Y-%m-%d').strftime('%d/%m/%Y')
            except ValueError:
                pass

        html_content = f"""
        <!DOCTYPE html>
        <html lang="it">
        <head>
            <meta charset="UTF-8">
            <title>Stampa Pratica ID {id_pratica}</title>
            <style>
                body {{ font-family: Arial, sans-serif; color: #333; margin: 40px; }}
                .header {{ text-align: center; border-bottom: 2px solid #333; padding-bottom: 10px; margin-bottom: 30px; }}
                .header h1 {{ margin: 0; font-size: 24px; text-transform: uppercase; }}
                .header p {{ margin: 5px 0 0 0; font-size: 14px; color: #666; }}
                .section-title {{ background-color: #f0f0f0; padding: 8px; font-weight: bold; font-size: 16px; margin-top: 20px; border-left: 4px solid #1565C0; }}
                table {{ width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f9f9f9; font-weight: bold; width: 30%; }}
                .footer {{ margin-top: 50px; text-align: center; font-size: 12px; color: #888; border-top: 1px solid #ddd; padding-top: 10px; }}
                @media print {{
                    body {{ margin: 0; }}
                }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>Studio Geometra Russo</h1>
                <p>Documento di Riepilogo Pratica</p>
            </div>

            <div class="section-title">Dati Anagrafici Cliente</div>
            <table>
                <tr><th>Nominativo</th><td>{dati['cognome']} {dati['nome']}</td></tr>
                <tr><th>Nato a</th><td>{dati['nato_a'] or ''} ({dati['prov'] or ''})</td></tr>
                <tr><th>Codice Fiscale</th><td>{dati['cf_piva'] or ''}</td></tr>
                <tr><th>Indirizzo Residenza</th><td>{dati['ind_residenza'] or ''}</td></tr>
                <tr><th>Indirizzo Immobile</th><td>{dati['ind_immobile'] or ''}</td></tr>
            </table>

            <div class="section-title">Dettagli Pratica (ID: {id_pratica})</div>
            <table>
                <tr><th>In qualità di</th><td>{dati['in_qualita_di'] or ''}</td></tr>
                <tr><th>Tipologia Immobile</th><td>{dati['tipologia_immobile'] or ''}</td></tr>
                <tr><th>Tipologia Pratica</th><td>{dati['tipologia_pratica'] or ''}</td></tr>
                <tr><th>Tipo Pratica</th><td>{dati['tipo']} {('- ' + dati['tipo_dettaglio']) if dati['tipo_dettaglio'] else ''}</td></tr>
                <tr><th>Data Ingresso</th><td>{data_ing}</td></tr>
                <tr><th>Data Apertura</th><td>{datetime.strptime(dati['data_apertura'], '%Y-%m-%d').strftime('%d/%m/%Y') if dati['data_apertura'] else ''}</td></tr>
                <tr><th>Scadenza</th><td>{datetime.strptime(dati['scadenza'], '%Y-%m-%d').strftime('%d/%m/%Y') if dati['scadenza'] else '-'}</td></tr>
                <tr><th>Stato</th><td>{dati['stato']}</td></tr>
            </table>
            
            <div class="footer">
                Documento generato automaticamente dal gestionale interno.
            </div>
        </body>
        </html>
        """

        # FIX CODIFICA: Aggiunto encoding='utf-8' per Windows
        fd, path = tempfile.mkstemp(suffix=".html", text=True)
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(html_content)

        try:
            if os.name == 'posix':
                subprocess.run(['open', path])
                messagebox.showinfo("Stampa Pronta", "Il documento è stato aperto nel browser.\nUsa Cmd+P per aprire la finestra di stampa.")
            else:
                os.startfile(path)
                messagebox.showinfo("Stampa Pronta", "Il documento è stato aperto nel browser.\nUsa Ctrl+P per aprire la finestra di stampa.")
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire la stampa:\n{e}")

    # --- LOGICA PRATICHE E CLIENTI ---
    def crea_interfaccia_pratiche(self, parent):
        frame_ricerca = tk.Frame(parent, bg=self.COLORE_SFONDO, pady=10)
        frame_ricerca.pack(fill="x", padx=15)
        
        tk.Label(frame_ricerca, text="Cerca:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).pack(side="left")
        self.entry_ricerca = tk.Entry(frame_ricerca, width=40, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_ricerca.pack(side="left", padx=10, ipady=3)
        self.entry_ricerca.bind("<KeyRelease>", self.filtra_pratiche)
        
        btn_mostra = self.crea_pulsante(frame_ricerca, "Mostra Tutte", self.reset_ricerca, "#555555", "#777777")
        btn_mostra.pack(side="left", padx=5)

        self.frame_input_p = tk.LabelFrame(parent, text=" Dettagli Pratica ", padx=15, pady=15, bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10, 'bold'))
        self.frame_input_p.pack(fill="x", padx=15, pady=5)

        tk.Label(self.frame_input_p, text="Cliente:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.combo_cliente = ttk.Combobox(self.frame_input_p, width=30, style="TCombobox")
        self.combo_cliente.grid(row=0, column=1, padx=5, pady=5)

        tk.Label(self.frame_input_p, text="In qualità di:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=2, sticky="w", pady=5, padx=(25, 0))
        self.combo_qualita = ttk.Combobox(self.frame_input_p, values=["Proprietario", "Comproprietario", "Affittuario", "Amministratore condominio", "Impresa"], width=28, style="TCombobox")
        self.combo_qualita.grid(row=0, column=3, padx=5, pady=5)

        tk.Label(self.frame_input_p, text="Tipologia Immobile:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.combo_tipologia = ttk.Combobox(self.frame_input_p, values=["Fabbricato singolo", "Condominio", "Appartamento", "Villetta", "Fabbricato rurale"], width=30, style="TCombobox")
        self.combo_tipologia.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        tk.Label(self.frame_input_p, text="Tipologia Pratica:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=1, column=2, sticky="w", pady=5, padx=(25, 0))
        self.combo_tipologia_pratica = ttk.Combobox(self.frame_input_p, values=["CILA", "SCIA", "SCIA in sanatoria", "SCIA alternativa al PdC", "PdC", "Autorizzazione allo scarico", "Computo Metrico", "Direzione Lavori"], width=28, style="TCombobox")
        self.combo_tipologia_pratica.grid(row=1, column=3, padx=5, pady=5)

        tk.Label(self.frame_input_p, text="Tipo Pratica:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.combo_tipo = ttk.Combobox(self.frame_input_p, values=["Catasto", "Urbanistica", "Perizia di Stima", "Perizia danni", "Perizia superbonus", "Tabelle millesimali"], width=30, style="TCombobox")
        self.combo_tipo.grid(row=2, column=1, padx=5, pady=5)
        self.combo_tipo.bind("<<ComboboxSelected>>", self.gestisci_sottomenu)

        self.lbl_sottotipo = tk.Label(self.frame_input_p, text="", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10))
        self.combo_sottotipo = ttk.Combobox(self.frame_input_p, width=28, style="TCombobox")

        tk.Label(self.frame_input_p, text="Data Ingresso:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=3, column=0, sticky="w", pady=5)
        self.date_ingresso = DateEntry(self.frame_input_p, width=28, date_pattern='%d/%m/%Y', locale='it_IT')
        self.date_ingresso.grid(row=3, column=1, padx=5, pady=5, sticky="w")

        tk.Label(self.frame_input_p, text="Scadenza:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=3, column=2, sticky="w", pady=5, padx=(25, 0))
        self.entry_scadenza = DateEntry(self.frame_input_p, width=28, date_pattern='%d/%m/%Y', locale='it_IT')
        self.entry_scadenza.grid(row=3, column=3, padx=5, pady=5, sticky="w")

        tk.Label(self.frame_input_p, text="Stato:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.combo_stato = ttk.Combobox(self.frame_input_p, values=["Aperta", "In attesa documenti", "Inviata", "Conclusa"], width=28, style="TCombobox")
        self.combo_stato.grid(row=4, column=1, padx=5, pady=5)

        self.frame_pagamenti = tk.LabelFrame(self.frame_input_p, text=" Pagamenti ", padx=10, pady=10, bg=self.COLORE_SFONDO, fg="#F9A825", font=(self.FONT_BASE, 10, 'bold'))
        self.frame_pagamenti.grid(row=5, column=0, columnspan=4, sticky="ew", padx=5, pady=10)

        tk.Label(self.frame_pagamenti, text="Voce", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, width=12, anchor="w", font=(self.FONT_BASE, 10)).grid(row=0, column=0, padx=5, pady=2)
        tk.Label(self.frame_pagamenti, text="Importo (€)", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, width=12, font=(self.FONT_BASE, 10)).grid(row=0, column=1, padx=5, pady=2)
        tk.Label(self.frame_pagamenti, text="Data Pag.", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, width=12, font=(self.FONT_BASE, 10)).grid(row=0, column=2, padx=5, pady=2)
        tk.Label(self.frame_pagamenti, text="Fattura n°", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, width=12, font=(self.FONT_BASE, 10)).grid(row=0, column=3, padx=5, pady=2)
        tk.Label(self.frame_pagamenti, text="Data Fatt.", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, width=12, font=(self.FONT_BASE, 10)).grid(row=0, column=4, padx=5, pady=2)

        def crea_riga_pagamento(parent, riga, label_testo, prefisso):
            tk.Label(parent, text=label_testo, bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, anchor="w", font=(self.FONT_BASE, 10)).grid(row=riga, column=0, padx=5, pady=2, sticky="w")
            
            entry_imp = tk.Entry(parent, width=14, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
            entry_imp.grid(row=riga, column=1, padx=5, pady=2)
            
            date_pag = DateEntry(parent, width=13, date_pattern='%d/%m/%Y', locale='it_IT')
            date_pag.grid(row=riga, column=2, padx=5, pady=2)
            
            entry_fat = tk.Entry(parent, width=14, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
            entry_fat.grid(row=riga, column=3, padx=5, pady=2)
            
            date_fat = DateEntry(parent, width=13, date_pattern='%d/%m/%Y', locale='it_IT')
            date_fat.grid(row=riga, column=4, padx=5, pady=2)
            
            setattr(self, f"entry_{prefisso}_imp", entry_imp)
            setattr(self, f"date_{prefisso}_data", date_pag)
            setattr(self, f"entry_{prefisso}_fat", entry_fat)
            setattr(self, f"date_{prefisso}_datafat", date_fat)

        crea_riga_pagamento(self.frame_pagamenti, 1, "1° Acconto:", "acc1")
        crea_riga_pagamento(self.frame_pagamenti, 2, "2° Acconto:", "acc2")
        crea_riga_pagamento(self.frame_pagamenti, 3, "3° Acconto:", "acc3")
        crea_riga_pagamento(self.frame_pagamenti, 4, "Saldo:", "saldo")

        frame_bottoni = tk.Frame(self.frame_input_p, bg=self.COLORE_SFONDO)
        frame_bottoni.grid(row=6, column=0, columnspan=4, pady=15)

        self.btn_salva_p = self.crea_pulsante(frame_bottoni, "Salva Nuova", self.salva_pratica, "#2E7D32", "#1B5E20")
        self.btn_salva_p.pack(side="left", padx=10)

        self.btn_aggiorna_p = self.crea_pulsante(frame_bottoni, "Aggiorna", self.aggiorna_pratica, "#1565C0", "#0D47A1")
        self.btn_aggiorna_p.pack(side="left", padx=10)

        self.btn_documenti = self.crea_pulsante(frame_bottoni, "Apri Documenti", self.apri_cartella_documenti, "#6A1B9A", "#4A148C")
        self.btn_documenti.pack(side="left", padx=10)

        self.btn_elimina_p = self.crea_pulsante(frame_bottoni, "Elimina", self.elimina_pratica, "#C62828", "#B71C1C")
        self.btn_elimina_p.pack(side="left", padx=10)

        self.btn_pulisci_p = self.crea_pulsante(frame_bottoni, "Pulisci", self.pulisci_campi_pratica, "#424242", "#212121")
        self.btn_pulisci_p.pack(side="left", padx=10)

        frame_tabella = tk.Frame(parent, bg=self.COLORE_SFONDO)
        frame_tabella.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        self.tree = ttk.Treeview(frame_tabella, columns=("ID", "Cliente", "In qualità di", "Tip. Immobile", "Tip. Pratica", "Tipo Pratica", "Stato", "Scadenza", "Giorni"), show="headings", style="Treeview")
        for col in self.tree["columns"]:
            self.tree.heading(col, text=col)
            
        self.tree.column("ID", width=40, anchor="center")
        self.tree.column("Cliente", width=130)
        self.tree.column("In qualità di", width=120)
        self.tree.column("Tip. Immobile", width=130)
        self.tree.column("Tip. Pratica", width=130)
        self.tree.column("Tipo Pratica", width=160)
        self.tree.column("Stato", width=100)
        self.tree.column("Scadenza", width=90, anchor="center")
        self.tree.column("Giorni", width=70, anchor="center")

        self.tree.tag_configure("scaduta", background="#C62828", foreground="white")
        self.tree.tag_configure("in_scadenza", background="#F9A825", foreground="black")

        scrollbar = ttk.Scrollbar(frame_tabella, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.tree.bind("<<TreeviewSelect>>", self.seleziona_pratica)

    def gestisci_sottomenu(self, event=None):
        tipo_scelto = self.combo_tipo.get()
        self.lbl_sottotipo.grid_forget()
        self.combo_sottotipo.grid_forget()
        self.combo_sottotipo.set("")
        
        if tipo_scelto == "Catasto":
            self.lbl_sottotipo.config(text="Dettaglio Catasto:")
            self.combo_sottotipo.config(values=["Inserimento in mappa e docfa", "Ricorsi", "Allineamento dati"])
            self.lbl_sottotipo.grid(row=2, column=2, sticky="w", pady=5, padx=(25, 0))
            self.combo_sottotipo.grid(row=2, column=3, padx=5, pady=5)
            
        elif tipo_scelto == "Urbanistica":
            self.lbl_sottotipo.config(text="Dettaglio Urbanistica:")
            self.combo_sottotipo.config(values=["Nuova Costruzione", "Ristrutturazione", "Regolarizzazione", "Sanatoria", "Autorizzazione allo scarico"])
            self.lbl_sottotipo.grid(row=2, column=2, sticky="w", pady=5, padx=(25, 0))
            self.combo_sottotipo.grid(row=2, column=3, padx=5, pady=5)

    def crea_interfaccia_clienti(self, parent):
        self.frame_input_c = tk.LabelFrame(parent, text=" Dati Anagrafici Cliente ", padx=15, pady=15, bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10, 'bold'))
        self.frame_input_c.pack(fill="x", padx=15, pady=10)

        tk.Label(self.frame_input_c, text="Cognome*:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=0, sticky="w", pady=5)
        self.entry_cli_cognome = tk.Entry(self.frame_input_c, width=30, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_cognome.grid(row=0, column=1, padx=5, pady=5, ipady=3, sticky="w")

        tk.Label(self.frame_input_c, text="Nome*:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=0, column=2, sticky="w", pady=5)
        self.entry_cli_nome = tk.Entry(self.frame_input_c, width=30, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_nome.grid(row=0, column=3, padx=5, pady=5, ipady=3, sticky="w")

        tk.Label(self.frame_input_c, text="Nato/a a:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=1, column=0, sticky="w", pady=5)
        self.entry_cli_nato = tk.Entry(self.frame_input_c, width=30, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_nato.grid(row=1, column=1, padx=5, pady=5, ipady=3, sticky="w")

        tk.Label(self.frame_input_c, text="Prov.:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=1, column=2, sticky="w", pady=5)
        self.entry_cli_prov = tk.Entry(self.frame_input_c, width=10, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_prov.grid(row=1, column=3, padx=5, pady=5, ipady=3, sticky="w")

        tk.Label(self.frame_input_c, text="Codice Fiscale:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=2, column=0, sticky="w", pady=5)
        self.entry_cli_cf = tk.Entry(self.frame_input_c, width=30, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_cf.grid(row=2, column=1, padx=5, pady=5, ipady=3, sticky="w")

        tk.Label(self.frame_input_c, text="Indirizzo Residenza:", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=3, column=0, sticky="w", pady=5)
        self.entry_cli_residenza = tk.Entry(self.frame_input_c, width=75, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_residenza.grid(row=3, column=1, columnspan=3, padx=5, pady=5, ipady=3, sticky="w")

        tk.Label(self.frame_input_c, text="Indirizzo Immobile (Pratica):", bg=self.COLORE_SFONDO, fg=self.COLORE_TESTO, font=(self.FONT_BASE, 10)).grid(row=4, column=0, sticky="w", pady=5)
        self.entry_cli_immobile = tk.Entry(self.frame_input_c, width=75, bg=self.COLORE_CAMPI, fg=self.COLORE_TESTO, insertbackground=self.COLORE_TESTO, relief="flat", font=(self.FONT_BASE, 10))
        self.entry_cli_immobile.grid(row=4, column=1, columnspan=3, padx=5, pady=5, ipady=3, sticky="w")

        frame_bottoni_c = tk.Frame(self.frame_input_c, bg=self.COLORE_SFONDO)
        frame_bottoni_c.grid(row=5, column=0, columnspan=4, pady=15)

        self.btn_salva_c = self.crea_pulsante(frame_bottoni_c, "Salva Cliente", self.salva_cliente, "#2E7D32", "#1B5E20")
        self.btn_salva_c.pack(side="left", padx=10)

        self.btn_aggiorna_c = self.crea_pulsante(frame_bottoni_c, "Aggiorna Cliente", self.aggiorna_cliente, "#1565C0", "#0D47A1")
        self.btn_aggiorna_c.pack(side="left", padx=10)

        self.btn_elimina_c = self.crea_pulsante(frame_bottoni_c, "Elimina", self.elimina_cliente, "#C62828", "#B71C1C")
        self.btn_elimina_c.pack(side="left", padx=10)

        self.btn_pulisci_c = self.crea_pulsante(frame_bottoni_c, "Pulisci", self.pulisci_campi_cliente, "#424242", "#212121")
        self.btn_pulisci_c.pack(side="left", padx=10)

        frame_tabella_c = tk.Frame(parent, bg=self.COLORE_SFONDO)
        frame_tabella_c.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        self.tree_clienti = ttk.Treeview(frame_tabella_c, columns=("ID", "Nominativo", "Nato a", "CF", "Residenza", "Immobile"), show="headings", style="Treeview")
        self.tree_clienti.heading("ID", text="ID")
        self.tree_clienti.heading("Nominativo", text="Nominativo")
        self.tree_clienti.heading("Nato a", text="Nato a (Prov)")
        self.tree_clienti.heading("CF", text="Codice Fiscale")
        self.tree_clienti.heading("Residenza", text="Residenza")
        self.tree_clienti.heading("Immobile", text="Immobile Pratica")
        
        self.tree_clienti.column("ID", width=40, anchor="center")
        self.tree_clienti.column("Nominativo", width=180)
        self.tree_clienti.column("Nato a", width=120)
        self.tree_clienti.column("CF", width=120)
        self.tree_clienti.column("Residenza", width=200)
        self.tree_clienti.column("Immobile", width=200)

        scrollbar_c = ttk.Scrollbar(frame_tabella_c, orient="vertical", command=self.tree_clienti.yview)
        self.tree_clienti.configure(yscrollcommand=scrollbar_c.set)
        self.tree_clienti.pack(side="left", fill="both", expand=True)
        scrollbar_c.pack(side="right", fill="y")
        
        self.tree_clienti.bind("<<TreeviewSelect>>", self.seleziona_cliente)

    def salva_cliente(self):
        cognome = self.entry_cli_cognome.get().strip()
        nome = self.entry_cli_nome.get().strip()
        nato = self.entry_cli_nato.get().strip()
        prov = self.entry_cli_prov.get().strip()
        cf = self.entry_cli_cf.get().strip()
        residenza = self.entry_cli_residenza.get().strip()
        immobile = self.entry_cli_immobile.get().strip()

        if not nome or not cognome:
            messagebox.showwarning("Attenzione", "Nome e Cognome sono obbligatori!")
            return

        self.cursor.execute('''
            INSERT INTO clienti (nome, cognome, nato_a, prov, cf_piva, ind_residenza, ind_immobile)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (nome, cognome, nato, prov, cf, residenza, immobile))
        self.conn.commit()
        
        self.carica_tabella_clienti()
        self.carica_clienti_tendina()
        self.pulisci_campi_cliente()
        messagebox.showinfo("Successo", "Cliente inserito correttamente!")

    def seleziona_cliente(self, event=None):
        selected = self.tree_clienti.focus()
        if not selected: return
        valori = self.tree_clienti.item(selected, 'values')
        if not valori: return
        
        self.id_cliente_selezionato = valori[0]
        self.pulisci_campi_cliente(keep_id=True)
        
        self.cursor.execute("SELECT * FROM clienti WHERE id = ?", (self.id_cliente_selezionato,))
        dati = self.cursor.fetchone()
        
        if dati:
            self.entry_cli_nome.insert(0, dati['nome'] if dati['nome'] else "")
            self.entry_cli_cognome.insert(0, dati['cognome'] if dati['cognome'] else "")
            self.entry_cli_nato.insert(0, dati['nato_a'] if dati['nato_a'] else "")
            self.entry_cli_prov.insert(0, dati['prov'] if dati['prov'] else "")
            self.entry_cli_cf.insert(0, dati['cf_piva'] if dati['cf_piva'] else "")
            self.entry_cli_residenza.insert(0, dati['ind_residenza'] if dati['ind_residenza'] else "")
            self.entry_cli_immobile.insert(0, dati['ind_immobile'] if dati['ind_immobile'] else "")

    def aggiorna_cliente(self):
        if not self.id_cliente_selezionato:
            messagebox.showwarning("Attenzione", "Seleziona prima un cliente dalla tabella!")
            return
            
        cognome = self.entry_cli_cognome.get().strip()
        nome = self.entry_cli_nome.get().strip()
        nato = self.entry_cli_nato.get().strip()
        prov = self.entry_cli_prov.get().strip()
        cf = self.entry_cli_cf.get().strip()
        residenza = self.entry_cli_residenza.get().strip()
        immobile = self.entry_cli_immobile.get().strip()

        if not nome or not cognome:
            messagebox.showwarning("Attenzione", "Nome e Cognome sono obbligatori!")
            return

        self.cursor.execute('''
            UPDATE clienti 
            SET nome=?, cognome=?, nato_a=?, prov=?, cf_piva=?, ind_residenza=?, ind_immobile=?
            WHERE id=?
        ''', (nome, cognome, nato, prov, cf, residenza, immobile, self.id_cliente_selezionato))
        self.conn.commit()
        
        self.carica_tabella_clienti()
        self.carica_clienti_tendina()
        self.carica_pratiche()
        self.pulisci_campi_cliente()
        messagebox.showinfo("Successo", "Cliente aggiornato correttamente!")

    def elimina_cliente(self):
        if not self.id_cliente_selezionato:
            messagebox.showwarning("Attenzione", "Seleziona prima un cliente dalla tabella!")
            return
            
        self.cursor.execute("SELECT COUNT(*) FROM pratiche WHERE cliente_id = ?", (self.id_cliente_selezionato,))
        num_pratiche = self.cursor.fetchone()[0]
        
        if num_pratiche > 0:
            messagebox.showerror("Impossibile eliminare", f"Questo cliente ha {num_pratiche} pratiche collegate.\nElimina prima le pratiche.")
            return

        risposta = messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questo cliente?")
        if risposta:
            self.cursor.execute("DELETE FROM clienti WHERE id = ?", (self.id_cliente_selezionato,))
            self.conn.commit()
            self.carica_tabella_clienti()
            self.carica_clienti_tendina()
            self.pulisci_campi_cliente()

    def carica_tabella_clienti(self):
        for row in self.tree_clienti.get_children():
            self.tree_clienti.delete(row)
            
        self.cursor.execute("SELECT id, nome, cognome, nato_a, prov, cf_piva, ind_residenza, ind_immobile FROM clienti ORDER BY cognome ASC, nome ASC")
        for row in self.cursor.fetchall():
            nominativo = f"{row['cognome'] if row['cognome'] else ''} {row['nome'] if row['nome'] else ''}".strip()
            nato_a = f"{row['nato_a'] if row['nato_a'] else ''} ({row['prov']})" if row['prov'] else (row['nato_a'] if row['nato_a'] else "")
            
            self.tree_clienti.insert("", "end", values=(row['id'], nominativo, nato_a, row['cf_piva'], row['ind_residenza'], row['ind_immobile']))

    def carica_clienti_tendina(self):
        self.cursor.execute("SELECT id, nome, cognome FROM clienti ORDER BY cognome ASC, nome ASC")
        clienti = self.cursor.fetchall()
        self.mappa_clienti = {}
        for c in clienti:
            nominativo = f"{c['cognome'] if c['cognome'] else ''} {c['nome'] if c['nome'] else ''}".strip()
            self.mappa_clienti[f"{c['id']} - {nominativo}"] = c['id']
            
        self.combo_cliente['values'] = list(self.mappa_clienti.keys())

    def pulisci_campi_cliente(self, keep_id=False):
        if not keep_id:
            self.id_cliente_selezionato = None
        self.entry_cli_nome.delete(0, tk.END)
        self.entry_cli_cognome.delete(0, tk.END)
        self.entry_cli_nato.delete(0, tk.END)
        self.entry_cli_prov.delete(0, tk.END)
        self.entry_cli_cf.delete(0, tk.END)
        self.entry_cli_residenza.delete(0, tk.END)
        self.entry_cli_immobile.delete(0, tk.END)
        
        for item in self.tree_clienti.selection():
            self.tree_clienti.selection_remove(item)

    def salva_pratica(self):
        cliente_str = self.combo_cliente.get()
        if not cliente_str or cliente_str not in self.mappa_clienti:
            messagebox.showwarning("Attenzione", "Seleziona un cliente valido dal menu a tendina!")
            return
            
        cliente_id = self.mappa_clienti[cliente_str]
        qualita = self.combo_qualita.get()
        tipologia = self.combo_tipologia.get()
        tipologia_pratica = self.combo_tipologia_pratica.get()
        tipo = self.combo_tipo.get()
        tipo_dettaglio = self.combo_sottotipo.get() if tipo in ["Catasto", "Urbanistica"] else ""
        stato = self.combo_stato.get() or "Aperta"
        
        data_ing_str = self.date_ingresso.get()
        data_ingresso = ""
        if data_ing_str:
            try:
                data_ingresso = datetime.strptime(data_ing_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError: pass
            
        data_selezionata = self.entry_scadenza.get()
        scadenza = ""
        if data_selezionata:
            try:
                scadenza = datetime.strptime(data_selezionata, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

        if not tipologia:
            messagebox.showwarning("Attenzione", "Seleziona la Tipologia Immobile!")
            return
            
        if not tipo:
            messagebox.showwarning("Attenzione", "Seleziona il Tipo Pratica!")
            return

        data_oggi = datetime.now().strftime("%Y-%m-%d")
        
        pagamenti_dati = []
        for pref in ["acc1", "acc2", "acc3", "saldo"]:
            imp = getattr(self, f"entry_{pref}_imp").get().strip()
            
            data_pag_str = getattr(self, f"date_{pref}_data").get()
            data_pag = ""
            if data_pag_str:
                try:
                    data_pag = datetime.strptime(data_pag_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError: pass
                
            fat = getattr(self, f"entry_{pref}_fat").get().strip()
            
            data_fat_str = getattr(self, f"date_{pref}_datafat").get()
            data_fat = ""
            if data_fat_str:
                try:
                    data_fat = datetime.strptime(data_fat_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError: pass
                
            pagamenti_dati.extend([imp, data_pag, fat, data_fat])

        self.cursor.execute('''
            INSERT INTO pratiche (
                cliente_id, in_qualita_di, tipologia_immobile, tipologia_pratica, tipo, tipo_dettaglio, stato, data_ingresso, data_apertura, scadenza,
                acc1_importo, acc1_data, acc1_fattura, acc1_data_fattura,
                acc2_importo, acc2_data, acc2_fattura, acc2_data_fattura,
                acc3_importo, acc3_data, acc3_fattura, acc3_data_fattura,
                saldo_importo, saldo_data, saldo_fattura, saldo_data_fattura
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cliente_id, qualita, tipologia, tipologia_pratica, tipo, tipo_dettaglio, stato, data_ingresso, data_oggi, scadenza,
            *pagamenti_dati
        ))
        
        self.conn.commit()
        self.carica_pratiche()
        self.carica_tendina_stampe()
        self.pulisci_campi_pratica()

    def seleziona_pratica(self, event=None):
        selected = self.tree.focus()
        if not selected: return
        valori = self.tree.item(selected, 'values')
        if not valori: return
            
        self.id_pratica_selezionata = valori[0]
        self.cliente_corrente = valori[1]
        
        self.cursor.execute("SELECT cliente_id FROM pratiche WHERE id = ?", (self.id_pratica_selezionata,))
        res = self.cursor.fetchone()
        if res:
            cliente_id = res['cliente_id']
            for key, val in self.mappa_clienti.items():
                if val == cliente_id:
                    self.combo_cliente.set(key)
                    break
        
        self.combo_qualita.set(valori[2])
        self.combo_tipologia.set(valori[3])
        self.combo_tipologia_pratica.set(valori[4])
        
        tipo_db = valori[5]
        if " - " in tipo_db:
            parti = tipo_db.split(" - ", 1)
            self.combo_tipo.set(parti[0])
            self.gestisci_sottomenu()
            self.combo_sottotipo.set(parti[1])
        else:
            self.combo_tipo.set(tipo_db)
            self.gestisci_sottomenu()
        
        self.combo_stato.set(valori[6])
        
        data_db = valori[7]
        if data_db and data_db != "-":
            try:
                self.entry_scadenza.set_date(datetime.strptime(data_db, "%d/%m/%Y").date())
            except ValueError:
                pass

        self.cursor.execute("SELECT * FROM pratiche WHERE id = ?", (self.id_pratica_selezionata,))
        p = self.cursor.fetchone()
        
        if p:
            if p['data_ingresso']:
                try:
                    self.date_ingresso.set_date(datetime.strptime(p['data_ingresso'], "%Y-%m-%d").date())
                except ValueError: pass
            else:
                self.date_ingresso.set_date(datetime.now().date())
                
            mappatura_pagamenti = ["acc1", "acc2", "acc3", "saldo"]
            
            for pref in mappatura_pagamenti:
                getattr(self, f"entry_{pref}_imp").delete(0, tk.END)
                getattr(self, f"entry_{pref}_fat").delete(0, tk.END)
                
                if p[f"{pref}_importo"]:
                    getattr(self, f"entry_{pref}_imp").insert(0, p[f"{pref}_importo"])
                    
                if p[f"{pref}_data"]:
                    try:
                        getattr(self, f"date_{pref}_data").set_date(datetime.strptime(p[f"{pref}_data"], "%Y-%m-%d").date())
                    except ValueError: 
                        pass
                else:
                    getattr(self, f"date_{pref}_data").set_date(datetime.now().date())
                    
                if p[f"{pref}_fattura"]:
                    getattr(self, f"entry_{pref}_fat").insert(0, p[f"{pref}_fattura"])
                    
                if p[f"{pref}_data_fattura"]:
                    try:
                        getattr(self, f"date_{pref}_datafat").set_date(datetime.strptime(p[f"{pref}_data_fattura"], "%Y-%m-%d").date())
                    except ValueError: 
                        pass
                else:
                    getattr(self, f"date_{pref}_datafat").set_date(datetime.now().date())

    def aggiorna_pratica(self):
        if not self.id_pratica_selezionata:
            messagebox.showwarning("Attenzione", "Seleziona prima una pratica!")
            return
            
        cliente_str = self.combo_cliente.get()
        if not cliente_str or cliente_str not in self.mappa_clienti:
            messagebox.showwarning("Attenzione", "Seleziona un cliente valido!")
            return
            
        cliente_id = self.mappa_clienti[cliente_str]
        qualita = self.combo_qualita.get()
        tipologia = self.combo_tipologia.get()
        tipologia_pratica = self.combo_tipologia_pratica.get()
        tipo = self.combo_tipo.get()
        tipo_dettaglio = self.combo_sottotipo.get() if tipo in ["Catasto", "Urbanistica"] else ""
        stato = self.combo_stato.get()
        
        data_ing_str = self.date_ingresso.get()
        data_ingresso = ""
        if data_ing_str:
            try:
                data_ingresso = datetime.strptime(data_ing_str, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError: pass
        
        data_selezionata = self.entry_scadenza.get()
        scadenza = ""
        if data_selezionata:
            try:
                scadenza = datetime.strptime(data_selezionata, "%d/%m/%Y").strftime("%Y-%m-%d")
            except ValueError:
                pass

        if not tipologia or not tipo:
            messagebox.showwarning("Attenzione", "Compila Tipologia e Tipo Pratica!")
            return

        pagamenti_dati = []
        for pref in ["acc1", "acc2", "acc3", "saldo"]:
            imp = getattr(self, f"entry_{pref}_imp").get().strip()
            
            data_pag_str = getattr(self, f"date_{pref}_data").get()
            data_pag = ""
            if data_pag_str:
                try:
                    data_pag = datetime.strptime(data_pag_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError: pass
                
            fat = getattr(self, f"entry_{pref}_fat").get().strip()
            
            data_fat_str = getattr(self, f"date_{pref}_datafat").get()
            data_fat = ""
            if data_fat_str:
                try:
                    data_fat = datetime.strptime(data_fat_str, "%d/%m/%Y").strftime("%Y-%m-%d")
                except ValueError: pass
                
            pagamenti_dati.extend([imp, data_pag, fat, data_fat])

        self.cursor.execute('''
            UPDATE pratiche 
            SET cliente_id = ?, in_qualita_di = ?, tipologia_immobile = ?, tipologia_pratica = ?, tipo = ?, tipo_dettaglio = ?, stato = ?, data_ingresso = ?, scadenza = ?,
                acc1_importo = ?, acc1_data = ?, acc1_fattura = ?, acc1_data_fattura = ?,
                acc2_importo = ?, acc2_data = ?, acc2_fattura = ?, acc2_data_fattura = ?,
                acc3_importo = ?, acc3_data = ?, acc3_fattura = ?, acc3_data_fattura = ?,
                saldo_importo = ?, saldo_data = ?, saldo_fattura = ?, saldo_data_fattura = ?
            WHERE id = ?
        ''', (
            cliente_id, qualita, tipologia, tipologia_pratica, tipo, tipo_dettaglio, stato, data_ingresso, scadenza,
            *pagamenti_dati,
            self.id_pratica_selezionata
        ))
        
        self.conn.commit()
        self.carica_pratiche()
        self.carica_tendina_stampe()
        self.pulisci_campi_pratica()
        messagebox.showinfo("Successo", "Pratica aggiornata!")

    def elimina_pratica(self):
        if not self.id_pratica_selezionata:
            messagebox.showwarning("Attenzione", "Seleziona prima una pratica!")
            return
            
        risposta = messagebox.askyesno("Conferma", "Sei sicuro di voler eliminare questa pratica?")
        if risposta:
            self.cursor.execute("DELETE FROM pratiche WHERE id = ?", (self.id_pratica_selezionata,))
            self.conn.commit()
            self.carica_pratiche()
            self.carica_tendina_stampe()
            self.pulisci_campi_pratica()

    def carica_pratiche(self, query_custom=None, parametri=None):
        for row in self.tree.get_children():
            self.tree.delete(row)
            
        if query_custom:
            self.cursor.execute(query_custom, parametri)
        else:
            self.cursor.execute('''
                SELECT p.id, c.nome, c.cognome, p.in_qualita_di, p.tipologia_immobile, p.tipologia_pratica, p.tipo, p.tipo_dettaglio, p.stato, p.scadenza 
                FROM pratiche p JOIN clienti c ON p.cliente_id = c.id
                ORDER BY p.id DESC
            ''')
            
        for row in self.cursor.fetchall():
            id_pratica = row['id']
            nominativo = f"{row['cognome'] if row['cognome'] else ''} {row['nome'] if row['nome'] else ''}".strip()
            qualita = row['in_qualita_di'] if row['in_qualita_di'] else ""
            tipologia = row['tipologia_immobile'] if row['tipologia_immobile'] else ""
            tipologia_pratica = row['tipologia_pratica'] if row['tipologia_pratica'] else ""
            
            tipo_base = row['tipo'] if row['tipo'] else ""
            tipo_dett = row['tipo_dettaglio']
            tipo_visualizzato = f"{tipo_base} - {tipo_dett}" if tipo_dett else tipo_base
            
            stato = row['stato']
            data_ita = "-"
            
            if row['scadenza']:
                try:
                    data_ita = datetime.strptime(row['scadenza'], "%Y-%m-%d").strftime("%d/%m/%Y")
                except ValueError:
                    pass
            
            testo_giorni, tag = self.calcola_stato_scadenza(data_ita, stato)
            self.tree.insert("", "end", values=(id_pratica, nominativo, qualita, tipologia, tipologia_pratica, tipo_visualizzato, stato, data_ita, testo_giorni), tags=(tag,))

    def pulisci_campi_pratica(self):
        self.id_pratica_selezionata = None
        self.combo_cliente.set("")
        self.combo_qualita.set("")
        self.combo_tipologia.set("")
        self.combo_tipologia_pratica.set("")
        self.combo_tipo.set("")
        self.gestisci_sottomenu()
        self.combo_sottotipo.set("")
        self.combo_stato.set("")
        self.date_ingresso.set_date(datetime.now().date())
        self.entry_scadenza.set_date(datetime.now().date())
        
        for pref in ["acc1", "acc2", "acc3", "saldo"]:
            getattr(self, f"entry_{pref}_imp").delete(0, tk.END)
            getattr(self, f"entry_{pref}_fat").delete(0, tk.END)
            getattr(self, f"date_{pref}_data").set_date(datetime.now().date())
            getattr(self, f"date_{pref}_datafat").set_date(datetime.now().date())

        for item in self.tree.selection():
            self.tree.selection_remove(item)

    def apri_cartella_documenti(self):
        if not self.id_pratica_selezionata:
            messagebox.showwarning("Attenzione", "Seleziona prima una pratica!")
            return
        if not self.cliente_corrente:
            return
            
        cliente_pulito = re.sub(r'[\\/*?:"<>|]', "", self.cliente_corrente).strip().replace(" ", "_")
        base_dir = os.path.expanduser("~/Documents/StudioGeometra/Pratiche")
        cartella_pratica = os.path.join(base_dir, f"Pratica_{self.id_pratica_selezionata}_{cliente_pulito}")
        
        try:
            os.makedirs(cartella_pratica, exist_ok=True)
            if os.name == 'posix':
                subprocess.Popen(['open', cartella_pratica])
            else:
                os.startfile(cartella_pratica)
        except Exception as e:
            messagebox.showerror("Errore", f"Impossibile aprire la cartella:\n{e}")

    def calcola_stato_scadenza(self, data_scadenza_str, stato_pratica):
        if not data_scadenza_str or stato_pratica == "Conclusa":
            return ("-", "")
        try:
            data_scad = datetime.strptime(data_scadenza_str, "%d/%m/%Y").date()
            delta = (data_scad - date.today()).days
            if delta < 0: return (f"{abs(delta)} gg fa", "scaduta")
            elif delta == 0: return ("Oggi", "in_scadenza")
            elif delta <= 7: return (f"tra {delta} gg", "in_scadenza")
            else: return (f"tra {delta} gg", "")
        except ValueError:
            return ("-", "")

    def avviso_scadenze(self):
        limite = date.today() + timedelta(days=7)
        self.cursor.execute('''
            SELECT c.nome, c.cognome, p.tipologia_immobile, p.scadenza 
            FROM pratiche p JOIN clienti c ON p.cliente_id = c.id
            WHERE p.stato != 'Conclusa' AND p.scadenza IS NOT NULL AND p.scadenza != ''
        ''')
        
        scadenze = []
        for row in self.cursor.fetchall():
            try:
                data_scad = datetime.strptime(row['scadenza'], "%Y-%m-%d").date()
                if data_scad <= limite:
                    giorni = (data_scad - date.today()).days
                    stato_txt = f"SCADUTA da {abs(giorni)} gg" if giorni < 0 else ("SCADE OGGI" if giorni == 0 else f"Tra {giorni} gg")
                    nominativo = f"{row['cognome']} {row['nome']}".strip()
                    scadenze.append(f"• {nominativo} - {row['tipologia_immobile']} ({stato_txt})")
            except ValueError:
                pass
                
        if scadenze:
            msg = "ATTENZIONE: Hai pratiche in scadenza o scadute:\n\n" + "\n".join(scadenze[:10])
            messagebox.showwarning("Avviso Scadenze", msg)

    def filtra_pratiche(self, event=None):
        testo = self.entry_ricerca.get().strip()
        if not testo:
            self.carica_pratiche()
            return
        query = '''
            SELECT p.id, c.nome, c.cognome, p.in_qualita_di, p.tipologia_immobile, p.tipologia_pratica, p.tipo, p.tipo_dettaglio, p.stato, p.scadenza 
            FROM pratiche p JOIN clienti c ON p.cliente_id = c.id
            WHERE c.nome LIKE ? OR c.cognome LIKE ? OR p.tipologia_immobile LIKE ? OR p.tipologia_pratica LIKE ? OR p.tipo LIKE ? OR p.tipo_dettaglio LIKE ?
            ORDER BY p.id DESC
        '''
        parametri = (f"%{testo}%", f"%{testo}%", f"%{testo}%", f"%{testo}%", f"%{testo}%", f"%{testo}%")
        self.carica_pratiche(query, parametri)

    def reset_ricerca(self):
        self.entry_ricerca.delete(0, tk.END)
        self.carica_pratiche()

if __name__ == "__main__":
    root = tk.Tk()
    app = GestionaleGeometra(root)
    root.mainloop()