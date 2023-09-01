import sys

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

        if CONFIG["gsVersion"]:
            self.load()

        self.show()

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

        self.ui.input_url_sistema.setText(CONFIG['sistema'])
        CONFIG['lojas'] = self.api.get_stores()
        self.ui.select_printer.addItems(CONFIG['printers'])
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
