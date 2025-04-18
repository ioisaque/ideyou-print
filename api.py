import os
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

        # base_url = f'{base_url}/api'

        return base_url

    def __request(self, payload: any, url, method: str = "POST", headers=None, timeout: int = 10) -> dict | None:
        data = {"code": 500, "data": [], "params": payload, "message": "Internal Server Error"}

        if CONFIG["sistema"] == '':
            return self.ui.alert('Erro 400',
                                 'Caminho do sistema indefinido, informe a\nURL do seu sistema para utilizar o serviço.')

        if headers is None:
            headers = {"User-Agent": "IdeYouPrint"}

        try:
            nome_loja = next((loja.get('nome') for loja in CONFIG["lojas"] if loja.get('id') == CONFIG["dStore"]), 'Unknown')

            if timeout == 0:
                raise TimeoutError("Forced timeout as timeout parameter is set to 0")
            
            response = requests.request(method=method, url=url, json=payload, headers=headers, timeout=timeout)
            data = response.json()

            if 'data' not in data:
                raise ValueError("Response does not contain 'data' attribute")

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">ERROR: {str(e)}</span>'
            # self.send_whatsapp(f'IdeYouPrint error on `{nome_loja}`: {str(e)}')
        finally:
            return data

    def send_whatsapp(self, mensagem: str, number: str = "447443695748") -> list | dict:
        try:
            print(mensagem)
            url = f"https://isaque.it/whatsapp/webservices/envios/"
            payload = {
                "session_id": "IDEYOU",
                "number": number,
                "mensagem": mensagem,
                "custo": 0,
                "free": 1
            }

            headers = {
                "User-Agent": "IdeYouPrint",
                "Content-Type": "application/json",
                "Authorization": "Bearer $2b$10$nyWgDoqN2w6B7ZD1vX5HquJ_9ClGW4OWxC4CK4SNk3xT5BYUd7ljK"
            }

            response = self.__request(payload, url, "POST", headers)

            print(response)

            return response

        except Exception as e:
            self.ui.log = f'<span style="color: #ffb22b;">Erro ao enviar mensagem para {number}, "{mensagem}": {str(e)}</span>'

    def check_app_version(self) -> int:
        try:
            url = f"{self.base_url}/api/settings/?name=autoprint"

            response = self.__request(None, url, "GET")

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

        except Exception as e:
            self.ui.log = f'<span style="color: #1976d2;">Erro ao conectar ao sistema: {str(e)}</span>'
            return 500

    def get_order_by_id(self, id_pedido: int = 0) -> dict:
        try:
            for order in CONFIG['queue']:
                if order['id'] == id_pedido:
                    return order

            url = f"{self.base_url}/api/pedidos/"
            payload: dict = {
                "id": id_pedido
            }

            return self.__request(payload, url).get('data')

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao buscar pedido {id_pedido}: {str(e)}</span>'

    def set_order_status(self, id_pedido: int = 0, status: int = 0) -> dict:
        try:
            url = f"{self.base_url}/api/pedidos/"
            payload: dict = {
                "id": id_pedido,
                "status": status,
                "comentario": "Pedido recusado pela loja." if status == 0 else None
            }
            return self.__request(payload, url)

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao atualizar status do pedido {id_pedido} como {status}: {str(e)}</span>'

    def set_order_printed(self, id_pedido: int = 0) -> dict:
        try:
            url = f"{self.base_url}/api/pedidos/"
            payload: dict = {
                "id": id_pedido,
                "printed": 1
            }

            return self.__request(payload, url, "POST", None)

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao definir pedido {id_pedido} como impresso: {str(e)}</span>'

    def get_stores(self) -> list:
        try:
            url = f"{self.base_url}/api/lojas/"
            payload: dict = {
                "listar": "todos"
            }

            response = self.__request(payload, url)

            return [{"id": loja.get('id'), "nome": loja.get('nome')} for loja in response.get('data')]

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao buscar lojas: {str(e)}</span>'
            return []

    def get_wating_orders(self, id_loja: int = 0) -> list:
        try:
            url = f"{self.base_url}/api/pedidos/"
            payload: dict = {
                "listar": "queue",
                "id_loja": int(id_loja if id_loja > 0 else CONFIG["dStore"])
            }
            response = self.__request(payload, url, "POST")            

            # Return an empty list if the response is not successful or doesn't contain 'data'
            if response == 0 or not isinstance(response, dict) or 'data' not in response:
                return []

            fila = response.get('data', [])

            self.ui.log = f'<span style="color: #3C3C3C;">{len(fila)} pedido{"s" if len(fila) == 1 else ""} na fila!</span>'

            return fila

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao retornar a fila de pedidos do sistema: {str(e)}</span>'
            return []

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
                self.ui.log = f'<span style="color: #9C9C9C;">#=> {command}</span>'
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
                for i in range(1 if int(pedido.get("status")) == 0 else int(CONFIG["nCopies"])):
                    options = (
                        f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="1" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%|lp{printer}"'
                        if CONFIG['isMacOS']
                        else f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies="1" -sDEVICE="{CONFIG["sDevice"]}" -sOutputFile="%printer%{printer}"'
                    )
                    gs_command = f'{CONFIG["command"]} {options} {local_path}'

                    self.ui.log = f'<span style="color: #8C8C8C;">#=> {gs_command}</span>'

                    # Execute the command for each copy
                    os.popen(gs_command)
                    # subprocess.run(gs_command)

        except Exception as e:
            self.ui.log = f'<span style="color: #f77b36;">Erro ao imprimir {template}#{pedido.get("id")}: {str(e)}</span>'
        # finally:
            # os.remove(local_path)
            # self.set_order_printed(pedido.get("id"))
