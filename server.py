import json
import socket

from PyQt6.QtCore import QThread
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin
from waitress import serve

from api import IdeYouApi


class PrintServer(QThread):
    def __init__(self, ui):
        super(PrintServer, self).__init__()
        self.running = False
        self.shutdown = False

        self.ui = ui
        self.api = IdeYouApi(ui)
        self.app = Flask(__name__)
        self.cors = CORS(self.app)
        self.app.config['CORS_HEADERS'] = 'Content-Type'
        self.host = socket.gethostname()
        self.ipaddr = socket.gethostbyname_ex(self.host)[-1][0]

        self.app.add_url_rule('/', '', self.__index)
        self.app.add_url_rule('/print', 'print', self.__print, methods=['POST'])

    def run(self):
        self.running = True
        while not self.shutdown:
            try:
                serve(self.app, host='0.0.0.0', port=6969)
            except Exception as e:
                print(e.__repr__())
            finally:
                if self.shutdown:
                    self.ui.log = 'Stopping SRV...'
                    break

    def stop(self):
        try:
            self.shutdown = True
            self.quit()
            self.running = False

        except Exception as e:
            print(e.__repr__())

    @cross_origin()
    def __index(self):
        ip = request.remote_addr
        client = request.user_agent.string

        self.__log(f'PING received from {ip} on {client}.')

        response = {'name': self.host, 'ip': self.ipaddr}
        return self.__create_response(response)

    @cross_origin()
    def __print(self):
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

            self.__log(f'Pedido {p.get("id")} enviado para {self.ui.dPrinter()}.')

        return self.__create_response(response)

    def __log(self, message):
        print(message)
        # self.ui.log = message
        # QMetaObject.invokeMethod(self.ui, 'log', Qt.ConnectionType.QueuedConnection, Q_ARG(str, message))

    def __create_response(self, data):
        response = jsonify(data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Max-Age', '86400')
        response.headers.add('Content-Type', 'application/json')

        return response
