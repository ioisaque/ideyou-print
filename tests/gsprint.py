import os
import platform
import tempfile
import subprocess
import time

isMacOS = platform.system() == 'Darwin'

if isMacOS:  # macOS
    tmp = tempfile.gettempdir()
    opt = os.popen('lpstat -d').read()
    printer = opt.split('system default destination: ')[-1].strip()

    command = 'gs'
    sDevice = 'ljet4'
    rootPTH = f'{tmp}/comandas/'
    sOutput = f'%|lp{printer}'
else:  # Windows
    opt = os.popen('wmic printer get name,default').read()
    printer = [line.split()[1] for line in opt.split('\n') if 'TRUE' in line][0]

    command = 'gswin32c.exe'
    sDevice = 'mswinpr2'
    rootPTH = f'C:/Users/isaqu/Downloads/'
    sOutput = f'"%printer%{printer}"'

while True:
    # set the folder path containing the PDF files to print
    files = [f for f in os.listdir(rootPTH) if f.lower().startswith('pedido#')]

    # set the gs options according to OS
    options = f'-dPrinted -dBATCH -dNOPAUSE -dQUIET -dNOSAFER -dNumCopies=1 -sDEVICE={sDevice} -sOutputFile={sOutput}'

    for file in files:
        # set full file path
        path = os.path.join(rootPTH, file)

        # set the Ghostscript command with necessary options
        gs_command = f'{command} {options} {path}'

        print(f'Printing {file} on {printer}...')

        if isMacOS:
            # Call Ghostscript using subprocess
            subprocess.call(gs_command)
        else:
            # execute the command silently in the background
            subprocess.Popen(gs_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        time.sleep(5)
        os.remove(path)
        time.sleep(2)
    time.sleep(1)