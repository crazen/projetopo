"""analisar_logs_gurobi.py - le os logs completos do Gurobi (logs_gurobi/*.log, gerados por rodar_gurobi_longo.py) e
extrai a melhor escala (incumbente) e o limite inferior em varios instantes da MESMA execucao.

Por que funciona: o Gurobi e deterministico (mesmos parametros, 1 thread). Uma execucao de 3600 s passa pelos mesmos
estados que execucoes de 300, 900 ou 1800 s, ate o instante em que elas parariam. Entao o log de 3600 s ja diz o
resultado que teriamos com cada limite menor, sem rodar de novo.

Cuidado: o valor do incumbente no log e o objetivo do modelo. Quando o solver para por tempo, ele pode ser um pouco
MAIOR que o custo real da escala (variaveis de penalidade nao apertadas). O custo real so e calculado no fim
(x fixado, em rodar_gurobi_longo.py). Por isso a coluna custo_real so e preenchida no instante final.

Cuidado 2: o caminho e o mesmo, mas a velocidade depende da maquina e da carga. As execucoes de 1 h de 21/11/2026
rodaram duas ao mesmo tempo no PC e andaram mais devagar que as da Etapa 5: a escala que a Etapa 5 tinha aos 300 s
aparece no log de 1 h entre 437 e 899 s. Ou seja, o valor "aos 300 s" deste log nao substitui o da Etapa 5.

Cuidado 3: o Gurobi so confere o relogio entre nos. Se a execucao passou mais de FOLGA s do limite, o instante do
limite vem do log (incumbente), e nao do resultado final.

Uso:   python analisar_logs_gurobi.py [--cortes 60,300,900,1800,3600]
Saida: resultados_gurobi_tempos.csv  (instancia, tempo_limite_s, t_s, incumbente, limite_inferior, gap_%, nos,
                                       custo_real, otimo_provado)
"""
import argparse, csv, glob, os, re

AQUI = os.path.dirname(os.path.abspath(__file__))
FOLGA = 60          # segundos alem do limite aceitos como "dentro do limite" (o Gurobi so confere o relogio entre nos)
NUM =re.compile(r"^-?\d+(\.\d+)?(e[+-]?\d+)?$")


def ler_log(caminho):
    """Lista de eventos (t, incumbente, limite, nos) em ordem, e o resumo final."""
    ev = []
    inc = None; lb = None; nos = 0; t = 0.0
    fim = {}
    for linha in open(caminho, encoding="utf-8", errors="replace"):
        s = linha.strip()
        m = re.match(r"Found heuristic solution: objective ([\d.e+-]+)", s)
        if m:
            v = float(m.group(1)); inc = v if inc is None else min(inc, v)
            ev.append((t, inc, lb, nos)); continue
        m = re.match(r"Root relaxation: objective ([\d.e+-]+), .* ([\d.]+) seconds", s)
        if m:
            lb = float(m.group(1)); t = max(t, float(m.group(2))); ev.append((t, inc, lb, nos)); continue
        m = re.match(r"Explored (\d+) nodes .* in ([\d.]+) seconds", s)
        if m:
            fim["nos"] = int(m.group(1)); fim["t"] = float(m.group(2)); continue
        m = re.match(r"Best objective ([\d.e+-]+|-), best bound ([\d.e+-]+|-), gap ([\d.e+-]+%|-)", s)
        if m:
            fim["inc"] = float(m.group(1)) if m.group(1) != "-" else None
            fim["lb"] = float(m.group(2)) if m.group(2) != "-" else None
            continue
        if s.startswith("Optimal solution found"):
            fim["otimo"] = True
        # linha da arvore de branch-and-bound: [H|*] Expl Unexpl ... Incumbent BestBd Gap It/Node Time
        tk = s.split()
        if len(tk) >= 6 and re.match(r"^\d+s$", tk[-1]):
            if tk[0] in ("H", "*"):
                tk = tk[1:]
            elif tk[0][0] in "H*" and tk[0][1:].isdigit():
                tk = [tk[0][1:]] + tk[1:]
            if not (tk[0].isdigit() and tk[1].isdigit()):
                continue
            try:
                tt = float(tk[-1][:-1]); gap = tk[-3]; bb = tk[-4]; ic = tk[-5]
                if not (gap.endswith("%") or gap == "-"):
                    continue
                t = tt; nos = int(tk[0])
                if NUM.match(bb):
                    lb = float(bb)
                if NUM.match(ic):
                    inc = float(ic)
                ev.append((t, inc, lb, nos))
            except (ValueError, IndexError):
                continue
            continue
        # linhas do simplex do no raiz: "Iteration Objective Primal Inf. Dual Inf. Time" -> so o tempo
        if len(tk) >= 5 and tk[0].isdigit() and re.match(r"^\d+s$", tk[-1]):
            t = max(t, float(tk[-1][:-1]))
    return ev, fim


