import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import asyncio
import sys
import os
from datetime import datetime
import queue

# Importar las funciones del script original
from audiolibro_creator import (
    create_arg_parser, list_available_voices, process_audiobook_creation,
    DEFAULT_OUTPUT_DIR, console, suppress_asyncio_exceptions
)

# Configurar CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class AudiobookCreatorGUI:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Generador de Audiolibros")
        self.root.geometry("800x700")
        
        # Variables
        self.text_file_path = tk.StringVar()
        self.output_file_name = tk.StringVar()
        self.selected_voice = tk.StringVar(value="es-ES-AlvaroNeural")
        self.rate_value = tk.StringVar(value="-5%")
        self.chunking_strategy = tk.StringVar(value="smart")
        self.retries_value = tk.IntVar(value=3)

        # Cola para comunicación entre hilos
        self.log_queue = queue.Queue()

        # Variables de progreso
        self.start_time = None
        self.total_chunks = 0
        
        self.setup_ui()
        self.update_log()
    
    def setup_ui(self):
        # Frame principal
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Título
        title_label = ctk.CTkLabel(
            main_frame, 
            text="Generador de Audiolibros con Edge-TTS",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.pack(pady=20)
        
        # Frame para configuración
        config_frame = ctk.CTkFrame(main_frame)
        config_frame.pack(fill="x", padx=20, pady=10)
        
        # Archivo de texto
        text_frame = ctk.CTkFrame(config_frame)
        text_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(text_frame, text="Archivo de texto (.txt):", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        text_file_frame = ctk.CTkFrame(text_frame)
        text_file_frame.pack(fill="x", padx=10, pady=(0,10))
        
        self.text_file_entry = ctk.CTkEntry(text_file_frame, textvariable=self.text_file_path, width=400)
        self.text_file_entry.pack(side="left", padx=(10,10), pady=10)
        
        ctk.CTkButton(
            text_file_frame, 
            text="Buscar", 
            command=self.browse_text_file,
            width=80
        ).pack(side="right", padx=(0,10), pady=10)
        
        # Nombre del archivo de salida
        output_frame = ctk.CTkFrame(config_frame)
        output_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(output_frame, text="Nombre del archivo de salida:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        output_entry_frame = ctk.CTkFrame(output_frame)
        output_entry_frame.pack(fill="x", padx=10, pady=(0,10))
        
        self.output_entry = ctk.CTkEntry(output_entry_frame, textvariable=self.output_file_name, width=400)
        self.output_entry.pack(side="left", padx=(10,10), pady=10)
        
        ctk.CTkLabel(output_entry_frame, text=".mp3", font=ctk.CTkFont(size=14)).pack(side="left", pady=10)
        
        # Configuración de voz
        voice_frame = ctk.CTkFrame(config_frame)
        voice_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkLabel(voice_frame, text="Configuración de voz:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))
        
        # Voz
        voice_row = ctk.CTkFrame(voice_frame)
        voice_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(voice_row, text="Voz:").pack(side="left", padx=(10,10))
        self.voice_combo = ctk.CTkComboBox(
            voice_row, 
            values=["es-ES-AlvaroNeural", "es-MX-DaliaNeural", "es-ES-ElviraNeural"],
            variable=self.selected_voice,
            width=200
        )
        self.voice_combo.pack(side="left", padx=(0,20))
        
        ctk.CTkButton(
            voice_row, 
            text="Ver todas las voces", 
            command=self.show_voices_window,
            width=120
        ).pack(side="right", padx=(0,10))
        
        # Velocidad
        rate_row = ctk.CTkFrame(voice_frame)
        rate_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(rate_row, text="Velocidad:").pack(side="left", padx=(10,10))
        self.rate_entry = ctk.CTkEntry(rate_row, textvariable=self.rate_value, width=100)
        self.rate_entry.pack(side="left", padx=(0,10))
        ctk.CTkLabel(rate_row, text="(ej: -5%, +10%)").pack(side="left")
        
        # Estrategia de fragmentación
        strategy_row = ctk.CTkFrame(voice_frame)
        strategy_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(strategy_row, text="Estrategia:").pack(side="left", padx=(10,10))
        self.strategy_combo = ctk.CTkComboBox(
            strategy_row, 
            values=["smart", "legacy"],
            variable=self.chunking_strategy,
            width=150
        )
        self.strategy_combo.pack(side="left", padx=(0,10))
        
        # Reintentos
        retries_row = ctk.CTkFrame(voice_frame)
        retries_row.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(retries_row, text="Reintentos:").pack(side="left", padx=(10,10))
        self.retries_spinbox = ctk.CTkEntry(retries_row, textvariable=self.retries_value, width=80)
        self.retries_spinbox.pack(side="left", padx=(0,10))
        
        # Botones de acción
        button_frame = ctk.CTkFrame(main_frame)
        button_frame.pack(fill="x", padx=20, pady=20)
        
        self.create_button = ctk.CTkButton(
            button_frame, 
            text="Crear Audiolibro", 
            command=self.create_audiobook,
            height=40,
            font=ctk.CTkFont(size=16, weight="bold")
        )
        self.create_button.pack(side="left", padx=(0,10), pady=10)
        
        self.stop_button = ctk.CTkButton(
            button_frame, 
            text="Detener", 
            command=self.stop_process,
            height=40,
            state="disabled"
        )
        self.stop_button.pack(side="left", padx=(0,10), pady=10)
        
        # Barra de progreso
        self.progress_bar = ctk.CTkProgressBar(button_frame)
        self.progress_bar.pack(side="right", padx=(10,0), pady=10, fill="x", expand=True)
        self.progress_bar.set(0)

        # Zona de estado
        status_frame = ctk.CTkFrame(main_frame)
        status_frame.pack(fill="x", padx=20, pady=(10,10))

        ctk.CTkLabel(status_frame, text="Estado:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))

        self.status_label = ctk.CTkLabel(
            status_frame,
            text="Esperando...",
            font=ctk.CTkFont(size=14),
            anchor="w",
            justify="left"
        )
        self.status_label.pack(fill="x", padx=10, pady=(0,5))

        # Etiqueta de tiempo estimado
        self.time_label = ctk.CTkLabel(
            status_frame,
            text="",
            font=ctk.CTkFont(size=12),
            anchor="w",
            text_color="gray"
        )
        self.time_label.pack(fill="x", padx=10, pady=(0,10))

        # Área de logs
        log_frame = ctk.CTkFrame(main_frame)
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0,20))

        ctk.CTkLabel(log_frame, text="Logs:", font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=10, pady=(10,5))

        self.log_text = ctk.CTkTextbox(log_frame, height=150)
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0,10))
    
    def browse_text_file(self):
        """Abrir diálogo para seleccionar archivo de texto"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar archivo de texto",
            filetypes=[("Archivos de texto", "*.txt"), ("Todos los archivos", "*.*")]
        )
        if file_path:
            self.text_file_path.set(file_path)
            # Auto-completar nombre de salida
            if not self.output_file_name.get():
                base_name = os.path.splitext(os.path.basename(file_path))[0]
                self.output_file_name.set(base_name)
    
    def show_voices_window(self):
        """Mostrar ventana con todas las voces disponibles"""
        voices_window = ctk.CTkToplevel(self.root)
        voices_window.title("Voces Disponibles")
        voices_window.geometry("600x400")
        
        # Crear lista de voces
        voices_frame = ctk.CTkFrame(voices_window)
        voices_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(voices_frame, text="Cargando voces...", font=ctk.CTkFont(size=16)).pack(pady=20)
        
        # Ejecutar en hilo separado
        def load_voices():
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                voices = loop.run_until_complete(list_available_voices())
                loop.close()
                
                # Actualizar UI en el hilo principal
                self.root.after(0, lambda: self.update_voices_window(voices_window))
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error al cargar voces: {e}"))
        
        threading.Thread(target=load_voices, daemon=True).start()
    
    def update_voices_window(self, window):
        """Actualizar ventana de voces con la lista cargada"""
        # Limpiar contenido anterior
        for widget in window.winfo_children():
            widget.destroy()
        
        # Crear nueva interfaz
        main_frame = ctk.CTkFrame(window)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(main_frame, text="Voces Disponibles", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(0,20))
        
        # Crear scrollable frame para las voces
        scroll_frame = ctk.CTkScrollableFrame(main_frame)
        scroll_frame.pack(fill="both", expand=True)
        
        # Aquí podrías agregar las voces dinámicamente
        # Por ahora, mostrar un mensaje
        ctk.CTkLabel(scroll_frame, text="Usa el comando --list-voices en CLI para ver todas las voces").pack(pady=20)
        
        ctk.CTkButton(window, text="Cerrar", command=window.destroy).pack(pady=10)
    
    def log_message(self, message):
        """Agregar mensaje al log"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {message}\n"
        self.log_queue.put(formatted_message)

    def update_status(self, status_text):
        """Actualizar zona de estado (sin acumular)"""
        self.root.after(0, lambda: self.status_label.configure(text=status_text))

    def update_progress(self, current, total):
        """Actualizar barra de progreso y calcular tiempo estimado"""
        import time
        from datetime import timedelta

        if self.start_time is None:
            self.start_time = time.time()
            self.total_chunks = total

        progress = current / total if total > 0 else 0
        self.root.after(0, lambda: self.progress_bar.set(progress))

        # Calcular tiempo estimado
        if current > 0:
            elapsed = time.time() - self.start_time
            avg_time_per_chunk = elapsed / current
            remaining_chunks = total - current
            estimated_remaining = avg_time_per_chunk * remaining_chunks

            percentage = (current / total * 100) if total > 0 else 0
            time_str = str(timedelta(seconds=int(estimated_remaining)))

            info_text = f"{percentage:.0f}% ({current}/{total}) - Tiempo restante: {time_str}"
            self.root.after(0, lambda: self.time_label.configure(text=info_text))
    
    def update_log(self):
        """Actualizar área de logs desde la cola"""
        try:
            while True:
                message = self.log_queue.get_nowait()
                self.log_text.insert("end", message)
                self.log_text.see("end")
        except queue.Empty:
            pass
        
        # Programar próxima actualización
        self.root.after(100, self.update_log)
    
    def create_audiobook(self):
        """Crear audiolibro en hilo separado"""
        if not self.text_file_path.get():
            messagebox.showerror("Error", "Debes seleccionar un archivo de texto")
            return
        
        if not os.path.exists(self.text_file_path.get()):
            messagebox.showerror("Error", "El archivo de texto no existe")
            return
        
        # Deshabilitar botón durante el proceso
        self.create_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.progress_bar.set(0)
        
        # Limpiar logs y resetear estado
        self.log_text.delete("1.0", "end")
        self.status_label.configure(text="Iniciando proceso...")
        self.time_label.configure(text="")
        self.start_time = None
        self.total_chunks = 0
        
        # Ejecutar en hilo separado
        def run_creation():
            try:
                # Preparar argumentos
                output_file = self.output_file_name.get() + ".mp3" if self.output_file_name.get() else None

                # Crear directorio de salida si no es ruta absoluta
                if output_file and not os.path.isabs(output_file):
                    os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
                    base_name = os.path.splitext(output_file)[0]
                    output_dir = os.path.join(DEFAULT_OUTPUT_DIR, base_name)
                    os.makedirs(output_dir, exist_ok=True)
                    output_file = os.path.join(output_dir, output_file)

                # Ejecutar proceso
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.set_exception_handler(suppress_asyncio_exceptions)

                loop.run_until_complete(process_audiobook_creation(
                    self.text_file_path.get(),
                    output_file,
                    self.selected_voice.get(),
                    self.retries_value.get(),
                    self.rate_value.get(),
                    self.chunking_strategy.get(),
                    status_callback=self.update_status,
                    progress_callback=self.update_progress
                ))

                loop.close()

                # Mostrar mensaje de éxito
                self.root.after(0, lambda: messagebox.showinfo("Éxito", f"Audiolibro creado exitosamente:\n{output_file}"))

            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("Error", f"Error al crear audiolibro: {e}"))
            finally:
                # Restaurar botones
                self.root.after(0, self.restore_buttons)
        
        self.creation_thread = threading.Thread(target=run_creation, daemon=True)
        self.creation_thread.start()
    
    def stop_process(self):
        """Detener proceso de creación"""
        # Implementar lógica de detención si es necesario
        messagebox.showinfo("Info", "Proceso detenido")
        self.restore_buttons()
    
    def restore_buttons(self):
        """Restaurar estado de botones"""
        self.create_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.progress_bar.set(1.0)
        if "Completado" not in self.status_label.cget("text"):
            self.status_label.configure(text="Listo")
            self.time_label.configure(text="")
    
    def run(self):
        """Ejecutar la aplicación"""
        self.root.mainloop()

def main():
    """Función principal para la GUI"""
    app = AudiobookCreatorGUI()
    app.run()

if __name__ == "__main__":
    main() 