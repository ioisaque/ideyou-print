import logging
import os
import re
import subprocess
import urllib
from time import sleep

import requests
from PyQt6.QtCore import QThread
from PyQt6.QtWidgets import QApplication

from init import CONFIG, reverse_template_mapping


class IdeYouApi(QThread):

    def __init__(self, ui):
        super(IdeYouApi, self).__init__()

        self.ui = ui
        self.__retry_amount = 3
        self.__connection_retry_timeout = 5

    @property
    def base_url(self) -> str:
        base_url = f'{self.ui.sistema}' + ""

        if any(addr in base_url for addr in ["192.168", "block.local", "localhost", "127.0.0.1"]):
            if not base_url.startswith("http"):
                base_url = f'http://{base_url}'
        else:
            base_url = f'{base_url if base_url.startswith("https") else base_url.replace("http", "https")}'
            if not base_url.startswith("https"):
                base_url = f'https://{base_url}'

        if base_url.endswith('/'):
            base_url = base_url[:-1]

        # base_url = f'{base_url}/webservices'

        return base_url

    def __request(self, payload, url, headers=None, method: str = "POST") -> dict:
        data = []

        if self.ui.sistema == '':
            return self.ui.alert('Erro 400',
                                 'Caminho do sistema indefinido, informe a\nURL do seu sistema para utilizar o serviço.')

        if headers is None:
            headers = {}

        for i in range(self.__retry_amount):
            try:
                response = requests.request(method=method, url=url, json=payload, headers=headers)
                data = response.json()

            except Exception as e:
                logging.error(f'Impossible to get the response from server: {e.__repr__()}')
                logging.error(f'Waiting {self.__connection_retry_timeout} - for retry')
                sleep(self.__connection_retry_timeout)

                if i > self.__retry_amount:
                    break
            finally:
                return data

    def get_order_by_id(self, id_pedido: int = 0) -> list:
        for order in CONFIG['queue']:
            if order['id'] == id_pedido:
                return order

        url = f"{self.base_url}/webservices/pedidos/"
        payload: dict = {
            "id": id_pedido
        }

        self.ui.log = f'Procurando pedido #{id_pedido} no sistema.'
        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')

    def get_stores(self) -> list:
        url = f"{self.base_url}/webservices/lojas/"
        payload: dict = {
            "listar": "todos"
        }

        self.ui.log = f'Buscando a lista de lojas no servidor.'
        response = self.__request(payload, url, {"User-Agent": "Postman"})

        return [{"id": loja.get('id'), "nome": loja.get('nome')} for loja in response.get('data')]

    def get_wating_orders(self, id_loja: int = 0) -> list:
        url = f"{self.base_url}/webservices/pedidos/"
        payload: dict = {
            "listar": "queue",
            "id_loja": id_loja if id_loja > 0 else CONFIG["dStore"]
        }

        self.ui.log = f'Buscando a lista de pedidos no servidor.'
        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')

    def download_order(self, pedido: dict) -> str | int:
        id_pedido = int(pedido.get('id'))
        template = CONFIG["deliveryTemplate" if int(pedido.get("delivery")) else "balcaoTemplate"]

        file_name = f'Pedido#{id_pedido}.pdf'
        local_path = os.path.join(CONFIG["rootPTH"], file_name)
        online_path = f'{self.base_url}/views/print/?id={id_pedido}&template={template}'

        try:
            file_size = 0
            self.ui.log = f'Baixando {template} #{id_pedido} do servidor.'
            # os.popen(f'curl -o "{local_path}" "{online_path}&download"')
            subprocess.run(['curl', '-o', local_path, f'{online_path}&download'])

            while file_size < 5120:
                sleep(0.1)
                try:
                    file_size = os.path.getsize(local_path)
                except FileNotFoundError:
                    sleep(0.1)

            return file_name
        except Exception as error:
            self.ui.log = error
            return 500
        finally:
            self.ui.preview(local_path)
            QApplication.processEvents()

    def print_order(self, pedido: dict):
        id_pedido = int(pedido.get('id'))
        template = CONFIG["deliveryTemplate" if int(pedido.get("delivery")) else "balcaoTemplate"]
        _template = reverse_template_mapping.get(template, "Padrão")

        try:
            printer = self.ui.dPrinter
            file_name = self.download_order(pedido)

            if not file_name == 500:
                local_path = os.path.join(CONFIG["rootPTH"], file_name)

                options = f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="{CONFIG["nCopies"]}" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%|lp{printer}"' if CONFIG['isMacOS'] else f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="{CONFIG["nCopies"]}" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%printer%{printer}"'
                gs_command = f'{CONFIG["command"]} {options} {local_path}'

                self.ui.log = f'#=> <span style="color: #0000FF;">PEDIDO #{id_pedido} RECEBIDO!</span> {CONFIG["nCopies"]}x {_template}, [{CONFIG["dPrinter"]}]. <a href="{self.base_url}/?do=pedidos&action=view&id={id_pedido}" style="color: #1976d2; cursor: pointer;">Visualizar</a>'

                os.popen(gs_command)
                # subprocess.run(gs_command)
        except Exception as error:
            self.ui.log = error
        # finally:
            # os.remove(local_path)

    def clean_up_files(self):

        files_to_delete = [file for file in os.listdir(CONFIG["rootPTH"]) if re.match(r'Pedido#\d+\.pdf', file)]

        # Iterate through the list of files and delete them
        for file_name in files_to_delete:
            file_path = os.path.join(CONFIG["rootPTH"], file_name)
            try:
                os.remove(file_path)
            except Exception as e:
                self.ui.log = f'<span style="color: #f77b36;">Erro ao apagar comanda/recibo: {str(e)}</span>'

        self.ui.alert('Pronto!', 'Processo de limpeza de arquivos temporários realizado.')
