"""Prueba de humo: convierte un clip a todos los formatos con FFmpeg y, con la interfaz, a MP3 y a cada documento."""
import gc
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.environ.get("GITHUB_ACTIONS"):  # en GitHub, el error queda como anotación, legible sin iniciar sesión
    sys.excepthook = lambda *exc: print("::error::" + "".join(traceback.format_exception(*exc)).replace("\n", "%0A"))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from PySide6.QtWidgets import QApplication  # noqa: E402

import main  # noqa: E402
from main import DOCS, FFMPEG, FORMATS, THEMES, Window, command, ext, probe  # noqa: E402

opened = []  # carpetas que la interfaz abriría al terminar (en CI no se abre el Explorador)
main.QDesktopServices = SimpleNamespace(openUrl=lambda url: opened.append(Path(url.toLocalFile())))

NS = ('xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
      'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" '
      'xmlns:table="urn:oasis:names:tc:opendocument:xmlns:table:1.0" '
      'xmlns:draw="urn:oasis:names:tc:opendocument:xmlns:drawing:1.0" '
      'xmlns:svg="urn:oasis:names:tc:opendocument:xmlns:svg-compatible:1.0"')
FLAT = {  # documentos de prueba en ODF plano: texto, hoja de cálculo y presentación
    "fodt": ("text", "<office:text><text:p>Hola JUANAN TECH</text:p></office:text>"),
    "fods": ("spreadsheet", '<office:spreadsheet><table:table table:name="Datos"><table:table-row>'
             '<table:table-cell office:value-type="float" office:value="42"><text:p>42</text:p></table:table-cell>'
             "</table:table-row></table:table></office:spreadsheet>"),
    "fodp": ("presentation", '<office:presentation><draw:page draw:name="1"><draw:frame svg:x="2cm" svg:y="2cm" '
             'svg:width="10cm" svg:height="3cm"><draw:text-box><text:p>Hola</text:p></draw:text-box></draw:frame>'
             "</draw:page></office:presentation>"),
}

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
    w.out_dir = tmp

    w.theme_btn.click()  # tema y accesibilidad: cambian la hoja de estilos y se recuerdan al reabrir
    assert f"QWidget#root {{ background: {THEMES[w.theme]['bg']}; }}" in app.styleSheet() and Window().theme == w.theme
    w.big.setChecked(True)
    w.hc.setChecked(True)
    assert "font-size: 25px" in app.styleSheet() and "QWidget#root { background: #000000; }" in app.styleSheet()
    img = w.a11y_btn.icon().pixmap(48, 48).toImage()
    assert any(img.pixelColor(x, y).alpha() for x in range(img.width()) for y in range(img.height())), "icono vacío"
    w.big.setChecked(False)
    w.hc.setChecked(False)
    w.theme_btn.click()
    print("OK tema y accesibilidad")

    def run(path, fmt):
        """Convierte un archivo con la interfaz, como lo haría el usuario."""
        w.list.clear()
        w.add([path])
        next(b for b in w.group.buttons() if b.text() == fmt).setChecked(True)
        w.toggle()
        end = time.time() + 600
        while w.go.text() == "Cancelar" and time.time() < end:
            app.processEvents()
            time.sleep(0.05)
        assert w.ok == 1, (fmt, w.list.item(0).toolTip())
        assert opened == [Path(tmp)], opened
        opened.clear()
        print("OK interfaz", fmt)

    run(src, "MP3")
    for e, (kind, body) in FLAT.items():
        Path(tmp, f"doc.{e}").write_text(f'<?xml version="1.0" encoding="UTF-8"?><office:document {NS} '
                                         f'office:version="1.3" office:mimetype="application/vnd.oasis.opendocument.'
                                         f'{kind}"><office:body>{body}</office:body></office:document>', "utf-8")
    for fmt in DOCS:
        family = "fods" if fmt in ("XLSX", "XLS", "ODS", "CSV", "NUMBERS") else "fodp" if fmt in ("PPTX", "PPT", "ODP") else "fodt"
        run(Path(tmp, f"doc.{family}"), fmt)

    from numbers_parser import Document
    doc = Document(str(Path(tmp, "doc.numbers")))
    assert doc.sheets[0].tables[0].cell(0, 0).value == 42
    del doc
    gc.collect()  # numbers-parser no cierra el ZIP que lee: se libera antes de borrar la carpeta temporal
    print("OK Numbers legible")
