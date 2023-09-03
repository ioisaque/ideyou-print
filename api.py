import logging
import requests
from time import sleep

from PyQt6.QtCore import QThread

from init import CONFIG


class IdeYouApi(QThread):

    def __init__(self, ui):
        super(IdeYouApi, self).__init__()

        self.ui = ui
        self.__retry_amount = 3
        self.__connection_retry_timeout = 10

    @property
    def base_url(self) -> str:
        base_url = f'{self.ui.sistema}' + ""

        if any(addr in base_url for addr in ["192.168", "block", "local", "127.0.0.1"]):
            if not base_url.startswith("http"):
                base_url = f'http://{base_url}'
        else:
            base_url = f'{base_url if base_url.startswith("https") else base_url.replace("http", "https")}'
            if not base_url.startswith("https"):
                base_url = f'https://{base_url}'

        if base_url.endswith('/'):
            base_url = base_url[:-1]

        base_url = f'{base_url}/webservices'

        return base_url

    def __request(self, payload, url, headers=None, method: str = "POST") -> dict:

        if self.ui.sistema == '':
            return self.ui.alert('Erro 400', 'Caminho do sistema indefinido, informe a\nURL do seu sistema para utilizar o serviço.')

        if headers is None:
            headers = {}

        for i in range(self.__retry_amount):
            try:
                response = requests.request(method=method, url=url, json=payload, headers=headers)
                data = response.json()

                return data
            except Exception as e:
                logging.error(f'Impossible to get the response from server: {e.__repr__()}')
                logging.error(f'Waiting {self.__connection_retry_timeout} - for retry')
                sleep(self.__connection_retry_timeout)

                if i > self.__retry_amount:
                    break

    def get_order_by_id(self, id_pedido: int = 0) -> list:
        url = f"{self.base_url}/pedidos/"
        payload: dict = {
            "id": id_pedido
        }

        self.ui.log = f'Buscando pedido {id_pedido}...'
        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')

    def get_stores(self) -> list:
        url = f"{self.base_url}/lojas/"
        payload: dict = {
            "listar": "todos"
        }

        self.ui.log = 'Buscando listagem de lojas...'
        response = self.__request(payload, url, {"User-Agent": "Postman"})

        return [{"id": loja.get('id'), "nome": loja.get('nome')} for loja in response.get('data')]

    def get_wating_orders(self, id_loja: int = 0) -> list:
        url = f"{self.base_url}/pedidos/"
        payload: dict = {
            "listar": "queue",
            "id_loja": id_loja if id_loja > 0 else CONFIG["dStore"]
        }

        self.ui.log = 'Buscando pedidos na fila...'
        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')
