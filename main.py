"""JT Conversor Multimedia · JUANAN TECH · GPL-3.0-or-later

Convierte vídeo, audio e imagen con FFmpeg a la máxima calidad: copia sin pérdida cuando el códec ya encaja
en el formato de destino y, si no, recodifica con ajustes visual/auditivamente sin pérdida.
Los documentos se convierten con un LibreOffice integrado (sin instalar), que se descomprime la primera vez.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QPoint, QProcess, QSettings, QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QFontDatabase, QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtWidgets import (QApplication, QButtonGroup, QDialog, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
FFMPEG = str(BASE / "ffmpeg" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"))
SAFE = ["-hide_banner", "-nostdin", "-protocol_whitelist", "file"]  # solo archivos locales: nada de red
LO_ZIP = BASE / "libreoffice.zip"  # LibreOffice 26.2.6 empaquetado por build.bat
CACHE = Path(os.environ.get("LOCALAPPDATA", Path.home())) / "JT Conversor Multimedia"
LO_DIR = CACHE / "LibreOffice-26.2.6"
SOFFICE = str(LO_DIR / "program" / "soffice.com") if LO_ZIP.exists() else shutil.which("soffice") or "soffice"
TAR = str(Path(os.environ.get("SystemRoot", r"C:\Windows")) / "System32" / "tar.exe")


class _Any:  # MKV admite prácticamente cualquier códec
    def __contains__(self, _):
        return True


H264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p"]
AAC, VORBIS = ["-c:a", "aac", "-b:a", "320k"], ["-c:a", "libvorbis", "-q:a", "10"]
MP3 = ["-c:a", "libmp3lame", "-b:a", "320k", "-ac", "2"]
AC3, PCM = ["-c:a", "ac3", "-b:a", "640k"], {"pcm_s16le", "pcm_s24le"}
MP4A = {"aac", "mp3", "alac", "ac3", "eac3"}


def img(codec, *opts):  # formato de imagen: sin audio (aok y aenc = None)
    return {codec}, ["-c:v", codec, *opts], None, None


# formato: (vídeo que se copia, recodificación de vídeo | None = solo audio, audio que se copia, recodificación de audio)
FORMATS = {
    "MP4": ({"h264", "hevc", "av1"}, H264, MP4A, AAC),
    "MKV": (_Any(), H264, _Any(), ["-c:a", "flac"]),
    "AVI": ({"mpeg4", "mjpeg"}, ["-c:v", "mpeg4", "-vtag", "xvid", "-q:v", "2"], {"mp3", "ac3"}, MP3),
    "MOV": ({"h264", "hevc", "prores"}, H264, {"aac", "alac", *PCM}, AAC),
    "WEBM": ({"vp8", "vp9", "av1"}, ["-c:v", "libvpx-vp9", "-crf", "15", "-b:v", "0", "-row-mt", "1",
                                     "-pix_fmt", "yuv420p"], {"opus", "vorbis"}, VORBIS),
    "H.265": ({"hevc"}, ["-c:v", "libx265", "-preset", "slow", "-crf", "18", "-pix_fmt", "yuv420p", "-tag:v", "hvc1",
                         "-x265-params", "log-level=error"], MP4A, AAC),
    "M4V": ({"h264"}, H264, {"aac", "alac"}, AAC),
    "GIF": ({"gif"}, ["-vf", "split[a][b];[a]palettegen=stats_mode=single[p];[b][p]paletteuse=new=1"], set(), ["-an"]),
    "MPG": ({"mpeg2video", "mpeg1video"}, ["-c:v", "mpeg2video", "-q:v", "2", "-pix_fmt", "yuv420p"],
            {"mp2", "ac3", "mp3"}, AC3),
    "TS": ({"h264", "hevc", "mpeg2video"}, H264, {"aac", "mp3", "mp2", "ac3", "eac3"}, AAC),
    "WMV": ({"wmv1", "wmv2", "wmv3", "vc1"}, ["-c:v", "wmv2", "-q:v", "2"], {"wmav1", "wmav2"},
            ["-c:a", "wmav2", "-b:a", "192k", "-ac", "2"]),
    "FLV": ({"h264", "flv1"}, H264, {"aac", "mp3"}, AAC),
    "3GP": ({"h264", "h263", "mpeg4"}, H264, {"aac", "amr_nb", "amr_wb"}, AAC),
    "OGV": ({"theora"}, ["-c:v", "libtheora", "-q:v", "10"], {"vorbis", "opus", "flac"}, VORBIS),
    "ProRes": ({"prores"}, ["-c:v", "prores_ks", "-profile:v", "3", "-pix_fmt", "yuv422p10le", "-vendor", "apl0"],
               PCM, ["-c:a", "pcm_s24le"]),
    "MP3": (None, None, {"mp3"}, MP3),
    "M4A": (None, None, {"aac", "alac"}, AAC),
    "WAV": (None, None, PCM, ["-c:a", "pcm_s24le"]),
    "FLAC": (None, None, {"flac"}, ["-c:a", "flac"]),
    "OGG": (None, None, {"vorbis"}, VORBIS),
    "OPUS": (None, None, {"opus"}, ["-c:a", "libopus", "-b:a", "256k"]),
    "AAC": (None, None, {"aac"}, AAC),
    "ALAC": (None, None, {"alac"}, ["-c:a", "alac"]),
    "AIFF": (None, None, {"pcm_s16be", "pcm_s24be"}, ["-c:a", "pcm_s24be"]),
    "WMA": (None, None, {"wmav1", "wmav2"}, ["-c:a", "wmav2", "-b:a", "192k", "-ac", "2"]),
    "AC3": (None, None, {"ac3"}, AC3),
    "JPG": img("mjpeg", "-q:v", "2"),
    "PNG": img("png"),
    "WEBP": img("libwebp", "-lossless", "1"),
    "AVIF": img("libaom-av1", "-still-picture", "1", "-crf", "10", "-pix_fmt", "yuv444p"),
    "BMP": img("bmp"),
    "TIFF": img("tiff"),
    "ICO": img("png", "-pix_fmt", "rgba", "-vf", "scale='min(iw,256)':'min(ih,256)':force_original_aspect_ratio=decrease"),
    "JP2": img("libopenjpeg"),
    "TGA": img("targa"),
    **{f.upper(): img(f) for f in ("qoi", "ppm", "pgm", "pbm", "pam", "hdr", "exr", "dpx", "pcx", "sgi")},
    "RAS": img("sunrast"),
    "XBM": img("xbm"),
    "XWD": img("xwd"),
}
# documento: formato de exportación de LibreOffice (NUMBERS pasa por XLSX y luego por numbers-parser)
DOCS = {
    "DOCX": "docx", "DOC": "doc", "ODT": "odt", "RTF": "rtf", "TXT": "txt:Text (encoded):UTF8", "HTML": "html",
    "EPUB": "epub", "PDF": "pdf", "XLSX": "xlsx", "XLS": "xls", "ODS": "ods",
    "CSV": "csv:Text - txt - csv (StarCalc):44,34,76", "NUMBERS": "xlsx", "PPTX": "pptx", "PPT": "ppt", "ODP": "odp",
}
PDF_IN = {**dict.fromkeys(("DOCX", "DOC", "ODT", "RTF"), "writer_pdf_import"),
          **dict.fromkeys(("PPTX", "PPT", "ODP"), "impress_pdf_import")}  # cómo abrir un PDF según el destino
APPROX = (".pages", ".key", ".numbers", ".pdf")  # orígenes cuya conversión es aproximada
EXT = {"H.265": "mp4", "ProRes": "mov", "ALAC": "m4a"}  # formatos cuyo botón no coincide con la extensión
MP4_FAMILY = (".mp4", ".mov", ".m4v", ".m4a", ".3gp")
EXTS = ("*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.f4v *.m4v *.mpg *.mpeg *.vob *.ts *.mts *.m2ts *.mxf *.3gp *.ogv "
        "*.asf *.rm *.rmvb *.divx *.gif *.mp3 *.m4a *.m4b *.aac *.wav *.flac *.ogg *.opus *.wma *.aif *.aiff *.ac3 "
        "*.dts *.amr *.ape *.wv *.mka *.caf *.mp2 *.jpg *.jpeg *.png *.webp *.avif *.bmp *.tif *.tiff *.ico *.jp2 "
        "*.tga *.qoi *.ppm *.pgm *.pbm *.pam *.hdr *.exr *.dpx *.pcx *.sgi *.ras *.xbm *.xwd *.heic *.heif *.psd *.dds "
        "*.doc *.docx *.docm *.dotx *.odt *.ott *.rtf *.txt *.htm *.html *.pdf *.xls *.xlsx *.xlsm *.ods *.csv *.numbers "
        "*.ppt *.pptx *.pps *.ppsx *.odp *.key *.pages *.wps *.wpd *.fodt *.fods *.fodp")


def ext(fmt):
    return EXT.get(fmt, fmt.lower())


def kind(fmt):
    if fmt in DOCS:
        return "Documento"
    v = FORMATS[fmt]
    return "Audio" if v[1] is None else "Imagen" if v[3] is None else "Vídeo"


def doc_command(src, fmt, outdir):
    """Argumentos de LibreOffice: sin interfaz y con un perfil propio que bloquea macros y enlaces externos."""
    infilter = [f"--infilter={PDF_IN[fmt]}"] if src.lower().endswith(".pdf") and fmt in PDF_IN else []
    return [f"-env:UserInstallation={(CACHE / 'perfil').as_uri()}", "--headless", "--norestore", "--nologo",
            "--nodefault", "--nolockcheck", *infilter, "--convert-to", DOCS[fmt], "--outdir", str(outdir), src]


def to_numbers(xlsx, dst):
    """Pasa los valores de cada hoja de un XLSX a un documento de Apple Numbers."""
    from numbers_parser import Document
    from openpyxl import load_workbook
    wb, doc = load_workbook(xlsx, read_only=True, data_only=True), Document()
    for i, ws in enumerate(wb.worksheets):
        if i:
            doc.add_sheet(ws.title)
        else:
            doc.sheets[0].name = ws.title
        table = doc.sheets[i].tables[0]
        for r, row in enumerate(ws.iter_rows(values_only=True)):
            for c, value in enumerate(row):
                if value is not None:
                    table.write(r, c, value)
    wb.close()
    doc.save(str(dst))


def probe(src):
    """(duración en s, códecs de vídeo, códecs de audio) leídos de la cabecera del archivo."""
    try:
        info = subprocess.run([FFMPEG, *SAFE, "-i", "file:" + src], capture_output=True, timeout=60,
                              creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0)).stderr.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        info = ""
    d = re.search(r"Duration: (\d+):(\d\d):(\d\d\.\d+)", info)
    streams = re.findall(r"Stream #\S+.*?: (Video|Audio): (\w+)(.*)", info)
    codecs = lambda kind: [c for k, c, rest in streams if k == kind and "attached pic" not in rest]
    return (int(d[1]) * 3600 + int(d[2]) * 60 + float(d[3]) if d else 0), codecs("Video"), codecs("Audio")


def command(src, dst, fmt, info, copy=True):
    """Argumentos de FFmpeg; con copy=True copia sin recodificar los flujos que ya son compatibles."""
    vok, venc, aok, aenc = FORMATS[fmt]
    _, vc, ac = info
    mp4 = Path(dst).suffix.lower() in MP4_FAMILY
    args = [*SAFE, "-v", "error", "-n", "-i", "file:" + src, "-progress", "pipe:1", "-nostats"]
    if aenc is None:  # imagen: el fotograma principal (o la carátula de un audio), sin sonido
        return args + ["-an", "-frames:v", "1", "-update", "1",
                       *(["-c:v", "copy"] if copy and vc and vc[0] in vok else venc), "file:" + str(dst)]
    if venc is None:
        ac = ac[:1]
        args += ["-map", "0:a:0"]
    else:
        args += ["-map", "0:V:0?", "-map", "0:a?"]
        if copy and vc and vc[0] in vok:
            args += ["-c:v", "copy"] + (["-tag:v", "hvc1"] if vc[0] == "hevc" and mp4 else [])
        else:
            args += venc
    args += ["-c:a", "copy"] if copy and ac and all(c in aok for c in ac) else aenc
    if mp4:
        args += ["-movflags", "+faststart"]
    return args + ["file:" + str(dst)]


def unique(path):
    """Nunca sobrescribe: «nombre (1).ext», «nombre (2).ext»…"""
    n, p = 1, path
    while p.exists():
        p, n = path.with_name(f"{path.stem} ({n}){path.suffix}"), n + 1
    return p


# Paletas de la web de JUANAN TECH: tema oscuro, tema claro y contraste alto (este último manda sobre el tema)
THEMES = {
    "dark": dict(bg="#0F172A", panel="#1E293B", line="#334155", text="#E6EEF7", muted="#94A3B8", dim="#64748B",
                 sel="#334155", hover="#00C2FF", accent="#00C2FF", accent2="#007EEA", on="#0F172A",
                 ctrl="#758399", icon="#FFFFFF"),
    "light": dict(bg="#FFFFFF", panel="#F0F4F9", line="#C8D2E0", text="#0F172A", muted="#475569", dim="#94A3B8",
                  sel="#D6E4F5", hover="#007EEA", accent="#00C2FF", accent2="#007EEA", on="#0F172A",
                  ctrl="#64748B", icon="#000000"),
    "contrast": dict(bg="#000000", panel="#000000", line="#FFFFFF", text="#FFFFFF", muted="#FFFFFF", dim="#AAAAAA",
                     sel="#333333", hover="#8EEAFF", accent="#8EEAFF", accent2="#8EEAFF", on="#000000",
                     ctrl="#FFFFFF", icon="#FFFFFF"),
}
QSS = """
* { font-family: Montserrat; font-size: %(f)spx; color: %(text)s; }
QWidget#root { background: %(bg)s; }
QLabel { background: transparent; }
QLabel#title { font-size: %(ft)spx; font-weight: 600; }
QLabel#muted { color: %(muted)s; }
QListWidget { background: %(panel)s; border: 2px dashed %(line)s; border-radius: 12px; padding: 6px; }
QListWidget::item { padding: 6px; border-radius: 6px; }
QListWidget::item:selected { background: %(sel)s; }
QPushButton { background: %(panel)s; border: 1px solid %(line)s; border-radius: 8px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { border-color: %(hover)s; }
QPushButton:checked { background: %(accent)s; border-color: %(accent)s; color: %(on)s; }
QPushButton:disabled { color: %(dim)s; }
QPushButton#primary { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 %(accent)s, stop:1 %(accent2)s);
                      border: none; color: %(on)s; font-size: %(fp)spx; padding: 10px 32px; }
