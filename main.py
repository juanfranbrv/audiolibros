#!/usr/bin/env python3
"""
Script principal para el Generador de Audiolibros
Permite elegir entre interfaz CLI y GUI
"""

import sys
import argparse

def main():
    parser = argparse.ArgumentParser(
        description="Generador de Audiolibros - Elige entre CLI y GUI",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        "--gui", 
        action="store_true",
        help="Ejecutar interfaz gráfica"
    )
    parser.add_argument(
        "--cli",
        action="store_true", 
        help="Ejecutar interfaz de línea de comandos"
    )
    
    # Si no se especifica argumento, mostrar opciones
    if len(sys.argv) == 1:
        print("=== Generador de Audiolibros ===")
        print("1. Interfaz gráfica (GUI)")
        print("2. Interfaz de línea de comandos (CLI)")
        print()
        
        choice = input("Elige una opción (1/2): ").strip()
        
        if choice == "1":
            run_gui()
        elif choice == "2":
            run_cli()
        else:
            print("Opción no válida. Ejecutando CLI por defecto.")
            run_cli()
    else:
        args = parser.parse_args()
        
        if args.gui:
            run_gui()
        elif args.cli:
            run_cli()
        else:
            # Si se pasan otros argumentos, ejecutar CLI
            run_cli()

def run_gui():
    """Ejecutar interfaz gráfica"""
    try:
        from audiolibro_gui import main as gui_main
        print("Iniciando interfaz gráfica...")
        gui_main()
    except ImportError as e:
        print(f"Error al importar la interfaz gráfica: {e}")
        print("Asegúrate de que customtkinter esté instalado: pip install customtkinter")
        sys.exit(1)
    except Exception as e:
        print(f"Error al ejecutar la interfaz gráfica: {e}")
        sys.exit(1)

def run_cli():
    """Ejecutar interfaz de línea de comandos"""
    try:
        from audiolibro_creator import main as cli_main
        import asyncio
        asyncio.run(cli_main())
    except ImportError as e:
        print(f"Error al importar el script CLI: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error al ejecutar la interfaz CLI: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 