import os
import sys
import json
import time
import tempfile
import platform
import subprocess
from threading import Thread
from flask_cors import CORS
from PyQt6.uic import loadUi
from flask import Flask, request, jsonify
from PyQt6.QtWidgets import QApplication, QMainWindow

app = Flask(__name__)
CORS(app)


class MainWindow(QMainWindow):

    def __init__(self):
        super(MainWindow, self).__init__()

        # Load the ui file
        loadUi("main.ui", self)
        self.show()
        self.load()
        self.btn_check.clicked.connect(self.load)

    def load(self):
        self.log_reset()
        self.isMacOS = platform.system() == 'Darwin'

        if self.isMacOS:  # macOS
            self.tmp = tempfile.gettempdir()
            self.opt = os.popen('lpstat -d').read()
            self.printer = self.opt.split(
                'system default destination: ')[-1].strip()

            self.command = 'gs'
            self.sDevice = 'ljet4'
            self.rootPTH = f'{self.tmp}/'
            self.sOutput = f'%|lp{self.printer}'
        else:  # Windows
            self.opt = os.popen('wmic printer get name,default').read()
            self.printer = [line.split()[1]
                            for line in self.opt.split('\n') if 'TRUE' in line][0]

            self.command = 'gswin32c.exe'
            self.sDevice = 'mswinpr2'
            self.rootPTH = f'C:/temp/'
            self.sOutput = f'"%printer%{self.printer}"'

        self.options = f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies=1 -sDEVICE={self.sDevice} -sOutputFile={self.sOutput}'

        try:
            gsv = subprocess.check_output([self.command, '-v']).decode('utf-8')
            gsv = gsv.split('\n')[0]
            gsv = gsv.split('(')[0].strip()

            self.log(gsv)
            self.log(f'Impressora: {self.printer}')
            # self.log(f'Diretório: {self.rootPTH}')
            # self.log(f'Sistema: {"MacOS" if self.isMacOS else "Windows"}')

            Thread(target=app.run, kwargs={
                   'host': 'localhost', 'port': 6969, 'debug': False}).start()
        except subprocess.CalledProcessError:
            self.log("Ghostscript NÃO ENCONTRADO.")

    def log(self, l: str):
        old = self.txt_log.toPlainText()
        self.txt_log.setText(old + ('\n' if len(old) else '') + l)

    def log_reset(self):
        # self.txt_log.setText('.')
        # time.sleep(1)
        # self.txt_log.setText('..')
        # time.sleep(1)
        # self.txt_log.setText('...')
        # time.sleep(1)
        self.txt_log.setText('')

    def print(self, id: int, online_path: str):
        file_name = f'Pedido#{id}.pdf'
        local_path = os.path.join(self.rootPTH, file_name)
        gs_command = f'{self.command} {self.options} {local_path}'

        print(f'Imprimindo pedido {id}, de "{online_path}".')

        try:
            subprocess.run(['curl', '-o', local_path,
                           f'{online_path}&download'])

            # Thread(target=self.log, kwargs={'l': f'Imprimindo pedido {id}, de "{online_path}".'}).start()

            if self.isMacOS:
                subprocess.call(gs_command)
            else:
                subprocess.Popen(gs_command, shell=True,
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(5)
            os.remove(local_path)
            time.sleep(2)
        except Exception as error:
            print(error)


if __name__ == "__main__":
    UI = QApplication(sys.argv)

    main_window = MainWindow()

    @app.route('/print', methods=['POST'])
    def process(ui=main_window):
        p = json.loads(request.data)

        if 'id' not in p:
            response = {
                'message': 'Pedido ID não informado, impressão cancelada.', 'type': 'error'}
        elif 'full_url' not in p or 'short_url' not in p:
            response = {
                'message': 'Url do PDF não informada, impressão cancelada.', 'type': 'error'}
        elif not p.get('full_url').find(str(p.get('id'))):
            response = {
                'message': 'ID e Url divergentes, impressão cancelada.', 'type': 'error'}
        else:
            response = {
                'message': 'Pedido recebido para impressão!', 'type': 'success'}
            ui.print(p.get('id'), p.get('full_url'))

        response = jsonify(response)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'POST')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Max-Age', '86400')
        response.headers.add('Content-Type', 'application/json')

        return response

    sys.exit(UI.exec())
