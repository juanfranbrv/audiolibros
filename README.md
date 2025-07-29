# Generador de Audiolibros con Edge-TTS

Este es un script de Python para la línea de comandos (CLI) que convierte archivos de texto (`.txt`) en audiolibros (`.mp3`) utilizando el potente y natural motor de Texto a Voz (TTS) de Microsoft Edge.

La herramienta está diseñada para ser robusta, eficiente y fácil de usar, ideal para procesar textos largos sin interrupciones.

## ✨ Características Principales

- **Alta Calidad de Voz**: Utiliza las voces neuronales de `edge-tts` para un resultado natural y agradable.
- **Procesamiento Eficiente**:
    - **Fragmentación Inteligente**: Agrupa párrafos pequeños para minimizar las llamadas a la API y acelerar el proceso.
    - **Reanudación Automática**: Si el proceso se interrumpe, puedes volver a ejecutarlo y continuará donde se quedó, sin perder el progreso.
- **Personalización de la Voz**: Permite ajustar la velocidad (`--rate`) de la voz para adaptarla a tus preferencias.
- **Anti-Suspensión**: Evita que el equipo entre en modo de suspensión durante la creación de audiolibros largos (solo en Windows).
- **Interfaz Amigable**: Usa la librería `rich` para una experiencia en la consola clara y atractiva, con barras de progreso y tiempo restante estimado.
- **Autonomía**: No requiere instalar Microsoft Edge ni una clave de API.

## 🚀 Uso

### Listar Voces Disponibles

Para ver todas las voces que puedes usar:
```bash
python audiolibro_creator.py --list-voices
```

### Crear un Audiolibro

**Uso Básico (con valores por defecto):**
```bash
python audiolibro_creator.py -t "tu_libro.txt"
```
Esto usará la voz `es-ES-AlvaroNeural` a una velocidad de `-5%` y creará un archivo `tu_libro.mp3` en `D:\AUDIOLIBROS\tu_libro\`.

**Uso Personalizado:**
```bash
python audiolibro_creator.py -t "tu_libro.txt" -o "mi_audiolibro.mp3" -v "es-MX-DaliaNeural" --rate=+10%
```
Esto creará el archivo en `D:\AUDIOLIBROS\mi_audiolibro\mi_audiolibro.mp3`.

**Especificar ruta completa:**
```bash
python audiolibro_creator.py -t "tu_libro.txt" -o "C:\MiCarpeta\mi_audiolibro.mp3"
```
Esto creará el archivo en la ruta especificada.

## 🔧 Cómo Funciona

### Estructura de Directorios

El script maneja los directorios de la siguiente manera:

- **Fragmentos temporales**: Se crean en la carpeta del proyecto (`temp_audio_chunks/`)
- **Archivo final**: Por defecto se guarda en `D:\AUDIOLIBROS\[nombre_del_archivo]\`
- **Organización**: Cada audiolibro tiene su propia carpeta con el mismo nombre que el archivo final

**Ejemplo de estructura:**
```
D:\AUDIOLIBROS\
├── El cadiceno - Rosalia de Castro\
│   └── El cadiceno - Rosalia de Castro.mp3
├── Los diablos - Joe Abercrombie\
│   └── Los diablos - Joe Abercrombie.mp3
└── mi_audiolibro\
    └── mi_audiolibro.mp3
```

### Proceso de Fragmentación

El script divide tu archivo de texto en fragmentos más pequeños para procesarlos eficientemente. Esto es necesario porque:

1. **Límites de la API**: Edge-TTS tiene límites en la longitud del texto que puede procesar en una sola llamada.
2. **Eficiencia**: Procesar fragmentos más pequeños permite mejor control de errores y reanudación.
3. **Memoria**: Evita problemas de memoria con archivos muy grandes.

### Estrategias de Fragmentación

El script ofrece dos estrategias diferentes:

#### 🧠 Estrategia "Smart" (Por Defecto)
- **Agrupa párrafos pequeños** en fragmentos más grandes (hasta ~2500 caracteres).
- **Ideal para textos con diálogos** o párrafos cortos.
- **Reduce significativamente** el número de llamadas a la API.
- **Más rápido** para la mayoría de textos.

#### 📝 Estrategia "Legacy"
- **Un fragmento por párrafo** (excepto si es muy largo).
- **Más preciso** para mantener la estructura original.
- **Útil para textos** con párrafos muy largos.

### Proceso Completo

1. **Lectura del Archivo**: El script lee completamente tu archivo de texto.
2. **Fragmentación**: Divide el texto usando la estrategia seleccionada.
3. **Creación de Fragmentos de Audio**: 
   - Crea una carpeta temporal `temp_audio_chunks/`
   - Convierte cada fragmento de texto a audio MP3 individual
   - Los archivos se nombran como `chunk_0000.mp3`, `chunk_0001.mp3`, etc.
4. **Concatenación Final**: 
   - Usa FFmpeg para unir todos los fragmentos en orden
   - Crea el archivo MP3 final
   - Limpia automáticamente los archivos temporales

### Sistema de Reanudación

Si interrumpes el proceso:
- **Los fragmentos ya creados se conservan** en la carpeta `temp_audio_chunks/`
- **Al volver a ejecutar**, el script detecta los fragmentos existentes
- **Continúa desde donde se quedó**, sin perder el progreso
- **Solo se borran los temporales** cuando el proceso termina con éxito

### Archivos Temporales

Durante el proceso se crean en la carpeta del proyecto:
- `temp_audio_chunks/chunk_0000.mp3` - Primer fragmento
- `temp_audio_chunks/chunk_0001.mp3` - Segundo fragmento
- `temp_audio_chunks/filelist.txt` - Lista para FFmpeg
- ... y así sucesivamente

**Nota**: Estos archivos se eliminan automáticamente al finalizar, pero se conservan si interrumpes el proceso. El archivo final se guarda en `D:\AUDIOLIBROS\[nombre_del_archivo]\` por defecto.

## 📋 Requisitos

- Python 3.8+
- FFmpeg

Las dependencias de Python se instalan fácilmente con:
```bash
pip install -r requirements.txt
``` 