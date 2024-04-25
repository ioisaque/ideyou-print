import logging
import os
import re
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

        response = self.__request(None, url, {"User-Agent": "Postman"}, "GET").get('data')

        v1 = float(CONFIG['version'])
        v2 = float(response.get("version"))

        if not v1 == v2:
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
            "id_status": id_status if not id_status == 402 else 0,
            "setStatusPedido": id_pedido,
            "comentario": "Pedido recusado pela loja." if id_status == 0 else None
        }

        return self.__request(payload, url, {"User-Agent": "Postman"})

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

        # self.ui.log = f'buscando a fila de pedidos no servidor.'
        return response.get('data')

    def download_order(self, id_pedido: int, template: str) -> str | int:
        file_name = f'{template}#{id_pedido}.pdf'
        local_path = os.path.join(CONFIG["rootPTH"], file_name)

        try:
            if not os.path.exists(local_path):
                file_size = 0
                self.ui.log = f'<span style="color: #000000;">baixando {template} #{id_pedido} do servidor.</span>'
                os.popen(f'curl -o "{local_path}" "{self.base_url}/views/print/?id={id_pedido}&template={template}&download"')
                # subprocess.run(['curl', '-o', local_path, f'{self.base_url}/views/print/?id={id_pedido}&template={template}&download'])

                while file_size < 5120:
                    sleep(0.1)
                    try:
                        file_size = os.path.getsize(local_path)
                    except FileNotFoundError:
                        sleep(0.1)
            else:
                self.ui.log = f'<span style="color: #1976d2;">{template}#{id_pedido} já baixado, download ignorado.</span>'

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao baixar {template}#{id_pedido}: {str(e)}</span>'
            return 500
        finally:
            QApplication.processEvents()
            return file_name

    def print_order(self, pedido: dict):
        template = CONFIG["deliveryTemplate" if int(pedido.get("delivery")) else "balcaoTemplate"]
        _template = reverse_template_mapping.get(template, "Padrão")

        try:
            printer = self.ui.dPrinter
            file_name = self.download_order(pedido.get("id"), template)

            if not file_name == 500:
                local_path = os.path.join(CONFIG["rootPTH"], file_name)

                options = f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="{CONFIG["nCopies"]}" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%|lp{printer}"' if CONFIG['isMacOS'] else f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="{CONFIG["nCopies"]}" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%printer%{printer}"'
                gs_command = f'{CONFIG["command"]} {options} {local_path}'

                self.ui.log = f'#=> <span style="color: #0000FF;">PEDIDO #{pedido.get("id")} RECEBIDO!</span> {CONFIG["nCopies"]}x {_template}, [{CONFIG["dPrinter"]}]. <a href="{self.base_url}/?do=pedidos&action=view&id={pedido.get("id")}" style="color: #1976d2; cursor: pointer;">Visualizar</a>'

                os.popen(gs_command)
                # subprocess.run(gs_command)
        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao imprimir {template}#{pedido.get("id")}: {str(e)}</span>'
        finally:
            # os.remove(local_path)
            self.set_order_printed(pedido.get("id"), 1)

    def clean_up_files(self):

        files_to_delete = [file for file in os.listdir(CONFIG["rootPTH"]) if re.match(r'(recibo|bundle|comanda|pedido)#\d+\.(pdf|png)', file)]

        # Iterate through the list of files and delete them
        for file_name in files_to_delete:
            file_path = os.path.join(CONFIG["rootPTH"], file_name)
            try:
                os.remove(file_path)
            except Exception as e:
                self.ui.log = f'<span style="color: #f77b36;">Erro ao apagar {file_path}: {str(e)}</span>'

        self.ui.alert('Pronto!', 'Processo de limpeza de arquivos temporários realizado.')
