import argparse
import asyncio
import hashlib
import json
import os
import sys
import time
import shutil
import re
from datetime import timedelta
import ctypes
import warnings
import logging
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
from rich.table import Table
from text_extractor import get_text_content # Import helper module
# from pydub import AudioSegment #<- MOVEMOS ESTA LÍNEA

# --- Silenciar warnings y logs de aiohttp/edge-tts ---
warnings.filterwarnings("ignore")
logging.getLogger("asyncio").setLevel(logging.CRITICAL)
logging.getLogger("aiohttp").setLevel(logging.CRITICAL)

# --- Inicialización de Rich Console ---
console = Console()

# --- Constantes ---
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(PROJECT_DIR, "temp_audio_chunks")
DEFAULT_OUTPUT_DIR = "D:\\AUDIOLIBROS"
DEFAULT_RETRIES = 3
CHUNK_MAX_SIZE = 2500  # Caracteres máximos por fragmento para evitar problemas con la API

# --- Gestión de Suspensión de Windows ---
def prevent_sleep():
    """Previene que el sistema entre en modo de suspensión (solo para Windows)."""
    if sys.platform == 'win32':
        try:
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS | ES_SYSTEM_REQUIRED)
        except Exception:
            pass

def allow_sleep():
    """Permite que el sistema entre en modo de suspensión (solo para Windows)."""
    if sys.platform == 'win32':
        try:
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass

def create_arg_parser():
    """Crea y configura el analizador de argumentos de la línea de comandos."""
    parser = argparse.ArgumentParser(
        description="Generador de Audiolibros con edge-tts y Rich.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "-t", "--text-file",
        help="Ruta al archivo de entrada (.txt, .pdf, .epub).",
        required=False
    )
    parser.add_argument(
        "-o", "--output-file",
        default=None,
        help="Ruta y nombre del archivo MP3 de salida. Si no se indica, se usará el nombre del archivo de texto.",
    )
    parser.add_argument(
        "-v", "--voice",
        default="es-ES-AlvaroNeural",
        help="Voz a utilizar para la síntesis (default: es-ES-AlvaroNeural)."
    )
    parser.add_argument(
        "--rate",
        default="-5%",
        help="Ajuste de la velocidad de la voz (ej. -10%%, +20%%). Default: -5%%."
    )
    parser.add_argument(
        '--chunking-strategy',
        default='smart',
        choices=['smart', 'legacy'],
        help="Estrategia para dividir el texto: 'smart' agrupa párrafos, 'legacy' va uno por uno (default: smart)."
    )
    parser.add_argument(
        "--list-voices",
        action="store_true",
        help="Muestra las voces disponibles y sale."
    )
    parser.add_argument(
        "--retries",
        type=int,
        default=DEFAULT_RETRIES,
        help=f"Número de reintentos por fragmento (default: {DEFAULT_RETRIES})."
    )
    return parser

async def list_available_voices():
    """Obtiene y muestra las voces disponibles directamente desde la librería edge_tts."""
    console.print("[bold cyan]Obteniendo lista de voces disponibles...[/bold cyan]")
    try:
        from edge_tts import VoicesManager # Importación local
        voices = await VoicesManager.create()
        
        table = Table(title="Voces Disponibles para Edge-TTS", show_lines=True)
        table.add_column("Nombre Corto (ShortName)", style="cyan", no_wrap=True)
        table.add_column("Género", style="magenta")
        table.add_column("Localidad", style="green")

        for voice in voices.voices:
            table.add_row(voice['ShortName'], voice['Gender'], voice['Locale'])
        
        console.print(table)

    except ImportError:
        console.print("[bold red]Error: `edge-tts` no encontrado. Asegúrate de que esté instalado.[/bold red]")
        console.print("Puedes instalarlo con: [cyan]pip install edge-tts[/cyan]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Ocurrió un error inesperado al obtener las voces: {e}[/bold red]")
        sys.exit(1)

def chunk_text_legacy(text: str) -> list[str]:
    """[LEGACY] Divide el texto en fragmentos manejables basados en párrafos y longitud."""
    paragraphs = re.split(r'\n\s*\n', text)

    chunks = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(para) > CHUNK_MAX_SIZE:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current_chunk = ""
            for sentence in sentences:
                if len(current_chunk) + len(sentence) + 1 < CHUNK_MAX_SIZE:
                    current_chunk += sentence + " "
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = sentence + " "
            if current_chunk:
                chunks.append(current_chunk.strip())
        else:
            chunks.append(para)

    return chunks

