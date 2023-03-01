import os
import subprocess
import sys
import tempfile

CONFIG = {}


def load():
    global CONFIG

    CONFIG['isMacOS'] = sys.platform != 'windows'

    if CONFIG['isMacOS']:  # macOS
        CONFIG['tmp'] = tempfile.gettempdir()
        CONFIG['opt'] = os.popen('lpstat -d').read()
        CONFIG['printer'] = CONFIG['opt'].split(
            'system default destination: ')[-1].strip()

        CONFIG['command'] = 'gs'
        CONFIG['sDevice'] = 'ljet4'
        CONFIG['rootPTH'] = f'{CONFIG["tmp"]}/'
        CONFIG['sOutput'] = f'%|lp{CONFIG["printer"]}'
    else:  # Windows
        CONFIG['opt'] = os.popen('wmic printer get name,default').read()
        CONFIG['printer'] = [line.split()[1] for line in CONFIG['opt'].split('\n') if 'TRUE' in line][0] if [
            line.split()[1] for line in CONFIG['opt'].split('\n') if 'TRUE' in line] else None

        CONFIG['command'] = 'gswin32c.exe'
        CONFIG['sDevice'] = 'mswinpr2'
        CONFIG['rootPTH'] = f'C:/temp/'
        CONFIG['sOutput'] = f'%printer%{CONFIG["printer"]}'

    CONFIG['options'] = f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies=1 -sDEVICE={CONFIG["sDevice"]} -sOutputFile={CONFIG["sOutput"]}'

    try:
        CONFIG['gsVersion'] = subprocess.check_output(
            [CONFIG['command'], '-v']).decode('utf-8')
        CONFIG['gsVersion'] = CONFIG['gsVersion'].split('\n')[0]
        CONFIG['gsVersion'] = CONFIG['gsVersion'].split('(')[0].strip()

    except subprocess.CalledProcessError:
        CONFIG['gsVersion'] = "Ghostscript NÃO ENCONTRADO."

    return CONFIG
