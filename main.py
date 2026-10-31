"""JT Conversor Multimedia · JUANAN TECH · GPL-3.0-or-later

Convierte vídeo y audio con FFmpeg a la máxima calidad: copia sin pérdida cuando el códec ya encaja
en el formato de destino y, si no, recodifica con ajustes visual/auditivamente sin pérdida.
"""
import re
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import QProcess, Qt
from PySide6.QtGui import QFontDatabase, QIcon
from PySide6.QtWidgets import (QApplication, QButtonGroup, QFileDialog, QGridLayout, QHBoxLayout, QLabel,
                               QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton,
                               QVBoxLayout, QWidget)

BASE = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
FFMPEG = str(BASE / "ffmpeg" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"))
SAFE = ["-hide_banner", "-nostdin", "-protocol_whitelist", "file"]  # solo archivos locales: nada de red


class _Any:  # MKV admite prácticamente cualquier códec
    def __contains__(self, _):
        return True


H264 = ["-c:v", "libx264", "-preset", "slow", "-crf", "16", "-pix_fmt", "yuv420p"]
AAC, VORBIS = ["-c:a", "aac", "-b:a", "320k"], ["-c:a", "libvorbis", "-q:a", "10"]
MP3 = ["-c:a", "libmp3lame", "-b:a", "320k", "-ac", "2"]
# formato: (vídeo que se copia, recodificación de vídeo | None = solo audio, audio que se copia, recodificación de audio)
FORMATS = {
    "MP4": ({"h264", "hevc", "av1"}, H264, {"aac", "mp3", "alac", "ac3", "eac3"}, AAC),
    "MKV": (_Any(), H264, _Any(), ["-c:a", "flac"]),
    "AVI": ({"mpeg4", "mjpeg"}, ["-c:v", "mpeg4", "-vtag", "xvid", "-q:v", "2"], {"mp3", "ac3"}, MP3),
    "MOV": ({"h264", "hevc", "prores"}, H264, {"aac", "alac", "pcm_s16le", "pcm_s24le"}, AAC),
    "WEBM": ({"vp8", "vp9", "av1"}, ["-c:v", "libvpx-vp9", "-crf", "15", "-b:v", "0", "-row-mt", "1",
                                     "-pix_fmt", "yuv420p"], {"opus", "vorbis"}, VORBIS),
    "MP3": (None, None, {"mp3"}, MP3),
    "M4A": (None, None, {"aac", "alac"}, AAC),
    "WAV": (None, None, {"pcm_s16le", "pcm_s24le"}, ["-c:a", "pcm_s24le"]),
    "FLAC": (None, None, {"flac"}, ["-c:a", "flac"]),
    "OGG": (None, None, {"vorbis"}, VORBIS),
}
EXTS = "*.mp4 *.mkv *.avi *.mov *.webm *.wmv *.flv *.m4v *.mpg *.mpeg *.ts *.mts *.3gp *.mp3 *.m4a *.aac *.wav *.flac *.ogg *.opus *.wma *.aiff"


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
    args = [*SAFE, "-v", "error", "-n", "-i", "file:" + src, "-progress", "pipe:1", "-nostats"]
    if venc is None:
        ac = ac[:1]
        args += ["-map", "0:a:0"]
    else:
        args += ["-map", "0:V:0?", "-map", "0:a?"]
        if copy and vc and vc[0] in vok:
            args += ["-c:v", "copy"] + (["-tag:v", "hvc1"] if vc[0] == "hevc" and fmt in ("MP4", "MOV") else [])
        else:
            args += venc
    args += ["-c:a", "copy"] if copy and ac and all(c in aok for c in ac) else aenc
    if fmt in ("MP4", "MOV", "M4A"):
        args += ["-movflags", "+faststart"]
    return args + ["file:" + str(dst)]


def unique(path):
    """Nunca sobrescribe: «nombre (1).ext», «nombre (2).ext»…"""
    n, p = 1, path
    while p.exists():
        p, n = path.with_name(f"{path.stem} ({n}){path.suffix}"), n + 1
    return p


QSS = """
* { font-family: Montserrat; font-size: 13px; color: #E6EEF7; }
QWidget#root { background: #0F172A; }
QLabel { background: transparent; }
QLabel#title { font-size: 22px; font-weight: 600; }
QLabel#muted { color: #94A3B8; }
QListWidget { background: #1E293B; border: 2px dashed #334155; border-radius: 12px; padding: 6px; }
QListWidget::item { padding: 6px; border-radius: 6px; }
QListWidget::item:selected { background: #334155; }
QPushButton { background: #1E293B; border: 1px solid #334155; border-radius: 8px; padding: 8px 14px; font-weight: 600; }
QPushButton:hover { border-color: #00C2FF; }
QPushButton:checked { background: #00C2FF; border-color: #00C2FF; color: #0F172A; }
QPushButton:disabled { color: #64748B; }
QPushButton#primary { background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #00C2FF, stop:1 #007EEA);
                      border: none; color: #0F172A; font-size: 15px; padding: 10px 32px; }
QProgressBar { background: #1E293B; border: none; border-radius: 6px; text-align: center; min-height: 22px; }
QProgressBar::chunk { border-radius: 6px; background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00C2FF, stop:1 #007EEA); }
QToolTip { background: #1E293B; border: 1px solid #00C2FF; }
"""


class Window(QWidget):
    def __init__(self):
        super().__init__(objectName="root", windowTitle="JT Conversor Multimedia", acceptDrops=True)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)  # para que se pinte el fondo navy del QSS
        self.resize(780, 600)
        self.out_dir, self.queue, self.proc, self.cancelled = None, [], None, False
        icon = QIcon(str(BASE / "assets" / "icon.png"))
        self.setWindowIcon(icon)

        logo = QLabel(pixmap=icon.pixmap(56, 56))
        titles = QVBoxLayout(spacing=0)
        titles.addWidget(QLabel("JT Conversor Multimedia", objectName="title"))
        titles.addWidget(QLabel("by JUANAN TECH · vídeo y audio a calidad máxima", objectName="muted"))
        header = QHBoxLayout()
        header.addWidget(logo)
        header.addLayout(titles, 1)

        self.list = QListWidget(selectionMode=QListWidget.SelectionMode.ExtendedSelection)
        self.add_btn = QPushButton("Añadir archivos", clicked=self.pick)
        self.del_btn = QPushButton("Quitar", clicked=lambda: [self.list.takeItem(self.list.row(i))
                                                              for i in self.list.selectedItems()])
        self.clear_btn = QPushButton("Limpiar", clicked=self.list.clear)
        files = QHBoxLayout()
        for w in (self.add_btn, self.del_btn, self.clear_btn):
            files.addWidget(w)
        files.addStretch()

        self.group, grid = QButtonGroup(self), QGridLayout()
        for row, (label, video) in enumerate((("Vídeo", True), ("Audio", False))):
            grid.addWidget(QLabel(label, objectName="muted"), row, 0)
            for col, fmt in enumerate(f for f, v in FORMATS.items() if (v[1] is not None) == video):
                b = QPushButton(fmt, checkable=True)
                self.group.addButton(b)
                grid.addWidget(b, row, col + 1)
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
        root.addWidget(QLabel("Arrastra aquí tus vídeos o audios, o pulsa «Añadir archivos».", objectName="muted"))
        root.addWidget(self.list, 1)
        for part in (files, grid, dest, bottom):
            root.addLayout(part)

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
        self.add(QFileDialog.getOpenFileNames(self, "Añadir archivos", "", f"Vídeo y audio ({EXTS});;Todos (*)")[0])

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
        self.fmt, self.done, self.ok, self.cancelled = self.group.checkedButton().text(), 0, 0, False
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
            return self.bar.setFormat(f"Terminado · {self.ok} de {self.done} correctos")
        src = self.queue[0].data(Qt.ItemDataRole.UserRole)
        self.info = probe(src)
        folder = Path(self.out_dir) if self.out_dir else Path(src).parent
        self.dst = unique(folder / f"{Path(src).stem}.{self.fmt.lower()}")
        self.start(src, copy=True)

    def start(self, src, copy):
        self.args = command(src, self.dst, self.fmt, self.info, copy)
        self.queue[0].setText(f"⏳ {Path(src).name}")
        self.proc = QProcess(self)
        self.proc.readyReadStandardOutput.connect(self.progress)
        self.proc.finished.connect(lambda code, status: self.finished(src, code, status))
        self.proc.errorOccurred.connect(lambda e: e == QProcess.ProcessError.FailedToStart
                                        and self.finished(src, -1, QProcess.ExitStatus.CrashExit))
        self.proc.start(FFMPEG, self.args)

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
        if not ok:
            self.dst.unlink(missing_ok=True)  # borra la salida a medias (siempre es un archivo nuevo)
            if not self.cancelled and "copy" in self.args:
                return self.start(src, copy=False)  # la copia directa no encajó: recodificar
        mark = "✔" if ok else "■" if self.cancelled else "✖"
        self.queue[0].setText(f"{mark} {Path(src).name}" + (f"  →  {self.dst.name}" if ok else ""))
        self.queue[0].setToolTip(str(self.dst) if ok else err[-800:] or "Cancelado")
        self.done, self.ok = self.done + 1, self.ok + ok
        self.queue = [] if self.cancelled else self.queue[1:]
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
    app.styleHints().setColorScheme(Qt.ColorScheme.Dark)
    for font in ("Montserrat-Regular.ttf", "Montserrat-SemiBold.ttf"):
        QFontDatabase.addApplicationFont(str(BASE / "assets" / font))
    app.setStyleSheet(QSS)
    if not Path(FFMPEG).is_file():
        QMessageBox.critical(None, "JT Conversor Multimedia", f"No se encuentra FFmpeg en:\n{FFMPEG}")
        sys.exit(1)
    window = Window()
    window.show()
    sys.exit(app.exec())
