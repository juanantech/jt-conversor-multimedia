<p align="center"><img src="assets/icon.png" width="128" alt="JT Conversor Multimedia"></p>

# JT Conversor Multimedia

Conversor de vídeo y audio de **JUANAN TECH**, de código abierto (GPL-3.0) y basado en [FFmpeg](https://ffmpeg.org).

- **Vídeo:** MP4, MKV, AVI, MOV, WEBM · **Audio:** MP3, M4A, WAV, FLAC, OGG (también extrae el audio de un vídeo).
- **Calidad máxima siempre:** si el códec ya encaja en el formato de destino, copia sin recodificar (0 % de pérdida y casi instantáneo). Si no, recodifica con ajustes visual/auditivamente sin pérdida: H.264 CRF 16, VP9 CRF 15, MPEG-4 q2, AAC y MP3 a 320 kbps, Vorbis q10, FLAC y WAV de 24 bits sin pérdida.
- Sin marcas de agua, sin publicidad, sin conexión a internet y sin telemetría.

## Uso

1. Arrastra archivos a la ventana o pulsa **Añadir archivos**.
2. Elige el formato y, si quieres, la carpeta de destino (por defecto, la del original).
3. Pulsa **Convertir**. Pasa el ratón por un archivo para ver la ruta del resultado o el error.

## Compilar

- **En tu PC:** instala Python 3.10–3.15 desde python.org y ejecuta `build.bat`. El resultado queda en `dist\JT Conversor Multimedia.exe`.
- **En GitHub:** publica una *release* en el repositorio. GitHub Actions compila el .exe, lo prueba y lo adjunta a la release.
- **Desde el código:** tras `build.bat`, `.venv\Scripts\python main.py`.

## Seguridad

- FFmpeg se ejecuta con una lista de argumentos, nunca a través de la consola (sin inyección de comandos), y siempre desde su ruta empaquetada, no desde el `PATH`.
- Las entradas solo pueden usar el protocolo `file`: un archivo trampa (p. ej. una lista HLS disfrazada de vídeo) no puede abrir conexiones de red. Las rutas llevan el prefijo `file:` para que un nombre como `-algo.mp4` o `http:x.mov` no se interprete como opción o protocolo.
- Nunca sobrescribe: crea `nombre (1).ext` y además pasa `-n` a FFmpeg. Solo borra las salidas a medias que acaba de crear.
- La descarga de FFmpeg se verifica por SHA-256. Las dependencias de Python se instalan con versiones y hashes fijados (`--require-hashes`). Las acciones de GitHub están fijadas por commit y el flujo usa permisos mínimos.

## Licencias

- JT Conversor Multimedia: GPL-3.0-or-later (ver `LICENSE`).
- FFmpeg 9.0.2, build *essentials* de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/): GPLv3. Código fuente: <https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz>.
- Qt / PySide6: LGPLv3 · Montserrat: SIL Open Font License 1.1 (`assets/OFL-Montserrat.txt`).

Freemake es una marca de sus respectivos propietarios. Este proyecto se ha escrito desde cero y no contiene código ni recursos de Freemake.
