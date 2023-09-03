import sys
from datetime import datetime
import re

from init import CONFIG, load, save
from PyQt6 import uic
from PyQt6.QtWidgets import QMainWindow, QMessageBox, QApplication
from server import PrintServer

template_mapping = {
    "Padrão": "bundle",
    "Apenas Comanda": "comanda",
    "Apenas Recibo": "recibo"
}
reverse_template_mapping = {v: k for k, v in template_mapping.items()}

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

        self.srv = PrintServer(self)
        self.api = self.srv.api

        if CONFIG["gsVersion"]:
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

            if not CONFIG['lojas']:
                CONFIG['lojas'] = self.api.get_stores()

            self.ui.select_loja.clear()
            self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

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

            self.ui.input_url_sistema.textChanged.connect(self.save)
            self.ui.input_id_pedido.textChanged.connect(self.limit_orderid_length)

            self.ui.select_loja.currentIndexChanged.connect(self.save)
            self.ui.select_printer.currentIndexChanged.connect(self.save)
            self.ui.select_printqtd.currentIndexChanged.connect(self.save)
            self.ui.select_modelo_balcao.currentIndexChanged.connect(self.save)
            self.ui.select_modelo_delivery.currentIndexChanged.connect(self.save)

            self.ui.cb_print_balcao.stateChanged.connect(self.save)
            self.ui.cb_print_delivery.stateChanged.connect(self.save)

        self.show()

    def load(self, first: bool = False):
        if self.srv.running:
            self.srv.stop()

        load()

        CONFIG['lojas'] = self.api.get_stores()
        self.ui.select_loja.clear()
        self.ui.select_loja.addItems([loja.get('nome') for loja in CONFIG['lojas']])

        if not self.srv.running:
            self.srv.start()

    def save(self):
        CONFIG["sistema"] = self.ui.input_url_sistema.toPlainText()
        CONFIG["dStore"] = re.sub(r'[^0-9]', '', self.ui.select_loja.currentText()).lstrip('0')

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

    def log(self, l: str):
        print(l)
        # old = self.ui.log_box.toPlainText()
        # self.ui.log_box.setText(old + ('\n' if len(old) else '') + l)3

    def alert(self, title: str, message: str):
        app = QApplication([])

        # Create a QMessageBox
        alert = QMessageBox()

        # Set the alert properties
        alert.setWindowTitle(title)
        alert.setText(message)
        alert.setIcon(QMessageBox.Icon.Information)  # You can change the icon as needed

        # Add buttons to the alert
        alert.addButton(QMessageBox.StandardButton.Ok)
        # You can add more buttons or customize their behavior if needed

        # Show the alert
        result = alert.exec()

        # Check the result (button clicked)
        if result == QMessageBox.StandardButton.Ok:
            print("OK button clicked")

        # Run the application event loop
        app.exec()

    @property
    def last_checked(self):
        return self.ui.last_checked.currentText()

    @last_checked.setter
    def last_checked(self, count):
        current_time = datetime.now()
        self.ui.last_checked.setText(current_time.strftime(f'Última checagem ás %H:%M:%S [{count} pedidos]'))

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
        return int(re.sub(r'[^0-9]', '', self.ui.select_loja.currentText()))

    @dStore.setter
    def dStore(self, value):
        CONFIG["dStore"] = int(re.sub(r'[^0-9]', '', value))

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

    def limit_orderid_length(self):
        max_length = 8
        current_text = self.ui.input_id_pedido.toPlainText()

        if len(current_text) > max_length:
            self.ui.input_id_pedido.setPlainText(current_text[:max_length])
