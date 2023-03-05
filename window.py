from init import load, CONFIG
from PyQt6 import QtWidgets, uic

MainViewUi, QtBaseClass = uic.loadUiType("assets/main.ui")


class MainWindow(QtWidgets.QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()
        self.ui = MainViewUi()
        self.ui.setupUi(self)
        self.ui.btn_reload.clicked.connect(self.__reload)

        if CONFIG["gsVersion"]:
            self.ui.gsv_label.setText(CONFIG["gsVersion"])
            self.ui.gsv_label.setStyleSheet('color: #000;')

            self.ui.select_printer.addItems(CONFIG['printers'])

    def get_printer(self):
        return self.ui.select_printer.currentText()

    def log(self, l: str):
        old = self.ui.log_box.toPlainText()
        self.ui.log_box.setText(old + ('\n' if len(old) else '') + l)
        return 0

    def __reload(self):
        load()
        self.ui.log_box.setText('Configurações recarregadas...')

