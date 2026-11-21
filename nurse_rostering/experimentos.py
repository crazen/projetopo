"""experimentos.py - roda os metodos (exato, GRASP, SA, matheuristica Fix-and-Optimize) em uma lista de instancias e grava
os resultados em CSV (uma linha por execucao, gravada assim que termina; nada se perde se o Colab cair).

Uso:
  python experimentos.py --dados dados --tempo 60
  python experimentos.py --dados dados --instancias instancias.txt --metodos exato,grasp,sa,fo --tempo 120 --sementes 3
  python experimentos.py --dados dados --metodos grasp+am3+des,sa+din+des,fo+din+des --tempo 300

Opcoes de cada metodo (versao 4, depois de '+'; sem opcoes = versao 3):
  din  penalidade dinamica das regras hard (SA e a fase SA do F&O); dinS = versao suave (viavel 80-98% do tempo)
  des  desempate por gravidade (GRASP, SA e a fase SA do F&O)
  amN  GRASP com construcao gulosa-amostral: o melhor de N candidatos sorteados (am10p = 10% dos candidatos)

Arquivo de instancias (uma por linha:  pasta  historico  semanas):
  n005w4 0 1,2,3,3
  n030w4 1 6,2,9,1          <- instancias da competicao (datasets_json.zip) funcionam do mesmo jeito
Sem --instancias, usa todas as instancias de teste que tem solucao de referencia (pastas Solution_H_*).

Colunas do CSV: instancia, enfermeiros, semanas, metodo, semente, custo, viavel, limite_inferior, gap_%,
                tempo_s, tempo_melhor_s, iteracoes, custo_referencia, lb_literatura, ub_literatura, gap_ub_lit_%
  tempo_melhor_s = instante em que a melhor escala da execucao foi encontrada (heuristicas)
  iteracoes      = exato: status do solver | GRASP: construcoes | SA: movimentos sorteados | F&O: subproblemas MIP
  gap_ub_lit_% = (custo - melhor solucao publicada) / melhor solucao publicada  (so para as 40 instancias
                 de referencias_literatura.csv)
"""
import argparse, csv, json, os, sys, time
from inrc2 import load_instance, parse_spec, list_reference_instances, load_solution_dir, evaluate, save_solution_json
from exato import resolver_exato
from grasp import grasp
from sa import sa
from fo import fo

CAMPOS = ["instancia", "enfermeiros", "semanas", "metodo", "semente", "custo", "viavel", "limite_inferior",
          "gap_%", "tempo_s", "tempo_melhor_s", "iteracoes", "custo_referencia", "lb_literatura", "ub_literatura", "gap_ub_lit_%"]
AQUI = os.path.dirname(os.path.abspath(__file__))


def carregar_literatura(arquivo=os.path.join(AQUI, "referencias_literatura.csv")):
    """Melhores limites publicados para a versao estatica (Legrain, Omer e Rosat, GERAD G-2023-02)."""
    if not os.path.exists(arquivo):
        return {}
    return {r["instancia"]: (float(r["lb_literatura"]), float(r["ub_literatura"])) for r in csv.DictReader(open(arquivo))}


def carregar_lista(dados, arquivo):
    """Lista de (pasta_dataset, h, semanas, pasta_solucao_referencia ou None)."""
    out = []
    if arquivo:
        for linha in open(arquivo):
            linha = linha.split("#")[0].strip()
            if linha:
                ds, h, wd = parse_spec(linha)
                base = os.path.join(dados, ds)
                ref = os.path.join(base, f"Solution_H_{h}-WD_{'-'.join(map(str, wd))}")
                out.append((base, h, wd, ref if os.path.isdir(ref) else None))
    else:
        for ds in sorted(os.listdir(dados)):
            base = os.path.join(dados, ds)
            if os.path.isdir(base):
                for h, wd, ref in list_reference_instances(base):
                    out.append((base, h, wd, ref))
    return out


