import subprocess
import win32print

FILE = r'C:/temp/comandas/print.png'

# Get the default printer name
PRINTER = win32print.GetDefaultPrinter()

# Set up the print command
CMD = f'mspaint /pt "{FILE}" "{PRINTER}"'

subprocess.run(CMD, shell=True)
