import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import openpyxl
from datetime import datetime
import os
import cargador


# ── Paleta de colores ──────────────────────────────────────────────────────────
BG        = "#1E1E2E"
SURFACE   = "#2A2A3E"
ACCENT    = "#7C6AF7"
ACCENT_LT = "#9D8FFF"
TEXT      = "#E8E6F0"
TEXT_DIM  = "#8884A8"
SUCCESS   = "#50FA7B"
DANGER    = "#FF5C57"
ENTRY_BG  = "#13131F"
BORDER    = "#3D3B57"


class FormularioApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestor de Transacciones")
        self.geometry("520x560")
        self.resizable(False, False)
        self.configure(bg=BG)

        # Estado
        self.filas: list[dict] = []

        self._build_ui()

    # ── Construcción UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        # Título
        tk.Label(
            self, text="Gestor de Transacciones",
            bg=BG, fg=ACCENT_LT,
            font=("Courier New", 16, "bold")
        ).pack(pady=(28, 4))

        tk.Label(
            self, text="Ingrese los datos del registro",
            bg=BG, fg=TEXT_DIM,
            font=("Courier New", 9)
        ).pack(pady=(0, 20))

        # ── Tarjeta del formulario ─────────────────────────────────────────────
        card = tk.Frame(self, bg=SURFACE, bd=0, relief="flat")
        card.pack(padx=32, fill="x")

        # Decoración: borde superior con acento
        accent_bar = tk.Frame(card, bg=ACCENT, height=3)
        accent_bar.pack(fill="x")

        inner = tk.Frame(card, bg=SURFACE, padx=24, pady=20)
        inner.pack(fill="x")

        # Num. Cliente
        self._label(inner, "Número de Cliente")
        self.num_cliente_var = tk.StringVar()
        self._entry(inner, self.num_cliente_var, "Ej: CLI-00123")

        # Fecha
        self._label(inner, "Fecha")
        self.fecha_var = tk.StringVar(value=datetime.today().strftime("%Y-%m-%d"))
        self._entry(inner, self.fecha_var, "YYYY-MM-DD")

        # Tipo de Transacción
        self._label(inner, "Tipo de Transacción")
        self.tipo_var = tk.StringVar(value="1")
        tipo_cb = ttk.Combobox(
            inner,
            textvariable=self.tipo_var,
            values=["1", "2"],
            state="readonly",
            font=("Courier New", 10),
        )
        self._style_combobox(tipo_cb)
        tipo_cb.pack(fill="x", pady=(0, 8))

        # ── Botones ────────────────────────────────────────────────────────────
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(padx=32, pady=(18, 0), fill="x")

        self._btn(
            btn_frame,
            "📂  Cargar Excel",
            self._cargar_excel,
            bg=SURFACE, fg=TEXT, active_bg=BORDER
        ).pack(fill="x", pady=(0, 10))

        self._btn(
            btn_frame,
            "💾  Generar archivo .txt",
            self._generar_txt,
            bg=ACCENT, fg="#FFFFFF", active_bg=ACCENT_LT
        ).pack(fill="x")

        # ── Barra de estado ────────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Listo")
        tk.Label(
            self, textvariable=self.status_var,
            bg=BG, fg=TEXT_DIM,
            font=("Courier New", 8),
            anchor="w"
        ).pack(side="bottom", fill="x", padx=32, pady=10)

    # ── Helpers de widgets ─────────────────────────────────────────────────────

    def _label(self, parent, text: str):
        tk.Label(
            parent, text=text,
            bg=SURFACE, fg=TEXT_DIM,
            font=("Courier New", 8, "bold"),
            anchor="w"
        ).pack(fill="x", pady=(6, 2))

    def _entry(self, parent, var: tk.StringVar, placeholder: str):
        e = tk.Entry(
            parent,
            textvariable=var,
            bg=ENTRY_BG, fg=TEXT,
            insertbackground=ACCENT,
            relief="flat",
            font=("Courier New", 10),
            bd=0,
        )
        e.pack(fill="x", ipady=7, pady=(0, 2))
        # Borde inferior simulado
        tk.Frame(parent, bg=BORDER, height=1).pack(fill="x", pady=(0, 4))

        # Placeholder
        if not var.get():
            e.insert(0, placeholder)
            e.config(fg=TEXT_DIM)
            e.bind("<FocusIn>",  lambda ev, en=e, ph=placeholder, v=var: self._on_focus_in(ev, en, ph, v))
            e.bind("<FocusOut>", lambda ev, en=e, ph=placeholder, v=var: self._on_focus_out(ev, en, ph, v))

    def _on_focus_in(self, _, entry, placeholder, var):
        if entry.get() == placeholder:
            entry.delete(0, "end")
            entry.config(fg=TEXT)

    def _on_focus_out(self, _, entry, placeholder, var):
        if not entry.get().strip():
            entry.insert(0, placeholder)
            entry.config(fg=TEXT_DIM)

    def _btn(self, parent, text, cmd, bg, fg, active_bg):
        b = tk.Button(
            parent,
            text=text,
            command=cmd,
            bg=bg, fg=fg,
            activebackground=active_bg,
            activeforeground=fg,
            relief="flat",
            font=("Courier New", 10, "bold"),
            cursor="hand2",
            pady=10,
            bd=0,
        )
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
            font=("Courier New", 10),
        )
        style.map("TCombobox", fieldbackground=[("readonly", ENTRY_BG)])
        cb.pack(fill="x", pady=(0, 4))

    # ── Lógica ─────────────────────────────────────────────────────────────────

    def _get_form_values(self):
        nc = self.num_cliente_var.get().strip()
        fe = self.fecha_var.get().strip()
        ti = self.tipo_var.get().strip()
        return nc, fe, ti

    def _cargar_excel(self):
        path = filedialog.askopenfilename(
            title="Seleccionar archivo Excel",
            filetypes=[("Excel files", "*.xlsx *.xls"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            registros, sum_monto, sum_correlativos = cargador.cargar_registros(path)
           

            self._status(f"✅  {len(registros)} fila(s) cargadas desde Excel.", SUCCESS)
        except Exception as e:
            messagebox.showerror("Error al cargar Excel", str(e))
            self._status("❌  Error al cargar Excel.", DANGER)

    def _generar_txt(self):
        # Agregar la fila del formulario si tiene datos válidos
        nc, fe, ti = self._get_form_values()
        registros = list(self.filas)  # copia

        if nc and nc not in ("Ej: CLI-00123",):
            registros.append({"num_cliente": nc, "fecha": fe, "tipo": ti})

        if not registros:
            messagebox.showwarning(
                "Sin datos",
                "No hay registros para exportar.\n"
                "Complete el formulario o cargue un Excel."
            )
            return

        path = filedialog.asksaveasfilename(
            title="Guardar archivo",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("NUM_CLIENTE|FECHA|TIPO_TRANSACCION\n")
                f.write("-" * 48 + "\n")
                for r in registros:
                    tipo_cod = "1" if str(r["tipo"]).startswith("1") else "2"
                    f.write(f"{r['num_cliente']}|{r['fecha']}|{tipo_cod}\n")

            self._status(
                f"✅  Archivo guardado: {os.path.basename(path)} ({len(registros)} reg.)",
                SUCCESS
            )
            messagebox.showinfo(
                "Éxito",
                f"Archivo generado correctamente.\n{len(registros)} registro(s) exportados."
            )
        except Exception as e:
            messagebox.showerror("Error al guardar", str(e))
            self._status("❌  Error al guardar el archivo.", DANGER)

    def _status(self, msg: str, color: str = TEXT_DIM):
        self.status_var.set(msg)
        for w in self.winfo_children():
            if isinstance(w, tk.Label) and w.cget("textvariable") == str(self.status_var):
                w.config(fg=color)
                break
        # Buscar el label de status directamente
        self.after(0, lambda: self._set_status_color(color))

    def _set_status_color(self, color):
        for w in self.winfo_children():
            if isinstance(w, tk.Label):
                try:
                    if w.cget("textvariable") and self.status_var:
                        w.config(fg=color)
                except Exception:
                    pass


if __name__ == "__main__":
    app = FormularioApp()
    app.mainloop()