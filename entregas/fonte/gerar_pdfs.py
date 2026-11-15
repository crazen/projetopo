"""gerar_pdfs.py - converte os .html desta pasta em PDF (Chrome headless) na pasta acima e confere o
numero de paginas de cada entrega contra o limite da disciplina.

Uso:  python gerar_pdfs.py [arquivo.html ...]      (sem argumentos: todos os .html)
"""
import glob, os, subprocess, sys
from pypdf import PdfReader

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.dirname(AQUI)
CHROME = [r"C:\Program Files\Google\Chrome\Application\chrome.exe",
          r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"]
LIMITE = {"etapa1": 2, "etapa2": 2, "etapa3": 2, "etapa4": 4, "etapa5": 2, "etapa6": 2, "etapa8": 12}

exe = next(c for c in CHROME if os.path.exists(c))
arquivos = sys.argv[1:] or sorted(glob.glob(os.path.join(AQUI, "*.html")))
for html in arquivos:
    html = os.path.abspath(html)
    nome = os.path.splitext(os.path.basename(html))[0]
    pdf = os.path.join(SAIDA, nome + ".pdf")
    subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", "--allow-file-access-from-files",
                    f"--print-to-pdf={pdf}", "file:///" + html.replace("\\", "/")],
                   check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    pags = len(PdfReader(pdf).pages)
    # a etapa 2 pode passar do limite so por causa das referencias (que nao contam)
    lim = LIMITE.get(nome.split("_")[0])
    aviso = "" if lim is None or pags <= lim else f"   <-- PASSOU DO LIMITE ({lim})"
    print(f"{nome + '.pdf':40s} {pags:2d} pagina(s){aviso}")