def chunk_text_smart(text: str) -> list[str]:
    """[SMART] Agrupa párrafos pequeños en fragmentos más grandes y eficientes."""
    paragraphs = re.split(r'\n\s*\n', text)

    final_chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        paragraph = paragraph.strip()
        if not paragraph:
            continue

        if len(paragraph) > CHUNK_MAX_SIZE:
            if current_chunk:
                final_chunks.append(current_chunk)
                current_chunk = ""

            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            oversized_paragraph_chunk = ""
            for sentence in sentences:
                if len(oversized_paragraph_chunk) + len(sentence) + 1 < CHUNK_MAX_SIZE:
                    oversized_paragraph_chunk += sentence + " "
                else:
                    # Si la primera frase ya supera el límite, el fragmento
                    # acumulado está vacío: no se añade.
                    if oversized_paragraph_chunk.strip():
                        final_chunks.append(oversized_paragraph_chunk.strip())
                    oversized_paragraph_chunk = sentence + " "
            if oversized_paragraph_chunk.strip():
                final_chunks.append(oversized_paragraph_chunk.strip())

        elif len(current_chunk) + len(paragraph) + 2 < CHUNK_MAX_SIZE:
            if current_chunk:
                current_chunk += "\n\n" + paragraph
            else:
                current_chunk = paragraph

        else:
            # current_chunk puede estar vacío si el párrafo mide casi
            # CHUNK_MAX_SIZE y es el primero del grupo.
            if current_chunk:
                final_chunks.append(current_chunk)
            current_chunk = paragraph

    if current_chunk:
        final_chunks.append(current_chunk)

    return final_chunks

def chunk_text(text: str, strategy: str) -> list[str]:
    """Divide el texto en fragmentos usando la estrategia especificada."""
    if strategy == 'smart':
        return chunk_text_smart(text)
    elif strategy == 'legacy':
        return chunk_text_legacy(text)
    else:
        return chunk_text_smart(text)

