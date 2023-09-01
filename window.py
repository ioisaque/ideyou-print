import sys
from datetime import datetime

import requests

from api import Api
from init import CONFIG, load
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow
from server import PrintServer

if hasattr(sys, '_MEIPASS'):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    assets_path = sys._MEIPASS + '/assets/'
else:
    assets_path = 'assets/'

MainViewUi, QtBaseClass = uic.loadUiType(assets_path + 'main.ui')


class MainWindow(QMainWindow):

    def __init__(self):
        super().__init__()
        self.ui = MainViewUi()
        self.ui.setupUi(self)

        self.api = Api()
        self.srv = PrintServer(self)
        self.ui.btn_reload.clicked.connect(self.load)
        self.ui.input_id_pedido.textChanged.connect(self.limit_orderid_length)

        if CONFIG["gsVersion"]:
            self.load()

            # Log current time
            count = 0
            current_time = datetime.now()
            self.ui.last_checked.setText(current_time.strftime(f'Última checagem ás %H:%M:%S [{count} pedidos]'))

        self.show()

    def limit_orderid_length(self):
        max_length = 8
        current_text = self.ui.input_id_pedido.toPlainText()

        if len(current_text) > max_length:
            self.ui.input_id_pedido.setPlainText(current_text[:max_length])

    def get_sistema_url(self):
        return self.ui.input_url_sistema.toPlainText()

    def get_loja(self):
        return self.ui.select_loja.currentText()

    def get_printer(self):
        return self.ui.select_printer.currentText()

    def log(self, l: str):
        old = self.ui.log_box.toPlainText()
        self.ui.log_box.setText(old + ('\n' if len(old) else '') + l)

    def load(self):
        if self.srv.running:
            self.srv.stop()

        load()

        self.ui.gsv_label.setText(CONFIG["gsVersion"])
        self.ui.gsv_label.setStyleSheet('color: #000;')

        self.ui.select_printer.addItems(CONFIG['printers'])
        self.ui.input_url_sistema.setText(CONFIG['sistema'])

        CONFIG['lojas'] = self.api.get_stores()
        self.ui.select_loja.clear()
        self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

        CONFIG['printTypes'] = []

        if self.ui.cb_print_balcao.isChecked():
            CONFIG['printTypes'].append('0')

        if self.ui.cb_print_delivery.isChecked():
            CONFIG['printTypes'].append('1')

        template_mapping = {
            "Padrão": "bundle",
            "Apenas Comanda": "comanda",
            "Apenas Recibo": "recibo"
        }

        CONFIG['balcaoTemplate'] = template_mapping.get(self.ui.select_modelo_balcao.currentText(), "")
        CONFIG['deliveryTemplate'] = template_mapping.get(self.ui.select_modelo_delivery.currentText(), "")

        if not self.srv.running:
            self.srv.start()