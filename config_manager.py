import json
import os

CONFIG_FILE = "config.json"

DEFAULT_CONFIG = {
    "voice": "es-ES-AlvaroNeural",
    "rate": "-5%",
    "chunking_strategy": "smart",
    "retries": 3,
    "last_input_directory": "",
    "last_output_directory": "D:\\AUDIOLIBROS" 
}

def load_config():
    """Carga la configuración desde el archivo JSON, o devuelve los valores por defecto."""
    if not os.path.exists(CONFIG_FILE):
        return DEFAULT_CONFIG.copy()
    
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            user_config = json.load(f)
            # Asegurarse de que todas las claves existan (merge con default)
            config = DEFAULT_CONFIG.copy()
            config.update(user_config)
            return config
    except Exception as e:
        print(f"Error al cargar configuración: {e}")
        return DEFAULT_CONFIG.copy()

def save_config(config):
    """Guarda la configuración en el archivo JSON."""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=4)
    except Exception as e:
        print(f"Error al guardar configuración: {e}")
