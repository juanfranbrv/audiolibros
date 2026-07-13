# Orden e independencia en la generación de audiolibros

## Objetivo

Garantizar que cada audiolibro respete el orden de lectura de su fuente, que nunca reutilice fragmentos pertenecientes a otro trabajo y que la interfaz proponga el nombre correcto al seleccionar un nuevo libro.

## Extracción de EPUB

Los documentos se extraerán siguiendo el `spine` del EPUB, que define su orden oficial de lectura. Solo cuando el archivo no contenga un `spine` utilizable se conservará como respaldo el orden de documentos del manifiesto.

## Fragmentos temporales y reanudación

Cada trabajo utilizará una subcarpeta identificada por una huella calculada a partir del texto ya dividido, la voz, la velocidad y la estrategia de fragmentación. La reanudación solo reutilizará archivos de una huella idéntica.

Antes del montaje se exigirá que existan exactamente todos los fragmentos esperados, con nombres consecutivos desde `chunk_0000.mp3`. Los archivos sobrantes, ausentes o con nombres inesperados impedirán el montaje. Tras completarlo se eliminará únicamente la subcarpeta del trabajo terminado.

## Ciclo de la interfaz

Al seleccionar un archivo nuevo, la interfaz reemplazará siempre el nombre de salida por el nombre base de ese archivo y recargará su contenido. Los valores necesarios para la generación se capturarán antes de iniciar el hilo de trabajo, de modo que un cambio posterior en la interfaz no altere el trabajo en curso.

Al finalizar un libro, la interfaz volverá a habilitar la generación. La siguiente selección se tratará como un trabajo nuevo y conservará únicamente las preferencias generales de voz, velocidad, estrategia y carpeta.

## Errores

Un EPUB sin documentos legibles producirá un error explícito. Un conjunto temporal incompleto o incoherente no se concatenará. Los fragmentos válidos permanecerán disponibles para reanudar el mismo trabajo.

## Pruebas

- Comprobar que un EPUB se extrae en el orden de su `spine`.
- Comprobar el orden real de `Tocando el vacío` y `Marte Rojo`.
- Comprobar que dos textos o configuraciones diferentes producen carpetas temporales diferentes.
- Comprobar que el montaje rechaza fragmentos ausentes, sobrantes o mal numerados.
- Comprobar que seleccionar un segundo archivo sustituye el nombre de salida del primero.
