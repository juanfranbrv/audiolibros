import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import asyncio
import sys
import os
import tempfile
from datetime import datetime
import queue

# Importar las funciones del script original
from audiolibro_creator import (
    create_arg_parser, list_available_voices, process_audiobook_creation,
    DEFAULT_OUTPUT_DIR, console, suppress_asyncio_exceptions
)
# Nuevo módulo de extracción
from text_extractor import get_text_content
# Nuevo módulo de configuración
import config_manager

# Configurar CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

def default_output_name(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def capture_generation_settings(gui):
    return {
        "output_name": gui.output_file_name.get(),
        "output_directory": gui.config.get("last_output_directory", DEFAULT_OUTPUT_DIR),
        "voice": gui.selected_voice.get(),
        "retries": gui.retries_value.get(),
        "rate": gui.rate_value.get(),
        "strategy": gui.chunking_strategy.get(),
    }

def create_processed_input_file(text):
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".txt",
        prefix="audiolibro_",
        delete=False,
    ) as temp_file:
        temp_file.write(text)
        return temp_file.name

def schedule_error_dialog(root, error_message):
    root.after(
        0,
        lambda message=error_message: messagebox.showerror("Error", message),
    )

class AudiobookCreatorGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Generador de Audiolibros v2.5")
        self.root.geometry("1000x800")
        
        # Cargar configuración
        self.config = config_manager.load_config()

        # Variables
        self.text_file_path = tk.StringVar()
        self.output_file_name = tk.StringVar()
        
        # Variables de Configuración
        self.selected_voice = tk.StringVar(value=self.config["voice"])
        self.rate_value = tk.StringVar(value=self.config["rate"])
        self.chunking_strategy = tk.StringVar(value=self.config["chunking_strategy"])
        self.retries_value = tk.IntVar(value=self.config["retries"])

        # Cola y Estado
        self.log_queue = queue.Queue()
        self.start_time = None
        self.loaded_preview_path = None
        
        self.setup_ui()
        self.update_log()
    
    def setup_ui(self):
        # 2 PESTAÑAS: Principal, Texto (Edición/Preview)
        self.tabview = ctk.CTkTabview(self.root)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)

        self.tab_main = self.tabview.add("Principal")
        self.tab_text = self.tabview.add("Texto & Edición")

        self.setup_main_tab()
        self.setup_text_tab()

    def setup_main_tab(self):
        # --- SECCIÓN 1: ARCHIVO ---
        file_frame = ctk.CTkFrame(self.tab_main)
        file_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(file_frame, text="1. Selección de Archivo", font=ctk.CTkFont(weight="bold", size=16)).pack(anchor="w", padx=10, pady=5)
        
        # Entrada
        input_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        input_row.pack(fill="x", padx=10, pady=5)
        self.text_file_entry = ctk.CTkEntry(input_row, textvariable=self.text_file_path, placeholder_text="Selecciona PDF, EPUB o TXT...")
        self.text_file_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkButton(input_row, text="📁 Buscar", command=self.browse_text_file, width=100).pack(side="right")

        # Salida
        out_row = ctk.CTkFrame(file_frame, fg_color="transparent")
        out_row.pack(fill="x", padx=10, pady=5)
        self.output_entry = ctk.CTkEntry(out_row, textvariable=self.output_file_name, placeholder_text="Nombre del archivo final...")
        self.output_entry.pack(side="left", fill="x", expand=True, padx=(0,10))
        ctk.CTkLabel(out_row, text=".mp3").pack(side="right")

        # --- SECCIÓN 2: CONFIGURACIÓN (Compacta) ---
        conf_frame = ctk.CTkFrame(self.tab_main)
        conf_frame.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(conf_frame, text="2. Configuración de Voz", font=ctk.CTkFont(weight="bold", size=16)).pack(anchor="w", padx=10, pady=5)

        grid_frame = ctk.CTkFrame(conf_frame, fg_color="transparent")
        grid_frame.pack(fill="x", padx=10, pady=5)

        # Fila 1
        ctk.CTkLabel(grid_frame, text="Voz:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
        self.voice_combo = ctk.CTkComboBox(grid_frame, values=["es-ES-AlvaroNeural", "es-MX-DaliaNeural", "es-ES-ElviraNeural", "en-US-ChristopherNeural"], variable=self.selected_voice, width=200)
        self.voice_combo.grid(row=0, column=1, padx=5, pady=5, sticky="w")
        
        ctk.CTkLabel(grid_frame, text="Velocidad:").grid(row=0, column=2, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(grid_frame, textvariable=self.rate_value, width=80).grid(row=0, column=3, padx=5, pady=5, sticky="w")

        # Fila 2
        ctk.CTkLabel(grid_frame, text="Estrategia:").grid(row=1, column=0, padx=5, pady=5, sticky="e")
        ctk.CTkComboBox(grid_frame, values=["smart", "legacy"], variable=self.chunking_strategy, width=150).grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ctk.CTkLabel(grid_frame, text="Reintentos:").grid(row=1, column=2, padx=5, pady=5, sticky="e")
        ctk.CTkEntry(grid_frame, textvariable=self.retries_value, width=80).grid(row=1, column=3, padx=5, pady=5, sticky="w")

        # --- SECCIÓN 3: EJECUCIÓN Y LOGS ---
        run_frame = ctk.CTkFrame(self.tab_main)
        run_frame.pack(fill="both", expand=True, padx=10, pady=10)

        # Botón Grande
        self.create_button = ctk.CTkButton(run_frame, text="▶ GENERAR AUDIOLIBRO", command=self.create_audiobook, height=50, font=ctk.CTkFont(size=18, weight="bold"), fg_color="green", hover_color="darkgreen")
        self.create_button.pack(fill="x", padx=20, pady=15)

        # Barra y Estado
        self.status_label = ctk.CTkLabel(run_frame, text="Listo.", anchor="w")
        self.status_label.pack(fill="x", padx=20)
        
        self.progress_bar = ctk.CTkProgressBar(run_frame)
        self.progress_bar.pack(fill="x", padx=20, pady=5)
        self.progress_bar.set(0)
        
        self.time_label = ctk.CTkLabel(run_frame, text="", text_color="gray")
        self.time_label.pack(pady=2)

        # Logs (Expansible)
        ctk.CTkLabel(run_frame, text="Registro:").pack(anchor="w", padx=20, pady=(10,0))
        self.log_text = ctk.CTkTextbox(run_frame, height=100)
        self.log_text.pack(fill="both", expand=True, padx=20, pady=10)

    def setup_text_tab(self):
        ctrl_frame = ctk.CTkFrame(self.tab_text, height=40)
        ctrl_frame.pack(fill="x", padx=10, pady=5)

        ctk.CTkButton(ctrl_frame, text="🔄 Recargar desde Archivo", command=self.load_preview).pack(side="left", padx=5)
        ctk.CTkLabel(ctrl_frame, text="Aquí puedes editar el texto manualmente si encuentras errores.", text_color="gray").pack(side="left", padx=10)

        self.preview_text = ctk.CTkTextbox(self.tab_text, wrap="word") 
        self.preview_text.pack(fill="both", expand=True, padx=10, pady=10)

    # --- LÓGICA ---
    def save_current_config(self):
        self.config["voice"] = self.selected_voice.get()
        self.config["rate"] = self.rate_value.get()
        self.config["chunking_strategy"] = self.chunking_strategy.get()
        self.config["retries"] = self.retries_value.get()
        config_manager.save_config(self.config)

    def browse_text_file(self):
        initial_dir = self.config.get("last_input_directory", "/")
        file_path = filedialog.askopenfilename(
            initialdir=initial_dir,
            title="Seleccionar archivo",
            filetypes=[("Archivos soportados", "*.txt *.pdf *.epub"), ("Todos", "*.*")]
        )
        if file_path:
            self.text_file_path.set(file_path)
            self.config["last_input_directory"] = os.path.dirname(file_path)
            self.output_file_name.set(default_output_name(file_path))
            
            # Auto-cargar preview al seleccionar archivo
            self.load_preview()

    def load_preview(self):
        file_path = self.text_file_path.get()
        if not file_path or not os.path.exists(file_path):
            return # Silent fail or simple ignore
        
        self.loaded_preview_path = None
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", "Procesando texto...")
        
        def _load():
            try:
                # Usamos el nuevo extractor que ya limpia
                text = get_text_content(file_path)
                self.root.after(
                    0,
                    lambda path=file_path, content=text: self._apply_preview_if_current(
                        path, content
                    ),
                )
            except Exception as e:
                error_message = str(e)
                self.root.after(
                    0,
                    lambda path=file_path, message=error_message: self._show_preview_error_if_current(
                        path, message
                    ),
                )
        
        threading.Thread(target=_load, daemon=True).start()

    def _apply_preview_if_current(self, file_path, text):
        if self.text_file_path.get() == file_path:
            self.loaded_preview_path = file_path
            self._update_preview(text)

    def _show_preview_error_if_current(self, file_path, error_message):
        if self.text_file_path.get() == file_path:
            messagebox.showerror("Error", error_message)

    def _update_preview(self, text):
        self.preview_text.delete("1.0", "end")
        self.preview_text.insert("1.0", text)
        # Cambiar foco a pestaña texto si el usuario quiere ver
        # self.tabview.set("Texto & Edición") # Opcional: no forzar cambio

    def log_message(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_queue.put(f"[{timestamp}] {message}\n")

    def update_log(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.insert("end", msg)
                self.log_text.see("end")
        except queue.Empty:
            pass
        self.root.after(100, self.update_log)

    def update_status(self, text):
        self.root.after(0, lambda: self.status_label.configure(text=text))
        self.log_message(text)

    def update_progress(self, current, total):
        # (Misma logica de progreso)
        import time
        from datetime import timedelta
        if self.start_time is None: self.start_time = time.time()
        progress = current / total if total > 0 else 0
        
        if current > 0:
            elapsed = time.time() - self.start_time
            avg = elapsed / current
            rem = (total - current) * avg
            time_str = str(timedelta(seconds=int(rem)))
        else:
            time_str = "--:--"
            
        self.root.after(0, lambda: [
            self.progress_bar.set(progress),
            self.time_label.configure(text=f"{int(progress*100)}% - Restante: {time_str}")
        ])

    def create_audiobook(self):
        if not self.text_file_path.get():
            messagebox.showerror("Error", "Selecciona un archivo.")
            return
        if self.loaded_preview_path != self.text_file_path.get():
            messagebox.showerror(
                "Error", "Espera a que termine de cargarse el texto del libro."
            )
            return

        self.save_current_config()
        self.create_button.configure(state="disabled", fg_color="gray")
        self.start_time = None
        self.log_text.delete("1.0", "end")

        # IMPORTANTE: Usar el texto del PREVIEW si ha sido editado, o cargar archivo si no?
        # Para consistencia con la edición manual:
        # Deberíamos "guardar" el contenido del preview en un archivo temporal o pasarlo directamente.
        # process_audiobook_creation actualmente lee del archivo.
        # MODIFICACION REQUERIDA: process_audiobook_creation debería aceptar texto raw o path.
        # Por ahora, para no romper compatibilidad masiva, guardaremos el contenido del textbox en un temp file
        # y pasaremos ESE temp file al procesador.
        
        edited_text = self.preview_text.get("1.0", "end-1c")
        generation_settings = capture_generation_settings(self)
        
        def _run():
            temp_file = None
            loop = None
            final_status = "Error."
            try:
                temp_file = create_processed_input_file(edited_text)

                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.set_exception_handler(suppress_asyncio_exceptions)
                
                out_name = generation_settings["output_name"]
                if not out_name.endswith(".mp3"): out_name += ".mp3"
                if not os.path.isabs(out_name):
                    save_dir = generation_settings["output_directory"]
                    out_path = os.path.join(save_dir, out_name)
                    os.makedirs(os.path.dirname(out_path), exist_ok=True)
                else:
                    out_path = out_name

                # Usar el archivo temporal como entrada
                loop.run_until_complete(process_audiobook_creation(
                    temp_file, # <--- USAR FILE TEMPORAL
                    out_path,
                    generation_settings["voice"],
                    generation_settings["retries"],
                    generation_settings["rate"],
                    generation_settings["strategy"],
                    status_callback=self.update_status,
                    progress_callback=self.update_progress
                ))
                final_status = "Finalizado."
                self.root.after(
                    0,
                    lambda path=out_path: messagebox.showinfo("Éxito", f"Creado: {path}"),
                )
            except Exception as e:
                schedule_error_dialog(self.root, str(e))
            finally:
                if loop is not None and not loop.is_closed():
                    loop.close()
                if temp_file and os.path.exists(temp_file): os.remove(temp_file)
                self.root.after(
                    0,
                    lambda status=final_status: self.restore_ui(status),
                )

        threading.Thread(target=_run, daemon=True).start()

    def restore_ui(self, status="Finalizado."):
        self.create_button.configure(state="normal", fg_color="green")
        self.status_label.configure(text=status)

    def run(self):
        self.root.mainloop()

def main():
    app = AudiobookCreatorGUI()
    app.run()

if __name__ == "__main__":
    main()
