import subprocess

pdf_file = 'H:\comanda.pdf'
acrobat = 'C:\Program Files (x86)\Adobe\Acrobat Reader DC\Reader\AcroRd32.exe'

cmd = '"{}" /n /o /t "{}" "{}"'.format(acrobat, pdf_file, 'RICOH_BW')

subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)