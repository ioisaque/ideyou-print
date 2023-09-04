import sys

from PyQt6 import QtWidgets

from init import load
from window import MainWindow

if __name__ == '__main__':
    load()

    app = QtWidgets.QApplication(sys.argv)

    ui = MainWindow()

    sys.exit(app.exec())
