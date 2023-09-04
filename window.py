import re
import sys
import urllib
from datetime import datetime

from PyQt6 import uic
from PyQt6.QtCore import QUrl, Qt, QEvent, QTimer
from PyQt6.QtGui import QDesktopServices, QMovie
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication

from init import CONFIG, load, save, reverse_template_mapping, template_mapping
from server import PrintServer

if hasattr(sys, '_MEIPASS'):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    assets_path = sys._MEIPASS + '/assets/'
else:
    assets_path = 'assets/'


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.check_interval = 60000

        self.srv = PrintServer(self)
        self.api = self.srv.api

        if CONFIG["gsVersion"]:
            MainViewUi, QtBaseClass = uic.loadUiType(assets_path + 'main.ui')

            self.ui = MainViewUi()
            self.ui.setupUi(self)

            # Create a QMovie instance and set the animated GIF
            movie = QMovie(assets_path + "load-bars.gif")
            self.ui.loading.setMovie(movie)

            # Start playing the animated GIF
            movie.start()

            self.ui.gsv_label.setText(CONFIG["gsVersion"])
            self.ui.gsv_label.setStyleSheet('color: #000;')

            self.ui.input_url_sistema.setText(CONFIG['sistema'])

            self.ui.select_printer.addItems(CONFIG['printers'])
            self.ui.select_printqtd.setCurrentIndex(int(CONFIG['nCopies']) - 1)

            # Try to find the printer on the list
            index = self.ui.select_printer.findText(CONFIG['dPrinter'])

            if index != -1:
                self.ui.select_printer.setCurrentIndex(index)
            else:
                self.ui.select_printer.setCurrentIndex(0)

            if not CONFIG['lojas'] and CONFIG['sistema']:
                self.load()
            else:
                self.ui.select_loja.clear()
                self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

                # Try to find the printer on the list
                index = self.ui.select_loja.findText(CONFIG['dStore'])

                if index != -1:
                    self.ui.select_loja.setCurrentIndex(index)
                else:
                    self.ui.select_loja.setCurrentIndex(0)

            self.ui.cb_print_balcao.setChecked(0 in CONFIG['printTypes'])
            self.ui.cb_print_delivery.setChecked(1 in CONFIG['printTypes'])

            # Try to find the template on the list
            template = reverse_template_mapping.get(CONFIG['balcaoTemplate'], "bundle")
            index = self.ui.select_modelo_balcao.findText(template)

            if index != -1:
                self.ui.select_modelo_balcao.setCurrentIndex(index)
            else:
                self.ui.select_modelo_balcao.setCurrentIndex(0)

            # Try to find the template on the list
            template = reverse_template_mapping.get(CONFIG['deliveryTemplate'], "bundle")
            index = self.ui.select_modelo_delivery.findText(template)

            if index != -1:
                self.ui.select_modelo_delivery.setCurrentIndex(index)
            else:
                self.ui.select_modelo_delivery.setCurrentIndex(0)

            # CONNECT ALL THE BEHAVIOR TO ITS DESIGNATED FUNCTION
            self.ui.btn_reload.clicked.connect(self.load)
            self.ui.btn_recheck.clicked.connect(lambda: self.check(True))

            self.ui.btn_print.clicked.connect(self.__print)
            self.ui.btn_cleanup.clicked.connect(self.api.clean_up_files)

            self.ui.input_url_sistema.textChanged.connect(self.save)
            self.ui.input_id_pedido.textChanged.connect(self.limit_orderid_length)

            self.ui.select_loja.currentIndexChanged.connect(self.save)
            self.ui.select_printer.currentIndexChanged.connect(self.save)
            self.ui.select_printqtd.currentIndexChanged.connect(self.save)
            self.ui.select_modelo_balcao.currentIndexChanged.connect(self.save)
            self.ui.select_modelo_delivery.currentIndexChanged.connect(self.save)

            self.ui.cb_print_balcao.stateChanged.connect(self.save)
            self.ui.cb_print_delivery.stateChanged.connect(self.save)

            self.ui.log_box.setOpenExternalLinks(True)  # Enable clickable links
            self.ui.input_id_pedido.installEventFilter(self)

            self.srv.start()
            self.preview(f'{self.api.base_url}/profile.php')

            self.ui.loading.hide()

            # Create a QTimer to periodically trigger the check function
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.check)
            self.timer.start(self.check_interval)  # Trigger every 60,000 milliseconds (1 minute)
        else:
            MainViewUi, QtBaseClass = uic.loadUiType(assets_path + 'gs_not_found.ui')

            self.ui = MainViewUi()
            self.ui.setupUi(self)
            self.ui.btn_get_gs.clicked.connect(self.downloadGS)

        self.show()

        # Set the notification sound
        self.sound_effect = QSoundEffect()
        self.sound_effect.setLoopCount(0)
        self.sound_effect.setSource(QUrl.fromLocalFile(assets_path + "slotmachine.wav"))

    def check(self, reset: bool = False):
        self.ui.loading.show()
        if reset:
            self.timer.stop()

        queue = self.api.get_wating_orders()

        self.last_checked = str(queue.get("waiting"))

        for pedido in queue.get('lista'):
            if int(pedido.get("delivery")) in CONFIG['printTypes']:
                if int(pedido.get("printed")) == 0:
                    self.__print(pedido)
                else:
                    self.log = f'<span style="color: #FF0000;">#=> PEDIDO #{pedido.get("id")} AGUARDANDO APROVAÇÃO!</span> <a href="{self.api.base_url}/?do=pedidos&action=view&id={pedido.get("id")}" style="color: #1976d2; cursor: pointer;">Visualizar</a>'

        if queue.get("waiting"):
            # Play the sound effect
            self.sound_effect.play()

            # Wait for the sound effect to finish playing
            while self.sound_effect.isPlaying():
                QApplication.processEvents()

        if reset:
            self.timer.start(self.check_interval)

    def __print(self, pedido: dict | bool = False):
        self.ui.loading.show()

        if pedido is False:
            id_pedido = int(self.ui.input_id_pedido.toPlainText())
            pedido = self.api.get_order_by_id(id_pedido)

        if pedido:
            self.api.print_order(pedido)
        else:
            self.log = f'<span style="color: #f77b36;">Erro ao imprimir [{id_pedido}], pedido não encontrado.</span>'

    def save(self):
        CONFIG["sistema"] = self.ui.input_url_sistema.toPlainText()
        CONFIG["dStore"] = self.ui.select_loja.currentText()

        CONFIG["dPrinter"] = self.ui.select_printer.currentText()
        CONFIG["nCopies"] = re.sub(r'[^0-9]', '', self.ui.select_printqtd.currentText()).lstrip('0')

        CONFIG['balcaoTemplate'] = template_mapping.get(self.ui.select_modelo_balcao.currentText(), "")
        CONFIG['deliveryTemplate'] = template_mapping.get(self.ui.select_modelo_delivery.currentText(), "")

        CONFIG['printTypes'] = []

        if self.ui.cb_print_balcao.isChecked():
            CONFIG['printTypes'].append(0)

        if self.ui.cb_print_delivery.isChecked():
            CONFIG['printTypes'].append(1)

        CONFIG['balcaoTemplate'] = template_mapping.get(self.ui.select_modelo_balcao.currentText(), "")
        CONFIG['deliveryTemplate'] = template_mapping.get(self.ui.select_modelo_delivery.currentText(), "")

        save()

    def load(self):
        self.ui.loading.show()

        if self.srv.running:
            self.srv.stop()

        load()
        CONFIG['lojas'] = self.api.get_stores()
        save()

        self.ui.select_loja.clear()
        self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

        self.preview(f'{self.api.base_url}/profile.php')

        if not self.srv.running:
            self.srv.start()

        self.ui.loading.hide()

    def preview(self, path_or_addr):
        if 'http' in path_or_addr:
            # Create a QWebEngineView widget to display web content
            webview = QWebEngineView()
            self.ui.preview_area.setWidget(webview)

            # Load a URL into the QWebEngineView
            url = urllib.parse.quote(path_or_addr, safe=':/?&=')
            webview.setUrl(QUrl.fromLocalFile(url) if 'file://' in url else QUrl(url))
        else:
            self.log = f'Pré-visualizando - {path_or_addr}'

            # Create a QPdfView widget
            pdf_view = QPdfView(self)

            # Create a QPdfDocument instance with a parent
            pdf_document = QPdfDocument(pdf_view)

            # Load the PDF from a file
            pdf_document.load(path_or_addr)

            # Set the PDF document for the QPdfView
            pdf_view.setDocument(pdf_document)

            # Create a scroll area widget
            self.ui.preview_area.setWidget(pdf_view)

    @property
    def log(self):
        return self.ui.log_box.toHtml()

    @log.setter
    def log(self, l: str):
        print(re.sub('<[^<]+?>', '', l))

        old = self.log
        self.ui.log_box.setText(f'<p style="margin: 0 !important;">{l}</p>{old}')

    @property
    def last_checked(self):
        return self.ui.last_checked.currentText()

    @last_checked.setter
    def last_checked(self, count):
        current_time = datetime.now()
        self.ui.last_checked.setText(current_time.strftime(f'Última checagem ás %H:%M:%S [{count} na fila]'))

    @property
    def nCopies(self):
        return re.sub(r'[^0-9]', '', self.ui.select_printqtd.currentText())

    @nCopies.setter
    def nCopies(self, value):
        CONFIG["nCopies"] = re.sub(r'[^0-9]', '', value)

        save()

    @property
    def dPrinter(self):
        return self.ui.select_printer.currentText()

    @dPrinter.setter
    def dPrinter(self, value):
        CONFIG["dPrinter"] = value

        save()

    @property
    def dStore(self):
        nome_loja = self.ui.select_loja.currentText()

        for loja in CONFIG["lojas"]:
            if loja["nome"] == nome_loja:
                return int(loja["id"])

        return 0

    @dStore.setter
    def dStore(self, value):
        CONFIG["dStore"] = value

        save()

    @property
    def sistema(self):
        return self.ui.input_url_sistema.toPlainText()

    @sistema.setter
    def sistema(self, value):
        CONFIG["sistema"] = value

        save()

    @property
    def lojas(self):
        return CONFIG['lojas']

    @lojas.setter
    def lojas(self, value):
        CONFIG["lojas"] = value

        save()

    @property
    def printBalcao(self):
        return '0' in CONFIG['printTypes']

    @printBalcao.setter
    def printBalcao(self, value):
        if value:
            CONFIG['printTypes'].append('0')
        else:
            CONFIG['printTypes'].remove('0')

        save()

    @property
    def printDelivery(self):
        return '1' in CONFIG['printTypes']

    @printDelivery.setter
    def printDelivery(self, value):
        if value:
            CONFIG['printTypes'].append('1')
        else:
            CONFIG['printTypes'].remove('1')

        save()

    @property
    def balcaoTemplate(self):
        return template_mapping.get(self.ui.select_modelo_balcao.currentText(), "")

    @balcaoTemplate.setter
    def balcaoTemplate(self, value):
        CONFIG["balcaoTemplate"] = template_mapping.get(value, "")

        save()

    @property
    def deliveryTemplate(self):
        return template_mapping.get(self.ui.select_modelo_delivery.currentText(), "")

    @deliveryTemplate.setter
    def deliveryTemplate(self, value):
        CONFIG["deliveryTemplate"] = template_mapping.get(value, "")

        save()

    def alert(self, title: str, message: str):
        self.ui.loading.show()
        QMessageBox.information(self, title, message)
        self.ui.loading.hide()


    def downloadGS(self):
        file_url = QUrl(CONFIG['gslink'])

        QDesktopServices.openUrl(file_url)

        self.close()

        # # Prompt the user to choose a location to save the file
        # file_path, _ = QFileDialog.getSaveFileName(self, "Save File", "ghostscript.exe", "All Files (*)")
        #
        # if file_path:
        #     # Create a QNetworkRequest to request the file
        #     request = QNetworkRequest(file_url)
        #
        #     # Create a QNetworkAccessManager to handle the download
        #     manager = QNetworkAccessManager(self)
        #
        #     # Handle the download progress and save the file
        #     reply = manager.get(request)
        #
        #     def onReadyRead():
        #         data = reply.readAll()
        #         with open(file_path, "wb") as file:
        #             file.write(data)
        #         reply.deleteLater()
        #         self.alert("Download Realizado", "O arquivo foi salvo no caminho informado!")
        #
        #     reply.finished.connect(onReadyRead)

    def limit_orderid_length(self):
        max_length = 8
        current_text = self.ui.input_id_pedido.toPlainText()

        if len(current_text) > max_length:
            self.ui.input_id_pedido.setPlainText(current_text[:max_length])

    def eventFilter(self, obj, event):
        if obj == self.ui.input_id_pedido and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
                id_pedido = int(self.ui.input_id_pedido.toPlainText())
                try:
                    pedido = self.api.get_order_by_id(id_pedido)
                    self.api.download_order(pedido)
                except Exception as e:
                    # self.log = f'<span style="color: #f77b36;">Erro ao visualizar pedido [{id_pedido}]: {str(e)}.</span>'
                    self.log = f'<span style="color: #f77b36;">Erro ao visualizar [{id_pedido}], pedido não encontrado.</span>'
                return True  # Event handled
        return super().eventFilter(obj, event)
