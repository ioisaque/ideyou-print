import logging
import requests
from time import sleep
from init import CONFIG


class Api:

    def __init__(self):
        self.__retry_amount = 3
        self.__connection_retry_timeout = 10
        self.__base_url: str = f'{CONFIG["sistema"]}/webservices'

    def __request(self, payload, url, headers=None, method: str = "POST") -> dict:

        if headers is None:
            headers = {}

        for i in range(self.__retry_amount):
            try:
                response = requests.request(method=method, url=url, json=payload, headers=headers)
                return response.json()
            except Exception as e:
                logging.error(f'Impossible to get the response from server: {e.__repr__()}')
                logging.error(f'Waiting {self.__connection_retry_timeout} - for retry')
                sleep(self.__connection_retry_timeout)

                if i > self.__retry_amount:
                    break

    def get_stores(self) -> dict:
        url = f"{self.__base_url}/lojas/"
        payload: dict = {
            "listar": "todos"
        }

        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')

    def get_wating_orders(self, id_loja: int = 1) -> list:
        url = f"{self.__base_url}/pedidos/"
        payload: dict = {
            "listar": "queue",
            "id_loja": id_loja
        }

        return self.__request(payload, url, {"User-Agent": "Postman"}).get('data')

    @property
    def base_url(self):
        return self.__base_url

    @base_url.setter
    def base_url(self, value):
        self.__base_url = value