def build_job_id(text_chunks: list[str], voice: str, rate: str, strategy: str) -> str:
    """Builds a stable identity for chunks that are safe to resume."""
    job_data = {
        "format_version": 1,
        "chunks": text_chunks,
        "voice": voice,
        "rate": rate,
        "strategy": strategy,
    }
    serialized = json.dumps(
        job_data, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(serialized).hexdigest()

def acquire_job_lock(job_id: str, temp_root: str = TEMP_DIR):
    """Acquires a non-blocking OS lock for one deterministic job."""
    lock_dir = os.path.join(temp_root, ".locks")
    os.makedirs(lock_dir, exist_ok=True)
    lock_path = os.path.join(lock_dir, f"{job_id}.lock")
    lock_file = open(lock_path, "a+b")

    try:
        lock_file.seek(0, os.SEEK_END)
        if lock_file.tell() == 0:
            lock_file.write(b"0")
            lock_file.flush()
        lock_file.seek(0)

        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock_file.close()
        raise RuntimeError(
            "Este mismo audiolibro ya se está generando en otra instancia."
        ) from exc

    return lock_file

def release_job_lock(lock_file):
    """Releases a lock returned by acquire_job_lock."""
    if lock_file is None or lock_file.closed:
        return

    try:
        lock_file.seek(0)
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(lock_file.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl

            fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
    finally:
        lock_file.close()

def get_ordered_chunk_files(temp_dir: str, expected_count: int, skipped_indices=()) -> list[str]:
    """Returns the exact expected chunk set or rejects inconsistent state.

    skipped_indices: fragmentos de texto vacíos, que no generan MP3.
    """
    skipped = set(skipped_indices)
    expected_names = [
        f"chunk_{index:04d}.mp3"
        for index in range(expected_count)
        if index not in skipped
    ]
    if not expected_names:
        raise RuntimeError("No hay fragmentos de audio para concatenar.")

    expected_set = set(expected_names)
    actual_set = {
        name for name in os.listdir(temp_dir) if name.lower().endswith(".mp3")
    }

    if actual_set != expected_set:
        missing = sorted(expected_set - actual_set)
        extra = sorted(actual_set - expected_set)
        details = []
        if missing:
            details.append(f"faltan: {', '.join(missing[:5])}")
        if extra:
            details.append(f"sobran o son inválidos: {', '.join(extra[:5])}")
        raise RuntimeError("Conjunto de fragmentos incoherente; " + "; ".join(details))

    ordered_files = [os.path.join(temp_dir, name) for name in expected_names]
    empty_files = [path for path in ordered_files if os.path.getsize(path) == 0]
    if empty_files:
        raise RuntimeError(
            f"El fragmento está vacío: {os.path.basename(empty_files[0])}"
        )

    return ordered_files

async def synthesize_chunk(text: str, voice: str, output_path: str, rate: str) -> bool:
    """Sintetiza un solo fragmento de texto a audio usando la librería edge_tts."""
    partial_path = output_path + ".part"
    try:
        from edge_tts import Communicate
        
        # Filtra los chunks que están vacíos o solo contienen espacios en blanco
        if not text.strip():
            return True # Considerado un éxito para no detener el proceso

        if os.path.exists(partial_path):
            os.remove(partial_path)

        communicate = Communicate(text, voice, rate=rate)
        await communicate.save(partial_path)
        if not os.path.exists(partial_path) or os.path.getsize(partial_path) == 0:
            raise RuntimeError("Edge TTS no generó audio para el fragmento.")
        os.replace(partial_path, output_path)
        return True
    except Exception as e:
        if os.path.exists(partial_path):
            os.remove(partial_path)

        # La librería puede lanzar una excepción si el texto está vacío después de sus propios filtros,
        # la capturamos aquí para evitar que el programa se detenga.
        console.print(f"\n[bold red]Error de la librería edge-tts al procesar un fragmento: {e}[/bold red]")
        return False

async def concatenate_chunks(output_file: str, temp_dir: str, expected_count: int, skipped_indices=()):
    """Concatena todos los archivos MP3 usando ffmpeg directamente."""
    console.print("\n[bold cyan]Concatenando archivos de audio con ffmpeg...[/bold cyan]")

    # 1. Obtener la ruta absoluta del directorio temporal y del archivo de salida
    temp_dir_abs = os.path.abspath(temp_dir)
    output_file_abs = os.path.abspath(output_file)

    # 2. Obtener y validar la lista completa en orden numérico.
    chunk_files_abs = get_ordered_chunk_files(temp_dir_abs, expected_count, skipped_indices)

    # 3. Crear un archivo temporal con la lista de archivos para ffmpeg
    filelist_path_abs = os.path.join(temp_dir_abs, "filelist.txt")
    with open(filelist_path_abs, 'w', encoding='utf-8') as f:
        for chunk_file in chunk_files_abs:
            # ffmpeg necesita rutas con barras inclinadas hacia adelante.
            safe_path = chunk_file.replace('\\', '/')
            f.write(f"file '{safe_path}'\n")

    # 4. Construir y ejecutar el comando de ffmpeg con rutas absolutas (silenciando warnings)
    ffmpeg_executable = "C:\\ffmpeg\\bin\\ffmpeg.exe"
    command = f'"{ffmpeg_executable}" -y -loglevel error -f concat -safe 0 -i "{filelist_path_abs}" -c copy "{output_file_abs}"'

    try:
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        _, stderr = await process.communicate()

        if process.returncode != 0:
            error_detail = stderr.decode(errors="replace").strip()
            raise RuntimeError(
                f"Error durante la concatenación con FFmpeg: {error_detail}"
            )

    except FileNotFoundError as exc:
        raise RuntimeError(
            "FFmpeg no se encontró en C:\\ffmpeg\\bin\\ffmpeg.exe."
        ) from exc
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"Error inesperado al ejecutar FFmpeg: {e}") from e


def cleanup(job_temp_dir: str):
    """Elimina únicamente los temporales del trabajo completado."""
    if os.path.isdir(job_temp_dir):
        shutil.rmtree(job_temp_dir)

async def process_audiobook_creation(text_file: str, output_file: str, voice: str, retries: int, rate: str, chunking_strategy: str, status_callback=None, progress_callback=None):
    """Función orquestadora principal para la creación del audiolibro."""
    job_lock_file = None
    prevent_sleep()
    try:
        start_time = time.monotonic()

        # Determinar si estamos en modo GUI (si hay callbacks)
        is_gui_mode = status_callback is not None

        # --- Panel de Inicio ---
        if not is_gui_mode:
            summary = (
                f"[bold]Archivo de entrada:[/] [cyan]{text_file}[/cyan]\n"
                f"[bold]Archivo de salida:[/] [cyan]{output_file}[/cyan]\n"
                f"[bold]Voz seleccionada:[/] [cyan]{voice}[/cyan]\n"
                f"[bold]Velocidad:[/] [cyan]{rate}[/cyan]\n"
                f"[bold]Estrategia de Fragmentación:[/] [cyan]{chunking_strategy}[/cyan]\n"
                f"[bold]Reintentos por fragmento:[/] [cyan]{retries}[/cyan]"
            )
            console.print(Panel(summary, title="Generador de Audiolibros", border_style="green"))

        # --- Preparación ---
        # No borra el directorio si existe, permitiendo la reanudación.
        os.makedirs(TEMP_DIR, exist_ok=True)

        try:
            # Modified to use the new text extractor
            text = get_text_content(text_file)
        except FileNotFoundError:
            if not is_gui_mode:
                console.print(f"[bold red]Error: El archivo '{text_file}' no fue encontrado.[/bold red]")
            raise RuntimeError(f"El archivo '{text_file}' no fue encontrado.")
        except Exception as e:
            if not is_gui_mode:
                console.print(f"[bold red]Error al leer y procesar el archivo: {e}[/bold red]")
            raise RuntimeError(f"Error al leer y procesar el archivo: {e}") from e

        text_chunks = chunk_text(text, chunking_strategy)
        total_chunks = len(text_chunks)
        job_id = build_job_id(text_chunks, voice, rate, chunking_strategy)
        job_lock_file = acquire_job_lock(job_id)
        job_temp_dir = os.path.join(TEMP_DIR, job_id)
        os.makedirs(job_temp_dir, exist_ok=True)

        # --- Barra de Progreso ---
        progress_columns = [
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("([progress.completed]{task.completed}/{task.total})"),
            TimeRemainingColumn(),
        ]

        # Solo mostrar barra de progreso en modo CLI
        if not is_gui_mode:
            progress_context = Progress(*progress_columns, console=console)
        else:
            # En modo GUI, usar un contexto dummy que no hace nada
            from contextlib import nullcontext
            progress_context = nullcontext()

        with progress_context as progress:
            # Solo crear tarea si estamos en modo CLI
            if not is_gui_mode:
                task = progress.add_task("Procesando fragmentos...", total=total_chunks)

            for i, chunk in enumerate(text_chunks):
                chunk_filename = os.path.join(job_temp_dir, f"chunk_{i:04d}.mp3")

                # Actualizar estado en GUI si existe callback
                if status_callback:
                    status_callback(f"Procesando fragmento {i+1}/{total_chunks}")
                if progress_callback:
                    progress_callback(i, total_chunks)

                # --- Lógica de Reanudación ---
                if os.path.exists(chunk_filename) and os.path.getsize(chunk_filename) > 0:
                    if not is_gui_mode:
                        progress.update(task, advance=1)
                    continue

                success = False
                for attempt in range(retries):
                    if not is_gui_mode:
                        progress.update(task, description=f"Procesando fragmento [cyan]({i+1}/{total_chunks})[/cyan]")

                    success = await synthesize_chunk(chunk, voice, chunk_filename, rate)

                    if success:
                        break
                    else:
                        if not is_gui_mode:
                            console.print(f"[yellow]ADVERTENCIA:[/yellow] Fallo al generar el fragmento {i+1}. Reintentando (intento {attempt+1}/{retries})...")
                        if attempt < retries - 1:
                            time.sleep(5)

                if not success:
                    if not is_gui_mode:
                        console.print(f"[bold red]ERROR FATAL:[/bold red] No se pudo generar el fragmento {i+1} después de {retries} intentos. Abortando.")
                    # No se borra la carpeta para poder revisar los logs o archivos.
                    raise RuntimeError(
                        f"No se pudo generar el fragmento {i+1} después de {retries} intentos."
                    )

                if not is_gui_mode:
                    progress.update(task, advance=1)

        # --- Concatenación y Limpieza ---
        # Solo se borra el directorio temporal si la concatenación es exitosa.
        if status_callback:
            status_callback("Concatenando fragmentos de audio...")
        if progress_callback:
            progress_callback(total_chunks, total_chunks)

        # Los fragmentos vacíos no generan MP3 (ver synthesize_chunk).
        empty_chunk_indices = {
            index for index, chunk in enumerate(text_chunks) if not chunk.strip()
        }
        await concatenate_chunks(
            output_file, job_temp_dir, total_chunks, empty_chunk_indices
        )
        cleanup(job_temp_dir)

        # --- Panel de Éxito ---
        end_time = time.monotonic()
        duration = timedelta(seconds=end_time - start_time)

        if status_callback:
            status_callback(f"¡Completado! Tiempo: {str(duration).split('.')[0]}")

        if not is_gui_mode:
            success_message = (
                f"¡Audiolibro [bold green]'{output_file}'[/bold green] creado con éxito!\n\n"
                f"Tiempo total empleado: [yellow]{str(duration).split('.')[0]}[/yellow]"
            )
            console.print(Panel(
                success_message,
                title="Proceso Completado",
                border_style="green"
            ))
    finally:
        release_job_lock(job_lock_file)
        allow_sleep()

def suppress_asyncio_exceptions(loop, context):
    """Suprimir excepciones de asyncio relacionadas con conexiones cerradas"""
    exception = context.get("exception")
    if exception and isinstance(exception, Exception):
        # Silenciar solo errores de conexión de aiohttp
        if "ClientConnectionError" in str(type(exception)) or "ConnectionResetError" in str(type(exception)):
            return
    # Para otros errores, usar el comportamiento por defecto
    loop.default_exception_handler(context)

async def main():
    """Función principal asíncrona que coordina todo."""
    # Configurar manejador de excepciones de asyncio
    loop = asyncio.get_event_loop()
    loop.set_exception_handler(suppress_asyncio_exceptions)

    parser = create_arg_parser()
    args = parser.parse_args()

    if args.list_voices:
        await list_available_voices()
        sys.exit(0)
    
    # --- Validación de Argumentos ---

    # El archivo de texto de entrada es siempre requerido para la creación.
    if not args.text_file:
        console.print("[bold red]Error: El argumento --text-file (-t) es requerido para crear un audiolibro.[/bold red]")
        parser.print_help()
        sys.exit(1)

    # Validar que el archivo de entrada existe
    if not os.path.isfile(args.text_file):
        console.print(f"[bold red]Error: El archivo de entrada '{args.text_file}' no existe o no es un archivo válido.[/bold red]")
        sys.exit(1)

    # Determinar el nombre del archivo de salida y su directorio
    output_file = args.output_file
    if not output_file:
        base_name = os.path.splitext(os.path.basename(args.text_file))[0]
        output_file = f"{base_name}.mp3"
        console.print(f"\n[cyan]No se especificó archivo de salida. Usando por defecto:[/] [bold magenta]{output_file}[/bold magenta]")
    
    # Crear el directorio de salida por defecto si no existe
    if not os.path.isabs(output_file):
        # Si no es una ruta absoluta, usar el directorio por defecto
        os.makedirs(DEFAULT_OUTPUT_DIR, exist_ok=True)
        # Crear carpeta con el nombre del archivo (sin extensión)
        base_name = os.path.splitext(output_file)[0]
        output_dir = os.path.join(DEFAULT_OUTPUT_DIR, base_name)
        os.makedirs(output_dir, exist_ok=True)
        output_file = os.path.join(output_dir, output_file)
        console.print(f"\n[cyan]Archivo de salida configurado en:[/] [bold magenta]{output_file}[/bold magenta]")
    else:
        # Si es una ruta absoluta, crear el directorio si no existe
        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)
    
    await process_audiobook_creation(args.text_file, output_file, args.voice, args.retries, args.rate, args.chunking_strategy)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        console.print("\n[bold yellow]Proceso interrumpido por el usuario.[/bold yellow]")
        console.print("[cyan]INFO: Los fragmentos de audio temporales se han conservado. Vuelve a ejecutar el comando para reanudar.[/cyan]")
        # Ya no se llama a cleanup() aquí
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]Ha ocurrido un error inesperado en la ejecución: {e}[/bold red]")
        # Tampoco se llama a cleanup() para permitir la depuración.
        sys.exit(1)
