# Audiobook Order and Job Isolation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir el orden de lectura de EPUB, impedir la mezcla de fragmentos entre trabajos y actualizar el nombre de salida al seleccionar cada libro.

**Architecture:** La extracción EPUB seguirá el `spine`. El generador derivará una subcarpeta temporal determinista de todo el contenido y configuración del trabajo, y validará el conjunto exacto de fragmentos antes de concatenar. La interfaz derivará siempre el nombre de salida del archivo recién seleccionado y capturará el estado del trabajo antes de arrancar el hilo.

**Tech Stack:** Python 3.10, `unittest`, EbookLib, BeautifulSoup, CustomTkinter, Edge TTS y FFmpeg.

## Global Constraints

- Mantener la reanudación para un trabajo idéntico.
- No reutilizar ningún fragmento de otro texto o configuración.
- Mantener compatibilidad con TXT, PDF, GUI y CLI.
- No añadir dependencias nuevas.

---

### Task 1: Orden de lectura EPUB

**Files:**
- Modify: `text_extractor.py`
- Create: `tests/test_text_extractor.py`

**Interfaces:**
- Consumes: `ebooklib.epub.read_epub(file_path)` y `book.spine`.
- Produces: `extract_from_epub(file_path: str) -> str` en orden de lectura.

- [ ] **Step 1: Write the failing test**

Crear un EPUB temporal cuyos documentos se añadan en orden `capitulo_2`, `capitulo_1`, pero cuyo `spine` sea `capitulo_1`, `capitulo_2`. Comprobar que el texto extraído coloca `PRIMERO` antes de `SEGUNDO`.

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.10 -m unittest tests.test_text_extractor -v`

Expected: FAIL porque el extractor actual recorre `book.get_items()`.

- [ ] **Step 3: Write minimal implementation**

Resolver cada identificador de `book.spine` mediante `book.get_item_with_id`, conservar solo `ITEM_DOCUMENT` y usar el manifiesto únicamente si el `spine` no aporta documentos legibles. Lanzar `RuntimeError` cuando no haya documentos.

- [ ] **Step 4: Run test to verify it passes**

Run: `py -3.10 -m unittest tests.test_text_extractor -v`

Expected: PASS.

### Task 2: Identidad y validación del trabajo temporal

**Files:**
- Modify: `audiolibro_creator.py`
- Create: `tests/test_audiolibro_creator.py`

**Interfaces:**
- Produces: `build_job_id(text_chunks: list[str], voice: str, rate: str, strategy: str) -> str`.
- Produces: `get_ordered_chunk_files(temp_dir: str, expected_count: int) -> list[str]`.
- Modifies: `concatenate_chunks(output_file: str, temp_dir: str, expected_count: int)`.

- [ ] **Step 1: Write failing identity tests**

Comprobar que la misma entrada genera la misma identidad y que cambiar texto, voz, velocidad o estrategia genera una identidad distinta.

- [ ] **Step 2: Run identity tests and verify failure**

Run: `py -3.10 -m unittest tests.test_audiolibro_creator.JobIdentityTests -v`

Expected: ERROR porque `build_job_id` aún no existe.

- [ ] **Step 3: Implement deterministic identity**

Calcular SHA-256 sobre una serialización JSON UTF-8 de `chunks`, `voice`, `rate`, `strategy` y una versión fija del formato. Usar `temp_audio_chunks/<job_id>`.

- [ ] **Step 4: Run identity tests and verify pass**

Run: `py -3.10 -m unittest tests.test_audiolibro_creator.JobIdentityTests -v`

Expected: PASS.

- [ ] **Step 5: Write failing chunk validation tests**

Comprobar el orden numérico exacto y el rechazo de archivos ausentes, sobrantes y mal nombrados.

- [ ] **Step 6: Run validation tests and verify failure**

Run: `py -3.10 -m unittest tests.test_audiolibro_creator.ChunkValidationTests -v`

Expected: ERROR porque `get_ordered_chunk_files` aún no existe.

- [ ] **Step 7: Implement strict validation and wire generation**

Enumerar exactamente `chunk_0000.mp3` hasta `chunk_N.mp3`, comparar con todos los MP3 de la subcarpeta y lanzar `RuntimeError` ante cualquier diferencia. Pasar la subcarpeta y el total a concatenación, y limpiar solo esa subcarpeta al terminar.

- [ ] **Step 8: Run creator tests and verify pass**

Run: `py -3.10 -m unittest tests.test_audiolibro_creator -v`

Expected: PASS.

### Task 3: Nuevo libro en la interfaz

**Files:**
- Modify: `audiolibro_gui.py`
- Create: `tests/test_audiolibro_gui.py`

**Interfaces:**
- Produces: `default_output_name(file_path: str) -> str`.
- Modifies: `AudiobookCreatorGUI.browse_text_file()` y `create_audiobook()`.

- [ ] **Step 1: Write the failing GUI state test**

Construir una instancia mínima con variables simuladas, seleccionar dos rutas consecutivas mediante `filedialog.askopenfilename` y comprobar que el segundo nombre sustituye al primero.

- [ ] **Step 2: Run test to verify it fails**

Run: `py -3.10 -m unittest tests.test_audiolibro_gui -v`

Expected: FAIL porque el nombre solo cambia cuando el campo está vacío.

- [ ] **Step 3: Implement new-selection reset**

Asignar siempre `default_output_name(file_path)` al seleccionar un archivo. Antes de crear el hilo, capturar texto editado, nombre, voz, reintentos, velocidad y estrategia en variables locales y utilizarlas dentro del trabajo.

- [ ] **Step 4: Run GUI test and verify pass**

Run: `py -3.10 -m unittest tests.test_audiolibro_gui -v`

Expected: PASS.

### Task 4: Verificación integrada

**Files:**
- Modify: `README.md` solo si la descripción de reanudación queda desactualizada.

- [ ] **Step 1: Run full automated suite**

Run: `py -3.10 -m unittest discover -s tests -v`

Expected: todos los tests PASS.

- [ ] **Step 2: Validate affected real EPUB files**

Extraer `Tocando el vacío` y `Marte Rojo` y comprobar que sus primeros documentos coinciden con sus respectivos `spine`.

- [ ] **Step 3: Check syntax and working tree**

Run: `py -3.10 -m compileall -q main.py audiolibro_creator.py audiolibro_gui.py text_extractor.py config_manager.py tests`

Expected: exit code 0.

Run: `git diff --check`

Expected: exit code 0 sin salida.
