"""relaxacao.py - limite da relaxacao linear (PL) do modelo nurse.mod em cada instancia.

Resolve o modelo com as variaveis binarias relaxadas para 0 <= x <= 1 (HiGHS) e compara o valor com o melhor
valor publicado. Esse valor e uma propriedade da FORMULACAO (nao do solver): mostra o quanto o PL "enxerga"
do custo real. Quanto mais longe do otimo, mais o branch-and-bound precisa trabalhar para provar a otimalidade.

Uso:   python relaxacao.py ../dados instancias_final.txt
Saida: relaxacao_linear.csv  (instancia, colunas, linhas, limite_pl, melhor_publicado, pl_sobre_melhor)
"""
import csv, os, sys, time
from inrc2 import load_instance, parse_spec
from exato import ModeloPLI

AQUI = os.path.dirname(os.path.abspath(__file__))

if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    lit = {r["instancia"]: float(r["ub_literatura"]) for r in csv.DictReader(open(os.path.join(AQUI, "referencias_literatura.csv")))}
    with open(os.path.join(AQUI, "relaxacao_linear.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instancia", "colunas", "linhas", "limite_pl", "melhor_publicado", "pl_sobre_melhor", "tempo_s"])
        for linha in open(sys.argv[2]):
            linha = linha.split("#")[0].strip()
            if not linha:
                continue
            ds, h, wd = parse_spec(linha)
            inst = load_instance(os.path.join(sys.argv[1], ds), h, wd)
            t = time.time()
            m = ModeloPLI(inst)
            m.h.setOptionValue("solve_relaxation", True)
            m.h.run()
            pl = m.h.getInfo().objective_function_value
            ub = lit.get(inst.name)
            w.writerow([inst.name, m.ncols, m.nrows, round(pl, 1), ub or "", round(pl / ub, 3) if ub else "",
                        round(time.time() - t, 1)])
            f.flush()
            print(f"{inst.name:32s} PL={pl:8.1f}  melhor publicado={ub}  PL/melhor={pl / ub:.2f}" if ub else inst.name, flush=True)
