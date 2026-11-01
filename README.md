<p align="center"><img src="assets/icon.png" width="128" alt="JT Conversor Multimedia"></p>

# JT Conversor Multimedia

Conversor de vídeo, audio, imagen y documentos de **JUANAN TECH**, de código abierto (GPL-3.0), basado en [FFmpeg](https://ffmpeg.org) y con [LibreOffice](https://www.libreoffice.org) integrado.

## Descargar

**[⬇ Descargar JT Conversor Multimedia para Windows (.zip)](https://github.com/juanantech/jt-conversor-multimedia/releases/latest/download/JT.Conversor.Multimedia.zip)**

El ZIP trae una carpeta con el programa, un único `.exe` portable, y `LEEME - Aviso de Windows.txt`. No se instala ni necesita nada más (ni Microsoft Office, ni LibreOffice, ni las apps de Apple), y funciona sin internet. Extrae el ZIP y abre `JT Conversor Multimedia.exe` con doble clic. La primera vez, Windows SmartScreen puede avisar porque el programa no está firmado: pulsa «Más información» → «Ejecutar de todas formas». El LÉEME explica por qué sale ese aviso y cómo comprobar que el programa está limpio.

## Qué hace

- **Vídeo (15):** MP4, MKV, AVI, MOV, WEBM, MP4 H.265, M4V, GIF, MPG, TS, WMV, FLV, 3GP, OGV y ProRes (MOV).
- **Audio (11):** MP3, M4A, WAV, FLAC, OGG, OPUS, AAC, ALAC, AIFF, WMA y AC3. También extrae el audio de un vídeo.
- **Imagen (22):** JPG, PNG, WEBP, AVIF, BMP, TIFF, ICO, JPEG 2000 (JP2), TGA, QOI, PPM, PGM, PBM, PAM, HDR, EXR, DPX, PCX, SGI, Sun Raster (RAS), XBM y XWD. Además abre HEIC/HEIF (fotos de iPhone), PSD y DDS. De un vídeo guarda el primer fotograma y de un audio, su carátula. Para GIF animado, usa el botón GIF de vídeo.
- **Documento (16):** DOCX, DOC, ODT, RTF, TXT, HTML, EPUB y PDF (texto); XLSX, XLS, ODS, CSV y NUMBERS (hojas de cálculo); PPTX, PPT y ODP (presentaciones). Abre también Pages, Numbers y Keynote de Apple, PDF, WPS y WordPerfect. Las conversiones desde Pages, Numbers, Keynote y PDF se marcan como «aproximado» porque el diseño puede variar; de Numbers se exportan los valores de cada hoja. Crear archivos Pages o Keynote no es posible fuera de las apps de Apple: usa DOCX o PPTX, que Pages y Keynote abren directamente.
- **Calidad máxima siempre:** si el códec ya encaja en el formato de destino, copia sin recodificar (0 % de pérdida y casi instantáneo). Si no, recodifica con ajustes visual/auditivamente sin pérdida: H.264 CRF 16, H.265 CRF 18, VP9 CRF 15, ProRes 422 HQ, MPEG-4/MPEG-2/WMV q2, Theora q10, AAC y MP3 a 320 kbps, AC3 a 640 kbps, Opus a 256 kbps, Vorbis q10, y FLAC, ALAC, WAV y AIFF sin pérdida. En imagen: JPG q2, AVIF CRF 10 (4:4:4), WEBP sin pérdida y el resto sin pérdida o al máximo de su formato (PBM y XBM son en blanco y negro, PGM en grises; ICO se limita a 256×256). Los formatos antiguos (WMV, FLV, 3GP, MPG) llegan hasta donde da su códec.
- Sin marcas de agua, sin publicidad, sin conexión a internet y sin telemetría.

## Uso

1. Arrastra archivos a la ventana o pulsa **Añadir archivos**.
2. Elige el formato y, si quieres, la carpeta de destino (por defecto, la del original).
3. Pulsa **Convertir**. Al terminar se abre la carpeta con los archivos convertidos. Pasa el ratón por un archivo para ver la ruta del resultado o el error.

La primera vez que conviertas un documento, el programa descomprime su LibreOffice (≈1 min) en `%LOCALAPPDATA%\JT Conversor Multimedia` y lo reutiliza después. Para liberar ese espacio, borra esa carpeta.

## Compilar

- **En tu PC:** instala Python 3.10–3.15 desde python.org y ejecuta `build.bat`. El resultado queda en `dist\JT Conversor Multimedia.exe`.
- **En GitHub:** publica una *release* en el repositorio. GitHub Actions compila el .exe, lo prueba y lo adjunta a la release.
- **Desde el código:** tras `build.bat`, `.venv\Scripts\python main.py`.

## Seguridad

- FFmpeg se ejecuta con una lista de argumentos, nunca a través de la consola (sin inyección de comandos), y siempre desde su ruta empaquetada, no desde el `PATH`.
- Las entradas solo pueden usar el protocolo `file`: un archivo trampa (p. ej. una lista HLS disfrazada de vídeo) no puede abrir conexiones de red. Las rutas llevan el prefijo `file:` para que un nombre como `-algo.mp4` o `http:x.mov` no se interprete como opción o protocolo.
- Nunca sobrescribe: crea `nombre (1).ext` y además pasa `-n` a FFmpeg. Solo borra las salidas a medias que acaba de crear.
- LibreOffice se ejecuta sin interfaz y con un perfil propio que desactiva las macros, bloquea las imágenes y enlaces externos y no actualiza vínculos al abrir documentos.
- Las descargas de FFmpeg y LibreOffice se verifican por SHA-256. Las dependencias de Python se instalan con versiones y hashes fijados (`--require-hashes`). Las acciones de GitHub están fijadas por commit y el flujo usa permisos mínimos.

## Licencias

- JT Conversor Multimedia: GPL-3.0-or-later (ver `LICENSE`).
- FFmpeg 9.0.2, build *essentials* de [gyan.dev](https://www.gyan.dev/ffmpeg/builds/): GPLv3. Código fuente: <https://ffmpeg.org/releases/ffmpeg-9.0.2.tar.xz>.
- LibreOffice 26.2.6: MPL-2.0 y otras licencias libres. Código fuente: <https://www.libreoffice.org/download/source-code/>.
- numbers-parser y openpyxl: MIT.
- Qt / PySide6: LGPLv3 · Montserrat: SIL Open Font License 1.1 (`assets/OFL-Montserrat.txt`).

Freemake es una marca de sus respectivos propietarios. Este proyecto se ha escrito desde cero y no contiene código ni recursos de Freemake.