def opcoes(metodo):
    """'sa+din+des' -> ('sa', {'penalidade': 'dinamica', 'desempate': True})."""
    base, *flags = metodo.split("+")
    kw = {}
    for f in flags:
        if f == "din" and base in ("sa", "fo"):
            kw["penalidade"] = "dinamica"
        elif f == "dinS" and base in ("sa", "fo"):          # oscilacao mais suave: fica viavel 80-98% do tempo
            kw.update(penalidade="dinamica", viab_baixa=0.8, viab_alta=0.98, lam_min=10.0)
        elif f == "cic" and base == "fo":                   # F&O em ciclos com SA reaquecido
            kw["ciclos"] = True
        elif f == "des" and base in ("grasp", "sa", "fo"):
            kw["desempate"] = True
        elif f.startswith("am") and base == "grasp":
            v = f[2:]
            kw["amostra"] = float(v[:-1]) / 100 if v.endswith("p") else int(v)
        else:
            sys.exit(f"opcao '{f}' invalida para o metodo {base}")
    return base, kw


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dados", required=True, help="pasta com os datasets (n005w4, n012w8, ...)")
    ap.add_argument("--instancias", help="arquivo com a lista de instancias (opcional)")
    ap.add_argument("--metodos", default="exato,grasp,sa,fo")
    ap.add_argument("--tempo", type=float, default=60, help="limite de tempo por execucao (s)")
    ap.add_argument("--sementes", type=int, default=1, help="execucoes com sementes diferentes (GRASP, SA e F&O)")
    ap.add_argument("--semente-inicial", type=int, default=1, help="primeira semente (as seguintes sao consecutivas)")
    ap.add_argument("--threads", type=int, default=1, help="threads do solver")
    ap.add_argument("--alpha", type=float, default=0.15, help="alpha da RCL do GRASP")
    ap.add_argument("--saida", default="resultados.csv")
    ap.add_argument("--solucoes", help="pasta para gravar as escalas encontradas (formato INRC-II)")
    a = ap.parse_args()

    lista = carregar_lista(a.dados, a.instancias)
    metodos = [m.strip() for m in a.metodos.split(",")]
    for m in metodos:
        if m != "exato":
            opcoes(m)
    novo = not os.path.exists(a.saida)
    if not novo and open(a.saida).readline().strip().split(",") != CAMPOS:
        sys.exit(f"{a.saida} foi gerado por outra versao (colunas diferentes): use outro nome em --saida")
    f = open(a.saida, "a", newline="")
    wr = csv.DictWriter(f, fieldnames=CAMPOS)
    if novo:
        wr.writeheader()
    conv = {}
    lit = carregar_literatura()
    print(f"{len(lista)} instancias x {metodos}, {a.tempo:.0f}s cada -> {a.saida}")
    for base, h, wd, ref in lista:
        inst = load_instance(base, h, wd)
        custo_ref = evaluate(inst, load_solution_dir(inst, ref))[2] if ref else ""
        for metodo in metodos:
            sementes = [0] if metodo == "exato" else range(a.semente_inicial, a.semente_inicial + a.sementes)
            for sem in sementes:
                print(f"\n== {inst.name}  {metodo}  semente={sem}", flush=True)
                lb = gap = it = ""
                if metodo == "exato":
                    r = resolver_exato(inst, limite=a.tempo, threads=a.threads)
                    lb = round(r["limite_inferior"], 1)
                    gap = round(100 * r["gap"], 1) if r["gap"] is not None else ""
                    it = r["status"]
                elif opcoes(metodo)[0] == "grasp":
                    r = grasp(inst, limite=a.tempo, alpha=a.alpha, semente=sem, verbose=False, **opcoes(metodo)[1])
                    it = r["iteracoes"]
                elif opcoes(metodo)[0] == "sa":
                    r = sa(inst, limite=a.tempo, semente=sem, verbose=False, **opcoes(metodo)[1])
                    it = r["iteracoes"]
                elif opcoes(metodo)[0] == "fo":
                    kw_fo = dict(opcoes(metodo)[1]); cic = kw_fo.pop("ciclos", False)
                    r = fo(inst, limite=a.tempo, semente=sem, threads=a.threads, verbose=False,
                           sa_kw=kw_fo, ciclos=cic)
                    it = r["iteracoes"]
                else:
                    sys.exit("metodo desconhecido: " + metodo)
                linha = {"instancia": inst.name, "enfermeiros": inst.N, "semanas": inst.W, "metodo": metodo,
                         "semente": sem, "custo": r["custo"] if r.get("custo") is not None else "",
                         "viavel": r["viavel"], "limite_inferior": lb, "gap_%": gap,
                         "tempo_s": round(r["tempo"], 1),
                         "tempo_melhor_s": r["historico"][-1][0] if r.get("historico") else "", "iteracoes": it, "custo_referencia": custo_ref,
                         "lb_literatura": "", "ub_literatura": "", "gap_ub_lit_%": ""}
                if inst.name in lit:
                    lb_l, ub_l = lit[inst.name]
                    linha.update(lb_literatura=lb_l, ub_literatura=ub_l)
                    if linha["custo"] != "":
                        linha["gap_ub_lit_%"] = round(100 * (linha["custo"] - ub_l) / ub_l, 1)
                wr.writerow(linha); f.flush()
                print("   ", {k: linha[k] for k in ("custo", "viavel", "limite_inferior", "gap_%", "tempo_s", "iteracoes")},
                      flush=True)
                if "historico" in r:
                    conv[f"{inst.name}|{metodo}|{sem}"] = r["historico"]
                if a.solucoes and r.get("sched"):
                    save_solution_json(inst, r["sched"], os.path.join(a.solucoes, f"{inst.name}_{metodo}_{sem}"))
    f.close()
    json.dump(conv, open(os.path.splitext(a.saida)[0] + "_convergencia.json", "w"))
    print(f"\nresultados em {a.saida}")


if __name__ == "__main__":
    main()
