"""organizar_dados.py - extrai os zips do INRC-II numa pasta unica, com uma subpasta por dataset.

Aceita qualquer combinacao dos pacotes do site do INRC-II (versao JSON):
  testdatasets_json.zip, datasets_json.zip (competicao), hidden-JSON.zip, late-extended-dataset.zip
Cada arquivo Sc-/H0-/WD-<dataset>... vai para <saida>/<dataset>/. As pastas de solucao de referencia
(Solution_H_*) dos conjuntos de teste sao mantidas. Arquivos XML e TXT sao ignorados.

Uso:  python organizar_dados.py <saida> <zip1> [<zip2> ...]
Ex.:  python organizar_dados.py ../dados ../testdatasets_json.zip ../datasets_json.zip ../hidden-JSON.zip ../late-extended-dataset.zip
"""
import os, re, sys, zipfile

PADRAO = re.compile(r"^(?:Sc|H0|WD|Sol)-(n\d+w\d+)")


def organizar(saida, zips):
    contagem = {}
    for z in zips:
        with zipfile.ZipFile(z) as arq:
            for info in arq.infolist():
                partes = info.filename.split("/")
                nome = partes[-1]
                if info.is_dir() or not nome.endswith(".json"):
                    continue
                m = PADRAO.match(nome)
                if not m:
                    continue
                ds = m.group(1)
                sol = [p for p in partes[:-1] if p.startswith("Solution_")]
                destino = os.path.join(saida, ds, *(sol[-1:]), nome)
                os.makedirs(os.path.dirname(destino), exist_ok=True)
                with open(destino, "wb") as f:
                    f.write(arq.read(info))
                contagem[ds] = contagem.get(ds, 0) + 1
    return contagem


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    c = organizar(sys.argv[1], sys.argv[2:])
    print(f"{len(c)} datasets em {sys.argv[1]}:", " ".join(sorted(c, key=lambda s: (int(s[1:4]), int(s.split('w')[1])))))
