import os
import re
import sys
import winreg as reg
from datetime import datetime
from time import sleep

from PyQt6 import uic, QtGui, QtCore
from PyQt6.QtCore import QEvent, Qt, QTimer, QUrl
from PyQt6.QtGui import QDesktopServices, QMovie, QIcon, QPixmap
from PyQt6.QtMultimedia import QSoundEffect
from PyQt6.QtPdf import QPdfDocument
from PyQt6.QtPdfWidgets import QPdfView
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWidgets import QApplication, QMainWindow, QMessageBox, QTableWidgetItem, QPushButton, QHBoxLayout, QWidget, \
    QTableWidget, QHeaderView, QLabel, QSizePolicy, QScrollArea, QVBoxLayout

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

                self.preview(assets_path + "/waitingurl.png")

                self.ui.loading.hide()
            else:
                self.ui.select_loja.clear()

                # Add items to ComboBox
                for loja in CONFIG['lojas']:
                    id = loja.get('id')
                    nome = loja.get('nome')
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
            self.ui.cb_auto_screenshot.setChecked(CONFIG['takeScreenShot'])

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
            self.ui.btn_lock.clicked.connect(self.toggleUI)
            self.ui.btn_reload.clicked.connect(self.load_settings)
            self.ui.btn_recheck.clicked.connect(lambda: self.check(True))

            self.ui.btn_print.clicked.connect(self.print_order)

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
            self.ui.cb_auto_screenshot.stateChanged.connect(self.save_settings)

            self.ui.log_box.setOpenExternalLinks(True)  # Enable clickable links
            self.ui.input_id_pedido.installEventFilter(self)

            self.preview(assets_path + "/connected.png")

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
        else:
            self.ui.tableWidget.cellClicked.connect(
                lambda row, col: self.preview(int(self.ui.tableWidget.item(row, 0).text())))
            self.toggleUI()

    def check(self, reset: bool = False):
        self.preview(assets_path + "/connected.png")
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
                    self.log = f'<span style="color: #FF0000;">ATENÇÃO AO PEDIDO {pedido.get("id")}!</span> <a href="{self.api.base_url}/?do=pedidos&action=view&id={pedido.get("id")}" style="color: #1976d2; cursor: pointer;">Visualizar</a>'

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
        self.ui.tableWidget.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        for order in orders:
            rowPosition = self.ui.tableWidget.rowCount()
            self.ui.tableWidget.insertRow(rowPosition)

            type_item = QTableWidgetItem(order["id"])
            type_item.setForeground(QtGui.QColor(str(order["color"])))
            type_item.setBackground(QtGui.QColor(str(order["color"])))
            self.ui.tableWidget.setItem(rowPosition, 0, type_item)

            # Set the text for the first column as "Pedido ID do dia data_hora"
            pedido_text = f'Pedido {order["id"]} para {order["data_hora"]}'
            pedido_item = QTableWidgetItem(pedido_text)

            if int(order.get("status")) == 0:
                pedido_item.setForeground(QtGui.QColor("#FFF"))
                pedido_item.setBackground(QtGui.QColor("#F00"))
            elif int(order.get("status")) == -1:
                pedido_item.setForeground(QtGui.QColor("#FFF"))
                pedido_item.setBackground(QtGui.QColor("#33CC66"))
            elif order.get("alterado_em"):
                pedido_item.setForeground(QtGui.QColor("#000"))
                pedido_item.setBackground(QtGui.QColor("#FFD22B"))
            else:
                pedido_item.setForeground(QtGui.QColor("#000"))
                pedido_item.setBackground(QtGui.QColor("#FFF"))

            self.ui.tableWidget.setItem(rowPosition, 1, pedido_item)

            # Set the tooltip for the first column item
            tooltip_txt = f'Alterado em: {order["alterado_em"]}' if order["alterado_em"] else f'Criado em: {order["criado_em"]}'
            pedido_item.setToolTip(tooltip_txt)

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

            if int(order.get("status")) == -1:
                # Botão de aprovar
                btn_approve = QPushButton()
                btn_approve.setIcon(QIcon(os.path.join(assets_path, "thumbs_up.png")))
                btn_approve.setIconSize(QtCore.QSize(15, 15))
                btn_approve.setStyleSheet("background-color: #33CC66;")
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

    def preview(self, thing: str | int):
        self.ui.loading.show()
        QApplication.processEvents()

        try:
            # Remove the existing widget from the preview area
            if self.ui.preview_area.widget() is not None:
                self.ui.preview_area.widget().deleteLater()

            if isinstance(thing, str) and 'http' in thing:
                # Create a QWebEngineView widget to display web content
                webview = QWebEngineView()
                self.ui.preview_area.setWidget(webview)

                def handle_load_finished(success: bool):
                    if not success:
                        self.preview(assets_path + "/desconnected.png")

                # Connect the loadFinished signal to the custom slot
                webview.loadFinished.connect(handle_load_finished)

                # Load a URL into the QWebEngineView
                webview.setUrl(QUrl(thing))
            elif isinstance(thing, str) and (thing.endswith('.jpg') or thing.endswith('.png') or thing.endswith('.gif')):
                label = QLabel()
                pixmap = QPixmap(thing)

                container_width = self.ui.preview_area.width() - 30
                container_height = self.ui.preview_area.height()

                scaled_pixmap = pixmap.scaled(container_width, container_height, Qt.AspectRatioMode.KeepAspectRatio,
                                              Qt.TransformationMode.SmoothTransformation)

                label.setPixmap(scaled_pixmap)
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                label.setFixedSize(scaled_pixmap.size())
                layout = QVBoxLayout()
                layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter)

                container_widget = QWidget()
                container_widget.setLayout(layout)
                container_widget.setStyleSheet("background-color: #FF5356;")

                self.ui.preview_area.setWidget(container_widget)
            else:
                file_path = self.api.download_order(int(thing), "preview")

                sleep(1)

                # Create a QPdfDocument instance with a parent
                pdf_document = QPdfDocument(self)

                # Load the PDF from a file
                pdf_document.load(file_path)

                # Create a QPdfView widget
                pdf_view = QPdfView(self)
                self.ui.preview_area.setWidget(pdf_view)

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

                pdf_view.setZoomMode(QPdfView.ZoomMode.FitInView)

            self.ui.loading.hide()

            if isinstance(thing, int):
                QTimer.singleShot(750, lambda: self.get_screenshot(pdf_view, int(thing)))
        except Exception as e:
            self.log = f'<span style="color: #f77b36;">Erro ao visualizar {thing}. % {str(e)} %</span>'

    def get_screenshot(self, widget, thing):
        if not CONFIG['takeScreenShot']:
            return

        screenshot = widget.grab()

        temp_file = os.path.join(CONFIG['rootPTH'], f'preview.jpg')
        screenshot.save(temp_file, 'jpg')

        clipboard = QApplication.clipboard()
        clipboard.setImage(screenshot.toImage())

        if isinstance(widget, QPdfView):
            widget.setZoomMode(QPdfView.ZoomMode.FitToWidth)

    def alert(self, title: str, message: str):
        self.ui.loading.show()
        QMessageBox.information(self, title, message)
        self.ui.loading.hide()

    def toggleUI(self):
        # Get the current enabled state of one of the widgets
        enabled_state = self.ui.input_url_sistema.isEnabled()

        # Toggle the state
        new_state = not enabled_state

        # Set the new state to all inputs, checkboxes, and selects
        self.ui.input_url_sistema.setEnabled(new_state)
        self.ui.select_loja.setEnabled(new_state)
        self.ui.select_printer.setEnabled(new_state)
        self.ui.select_printqtd.setEnabled(new_state)
        self.ui.select_modelo_balcao.setEnabled(new_state)
        self.ui.select_modelo_delivery.setEnabled(new_state)
        self.ui.cb_print_balcao.setEnabled(new_state)
        self.ui.cb_print_delivery.setEnabled(new_state)
        self.ui.cb_open_on_logon.setEnabled(new_state)
        self.ui.cb_auto_screenshot.setEnabled(new_state)

        if new_state:
            self.ui.btn_lock.setIcon(QIcon(os.path.join(assets_path, "unlocked.png")))  # Set the icon to an unlocked icon
        else:
            self.ui.btn_lock.setIcon(QIcon(os.path.join(assets_path, "locked.png")))  # Set the icon to a locked icon

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
            self.log = f'<span style="color: #f77b36;">Erro ao imprimir pedido {id_pedido}, não encontrado!</span>'

        self.ui.loading.hide()

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
                    self.log = f'<span style="color: #f77b36;">Erro ao visualizar pedido {id_pedido}: {str(e)}.</span>'
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

        self.preview(assets_path + "/waitingurl.png")

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
        CONFIG['takeScreenShot'] = self.ui.cb_auto_screenshot.isChecked()

        save()
        toggle_logon_behavior(CONFIG['openOnLogon'])

    def closeEvent(self, event):
        # Cria uma caixa de mensagem de confirmação
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle('Atenção!')
        msg_box.setText('Tem certeza de que deseja sair?\n\nOs pedidos não serão mais impressos automaticamente!')

        # Define o ícone
        msg_box.setIcon(QMessageBox.Icon.Question)

        # Cria botões personalizados
        yes_button = QPushButton('Sim, quero sair!')
        no_button = QPushButton('Não, vou ficar!')

        # Define as cores de fundo dos botões usando estilos
        yes_button.setStyleSheet("font-weight: bold; padding: 2px 5px; background-color: red; color: white;")
        no_button.setStyleSheet("font-weight: bold; padding: 2px 5px; background-color: green; color: white;")

        # Adiciona os botões à caixa de mensagem
        msg_box.addButton(yes_button, QMessageBox.ButtonRole.YesRole)
        msg_box.addButton(no_button, QMessageBox.ButtonRole.NoRole)

        # Define o botão padrão (focado)
        msg_box.setDefaultButton(no_button)

        # Exibe a caixa de mensagem e espera pela resposta
        msg_box.exec()

        # Verifica a resposta do usuário
        if msg_box.clickedButton() == yes_button:
            event.accept()  # Fecha a janela
        else:
            event.ignore()  # Cancela o fechamento

    @property
    def log(self):
        return self.ui.log_box.toHtml()

    @log.setter
    def log(self, l: str):
        print(re.sub('<[^<]+?>', '', l))

        old = self.log
        self.ui.log_box.setText(f'<p style="margin: 0 !important;">{datetime.now().strftime("%H:%M:%S")} - {l}</p>{old}')

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
    def takeScreenShot(self):
        return self.ui.cb_auto_screenshot.isChecked()

    @takeScreenShot.setter
    def takeScreenShot(self, value):
        CONFIG["takeScreenShot"] = value

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
