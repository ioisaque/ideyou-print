import subprocess
import os

import win32print
from PyPDF2 import PdfReader

PDF_FILE = r'C:/temp/comandas/Comanda#198.pdf'

# Get the default printer name
printer_name = win32print.GetDefaultPrinter()

# Open the PDF file and get the number of pages
with open(PDF_FILE, 'rb') as pdf_file:
    pdf_reader = PdfReader(pdf_file)
    num_pages = len(pdf_reader.pages)

# Set up the print command
print_command = f'"{os.environ["SystemRoot"]}\\system32\\rundll32.exe"' \
                f'"{os.environ["SystemRoot"]}\\system32\\shimgvw.dll",' \
                f' PrintTo /pt "{PDF_FILE}" "{printer_name}"'

# Print each page of the PDF file
for i in range(num_pages):
    subprocess.run(print_command, shell=True)