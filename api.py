import logging
import os
import re
import subprocess
import tempfile
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
        base_url = f'{CONFIG["sistema"]}' + ""

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

        if CONFIG["sistema"] == '':
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

    def check_app_version(self) -> int:
        url = f"{self.base_url}/webservices/settings/?name=autoprint"

        response = self.__request(None, url, {"User-Agent": "Postman"}, "GET")

        # Check if the response is None or if 'data' is not in the response
        if response is None or 'version' not in response:
            return 200
        else:
            response = response.get('data')

        v1 = float(CONFIG['version'])
        v2 = float(response.get("version"))

        if v1 < v2:
            print(repr(response.get("version")), repr(CONFIG['version']))
            return 400

        return 200

    def get_order_by_id(self, id_pedido: int = 0) -> dict:
        for order in CONFIG['queue']:
            if order['id'] == id_pedido:
                return order

        url = f"{self.base_url}/webservices/pedidos/"
        payload: dict = {
            "id": id_pedido
        }

        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')

    def set_order_status(self, id_pedido: int = 0, id_status: int = 0) -> dict:
        url = f"{self.base_url}/webservices/pedidos/"
        payload: dict = {
            "dialog": True,
            "id_status": id_status if not id_status == -1 else 0,
            "setStatusPedido": id_pedido,
            "comentario": "Pedido recusado pela loja." if id_status == 0 else None
        }
        response = self.__request(payload, url, {"User-Agent": "Postman"})

        return response

    def set_order_printed(self, id_pedido: int = 0, id_status: int = 0) -> dict:
        url = f"{self.base_url}/webservices/pedidos/"
        payload: dict = {
            "id_status": id_status,
            "setPrintedPedido": id_pedido
        }

        return self.__request(payload, url, {"User-Agent": "Postman"})

    def get_stores(self) -> list:
        url = f"{self.base_url}/webservices/lojas/"
        payload: dict = {
            "listar": "todos"
        }

        response = self.__request(payload, url, {"User-Agent": "Postman"})

        return [{"id": loja.get('id'), "nome": loja.get('nome')} for loja in response.get('data')]

    def get_wating_orders(self, id_loja: int = 0) -> list:
        url = f"{self.base_url}/webservices/pedidos/"
        payload: dict = {
            "listar": "queue",
            "id_loja": int(id_loja if id_loja > 0 else CONFIG["dStore"])
        }
        response = self.__request(payload, url, {"User-Agent": "Postman"})

        self.ui.log = f'<span style="color: #6C6C6C;">verificando a fila de pedidos no servidor.</span>'

        # Return an empty list if the response is not successful or doesn't contain 'data'
        if response == 0 or not isinstance(response, dict) or 'data' not in response:
            return []

        return response.get('data', [])

    def download_order(self, id_pedido: int, template: str) -> str | int:
        file_size = 0
        file_name = f'{template}#{id_pedido}.pdf'
        local_path = os.path.join(CONFIG["rootPTH"], file_name)

        try:
            # Use a temporary file
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as temp_file:
                local_path = temp_file.name

                if os.path.exists(local_path):
                    os.remove(local_path)  # Remove existing temp file (if any)

                command = f'curl -o "{local_path}" "{self.base_url}/views/print/?id={id_pedido}&template={template}&download=true"'
                self.ui.log = f'<span style="color: #FFD22B;">#=> {command}</span>'
                os.popen(command)

                # subprocess.run(['curl', '-o', local_path, f'{self.base_url}/views/print/?id={id_pedido}&template={template}&download=true'])

                while file_size < 5120:
                    sleep(0.1)
                    try:
                        file_size = os.path.getsize(local_path)
                    except FileNotFoundError:
                        sleep(0.1)

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao baixar {template}#{id_pedido}: {str(e)}</span>'
            return 500
        finally:
            QApplication.processEvents()
            return local_path

    def print_order(self, pedido: dict):
        template = CONFIG["deliveryTemplate" if int(pedido.get("delivery")) else "balcaoTemplate"]
        _template = reverse_template_mapping.get(template, "Padrão")

        try:
            printer = self.ui.dPrinter
            local_path = self.download_order(pedido.get("id"), template)

            if not local_path == 500:
                for i in range(1 if int(pedido.get("status")) <= 0 else int(CONFIG["nCopies"])):
                    options = (
                        f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="1" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%|lp{printer}"'
                        if CONFIG['isMacOS']
                        else f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="1" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%printer%{printer}"'
                    )
                    gs_command = f'{CONFIG["command"]} {options} {local_path}'

                    self.ui.log = f'<span style="color: #0076F3;">#=> {gs_command}</span>'

                    # Execute the command for each copy
                    os.popen(gs_command)
                    # subprocess.run(gs_command)

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao imprimir {template}#{pedido.get("id")}: {str(e)}</span>'
        finally:
            # os.remove(local_path)
            self.set_order_printed(pedido.get("id"), 1)