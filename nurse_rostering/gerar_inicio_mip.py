"""gerar_inicio_mip.py - gera a escala inicial (MIP start) do Gurobi com a matheuristica SA + F&O.

Para cada instancia, roda fo.py por <tempo> s e grava inicio_mip/<instancia>.run com comandos AMPL
'let x[...] := 1;' (as demais variaveis x ficam 0). rodar_gurobi_longo.py le esse arquivo, completa as
outras variaveis (fixa x e resolve) e entrega a escala ao Gurobi como solucao inicial.

Uso:  python gerar_inicio_mip.py ../dados <tempo_s> <processos> [lista.txt ...]
      sem lista: instancias de teste (com solucao de referencia) + instancias_final.txt
"""
import os, sys
from multiprocessing import Pool
from inrc2 import load_instance, parse_spec, list_reference_instances, evaluate

AQUI = os.path.dirname(os.path.abspath(__file__))


def specs(dados, listas):
    out = []
    if not listas:
        for ds in ("n005w4", "n012w8", "n021w4"):
            for h, wd, _ in list_reference_instances(os.path.join(dados, ds)):
                out.append(f"{ds} {h} {','.join(map(str, wd))}")
        listas = [os.path.join(AQUI, "instancias_final.txt")]
    for arq in listas:
        for l in open(arq):
            l = l.split("#")[0].strip()
            if l:
                out.append(l)
    return out


def rodar(args):
    dados, spec, tempo = args
    from fo import fo
    ds, h, wd = parse_spec(spec)
    inst = load_instance(os.path.join(dados, ds), h, wd)
    r = fo(inst, limite=tempo, semente=1, verbose=False)
    q = lambda x: "'" + str(x).replace("'", "''") + "'"
    linhas = [f"# escala inicial (SA + F&O, {tempo:.0f} s): custo = {r['custo']}, viavel = {r['viavel']}"]
    for n in range(inst.N):
        for d in range(inst.D):
            a = r["sched"][n][d]
            if a is not None:
                s, k = a
                linhas.append(f"let x[{q(inst.nurses[n])},{d},{q(inst.shifts[s])},{q(inst.skills[k])}] := 1;")
    open(os.path.join(AQUI, "inicio_mip", inst.name + ".run"), "w").write("\n".join(linhas) + "\n")
    return inst.name, r["custo"], r["viavel"]


if __name__ == "__main__":
    dados, tempo, proc = sys.argv[1], float(sys.argv[2]), int(sys.argv[3])
    tarefas = [(dados, s, tempo) for s in specs(dados, sys.argv[4:])]
    with Pool(proc) as p:
        for nome, custo, viavel in p.imap_unordered(rodar, tarefas):
            print(f"{nome:32s} custo={custo} viavel={viavel}", flush=True)
