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
        self.ui.btn_reload.clicked.connect(self.reload)

        if CONFIG["gsVersion"]:
            self.ui.gsv_label.setText(CONFIG["gsVersion"])
            self.ui.gsv_label.setStyleSheet('color: #000;')

            self.srv.start()
            CONFIG['lojas'] = self.api.get_stores()

            self.ui.select_printer.addItems(CONFIG['printers'])
            self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

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

    def reload(self):
        self.srv.stop()
        load()
        self.srv.start()