QPushButton#icon { background: transparent; border-color: %(ctrl)s; padding: 0; min-width: 44px; max-width: 44px;
                   min-height: 44px; max-height: 44px; }
QPushButton#icon:hover { background: %(panel)s; }
QDialog#a11y { background: %(bg)s; border: 1px solid %(ctrl)s; border-radius: 12px; }
QDialog#a11y QPushButton { background: %(panel)s; border-color: %(ctrl)s; border-radius: 6px; padding: 8px 12px;
                           min-height: 26px; font-weight: 400; text-align: left; }
QDialog#a11y QPushButton:checked { background: %(panel)s; color: %(text)s; border-color: %(hover)s; text-decoration: underline; }
QDialog#a11y QPushButton#link { background: transparent; border: none; color: %(hover)s; font-weight: 600;
                                text-decoration: underline; padding: 8px 0; }
QLabel#info { color: %(muted)s; font-size: %(fs)spx; border-top: 1px solid %(line)s; padding-top: 16px; }
QProgressBar { background: %(panel)s; border: none; border-radius: 6px; text-align: center; min-height: 22px; }
QProgressBar::chunk { border-radius: 6px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 %(accent)s, stop:1 %(accent2)s); }
QToolTip { background: %(panel)s; border: 1px solid %(hover)s; }
"""
A11Y = (("texto_ampliado", "Texto ampliado"), ("contraste_alto", "Contraste alto"), ("menos_movimiento", "Menos movimiento"))
A11Y_INFO = ("Los ajustes se aplican a todo el programa y se recuerdan para la próxima vez. Pulsa otra vez cada opción "
             "para desactivarla. Puedes usar el teclado para recorrer los controles y Escape para cerrar este panel.")
EFFECTS = (Qt.UIEffect.UI_AnimateMenu, Qt.UIEffect.UI_FadeMenu, Qt.UIEffect.UI_AnimateCombo,  # «Menos movimiento»
           Qt.UIEffect.UI_AnimateTooltip, Qt.UIEffect.UI_FadeTooltip, Qt.UIEffect.UI_AnimateToolBox)
ICONS = {  # iconos de línea 24×24 de la web: tema (◐) y accesibilidad
    "tema": '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5a8.5 8.5 0 0 0 0 17z" fill="{c}"/>',
    "accesibilidad": '<circle cx="14" cy="3.5" r="1.75"/><path d="M13 7l-1 7h6l3 6 2-1M12.7 9H18M9 10a6 6 0 1 0 6 9"/>',
}


def svg_icon(name, color):
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" stroke-width="1.8" '
           f'stroke-linecap="round" stroke-linejoin="round">{ICONS[name].format(c=color)}</svg>')
    pix = QPixmap(48, 48)
    pix.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pix)
    QSvgRenderer(svg.encode()).render(painter)
    painter.end()
    pix.setDevicePixelRatio(2)  # nítido en pantallas con escalado
    return QIcon(pix)


class Window(QWidget):
    def __init__(self):
        super().__init__(objectName="root", windowTitle="JT Conversor Multimedia", acceptDrops=True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)  # para que se pinte el fondo del QSS
        self.resize(1000, 700)
        self.out_dir, self.queue, self.proc, self.cancelled = None, [], None, False
        icon = QIcon(str(BASE / "assets" / "icon.png"))
        self.setWindowIcon(icon)

        logo = QLabel(pixmap=icon.pixmap(56, 56))
        titles = QVBoxLayout(spacing=0)
        titles.addWidget(QLabel("JT Conversor Multimedia", objectName="title"))
        titles.addWidget(QLabel("by JUANAN TECH · vídeo, audio, imagen y documentos a calidad máxima", objectName="muted"))
        # Tema y accesibilidad, como en la web; se recuerdan en ajustes.ini
        self.prefs = QSettings(str(CACHE / "ajustes.ini"), QSettings.Format.IniFormat)
        system = "light" if QApplication.styleHints().colorScheme() == Qt.ColorScheme.Light else "dark"
        self.theme = t if (t := self.prefs.value("tema")) in ("dark", "light") else system
        self.theme_btn = QPushButton(objectName="icon", clicked=self.toggle_theme)
        self.motion = {e: QApplication.isEffectEnabled(e) for e in EFFECTS}  # animaciones que indica Windows
        self.a11y_btn = QPushButton(objectName="icon", toolTip="Accesibilidad", accessibleName="Abrir ajustes de accesibilidad")
        self.panel = QDialog(self, Qt.WindowType.Popup, objectName="a11y", accessibleName="Ajustes de accesibilidad")
        self.panel.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)  # esquinas redondeadas
        self.panel.setAttribute(Qt.WidgetAttribute.WA_NoMouseReplay)  # pulsar el botón con el panel abierto lo cierra
        self.panel.setFixedWidth(240)
        box = QVBoxLayout(self.panel, spacing=10)
        box.setContentsMargins(20, 20, 20, 20)
        self.opts = {}
        for key, label in A11Y:
            b = self.opts[key] = QPushButton(label, checkable=True, checked=self.prefs.value(key, False, bool))
            b.toggled.connect(lambda on, key=key: (self.prefs.setValue(key, on), self.restyle()))
            box.addWidget(b)
        info = QLabel(A11Y_INFO, objectName="info", wordWrap=True, visible=False)
        box.addWidget(QPushButton("Accesibilidad", objectName="link", checkable=True,
                                  toggled=lambda on: (info.setVisible(on), self.panel.adjustSize())))
        box.addWidget(info)
        self.a11y_btn.clicked.connect(lambda: (self.panel.move(self.a11y_btn.mapToGlobal(
            QPoint(self.a11y_btn.width() - self.panel.width(), self.a11y_btn.height() + 8))), self.panel.show()))
        header = QHBoxLayout()
        header.addWidget(logo)
        header.addLayout(titles, 1)
        for b in (self.theme_btn, self.a11y_btn):
            b.setIconSize(QSize(22, 22))
            header.addWidget(b)

        self.list = QListWidget(selectionMode=QListWidget.SelectionMode.ExtendedSelection)
        self.add_btn = QPushButton("Añadir archivos", clicked=self.pick)
        self.del_btn = QPushButton("Quitar", clicked=lambda: [self.list.takeItem(self.list.row(i))
                                                              for i in self.list.selectedItems()])
        self.clear_btn = QPushButton("Limpiar", clicked=self.list.clear)
        files = QHBoxLayout()
        for w in (self.add_btn, self.del_btn, self.clear_btn):
            files.addWidget(w)
        files.addStretch()

        self.group, grid, row = QButtonGroup(self), QGridLayout(), 0
        for label in ("Vídeo", "Audio", "Imagen", "Documento"):
            grid.addWidget(QLabel(label, objectName="muted"), row, 0)
            fmts = [f for f in (*FORMATS, *DOCS) if kind(f) == label]
            for i, fmt in enumerate(fmts):  # 11 botones por fila
                b = QPushButton(fmt, checkable=True)
                self.group.addButton(b)
                grid.addWidget(b, row + i // 11, i % 11 + 1)
            row += (len(fmts) + 10) // 11
        self.group.buttons()[0].setChecked(True)

        self.dest = QLabel("Misma carpeta que el original", objectName="muted")
        self.dest_btn = QPushButton("Cambiar…", clicked=self.pick_dir)
        dest = QHBoxLayout()
        dest.addWidget(QLabel("Guardar en:"))
        dest.addWidget(self.dest, 1)
        dest.addWidget(self.dest_btn)

        self.bar = QProgressBar()
        self.go = QPushButton("Convertir", objectName="primary", clicked=self.toggle)
        bottom = QHBoxLayout()
        bottom.addWidget(self.bar, 1)
        bottom.addWidget(self.go)

        root = QVBoxLayout(self, spacing=12)
        root.setContentsMargins(20, 18, 20, 18)
        root.addLayout(header)
        root.addWidget(QLabel("Arrastra aquí tus vídeos, audios, imágenes o documentos, o pulsa «Añadir archivos».", objectName="muted"))
        root.addWidget(self.list, 1)
        for part in (files, grid, dest, bottom):
            root.addLayout(part)
        self.restyle()

    # --- tema y accesibilidad -------------------------------------------------------------
    def toggle_theme(self):
        self.theme = "light" if self.theme == "dark" else "dark"
        self.prefs.setValue("tema", self.theme)
        self.restyle()

    def restyle(self):
        big, hc, calm = (self.opts[key].isChecked() for key, _ in A11Y)
        pal = THEMES["contrast" if hc else self.theme]
        k = 1.125 if big else 1  # texto ampliado: +12,5 %, como en la web
        QApplication.instance().setStyleSheet(QSS % {**pal, "f": round(13 * k), "ft": round(22 * k), "fp": round(15 * k),
                                                     "fs": round(11 * k)})
        for effect, on in self.motion.items():  # menos movimiento: sin animaciones de menús ni de avisos
            QApplication.setEffectEnabled(effect, on and not calm)
        light = self.theme == "light" and not hc
        QApplication.styleHints().setColorScheme(Qt.ColorScheme.Light if light else Qt.ColorScheme.Dark)
        tip = "Cambiar a tema oscuro" if self.theme == "light" else "Cambiar a tema claro"
        self.theme_btn.setToolTip(tip)
        self.theme_btn.setAccessibleName(tip)
        self.theme_btn.setIcon(svg_icon("tema", pal["text"]))
        self.a11y_btn.setIcon(svg_icon("accesibilidad", pal["icon"]))

    # --- archivos -------------------------------------------------------------------------
    def add(self, paths):
        have = {self.list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.list.count())}
        for p in map(str, paths):
            if Path(p).is_file() and p not in have:
                item = QListWidgetItem(Path(p).name)
                item.setData(Qt.ItemDataRole.UserRole, p)
                item.setToolTip(p)
                self.list.addItem(item)
                have.add(p)

    def pick(self):
        self.add(QFileDialog.getOpenFileNames(self, "Añadir archivos", "", f"Vídeo, audio, imagen y documentos ({EXTS});;Todos (*)")[0])

    def pick_dir(self):
        if d := QFileDialog.getExistingDirectory(self, "Carpeta de destino"):
            self.out_dir = d
            self.dest.setText(d)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls() and not self.proc:
            e.acceptProposedAction()

    def dropEvent(self, e):
        self.add(u.toLocalFile() for u in e.mimeData().urls() if u.isLocalFile())

    # --- conversión -----------------------------------------------------------------------
    def toggle(self):
        if self.proc:
            self.cancelled = True
            return self.proc.kill()
        self.queue = [self.list.item(i) for i in range(self.list.count())]
        if not self.queue:
            return
        self.fmt, self.done, self.ok, self.cancelled, self.folders = self.group.checkedButton().text(), 0, 0, False, set()
        self.busy(True)
        self.next()

    def busy(self, on):
        for w in (self.add_btn, self.del_btn, self.clear_btn, self.dest_btn, *self.group.buttons()):
            w.setEnabled(not on)
        self.go.setText("Cancelar" if on else "Convertir")
        self.bar.setValue(0)
        self.bar.setFormat("%p %")

    def next(self):
        if not self.queue:
            self.busy(False)
            self.bar.setValue(100)
            for folder in () if self.cancelled else self.folders:  # abre la carpeta con lo convertido
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
            return self.bar.setFormat(f"Terminado · {self.ok} de {self.done} correctos")
        src = self.queue[0].data(Qt.ItemDataRole.UserRole)
        self.info = (0, [], []) if self.fmt in DOCS else probe(src)
        folder = Path(self.out_dir) if self.out_dir else Path(src).parent
        self.dst = unique(folder / f"{Path(src).stem}.{ext(self.fmt)}")
        self.start(src, copy=True)

    def start(self, src, copy):
        self.queue[0].setText(f"⏳ {Path(src).name}")
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.progress)
        self.proc.finished.connect(lambda code, status: self.finished(src, code, status))
        self.proc.errorOccurred.connect(lambda e: e == QProcess.ProcessError.FailedToStart
                                        and self.finished(src, -1, QProcess.ExitStatus.CrashExit))
        if self.fmt not in DOCS:
            self.args = command(src, self.dst, self.fmt, self.info, copy)
            return self.proc.start(FFMPEG, self.args)
        if LO_ZIP.exists() and not (LO_DIR / "listo").exists():  # solo la primera vez
            self.queue[0].setText(f"⏳ {Path(src).name} · preparando LibreOffice (solo la primera vez, ~1 min)")
            LO_DIR.mkdir(parents=True, exist_ok=True)
            self.args = ["descomprimir"]
            return self.proc.start(TAR, ["-xf", str(LO_ZIP), "-C", str(LO_DIR)])
        (CACHE / "perfil" / "user").mkdir(parents=True, exist_ok=True)
        shutil.copy(BASE / "assets" / "registrymodifications.xcu", CACHE / "perfil" / "user")
        self.tmp = Path(tempfile.mkdtemp(prefix="jtconv-"))
        self.args = doc_command(src, self.fmt, self.tmp)
        self.proc.start(SOFFICE, self.args)

    def save_doc(self, src, ok, err):
        """Recoge el resultado de LibreOffice de su carpeta temporal (y lo pasa a Numbers si toca)."""
        out = self.tmp / f"{Path(src).stem}.{DOCS[self.fmt].split(':')[0]}"
        try:
            if not (ok and out.exists() and out.stat().st_size):
                return False, f"Este archivo no se puede convertir a {self.fmt}.\n{err}".strip()
            if self.fmt == "NUMBERS":
                to_numbers(out, self.dst)
            else:
                shutil.move(out, self.dst)
            return True, ""
        except Exception as e:  # p. ej. un documento dañado
            return False, str(e)
        finally:
            shutil.rmtree(self.tmp, ignore_errors=True)

    def progress(self):
        t = re.findall(r"out_time_us=(\d+)", bytes(self.proc.readAllStandardOutput()).decode(errors="replace"))
        if t and self.info[0]:
            part = min(int(t[-1]) / 1e6 / self.info[0], 1)
            self.bar.setValue(int((self.done + part) * 100 / (self.done + len(self.queue))))

    def finished(self, src, code, status):
        err = bytes(self.proc.readAllStandardError()).decode("utf-8", "replace").strip()
        self.proc.deleteLater()
        self.proc = None
        ok = code == 0 and status == QProcess.ExitStatus.NormalExit
        if self.args == ["descomprimir"]:
            if ok:
                (LO_DIR / "listo").touch()
            if ok and not self.cancelled:
                return self.start(src, copy=True)
            ok = False
        elif self.fmt in DOCS:
            ok, err = self.save_doc(src, ok, err)
        if not ok:
            self.dst.unlink(missing_ok=True)  # borra la salida a medias (siempre es un archivo nuevo)
            if not self.cancelled and "copy" in self.args:
                return self.start(src, copy=False)  # la copia directa no encajó: recodificar
        mark = "✔" if ok else "■" if self.cancelled else "✖"
        approx = ok and self.fmt in DOCS and Path(src).suffix.lower() in APPROX
        self.queue[0].setText(f"{mark} {Path(src).name}" + (f"  →  {self.dst.name}" if ok else "")
                              + (" · aproximado" if approx else ""))
        self.queue[0].setToolTip((str(self.dst) + ("\nConversión aproximada: el diseño puede variar." if approx else ""))
                                 if ok else err[-800:] or "Cancelado")
        self.done, self.ok = self.done + 1, self.ok + ok
        if ok:
            self.folders.add(self.dst.parent)
        self.queue = [] if self.cancelled else self.queue[1:]
        self.bar.setValue(int(self.done * 100 / (self.done + len(self.queue))))
        self.next()

    def closeEvent(self, e):
        if self.proc:
            self.cancelled = True
            self.proc.kill()
            self.proc.waitForFinished(3000)
        e.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    for font in ("Montserrat-Regular.ttf", "Montserrat-SemiBold.ttf"):
        QFontDatabase.addApplicationFont(str(BASE / "assets" / font))
    if not Path(FFMPEG).is_file():
        QMessageBox.critical(None, "JT Conversor Multimedia", f"No se encuentra FFmpeg en:\n{FFMPEG}")
        sys.exit(1)
    window = Window()
    window.show()
    sys.exit(app.exec())
