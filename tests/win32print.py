import win32api as api
import win32print as wp
from glob import glob


PDF_FILE = 'H:\comanda.pdf'
PDF_DIR = "C:/temp/comandas/**/*"
PRINTER = wp.OpenPrinter('RICOH_BW')

# JOB = wp.StartDocPrinter(PRINTER, 1, ("comanda", None, "RAW"))
# wp.StartPagePrinter(PRINTER)
# wp.WritePrinter(PRINTER, PDF_FILE)
# wp.EndPagePrinter(PRINTER)

# api.ShellExecute(0, 'print', PDF_FILE, '.', '/manualstoprint', 0)

# wp.ClosePrinter(PRINTER)

for f in glob(PDF_DIR, recursive=True):
    api.ShellExecute(0, "print", f, ".",  "/manualstoprint",  0)

input("press any key to exit")