import re
import sys
import requests
import urllib.parse
from PyQt5.QtCore import QUrl, Qt, QTimer
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QPushButton, QTextEdit, QLabel, QDialog
from PyQt5.QtWebEngineWidgets import QWebEngineView
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import pyqtSignal


class VirusTotalWeb(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("newVirusToalWeb")
        self.setStyleSheet(
            "QMainWindow { background: #020305; color: #8cff87; }"
            "QLineEdit, QTextEdit { background: #0b1318; color: #8cff87; border: 1px solid #1c5d2f; }"
            "QPushButton { background: #11251a; color: #b8ffb4; border: 1px solid #1c5d2f; padding: 6px; }"
            "QPushButton:hover { background: #1c5d2f; }"
            "QLabel { color: #8cff87; }"
        )

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        top = QHBoxLayout()
        top.setSpacing(8)

        label = QLabel("URL:")
        label.setFixedWidth(40)
        self.url_input = QLineEdit("https://")
        self.url_input.setPlaceholderText("Pega aquí la web a analizar")
        self.url_input.returnPressed.connect(self.load_url)

        load_btn = QPushButton("Cargar")
        load_btn.clicked.connect(self.load_url)
        analyze_btn = QPushButton("Analizar")
        analyze_btn.clicked.connect(self.analyze_url)
        reject_btn = QPushButton("Rechazar cookies")
        reject_btn.clicked.connect(self.reject_cookies)

        top.addWidget(label)
        top.addWidget(self.url_input)
        top.addWidget(load_btn)
        top.addWidget(analyze_btn)
        top.addWidget(reject_btn)
        layout.addLayout(top)

        if QWebEngineView is not None:
            self.webview = QWebEngineView()
            self.webview.setUrl(QUrl("about:blank"))
            self.webview.loadFinished.connect(self.on_load_finished)
            self.webview.setMinimumHeight(380)
        else:
            self.webview = QLabel("WebEngine no disponible. Instala PyQtWebEngine para habilitar la vista web.")
            self.webview.setAlignment(Qt.AlignCenter)
            self.webview.setMinimumHeight(380)
        layout.addWidget(self.webview, 3)

        self.report = QTextEdit()
        self.report.setReadOnly(True)
        self.report.setLineWrapMode(QTextEdit.NoWrap)
        self.report.setStyleSheet("font-family: 'Consolas', monospace; font-size: 12px;")
        self.report.setPlainText("Interfaz lista. Introduce una URL y pulsa Cargar o Analizar.\n")
        layout.addWidget(self.report, 2)

        self.current_url = ""
        self.last_cookies = ""

        self.resize(1200, 850)
        self.show()

        self.resize(1200, 850)
        self.show()

    def normalize_url(self, url):
        url = url.strip()
        if not url:
            return ""
        if not re.match(r"^https?://", url, re.I):
            url = "http://" + url
        return url

    def append_report(self, text):
        self.report.append(text)

    def webview_available(self):
        return QWebEngineView is not None and isinstance(self.webview, QWebEngineView)

    def load_url(self):
        url = self.normalize_url(self.url_input.text())
        if not url:
            self.append_report("[error] URL inválida.")
            return
        self.current_url = url
        self.append_report(f"[cargar] Cargando {url}")
        if not self.webview_available():
            self.append_report("[error] No hay WebEngine disponible. Instala PyQtWebEngine para ver páginas.")
            return
        self.webview.setUrl(QUrl(url))

    def analyze_url(self):
        url = self.normalize_url(self.url_input.text())
        if not url:
            self.append_report("[error] URL inválida.")
            return
        self.current_url = url
        self.report.clear()
        self.append_report(f"[análisis] Analizando {url}\n")
        try:
            session = requests.Session()
            session.headers.update({
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"
            })
            response = session.get(url, timeout=18, allow_redirects=True)
            self.append_report(f"HTTP: {response.status_code} {response.reason}")
            self.append_report(f"URL final: {response.url}\n")
            self.append_report("Encabezados:\n")
            for key, value in response.headers.items():
                self.append_report(f"  {key}: {value}")

            if response.cookies:
                self.append_report("\nCookies recibidas desde el servidor:")
                for cookie in response.cookies:
                    httponly = cookie._rest.get("HttpOnly", False)
                    self.append_report(
                        f"  {cookie.name}={cookie.value} domain={cookie.domain} path={cookie.path} secure={cookie.secure} httponly={httponly}"
                    )
            else:
                self.append_report("\nNo se encontraron cookies establecidas por el servidor.")

            hidden_inputs = re.findall(r"<input[^>]+type=['\"]?hidden['\"]?[^>]*>", response.text, flags=re.I)
            comments = re.findall(r"<!--(.*?)-->", response.text, flags=re.S)
            self.append_report(f"\nCampos ocultos encontrados: {len(hidden_inputs)}")
            for hidden in hidden_inputs[:12]:
                self.append_report("  " + hidden.strip())
            self.append_report(f"\nComentarios HTML detectados: {len(comments)}")
            for comment in comments[:12]:
                clean = " ".join(comment.split())
                self.append_report("  " + clean[:220])

            third_parties = self.analyze_third_party(response.text, response.url)
            self.append_report("\nDominios de terceros detectados:")
            if third_parties:
                for domain in sorted(third_parties)[:30]:
                    self.append_report(f"  {domain}")
            else:
                self.append_report("  Ninguno detectado desde la HTML inicial.")

            self.append_report("\nCargando la web en vivo para auditoría de cookies y consentimientos...")
            if self.webview_available():
                self.webview.setUrl(QUrl(url))
            else:
                self.append_report("[info] No se puede cargar la vista web; falta PyQtWebEngine.")
        except Exception as exc:
            self.append_report(f"[error] Fallo en el análisis: {exc}")

    def analyze_third_party(self, html, base_url):
        base_host = urllib.parse.urlparse(base_url).hostname or ""
        domains = set()
        patterns = [r"src=\s*[\"']([^\"']+)[\"']", r"href=\s*[\"']([^\"']+)[\"']", r"action=\s*[\"']([^\"']+)[\"']", r"data=\s*[\"']([^\"']+)[\"']"]
        for pattern in patterns:
            for match in re.findall(pattern, html, flags=re.I):
                parsed = urllib.parse.urlparse(match)
                host = parsed.hostname
                if host and host != base_host and not host.endswith("." + base_host):
                    domains.add(host)
        return domains

    def on_load_finished(self, ok):
        if not ok:
            self.append_report("[error] No se pudo cargar la página.")
            return
        self.append_report("[live] Página cargada. Recopilando información de ejecución...")
        script = (
            "(function(){"
            "var r={cookies:document.cookie, localStorage:[], sessionStorage:[], banners:[], forms:[], scripts:[]};"
            "for(var i=0;i<localStorage.length;i++){r.localStorage.push(localStorage.key(i));}"
            "for(var i=0;i<sessionStorage.length;i++){r.sessionStorage.push(sessionStorage.key(i));}"
            "var nodes=document.querySelectorAll('button,input[type=button],input[type=submit],a');"
            "for(var j=0;j<nodes.length;j++){"
            "  var n=nodes[j]; var text=(n.innerText||n.value||'').trim().toLowerCase();"
            "  if(text.match(/reject|decline|deny|no thanks|no, thanks|opt-out|cookie.*reject|cookie.*decline/)) r.banners.push(text);"
            "}"
            "var forms=document.querySelectorAll('form'); for(var k=0;k<forms.length;k++){ if(forms[k].action) r.forms.push(forms[k].action);}"
            "var scripts=document.querySelectorAll('script[src]'); for(var s=0;s<scripts.length;s++){ r.scripts.push(scripts[s].src);}"
            "return r;"
            "})();"
        )
        self.webview.page().runJavaScript(script, self.on_runtime_info)

    def on_runtime_info(self, data):
        if not isinstance(data, dict):
            self.append_report("[error] No se pudo obtener información de ejecución.")
            return
        cookies = data.get("cookies", "")
        self.append_report(f"\nCookies en ejecución: {cookies if cookies else '[ninguna]'}")
        if data.get("localStorage"):
            self.append_report("LocalStorage:")
            for key in data["localStorage"][:20]:
                self.append_report(f"  {key}")
        if data.get("sessionStorage"):
            self.append_report("SessionStorage:")
            for key in data["sessionStorage"][:20]:
                self.append_report(f"  {key}")
        if data.get("banners"):
            self.append_report("Botones de rechazo/consentimiento detectados:")
            for text in data["banners"][:20]:
                self.append_report(f"  {text}")
        else:
            self.append_report("No se detectaron botones de rechazo explícitos en el DOM.")
        if data.get("forms"):
            self.append_report("Formularios y destinos:")
            for action in data["forms"][:20]:
                self.append_report(f"  {action}")
        self.last_cookies = cookies

    def reject_cookies(self):
        if not self.current_url:
            self.append_report("[info] Carga primero una página para probar el rechazo de cookies.")
            return
        if not self.webview_available():
            self.append_report("[error] Rechazo de cookies no disponible sin WebEngine.")
            return
        self.append_report("\n[rechazo] Intentando pulsar botones de rechazo y verificar estado de cookies...")
        script = (
            "(function(){var buttons=document.querySelectorAll('button,input[type=button],input[type=submit],a');"
            "var patterns=['reject','decline','deny','no thanks','no, thanks','opt-out','cookie settings','cookie policy'];"
            "var clicked=0; for(var i=0;i<buttons.length;i++){var b=buttons[i]; var text=(b.innerText||b.value||'').trim().toLowerCase();"
            "if(patterns.some(function(p){return text.indexOf(p)!==-1;})){b.click(); clicked++;}} return clicked;})();"
        )
        self.webview.page().runJavaScript(script, self.on_reject_clicked)

    def on_reject_clicked(self, count):
        if count is None:
            self.append_report("[error] No se pudo ejecutar el script de rechazo.")
            return
        self.append_report(f"Botones de rechazo pulsados: {count}")

        def check():
            js = (
                "(function(){return {cookies:document.cookie, localStorage:Array.from({length:localStorage.length},function(_,i){return localStorage.key(i);}), sessionStorage:Array.from({length:sessionStorage.length},function(_,i){return sessionStorage.key(i);})};})();"
            )
            self.webview.page().runJavaScript(js, self.on_reject_check)

        QTimer.singleShot(2400, check)

    def on_reject_check(self, info):
        if not isinstance(info, dict):
            self.append_report("[error] No se pudo verificar el rechazo de cookies.")
            return
        new_cookies = info.get("cookies", "")
        self.append_report(f"\nEstado de cookies tras rechazo: {new_cookies if new_cookies else '[ninguna]'}")
        if self.last_cookies and not new_cookies:
            self.append_report("El rechazo eliminó las cookies runtime. Puede haber funcionado.")
        elif new_cookies == self.last_cookies:
            self.append_report("El rechazo no cambió las cookies. Es posible que el botón no sea efectivo.")
        else:
            self.append_report("El rechazo cambió el estado de cookies. Comprueba posibles rastreadores persistentes.")
        if info.get("localStorage"):
            self.append_report("LocalStorage tras rechazo:")
            for key in info["localStorage"][:20]:
                self.append_report(f"  {key}")
        if info.get("sessionStorage"):
            self.append_report("SessionStorage tras rechazo:")
            for key in info["sessionStorage"][:20]:
                self.append_report(f"  {key}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    window = VirusTotalWeb()
    sys.exit(app.exec_())
