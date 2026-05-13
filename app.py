import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import openpyxl
from datetime import datetime
import os
import cargador


# ── Paleta de colores ──────────────────────────────────────────────────────────
BG        = "#0A1628"   # Azul marino profundo
SURFACE   = "#112240"   # Azul marino medio
SURFACE2  = "#0D1B36"   # Azul marino oscuro secundario
ACCENT    = "#C8102E"   # Rojo institucional
ACCENT_LT = "#E8314E"   # Rojo claro / hover
TEXT      = "#E8EDF5"   # Blanco azulado
TEXT_DIM  = "#7A8BAA"   # Gris azulado tenue
SUCCESS   = "#2ECC71"   # Verde éxito
DANGER    = "#C8102E"   # Rojo error
ENTRY_BG  = "#071020"   # Fondo campo de entrada
BORDER    = "#1E3A5F"   # Borde azul oscuro
HEADER_BG = "#C8102E"   # Encabezado tabla rojo
ROW_ALT   = "#0F1E35"   # Fila alternada


class FormularioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Transacciones")
        self.geometry("620x700")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.registros = []
        self.sum_montos = 0
        self.sum_correlativos = 0
        self.estrategia = None
        self.errores_presentes = False

        self.filas: list[dict] = []

        self._build_ui()

    # ── Construcción UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Barra superior de marca ────────────────────────────────────────────
        header = tk.Frame(self, bg=ACCENT, height=5)
        header.pack(fill="x")

        # ── Encabezado ─────────────────────────────────────────────────────────
        title_frame = tk.Frame(self, bg=BG)
        title_frame.pack(fill="x", padx=32, pady=(22, 0))

        # Indicador lateral rojo
        tk.Frame(title_frame, bg=ACCENT, width=4).pack(side="left", fill="y", padx=(0, 12))

        title_text = tk.Frame(title_frame, bg=BG)
        title_text.pack(side="left")

        tk.Label(
            title_text, text="GESTOR DE TRANSACCIONES",
            bg=BG, fg=TEXT,
            font=("Trebuchet MS", 15, "bold")
        ).pack(anchor="w")

        tk.Label(
            title_text, text="Sistema de procesamiento bancario",
            bg=BG, fg=TEXT_DIM,
            font=("Trebuchet MS", 8)
        ).pack(anchor="w")

        # ── Separador ──────────────────────────────────────────────────────────
        tk.Frame(self, bg=BORDER, height=1).pack(fill="x", padx=32, pady=(14, 0))

        # ── Tarjeta del formulario ─────────────────────────────────────────────
        card = tk.Frame(self, bg=SURFACE, bd=0, relief="flat")
        card.pack(padx=32, pady=(18, 0), fill="x")

        # Borde superior rojo
        tk.Frame(card, bg=ACCENT, height=3).pack(fill="x")

        inner = tk.Frame(card, bg=SURFACE, padx=24, pady=18)
        inner.pack(fill="x")

        # Tipo de Transacción
        self._label(inner, "▸  TIPO DE TRANSACCIÓN")
        self.tipo_var = tk.StringVar(value="Interna")
        tipo_cb = ttk.Combobox(
            inner,
            textvariable=self.tipo_var,
            values=["Interna", "Sinpe"],
            state="readonly",
            font=("Trebuchet MS", 10),
        )
        self._style_combobox(tipo_cb)

        # ── Botones ────────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(padx=32, pady=(16, 0), fill="x")

        btn_row = tk.Frame(btn_frame, bg=BG)
        btn_row.pack(fill="x")

        self._btn(
            btn_row,
            "📂  CARGAR EXCEL",
            self._cargar_excel,
            bg=SURFACE, fg=TEXT, active_bg=BORDER
        ).pack(side="left", expand=True, fill="x", padx=(0, 6))

        self._btn(
            btn_row,
            "💾  GENERAR .TXT",
            self._generar_txt,
            bg=ACCENT, fg="#FFFFFF", active_bg=ACCENT_LT
        ).pack(side="left", expand=True, fill="x", padx=(6, 0))

        # ── Sección de errores ─────────────────────────────────────────────────
        error_label_frame = tk.Frame(self, bg=BG)
        error_label_frame.pack(padx=32, pady=(20, 0), fill="x")

        tk.Frame(error_label_frame, bg=ACCENT, width=3).pack(side="left", fill="y", padx=(0, 8))
        tk.Label(
            error_label_frame, text="REGISTRO DE ERRORES",
            bg=BG, fg=TEXT_DIM,
            font=("Trebuchet MS", 8, "bold")
        ).pack(side="left", anchor="w")

        self.error_count_var = tk.StringVar(value="")
        tk.Label(
            error_label_frame, textvariable=self.error_count_var,
            bg=BG, fg=ACCENT,
            font=("Trebuchet MS", 8, "bold")
        ).pack(side="right", anchor="e")

        # ── Tabla de errores ───────────────────────────────────────────────────
        table_frame = tk.Frame(self, bg=SURFACE, bd=0)
        table_frame.pack(padx=32, pady=(6, 0), fill="x")

        # Encabezado de tabla
        header_row = tk.Frame(table_frame, bg=HEADER_BG)
        header_row.pack(fill="x")

        tk.Label(
            header_row, text="FILA", width=8,
            bg=HEADER_BG, fg="#FFFFFF",
            font=("Trebuchet MS", 8, "bold"),
            anchor="center", pady=6
        ).pack(side="left")

        tk.Frame(header_row, bg="#A00020", width=1).pack(side="left", fill="y")

        tk.Label(
            header_row, text="DESCRIPCIÓN DEL ERROR",
            bg=HEADER_BG, fg="#FFFFFF",
            font=("Trebuchet MS", 8, "bold"),
            anchor="w", pady=6, padx=8
        ).pack(side="left", fill="x", expand=True)

        # Contenedor con scroll para las filas
        canvas_container = tk.Frame(table_frame, bg=SURFACE2, height=150)
        canvas_container.pack(fill="x")
        canvas_container.pack_propagate(False)

        self.error_canvas = tk.Canvas(
            canvas_container, bg=SURFACE2,
            highlightthickness=0, height=150
        )
        scrollbar = ttk.Scrollbar(
            canvas_container, orient="vertical",
            command=self.error_canvas.yview
        )
        self.error_canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side="right", fill="y")
        self.error_canvas.pack(side="left", fill="both", expand=True)

        self.error_inner = tk.Frame(self.error_canvas, bg=SURFACE2)
        self.error_canvas_window = self.error_canvas.create_window(
            (0, 0), window=self.error_inner, anchor="nw"
        )
        self.error_inner.bind("<Configure>", self._on_error_frame_configure)
        self.error_canvas.bind("<Configure>", self._on_canvas_configure)

        # Placeholder inicial
        self._show_empty_error_state()

        # ── Barra de estado ────────────────────────────────────────────────────
        status_frame = tk.Frame(self, bg=SURFACE2)
        status_frame.pack(side="bottom", fill="x")

        tk.Frame(status_frame, bg=ACCENT, height=2).pack(fill="x")

        self.status_var = tk.StringVar(value="● Listo")
        self.status_label = tk.Label(
            status_frame, textvariable=self.status_var,
            bg=SURFACE2, fg=TEXT_DIM,
            font=("Trebuchet MS", 8),
            anchor="w", padx=14, pady=6
        )
        self.status_label.pack(fill="x")

    # ── Helpers de widgets ─────────────────────────────────────────────────────

    def _label(self, parent, text: str):
        tk.Label(
            parent, text=text,
            bg=SURFACE, fg=TEXT_DIM,
            font=("Trebuchet MS", 7, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(4, 3))

    def _btn(self, parent, text, cmd, bg, fg, active_bg):
        b = tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg, fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            font=("Trebuchet MS", 9, "bold"),
            cursor="hand2",
            pady=11,
            bd=0,
        )
        # Hover effect
        b.bind("<Enter>", lambda e: b.config(bg=active_bg))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    def _style_combobox(self, cb):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(
            "TCombobox",
            fieldbackground=ENTRY_BG,
            background=SURFACE,
            foreground=TEXT,
            arrowcolor=ACCENT,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            selectbackground=ACCENT,
            selectforeground="#FFFFFF",
            font=("Trebuchet MS", 10),
        )
        style.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)])
        cb.pack(fill="x", pady=(0, 4), ipady=5)

        # Scrollbar style
        style.configure(
            "Vertical.TScrollbar",
            background=SURFACE,
            troughcolor=SURFACE2,
            arrowcolor=TEXT_DIM,
            bordercolor=BORDER,
        )

    # ── Tabla de errores ───────────────────────────────────────────────────────

    def _on_error_frame_configure(self, event):
        self.error_canvas.configure(scrollregion=self.error_canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self.error_canvas.itemconfig(self.error_canvas_window, width=event.width)

    def _show_empty_error_state(self):
        for w in self.error_inner.winfo_children():
            w.destroy()
        tk.Label(
            self.error_inner,
            text="Sin errores registrados",
            bg=SURFACE2, fg=TEXT_DIM,
            font=("Trebuchet MS", 8, "italic"),
            pady=20
        ).pack(expand=True)
        self.error_count_var.set("")

    def _populate_error_table(self, errores: dict):
        for w in self.error_inner.winfo_children():
            w.destroy()

        if not errores:
            self._show_empty_error_state()
            return

        self.error_count_var.set(f"{len(errores)} error(es)")
        items = sorted(list(errores.items()))
        for i, (fila, err) in enumerate(items):
            row_bg = ROW_ALT if i % 2 == 0 else SURFACE2
            row = tk.Frame(self.error_inner, bg=row_bg)
            row.pack(fill="x")

            # Columna fila
            tk.Label(
                row, text=str(fila), width=8,
                bg=row_bg, fg=ACCENT_LT,
                font=("Courier New", 8, "bold"),
                anchor="center", pady=5
            ).pack(side="left")

            tk.Frame(row, bg=BORDER, width=1).pack(side="left", fill="y")

            # Columna descripción
            tk.Label(
                row, text=str(err),
                bg=row_bg, fg=TEXT,
                font=("Trebuchet MS", 8),
                anchor="w", padx=8, pady=5,
                wraplength=380, justify="left"
            ).pack(side="left", fill="x", expand=True)

            # Separador horizontal
            tk.Frame(self.error_inner, bg=BORDER, height=1).pack(fill="x")

    # ── Lógica ─────────────────────────────────────────────────────────────────

    def _cargar_excel(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            self.estrategia = (
                cargador.EstrategiaSIN()
                if self.tipo_var.get() == "Sinpe"
                else cargador.EstrategiaNormal()
            )
            registros, sum_monto, sum_correlativos, errores = cargador.cargar_registros(
                path, self.estrategia
            )
            self.registros = registros
            self.sum_montos = sum_monto
            self.sum_correlativos = sum_correlativos

            for r in registros:
                print(r.to_env())
            print(f"Sumatoria Monto: {sum_monto}, Sumatoria Correlativos: {sum_correlativos}")

            # Poblar tabla de errores
            self._populate_error_table(errores)

            if errores:
                self.errores_presentes = True
                self._status(
                    f"⚠  {len(registros)} fila(s) cargadas · {len(errores)} error(es) detectados",
                    "#F0A500"
                )
            else:
                self.errores_presentes = False
                self._status(f"✔  {len(registros)} fila(s) cargadas exitosamente.", SUCCESS)

        except Exception as e:
            messagebox.showerror("Error al cargar Excel", str(e))
            self._status("✖  Error al cargar el archivo Excel.", DANGER)

    def _generar_txt(self):
        if not self.registros or len(self.registros) < 2:
            messagebox.showwarning(
                "Sin datos",
                "No hay registros para exportar.\n"
                "Complete el formulario o cargue un Excel."
            )
            return
        
        if self.errores_presentes:
            continuar = messagebox.askyesno(
                "Errores detectados",
                "Hay errores presentes en la tabla.\n\n"
                "¿Desea continuar con la generación del archivo?"
            )

            if not continuar:
                return

        archivo = cargador.generar_txt(
            suma_monto=self.sum_montos,
            suma_corr=self.sum_correlativos,
            estrategia= self.estrategia,
            registros=self.registros
        )

        extension = (
            ".SIN"
            if isinstance(self.estrategia, cargador.EstrategiaSIN)
            else ".ENV"
        )

        path = filedialog.asksaveasfilename(
            title="Guardar archivo",
            defaultextension=extension,
            filetypes=[
                (f"{extension} files", f"*{extension}"),
                ("All files", "*.*")
            ]
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(archivo)

            self._status(
                f"✔  Guardado: {os.path.basename(path)} · {len(self.registros)} registros",
                SUCCESS
            )
            messagebox.showinfo(
                "Éxito",
                f"Archivo generado correctamente.\n{len(self.registros)} registro(s) exportados."
            )
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))
            self._status("✖  Error al guardar el archivo.", DANGER)

    def _status(self, msg: str, color: str = TEXT_DIM):
        self.status_var.set(msg)
        self.status_label.config(fg=color)


if __name__ == "__main__":
    app = FormularioApp()
    app.mainloop()