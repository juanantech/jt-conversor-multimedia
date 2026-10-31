"""Prueba de humo: crea un clip y lo convierte a todos los formatos, primero con FFmpeg y luego con la interfaz."""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication  # noqa: E402

from main import FFMPEG, FORMATS, Window, command, ext, probe  # noqa: E402

with tempfile.TemporaryDirectory() as tmp:
    src = Path(tmp, "-prueba ñ.mkv")  # nombre que empieza por «-»: no debe confundirse con una opción
    subprocess.run([FFMPEG, "-v", "error", "-f", "lavfi", "-i", "testsrc2=d=2:s=320x240", "-f", "lavfi",
                    "-i", "sine=d=2", "-c:v", "libx264", "-c:a", "aac", "file:" + str(src)], check=True)
    info = probe(str(src))
    assert info[1] == ["h264"] and info[2] == ["aac"], info
    for fmt in FORMATS:
        for copy in (True, False):
            dst = Path(tmp, f"{fmt}-{copy}.{ext(fmt)}")
            subprocess.run([FFMPEG, *command(str(src), dst, fmt, info, copy)], check=True, capture_output=True)
            out = probe(str(dst))
            assert out[1] or FORMATS[fmt][1] is None, f"{fmt}: sin vídeo"
            assert out[2] or fmt == "GIF" or FORMATS[fmt][3] is None, f"{fmt}: sin audio"
            print("OK", fmt, "copia" if copy else "recodificado")

    app = QApplication([])
    w = Window()
    w.add([src])
    w.out_dir = tmp
    next(b for b in w.group.buttons() if b.text() == "MP3").setChecked(True)
    w.toggle()
    end = time.time() + 120
    while w.go.text() == "Cancelar" and time.time() < end:
        app.processEvents()
        time.sleep(0.05)
    assert w.ok == 1 and Path(tmp, "-prueba ñ.mp3").is_file(), w.list.item(0).toolTip()
    print("OK interfaz")
