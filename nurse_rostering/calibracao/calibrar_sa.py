"""calibrar_sa.py - calibracao dos parametros do SA (T0, Tf) em instancias que NAO estao no conjunto final.

Instancias de calibracao: 4 instancias da literatura (Legrain e Omer, 2023) diferentes das 8 do conjunto final,
para nao ajustar os parametros nas mesmas instancias usadas na comparacao.
Uso:  python calibracao/calibrar_sa.py ../dados <limite_s> <processos>
Saida: calibracao/calibracao_sa.csv  (uma linha por execucao)
"""
import csv, itertools, os, sys
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from inrc2 import load_instance, parse_spec

INST = ["n030w4 1 6,7,5,3", "n040w4 2 6,1,0,6", "n030w8 1 6,7,5,3,5,6,2,9", "n050w8 1 9,7,5,3,8,8,3,1"]
T0S = [20, 40, 100]
TFS = [0.5, 2, 5]


def rodar(args):
    dados, spec, T0, Tf, limite = args
    from sa import sa
    ds, h, wd = parse_spec(spec)
    inst = load_instance(os.path.join(dados, ds), h, wd)
    r = sa(inst, limite=limite, semente=1, T0=T0, Tf=Tf, verbose=False)
    return dict(instancia=inst.name, T0=T0, Tf=Tf, custo=r["custo"], viavel=r["viavel"], movimentos=r["iteracoes"])


if __name__ == "__main__":
    dados, limite, proc = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    tarefas = [(dados, s, T0, Tf, limite) for s, T0, Tf in itertools.product(INST, T0S, TFS)]
    saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "calibracao_sa.csv")
    with Pool(proc) as p, open(saida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["instancia", "T0", "Tf", "custo", "viavel", "movimentos"]); w.writeheader()
        for r in p.imap_unordered(rodar, tarefas):
            w.writerow(r); f.flush(); print(r, flush=True)
