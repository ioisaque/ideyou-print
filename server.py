import os
import json
import socket
import subprocess
from PyQt6 import QtCore
from init import CONFIG
from flask import Flask, request, jsonify


class PrintServer(Flask):

    def __init__(self, ui, name):
        super().__init__(name)
        self.ui = ui
        self.__log(f'Server init.')
        self.add_url_rule('/', '', self.__index)
        self.add_url_rule('/print', 'print', self.__print, methods=['POST'])

    def __index(self):
        ip_address = request.remote_addr
        device_name = request.user_agent.string  # This is the device name
        self.__log(f'PING received from {ip_address} on {device_name}.')
        response = {'message': socket.gethostname(), 'type': 'success'}
        return self.__create_response(response)

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
            self.__log(f'Imprimindo pedido {p.get("id")}, de "{p.get("full_url")}".')
            self.__print_file(p.get('id'), p.get('full_url'))

        return self.__create_response(response)

    def __log(self, message):
        print(message)
        # QtCore.QMetaObject.invokeMethod(self.ui, 'log', QtCore.Qt.ConnectionType.QueuedConnection, QtCore.Q_ARG(str, message))

    def __print_file(self, id: int, online_path: str):
        file_name = f'Pedido#{id}.pdf'
        local_path = os.path.join(CONFIG["rootPTH"], file_name)
        gs_command = f'{CONFIG["command"]} {CONFIG["options"]} {local_path}'

        try:
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
