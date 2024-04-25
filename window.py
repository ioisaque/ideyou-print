import os
import re
import sys
import urllib
import winreg as reg
from datetime import datetime
from time import sleep

from PyQt6 import uic, QtGui, QtCore
from PyQt6.QtCore import QEvent, Qt, QTimer, QUrl, QRectF
from PyQt6.QtGui import QDesktopServices, QMovie, QIcon
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QPushButton, QHBoxLayout, QWidget, \
    QTableWidget, QHeaderView

from api import IdeYouApi
from init import CONFIG, load, reverse_template_mapping, save, template_mapping

if hasattr(sys, '_MEIPASS'):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    assets_path = sys._MEIPASS + '/assets/'
else:
    assets_path = 'assets/'


def toggle_logon_behavior(value):
    exe_name = "IdeYouPrint"
    exe_path = os.path.join(os.getcwd(), f'{exe_name}.exe')
    key = r"Software\Microsoft\Windows\CurrentVersion\Run"

    if value:
        try:
            reg_key = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE)
            reg.SetValueEx(reg_key, exe_name, 0, reg.REG_SZ, exe_path)
            reg.CloseKey(reg_key)
        except Exception as e:
            print(f"Error setting auto-run on startup: {e}")
    else:
        try:
            reg_key = reg.OpenKey(reg.HKEY_CURRENT_USER, key, 0, reg.KEY_SET_VALUE)
            reg.DeleteValue(reg_key, exe_name)
            reg.CloseKey(reg_key)
        except Exception as e:
            print(f"Error removing auto-run on startup: {e}")


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.check_interval = 60000

        self.api = IdeYouApi(self)

        if CONFIG["gsVersion"]:
            MainViewUi, QtBaseClass = uic.loadUiType(assets_path + 'main.ui')

            self.ui = MainViewUi()
            self.ui.setupUi(self)

            # Create a QMovie instance and set the animated GIF
            movie = QMovie(assets_path + "load-bars.gif")
            self.ui.loading.setMovie(movie)

            movie.start()
            self.show()
            self.setWindowTitle(f"IdeYouPrint | Versão {CONFIG['version']}")

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
                self.ui.loading.show()
                QApplication.processEvents()

                load()
                CONFIG['lojas'] = self.api.get_stores()
                save()

                self.ui.select_loja.clear()
                self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

                self.preview(f'{self.api.base_url}/profile.php')

                self.ui.loading.hide()
            else:
                self.ui.select_loja.clear()

                # Add items to ComboBox
                for loja in CONFIG['lojas']:
                    nome = loja.get('nome')
                    id = loja.get('id')
                    self.ui.select_loja.addItem(nome, id)

                # Try to find the printer on the list
                index = self.ui.select_loja.findData(CONFIG['dStore'])

                if index != -1:
                    self.ui.select_loja.setCurrentIndex(index)
                else:
                    self.ui.select_loja.setCurrentIndex(0)

            self.ui.cb_print_balcao.setChecked(0 in CONFIG['printTypes'])
            self.ui.cb_print_delivery.setChecked(1 in CONFIG['printTypes'])
            self.ui.cb_open_on_logon.setChecked(CONFIG['openOnLogon'])

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
            self.ui.btn_reload.clicked.connect(self.load_settings)
            self.ui.btn_recheck.clicked.connect(lambda: self.check(True))

            self.ui.btn_print.clicked.connect(self.print_order)
            self.ui.btn_cleanup.clicked.connect(self.api.clean_up_files)

            self.ui.input_url_sistema.textChanged.connect(self.save_settings)
            self.ui.input_id_pedido.textChanged.connect(self.limit_orderid_length)

            self.ui.select_loja.currentIndexChanged.connect(self.save_settings)
            self.ui.select_printer.currentIndexChanged.connect(self.save_settings)
            self.ui.select_printqtd.currentIndexChanged.connect(self.save_settings)
            self.ui.select_modelo_balcao.currentIndexChanged.connect(self.save_settings)
            self.ui.select_modelo_delivery.currentIndexChanged.connect(self.save_settings)

            self.ui.cb_print_balcao.stateChanged.connect(self.save_settings)
            self.ui.cb_print_delivery.stateChanged.connect(self.save_settings)
            self.ui.cb_open_on_logon.stateChanged.connect(self.save_settings)

            self.ui.log_box.setOpenExternalLinks(True)  # Enable clickable links
            self.ui.input_id_pedido.installEventFilter(self)

            self.preview(f'{self.api.base_url}/profile.php')

            # Create a QTimer to periodically trigger the check function
            self.timer = QTimer(self)
            self.timer.timeout.connect(self.check)
            self.timer.start(self.check_interval)  # Trigger every 60,000 milliseconds (1 minute)
        else:
            MainViewUi, QtBaseClass = uic.loadUiType(assets_path + 'gs_not_found.ui')

            self.ui = MainViewUi()
            self.ui.setupUi(self)
            self.show()

            self.ui.btn_get_gs.clicked.connect(self.downloadGS)

        # Set the notification sound
        self.sound_effect = QSoundEffect()
        self.sound_effect.setLoopCount(0)
        self.sound_effect.setSource(QUrl.fromLocalFile(assets_path + "slotmachine.wav"))

        scrollbar_stylesheet = """
        QScrollBar:vertical {
            width: 15px;
            border: none;
            background: transparent;
        }
        QScrollBar::handle:vertical {
            cursor: grab;
            background: #000000;
        }
        """
        # Apply the styles to the scrollbar
        self.set_open_hand_cursor()
        self.ui.tableWidget.setStyleSheet(scrollbar_stylesheet)
        self.ui.tableWidget.verticalScrollBar().sliderPressed.connect(self.set_closed_hand_cursor)
        self.ui.tableWidget.verticalScrollBar().sliderReleased.connect(self.set_open_hand_cursor)

        CONFIG["queue"] = []
        save()

        if not self.api.check_app_version() == 200:
            self.alert("Nova versão disponível!", "Para atualizar este aplicativo, siga os passos:<br><br>1. Apague esta versão do seu computador.<br>2. Faça login no seu sistema.<br>3. No menu, clique em configurações -> pedidos.<br>4. Depois, clique no botão verde no topo IdeYou Print.<br>5. Pronto, terminando de baixar é só abrir e usar!<br><br> Qualquer dúvidas, procure seu gerente! :)")
            QTimer.singleShot(0, QApplication.quit)

    def check(self, reset: bool = False):
        self.ui.loading.show()
        QApplication.processEvents()

        if reset:
            self.timer.stop()

        queue = self.api.get_wating_orders()

        if len(queue):
            CONFIG["queue"] = queue
            save()
            self.list_queue(queue)

        self.last_checked = str(len(queue))

        for pedido in queue:
            if int(pedido.get("delivery")) in CONFIG['printTypes']:
                if not int(pedido.get("printed")) == 1:
                    self.print_order(pedido)
                else:
                    self.log = f'<span style="color: #FF0000;">#=> ATENÇÃO AO PEDIDO #{pedido.get("id")}!</span> <a href="{self.api.base_url}/?do=pedidos&action=view&id={pedido.get("id")}" style="color: #1976d2; cursor: pointer;">Visualizar</a>'

        if len(queue):
            # Play the sound effect
            self.sound_effect.play()

            # Wait for the sound effect to finish playing
            while self.sound_effect.isPlaying():
                QApplication.processEvents()

        if reset:
            self.timer.start(self.check_interval)

        self.ui.loading.hide()

    def list_queue(self, orders):
        self.ui.tableWidget.clearContents()
        self.ui.tableWidget.setRowCount(0)

        headers = ["", "Identificação", "Ações"]
        self.ui.tableWidget.setColumnCount(len(headers))
        self.ui.tableWidget.setHorizontalHeaderLabels(headers)
        self.ui.tableWidget.cellClicked.connect(self.on_cell_clicked)
        self.ui.tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for order in orders:
            self.api.download_order(order.get("id"),
                                    CONFIG["deliveryTemplate" if int(order.get("delivery")) else "balcaoTemplate"])
            rowPosition = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(rowPosition)

            type_item = QTableWidgetItem(order["id"])
            type_item.setForeground(QtGui.QColor(str(order["color"])))
            type_item.setBackground(QtGui.QColor(str(order["color"])))
            self.ui.tableWidget.setItem(rowPosition, 0, type_item)

            # Set the text for the first column as "Pedido ID do dia data_hora"
            pedido_text = f'Pedido {order["id"]} para {order["data_hora"]}'
            pedido_item = QTableWidgetItem(pedido_text)
            self.ui.tableWidget.setItem(rowPosition, 1, pedido_item)

            # Set the tooltip for the first column item
            criado_tooltip = f'Criado em: {order["criado_em"]}'
            pedido_item.setToolTip(criado_tooltip)

            # Botões na coluna ações
            btn_layout = QHBoxLayout()
            btn_layout.setContentsMargins(5, 0, 5, 0)

            # Botão de imprimir
            btn_print = QPushButton()
            btn_print.setIcon(QIcon(os.path.join(assets_path, "printer.png")))
            btn_print.setIconSize(QtCore.QSize(15, 15))
            btn_print.setCursor(Qt.CursorShape.PointingHandCursor)
            btn_print.clicked.connect(lambda _, pedido=order: self.print_order(pedido))
            btn_layout.addWidget(btn_print)

            if order.get("status") == 402:
            # Botão de dispensar
                btn_cancel = QPushButton()
                btn_cancel.setIcon(QIcon(os.path.join(assets_path, "thumbs_up.png")))
                btn_cancel.setIconSize(QtCore.QSize(15, 15))
                btn_cancel.setStyleSheet("background-color: #0076F3;")
                btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_cancel.clicked.connect(lambda _, row=rowPosition, id=order["id"]: self.set_order_status(row, id, 0))
                btn_layout.addWidget(btn_cancel)
            elif order.get("status") == 404:
                # Botão de aprovar
                btn_approve = QPushButton()
                btn_approve.setIcon(QIcon(os.path.join(assets_path, "thumbs_up.png")))
                btn_approve.setIconSize(QtCore.QSize(15, 15))
                btn_approve.setStyleSheet("background-color: green;")
                btn_approve.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_approve.clicked.connect(
                    lambda _, row=rowPosition, id=order["id"]: self.set_order_status(row, id, 1))
                btn_layout.addWidget(btn_approve)

                # Botão de cancelar
                btn_cancel = QPushButton()
                btn_cancel.setIcon(QIcon(os.path.join(assets_path, "thumbs_down.png")))
                btn_cancel.setIconSize(QtCore.QSize(15, 15))
                btn_cancel.setStyleSheet("background-color: red;")
                btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_cancel.clicked.connect(
                    lambda _, row=rowPosition, id=order["id"]: self.set_order_status(row, id, 0))
                btn_layout.addWidget(btn_cancel)
            else:
                # Botão de dispensar
                btn_cancel = QPushButton()
                btn_cancel.setIcon(QIcon(os.path.join(assets_path, "thumbs_up.png")))
                btn_cancel.setIconSize(QtCore.QSize(15, 15))
                btn_cancel.setStyleSheet("background-color: #0076F3;")
                btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
                btn_cancel.clicked.connect(
                    lambda _, id=order["id"]: [
                        self.ui.tableWidget.removeRow(i)
                        for i in range(self.ui.tableWidget.rowCount())
                        if self.ui.tableWidget.item(i, 0).text() == str(id)
                    ])
                btn_layout.addWidget(btn_cancel)

            # Adicionando o layout de botões à célula
            btn_container = QWidget()
            btn_container.setLayout(btn_layout)
            self.ui.tableWidget.setCellWidget(rowPosition, 2, btn_container)

            # After populating the table, resize the columns to fit their contents
            self.ui.tableWidget.resizeColumnsToContents()

            # Setting the width of the last column to fill the remaining space
            header = self.ui.tableWidget.horizontalHeader()
            remaining_space = self.ui.tableWidget.viewport().width() - header.length()
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.resizeSection(2, remaining_space)

    def on_cell_clicked(self, row, column):
        id_pedido = int(self.ui.tableWidget.item(row, 0).text())

        try:
            self.preview(id_pedido)
        except Exception as e:
            self.log = f'<span style="color: #f77b36;">Erro ao visualizar pedido #{id_pedido}. % {str(e)} %</span>'

    def preview(self, thing: str | int):
        self.ui.loading.show()
        QApplication.processEvents()

        if isinstance(thing, str) and 'http' in thing:
            # Create a QWebEngineView widget to display web content
            webview = QWebEngineView()
            self.ui.preview_area.setWidget(webview)

            # Load a URL into the QWebEngineView
            url = urllib.parse.quote(thing, safe=':/?&=')
            webview.setUrl(QUrl.fromLocalFile(url) if 'file://' in url else QUrl(url))
        else:
            pedido = self.api.get_order_by_id(int(thing))
            template = CONFIG["deliveryTemplate" if int(pedido.get("delivery")) else "balcaoTemplate"]

            file_name = self.api.download_order(int(thing), template)

            self.log = f'Pré-visualizando - {file_name}'

            # Create a QPdfView widget
            pdf_view = QPdfView(self)
            self.ui.preview_area.setWidget(pdf_view)

            # Create a QPdfDocument instance with a parent
            pdf_document = QPdfDocument(pdf_view)

            # Load the PDF from a file
            pdf_document.load(os.path.join(CONFIG["rootPTH"], file_name))

            # Set the PDF document for the QPdfView
            pdf_view.setDocument(pdf_document)
            pdf_view.setZoomMode(QPdfView.ZoomMode.FitToWidth)

            scrollbar_stylesheet = """
            QScrollBar:vertical {
                width: 0px;
                border: none;
                background: transparent;
            }
            """
            pdf_view.setStyleSheet(scrollbar_stylesheet)

            # pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

        self.ui.loading.hide()

        if isinstance(thing, int):
            QTimer.singleShot(500, lambda: self.get_screenshot(pdf_view, int(thing)))

    def get_screenshot(self, widget, thing):
        self.log = f'tirando print do pedido #{thing}.'

        screenshot = widget.grab()

        temp_file = os.path.join(CONFIG['rootPTH'], f'pedido#{thing}.jpg')
        screenshot.save(temp_file, 'jpg')

        clipboard = QApplication.clipboard()
        clipboard.setImage(screenshot.toImage())

        if isinstance(widget, QPdfView):
            widget.setZoomMode(QPdfView.ZoomMode.FitToWidth)

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

    def print_order(self, pedido: dict | bool = False):
        self.ui.loading.show()
        QApplication.processEvents()

        if pedido is False:
            id_pedido = int(self.ui.input_id_pedido.toPlainText())
            pedido = self.api.get_order_by_id(id_pedido)

        if pedido:
            self.api.print_order(pedido)
        else:
            self.log = f'<span style="color: #f77b36;">Erro ao imprimir [{id_pedido}], pedido não encontrado.</span>'

    def set_order_status(self, row: int, id_pedido: int, id_status: int):
        try:
            response = self.api.set_order_status(id_pedido, id_status)

            for element in response.get('messages'):
                if element['type'] not in ['success', 'debug', 'data']:
                    self.alert(element['type'], element['message'])

            if response.get('code') == 200:
                # self.ui.tableWidget.removeRow(row)
                for i in range(self.ui.tableWidget.rowCount()):
                    if self.ui.tableWidget.item(i, 0).text() == str(id_pedido):
                        self.ui.tableWidget.removeRow(i)
                        break
        except Exception as e:
            self.alert("Falha na operação!",
                       f'<span style="color: #FF0000;">Erro ao atualizar pedido #{id_pedido}, realize essa operação no sistema e informe o administrador o erro abaixo: <br><br>% {str(e)} %</span>')

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
                    self.preview(id_pedido)
                except Exception as e:
                    self.log = f'<span style="color: #f77b36;">Erro ao visualizar pedido #{id_pedido}: {str(e)}.</span>'
                return True  # Event handled
        return super().eventFilter(obj, event)

    def set_closed_hand_cursor(self):
        self.ui.tableWidget.verticalScrollBar().setCursor(QtCore.Qt.CursorShape.ClosedHandCursor)

    def set_open_hand_cursor(self):
        self.ui.tableWidget.verticalScrollBar().setCursor(QtCore.Qt.CursorShape.OpenHandCursor)

    def load_settings(self):
        self.ui.loading.show()
        QApplication.processEvents()

        load()
        CONFIG['lojas'] = self.api.get_stores()
        save()

        self.ui.select_loja.clear()
        self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

        self.preview(f'{self.api.base_url}/profile.php')

        self.ui.loading.hide()

    def save_settings(self):
        CONFIG["sistema"] = self.ui.input_url_sistema.toPlainText()
        CONFIG["dStore"] = self.dStore

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

        CONFIG['openOnLogon'] = self.ui.cb_open_on_logon.isChecked()

        save()

        toggle_logon_behavior(CONFIG['openOnLogon'])

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
        id_loja = 0
        dLoja = self.ui.select_loja.currentText()

        for loja in CONFIG["lojas"]:
            if dLoja == loja["nome"]:
                id_loja = int(loja["id"])

        return str(id_loja)

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
    def openOnLogon(self):
        return self.ui.cb_open_on_logon.isChecked()

    @openOnLogon.setter
    def openOnLogon(self, value):
        CONFIG["openOnLogon"] = value

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
