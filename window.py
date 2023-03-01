from init import load, CONFIG
from PyQt6 import QtWidgets, uic

MainViewUi, QtBaseClass = uic.loadUiType("assets/main.ui")


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = MainViewUi()
        self.ui.setupUi(self)
        self.ui.reload.clicked.connect(self.__reload)

        self.log(CONFIG["gsVersion"])
        self.log(f'Impressora: {CONFIG["printer"]}')

    def log(self, l: str):
        old = self.ui.log_box.toPlainText()
        self.ui.log_box.setText(old + ('\n' if len(old) else '') + l)

    def __reload(self):
        load()
        self.ui.log_box.setText('')
        self.log(CONFIG["gsVersion"])
        self.log(f'Impressora: {CONFIG["printer"]}')

