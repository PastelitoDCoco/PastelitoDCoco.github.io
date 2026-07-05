import os
import time
import threading
import concurrent.futures
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime, timedelta


class MegaCercadorApp:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Mega cercador ultra ràpid de text dins d'arxius")
        self.root.geometry("950x620")
        self.root.resizable(True, True)

        self.selected_folder = None
        self.total_matches = 0
        self.stop_event = threading.Event()
        self.searching = False
        self.search_icon_frames = ["⏳", "🔎", "✨", "🚀"]
        self.search_icon_index = 0

        self._build_interface()

    def _build_interface(self):
        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Futuristic.TFrame", background="#0f172a")
        style.configure("Futuristic.TLabel", background="#0f172a", foreground="#7dd3fc", font=("Segoe UI", 10))
        style.configure("Futuristic.TButton", background="#2563eb", foreground="#ffffff", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", background="#0f172a", fieldbackground="#0f172a", foreground="#e2e8f0", rowheight=24)
        style.map("Futuristic.TButton", background=[("active", "#38bdf8")])

        self.root.configure(bg="#0f172a")

        control_frame = ttk.Frame(self.root, padding=(10, 10, 10, 0), style="Futuristic.TFrame")
        control_frame.pack(fill=tk.X)

        folder_button = ttk.Button(control_frame, text="Seleccionar carpeta", command=self.select_folder, style="Futuristic.TButton")
        folder_button.grid(row=0, column=0, sticky=tk.W)
        self.folder_button = folder_button

        self.folder_label = ttk.Label(control_frame, text="Cap carpeta seleccionada", wraplength=620, style="Futuristic.TLabel")
        self.folder_label.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), columnspan=2)

        self.search_icon_label = ttk.Label(control_frame, text="", style="Futuristic.TLabel", font=("Segoe UI Emoji", 18))
        self.search_icon_label.grid(row=0, column=3, sticky=tk.E, padx=(10, 0))

        search_label = ttk.Label(control_frame, text="Terme a buscar:", style="Futuristic.TLabel")
        search_label.grid(row=1, column=0, pady=(10, 0), sticky=tk.W)

        self.search_entry = ttk.Entry(control_frame, width=70)
        self.search_entry.grid(row=1, column=1, pady=(10, 0), sticky=tk.W)

        self.search_button = ttk.Button(control_frame, text="Buscar", command=self.start_search, style="Futuristic.TButton")
        self.search_button.grid(row=1, column=2, padx=(10, 0), pady=(10, 0), sticky=tk.W)

        self.stop_button = ttk.Button(control_frame, text="Aturar", command=self.stop_search, state="disabled", style="Futuristic.TButton")
        self.stop_button.grid(row=1, column=3, padx=(10, 0), pady=(10, 0), sticky=tk.W)

        result_frame = ttk.Frame(self.root, padding=(10, 10, 10, 10), style="Futuristic.TFrame")
        result_frame.pack(fill=tk.BOTH, expand=True)

        columns = ("fitxer", "linia", "text")
        self.result_tree = ttk.Treeview(result_frame, columns=columns, show="headings", selectmode="browse", style="Treeview")
        self.result_tree.heading("fitxer", text="Arxiu i ruta")
        self.result_tree.heading("linia", text="Línia")
        self.result_tree.heading("text", text="Text trobat")
        self.result_tree.column("fitxer", width=450, anchor=tk.W)
        self.result_tree.column("linia", width=70, anchor=tk.CENTER)
        self.result_tree.column("text", width=400, anchor=tk.W)
        self.result_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.result_tree.yview)
        self.result_tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_label = ttk.Label(self.root, text="Preparat per cercar.", padding=(10, 0, 10, 10), style="Futuristic.TLabel")
        self.status_label.pack(fill=tk.X)

    def select_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.selected_folder = folder
            self.folder_label.config(text=folder)
            self.status_label.config(text="Carpeta seleccionada: {}".format(folder))

    def _animate_search_icon(self):
        if not self.searching:
            return
        self.search_icon_label.config(text=self.search_icon_frames[self.search_icon_index])
        self.search_icon_index = (self.search_icon_index + 1) % len(self.search_icon_frames)
        self.root.after(300, self._animate_search_icon)

    def _start_search_animation(self):
        self.searching = True
        self.search_icon_index = 0
        self._animate_search_icon()

    def _stop_search_animation(self):
        self.searching = False
        self.search_icon_label.config(text="")

    def stop_search(self):
        if self.searching:
            self.stop_event.set()
            self._update_status("Aturant la cerca... espera uns instants")
            self.stop_button.config(state="disabled")

    def start_search(self):
        term = self.search_entry.get().strip()
        if not self.selected_folder:
            messagebox.showwarning("Atenció", "Cal seleccionar una carpeta abans de buscar.")
            return
        if not term:
            messagebox.showwarning("Atenció", "Introdueix un terme a buscar.")
            return

        self.stop_event.clear()
        self._set_controls_state("disabled")
        self._clear_results()
        self.status_label.config(text="Iniciant la cerca...")
        self._start_search_animation()
        threading.Thread(target=self._search_in_background, args=(term,), daemon=True).start()

    def _search_in_background(self, term):
        start_time = time.perf_counter()
        file_paths = self._gather_files(self.selected_folder)
        self.total_matches = 0

        if not file_paths:
            self._update_status("No s'han trobat arxius .php ni .java a la carpeta seleccionada.")
            self._set_controls_state("normal")
            return

        max_workers = os.cpu_count() or 4
        self._update_status(f"Cercant '{term}' en {len(file_paths)} arxius amb {max_workers} fils...")

        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(self._search_file, path, term) for path in file_paths]
            for future in concurrent.futures.as_completed(futures):
                if self.stop_event.is_set():
                    break
                result_rows = future.result()
                if result_rows:
                    self.total_matches += len(result_rows)
                    self.root.after(0, self._insert_results, result_rows)

        elapsed = time.perf_counter() - start_time
        self._stop_search_animation()
        if self.stop_event.is_set():
            final_message = f"Cerca aturada després de {elapsed:.2f} s amb {self.total_matches} coincidències."
        else:
            final_message = f"Cerca finalitzada: {self.total_matches} coincidències en {elapsed:.2f} s."
        self._update_status(final_message)
        self.root.after(0, lambda: messagebox.showinfo("Resultat de la cerca", final_message))
        self._set_controls_state("normal")

    def _gather_files(self, base_folder):
        valid_extensions = {".php", ".java"}
        file_paths = []
        for root_dir, _, files in os.walk(base_folder):
            for name in files:
                _, ext = os.path.splitext(name)
                if ext.lower() in valid_extensions:
                    file_paths.append(os.path.join(root_dir, name))
        return file_paths

    def _search_file(self, path, term):
        results = []
        if self.stop_event.is_set():
            return results
        lower_term = term.lower()
        text_lines = self._read_file_lines(path)
        for line_number, line in enumerate(text_lines, start=1):
            if self.stop_event.is_set():
                break
            if lower_term in line.lower():
                snippet = line.strip()
                if len(snippet) > 220:
                    snippet = snippet[:220].rstrip() + "..."
                results.append((path, line_number, snippet))
        return results

    def _read_file_lines(self, path):
        encodings = ["utf-8", "latin-1", "cp1252"]
        for encoding in encodings:
            try:
                with open(path, "r", encoding=encoding, errors="ignore") as handle:
                    return handle.readlines()
            except (OSError, UnicodeError):
                continue
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as handle:
                return handle.readlines()
        except Exception:
            return []

    def _insert_results(self, rows):
        for path, line_number, snippet in rows:
            self.result_tree.insert("", tk.END, values=(path, line_number, snippet))

    def _clear_results(self):
        for item in self.result_tree.get_children():
            self.result_tree.delete(item)

    def _update_status(self, message):
        self.root.after(0, lambda: self.status_label.config(text=message))

    def _set_controls_state(self, state):
        for widget in self.root.winfo_children():
            if isinstance(widget, ttk.Frame):
                for child in widget.winfo_children():
                    if isinstance(child, ttk.Button) or isinstance(child, ttk.Entry):
                        child.config(state=state)
        if state == "disabled":
            self.stop_button.config(state="normal")
        else:
            self.stop_button.config(state="disabled")
        if state == "normal":
            self.search_entry.config(state="normal")

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    app = MegaCercadorApp()
    app.run()
