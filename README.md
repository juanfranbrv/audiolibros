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
Esto usará la voz `es-ES-AlvaroNeural` a una velocidad de `-5%` y creará un archivo `tu_libro.mp3`.

**Uso Personalizado:**
```bash
python audiolibro_creator.py -t "tu_libro.txt" -o "mi_audiolibro.mp3" -v "es-MX-DaliaNeural" --rate=+10%
```

## 📋 Requisitos

- Python 3.8+
- FFmpeg

Las dependencias de Python se instalan fácilmente con:
```bash
pip install -r requirements.txt
``` 