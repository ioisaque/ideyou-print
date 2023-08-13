import os
import subprocess
import sys
import tempfile

CONFIG = {}


def load():
    global CONFIG

    CONFIG['isMacOS'] = str(sys.platform).find('win')
    CONFIG['printers'] = []

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

    try:
        CONFIG['gsVersion'] = subprocess.check_output([CONFIG['command'], '-v']).decode('utf-8')
        CONFIG['gsVersion'] = CONFIG['gsVersion'].split('\n')[0]
        CONFIG['gsVersion'] = CONFIG['gsVersion'].split('(')[0].strip()

    except subprocess.CalledProcessError:
        CONFIG['gsVersion'] = None

    return CONFIG
