import sys
from threading import Thread

from PyQt6 import QtWidgets, QtCore
from flask_cors import CORS

from init import load
from server import PrintServer

from window import MainWindow

if __name__ == '__main__':

    app = QtWidgets.QApplication(sys.argv)
    load()
    main_window = MainWindow()

    srv = PrintServer(main_window, 'IdeYouPrint')
    CORS(srv)

    if sys.platform == 'windows':
        main_window.setWindowFlags(QtCore.Qt.WindowCloseButtonHint | QtCore.Qt.WindowMinimizeButtonHint)
    # else:
        # QtCore.Qt.WindowType.Dialog
        # QtCore.Qt.WindowType.CustomizeWindowHint
        # main_window.setWindowFlags(QtCore.Qt.WindowType.CustomizeWindowHint)

    main_window.showNormal()
    Thread(target=srv.run, name='PrintServer', kwargs={'host': '0.0.0.0', 'port': 6969}).start()

    app.exec()
