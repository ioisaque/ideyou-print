import os
import json
import socket
import subprocess

import requests
from PyQt6.QtCore import QThread
from waitress import serve

from init import CONFIG
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin


class PrintServer(QThread):
    def __init__(self, ui):
        super(PrintServer, self).__init__()
        self.shutdown = False

        self.ui = ui
        self.app = Flask(__name__)
        self.cors = CORS(self.app)
        self.app.config['CORS_HEADERS'] = 'Content-Type'
        self.host = socket.gethostname()
        self.ipaddr = socket.gethostbyname_ex(self.host)[-1][0]

        self.app.add_url_rule('/', '', self.__index)
        self.app.add_url_rule('/print', 'print', self.__print, methods=['POST'])

    def run(self):
        while not self.shutdown:
            try:
                serve(self.app, host='0.0.0.0', port=6969)
            except Exception as e:
                print(e.__repr__())
            finally:
                if self.shutdown:
                    break

    def stop(self):
        try:
            self.shutdown = True
            self.quit()

        except Exception as e:
            print(e.__repr__())

    @cross_origin()
    def __index(self):
        count = 0
        ip = request.remote_addr
        client = request.user_agent.string

        self.__log(f'PING received from {ip} on {client}.')

        self.__log(f'Loja {self.ui.get_loja()} verificada, {count} pedidos na fila.')

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
            self.__log(f'Pedido {p.get("id")} enviado para {self.ui.get_printer()}.')
            self.__print_file(p.get('id'), p.get('full_url'))

        return self.__create_response(response)

    def __log(self, message):
        print(message)
        # self.ui.log(message)
        # QMetaObject.invokeMethod(self.ui, 'log', Qt.ConnectionType.QueuedConnection, Q_ARG(str, message))

    def __print_file(self, id: int, online_path: str):
        file_name = f'Pedido#{id}.pdf'
        local_path = os.path.join(CONFIG["rootPTH"], file_name)

        try:
            printer = self.ui.get_printer()
            options = f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies=1 -sDEVICE={CONFIG["sDevice"]} -sOutputFile="%|lp{printer}"' if CONFIG['isMacOS'] else f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies=1 -sDEVICE={CONFIG["sDevice"]} -sOutputFile="%printer%{printer}"'

            gs_command = f'{CONFIG["command"]} {options} {local_path}'
            print(f'{gs_command}')
            subprocess.run(['curl', '-o', local_path, f'{online_path}&download'])
            subprocess.run(gs_command)
        except Exception as error:
            print(error)
        finally:
            os.remove(local_path)

    def __create_response(self, data):
        response = jsonify(data)
        response.headers.add('Access-Control-Allow-Origin', '*')
        response.headers.add('Access-Control-Allow-Methods', 'GET')
        response.headers.add('Access-Control-Allow-Headers', '*')
        response.headers.add('Access-Control-Max-Age', '86400')
        response.headers.add('Content-Type', 'application/json')

        return response
