"""tamanho_modelos.py - estatisticas das instancias (demanda, pedidos, habilidades) e tamanho do modelo PLI
(linhas/colunas do nurse.mod traduzido). Gera tamanho_modelos.json, usado por entregas/fonte/preencher_tabelas.py."""
import sys, collections, json
sys.path.insert(0, ".")
from inrc2 import load_instance, parse_spec
from exato import ModeloPLI
specs = [l.split("#")[0].strip() for l in open("instancias_final.txt")]
specs = [s for s in specs if s] + ["n005w4 0 1,2,3,3", "n012w8 0 3,5,0,2,0,4,5,2", "n021w4 0 5,4,1,2"]
out = []
for sp in specs:
    ds, h, wd = parse_spec(sp)
    i = load_instance("../dados/" + ds, h, wd)
    contratos = collections.Counter()
    sc = json.load(open(f"../dados/{ds}/Sc-{ds}.json"))
    for n in sc["nurses"]: contratos[n["contract"]] += 1
    nsk = collections.Counter(len(s) for s in i.nurse_skills)
    dmin = sum(i.dmin[d][s][k] for d in range(i.D) for s in range(len(i.shifts)) for k in range(len(i.skills)))
    dopt = sum(i.dopt[d][s][k] for d in range(i.D) for s in range(len(i.shifts)) for k in range(len(i.skills)))
    xv = sum(len(i.nurse_skills[n]) for n in range(i.N)) * i.D * len(i.shifts)
    m = ModeloPLI(i)
    out.append(dict(inst=i.name, N=i.N, W=i.W, D=i.D, S=len(i.shifts), K=len(i.skills), contratos=dict(contratos),
                    habil=dict(nsk), dmin=dmin, dopt=dopt, pedidos=len(i.requests), x=xv, linhas=m.nrows, colunas=m.ncols,
                    forb=len(i.forbidden), capac=i.N * i.D))
    print(out[-1], flush=True)
json.dump(out, open("tamanho_modelos.json", "w"), indent=1)
