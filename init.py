import os
import sys
import json
import tempfile
import subprocess

CONFIG = {
    'version': "1.6"
}
S_CONFIG = [
    "dStore",
    "nCopies",
    "dPrinter",
    'lojas',
    'sistema',
    'deliveryTemplate',
    'balcaoTemplate',
    'printTypes',
    'openOnLogon',
    "queue"
]

template_mapping = {
    "Padrão": "bundle",
    "Apenas Comanda": "comanda",
    "Apenas Recibo": "recibo"
}
reverse_template_mapping = {v: k for k, v in template_mapping.items()}


def save():
    params = {}

    for key in S_CONFIG:
        params[key] = CONFIG[key]

    with open(f'{CONFIG["rootPTH"]}ideyou_config.json', "w") as jsonfile:
        jsonfile.write(json.dumps(params))


def load():
    global CONFIG
    global S_CONFIG

    CONFIG['queue'] = []
    CONFIG["nCopies"] = 1
    CONFIG["dPrinter"] = ""
    CONFIG["dStore"] = "0"
    CONFIG['lojas'] = [{"id": 0, "nome": "N/A"}]
    CONFIG['sistema'] = "http://sistema.ideyou.com.br"

    CONFIG["openOnLogon"] = 0
    CONFIG['deliveryTemplate'] = "bundle"
    CONFIG['balcaoTemplate'] = "comanda"
    CONFIG['printTypes'] = [0, 1]
    CONFIG['printers'] = []

    CONFIG['gslink'] = "https://cdn.ideyou.com.br/archive/ghostscript/gs1000w32.exe"

    CONFIG['isMacOS'] = str(sys.platform).find('win')

    if CONFIG['isMacOS']:  # macOS
        default = os.popen('lpstat -d').read().split('system default destination: ')[-1].strip()

        for line in os.popen('lpstat -v').readlines():
            name = line.split(":")[0].replace("device for ", "").strip()

            if name != default:
                CONFIG['printers'].append(name)
            else:
                CONFIG['printers'].insert(0, name)

        CONFIG['command'] = 'gs'
        CONFIG['sDevice'] = 'ljet4'
        CONFIG['rootPTH'] = f'{tempfile.gettempdir()}/'
    else:  # Windows
        lines = os.popen('wmic printer get name,default').read().split('\n')[1:-2]

        for line in lines:
            default, name = line[0:6].strip(), line[6:].strip()

            if default == 'TRUE':
                CONFIG['printers'].insert(0, name)
            elif name:
                CONFIG['printers'].append(name)

        CONFIG['command'] = 'gswin32c.exe'
        CONFIG['sDevice'] = 'mswinpr2'
        CONFIG['rootPTH'] = f'C:/tmp/'

        if not os.path.exists(CONFIG['rootPTH']):
            os.makedirs(CONFIG['rootPTH'])

    try:
        CONFIG['gsVersion'] = os.popen(f'{CONFIG["command"]} -v').read()
        CONFIG['gsVersion'] = CONFIG['gsVersion'].split('\n')[0]
        CONFIG['gsVersion'] = CONFIG['gsVersion'].split('(')[0].strip()

    except subprocess.CalledProcessError:
        CONFIG['gsVersion'] = None

    ideyou_config = f'{CONFIG["rootPTH"]}ideyou_config.json'

    if os.path.exists(ideyou_config):
        with open(ideyou_config, "r") as jsonfile:
            saved = json.load(jsonfile)

            for key in saved:
                CONFIG[key] = saved[key]
    else:
        with open(ideyou_config, "w") as jsonfile:
            json.dump({key: CONFIG[key] for key in S_CONFIG}, jsonfile)

    if not CONFIG['sistema'].startswith('http'):
        CONFIG['sistema'] = 'http://' + CONFIG['sistema']

    if CONFIG['sistema'].endswith('/'):
        CONFIG['sistema'] = CONFIG['sistema'][:-1]

    return CONFIG