def no_instante(ev, fim, corte):
    """Estado no instante 'corte' (o ultimo evento ate ele); se a execucao terminou antes, o estado final."""
    if fim.get("t") is not None and fim["t"] <= corte:
        return fim["t"], fim.get("inc"), fim.get("lb"), fim.get("nos"), True
    est = None
    for e in ev:
        if e[0] <= corte:
            est = e
        else:
            break
    if est is None:
        return corte, None, None, 0, False
    return corte, est[1], est[2], est[3], False


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--cortes", default="60,300,900,1800,3600")
    a = ap.parse_args()
    cortes = [float(x) for x in a.cortes.split(",")]
    reais = {}
    for arq in glob.glob(os.path.join(AQUI, "resultados_gurobi_longo*.csv")):
        for r in csv.DictReader(open(arq)):
            reais[os.path.basename(r["log"])] = r
    linhas = []
    for log in sorted(glob.glob(os.path.join(AQUI, "logs_gurobi", "*_puro_*s_1t.log"))):
        nome = os.path.basename(log)
        m = re.match(r"(.+)_puro_(\d+)s_1t\.log", nome)
        inst, lim = m.group(1), float(m.group(2))
        r = reais.get(nome)
        if r is None:
            continue                                     # execucao ainda em andamento
        ev, fim = ler_log(log)
        # o Gurobi so confere o relogio entre nos: se passou mais de FOLGA s do limite, o resultado final nao vale
        # como "limite" (ex.: n050w8 parou aos 5218 s); nesse caso o instante do limite vem do log, como os demais
        passou = float(r["tempo_s"]) > lim + FOLGA
        for c in [x for x in cortes if x <= lim]:
            t, inc, lb, nos, acabou = no_instante(ev, fim, c)
            final = acabou or (c == lim and not passou)
            custo = r["custo"] if final else ""
            ub = float(custo) if custo not in ("", None) else inc
            gap = round(100 * (ub - lb) / ub, 2) if ub and lb is not None else ""
            linhas.append(dict(instancia=inst, tempo_limite_s=f"{lim:g}", t_s=f"{c:g}",
                               incumbente=f"{inc:.0f}" if inc is not None else "",
                               limite_inferior=f"{lb:.1f}" if lb is not None else "", **{"gap_%": gap},
                               nos=nos if nos is not None else "", custo_real=custo,
                               otimo_provado=bool(final and r["otimo_provado"] == "True"),
                               tempo_total_s=r["tempo_s"]))
            if acabou:
                break
    saida = os.path.join(AQUI, "resultados_gurobi_tempos.csv")
    campos = ["instancia", "tempo_limite_s", "t_s", "incumbente", "limite_inferior", "gap_%", "nos", "custo_real",
              "otimo_provado", "tempo_total_s"]
    with open(saida, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos); w.writeheader(); w.writerows(linhas)
    for l in linhas:
        print(l)
    print("->", saida)


if __name__ == "__main__":
    main()
