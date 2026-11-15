"""consolidar.py - junta os resultados finais (Gurobi/AMPL, HiGHS e heuristicas v2) numa tabela por instancia
e gera as figuras dos documentos.

Entradas (nesta pasta):
  resultados_ampl_final.csv          Gurobi via AMPL (rodar_final.run), 300 s
  final_1..4.csv                     execucao anterior: so as linhas 'exato' (HiGHS) sao usadas
  v2_gs_*.csv, v2_lns_*.csv          GRASP (VND local no ILS), SA e LNS, 300 s, 2 sementes
  v2_*_convergencia.json             historico (tempo, melhor custo) de cada execucao heuristica
Saidas:
  resultados_v2.csv                  todas as execucoes heuristicas v2
  comparacao_final.csv               uma linha por instancia, todos os metodos
  ../entregas/fonte/fig_gap.png      custo / melhor valor publicado, por instancia e metodo
  ../entregas/fonte/fig_convergencia.png
"""
import glob, json, os
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(AQUI, "..", "entregas", "fonte")
ORDEM = ["n030w4", "n040w4", "n050w4", "n060w4", "n030w8", "n040w8", "n050w8", "n060w8"]
# paleta categorica de referencia (validada: adjacente CVD >= 9,1; contraste baixo compensado por rotulos)
COR = {"Gurobi": "#2a78d6", "GRASP": "#eb6834", "SA": "#1baf7a", "LNS": "#eda100"}
MARCA = {"Gurobi": "s", "GRASP": "o", "SA": "D", "LNS": "^"}
TXT, TXT2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"


def curto(nome):
    return nome.split("_")[0]


def carregar():
    os.chdir(AQUI)
    v2 = pd.concat([pd.read_csv(f) for f in sorted(glob.glob("v2_*.csv"))], ignore_index=True)
    v2.to_csv("resultados_v2.csv", index=False)
    assert v2.viavel.all(), "ha execucao inviavel"
    v2["inst"] = v2.instancia.map(curto)
    hig = pd.concat([pd.read_csv(f"final_{k}.csv") for k in range(1, 5)], ignore_index=True)
    hig = hig[hig.metodo == "exato"].assign(inst=lambda d: d.instancia.map(curto)).set_index("inst")
    gur = pd.read_csv("resultados_ampl_final.csv", sep=";")
    gur = gur.assign(inst=gur.instancia.map(curto)).set_index("inst")
    lit = v2.groupby("inst")[["enfermeiros", "semanas", "lb_literatura", "ub_literatura"]].first()
    agg = v2.groupby(["inst", "metodo"]).agg(medio=("custo", "mean"), melhor=("custo", "min"),
                                             it=("iteracoes", "mean")).unstack()
    t = pd.DataFrame(index=ORDEM)
    t["N"] = lit.enfermeiros; t["sem"] = lit.semanas
    t["lb_lit"] = lit.lb_literatura; t["ub_lit"] = lit.ub_literatura
    t["gurobi"] = gur.custo; t["gurobi_lb"] = gur.limite_inferior.round(0); t["gurobi_gap"] = gur["gap_%"]
    t["gurobi_t"] = gur.tempo_s; t["gurobi_status"] = gur.status
    t["highs"] = hig.custo; t["highs_lb"] = hig.limite_inferior
    for m in ["grasp", "sa", "lns"]:
        t[f"{m}_medio"] = agg[("medio", m)]; t[f"{m}_melhor"] = agg[("melhor", m)]; t[f"{m}_it"] = agg[("it", m)]
    for m in ["gurobi", "highs", "grasp_medio", "sa_medio", "lns_medio", "grasp_melhor", "sa_melhor", "lns_melhor"]:
        t[f"dev_{m}"] = (100 * (t[m] - t.ub_lit) / t.ub_lit).round(1)
    t.index.name = "instancia"
    t.to_csv("comparacao_final.csv")
    return t, v2


def estilo(ax):
    ax.set_facecolor("#fcfcfb")
    for s in ["top", "right"]:
        ax.spines[s].set_visible(False)
    for s in ["left", "bottom"]:
        ax.spines[s].set_color(TXT2); ax.spines[s].set_linewidth(0.6)
    ax.tick_params(colors=TXT2, labelsize=9, width=0.6)
    ax.grid(True, color=GRADE, linewidth=0.6); ax.set_axisbelow(True)


def fig_gap(t):
    """Dot plot: custo / melhor valor publicado (escala log), uma linha por instancia, um marcador por metodo."""
    plt.rcParams["font.family"] = "Times New Roman"
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
    fig.patch.set_facecolor("#fcfcfb"); estilo(ax); ax.grid(axis="y", visible=False)
    cols = {"Gurobi": "gurobi", "GRASP": "grasp_medio", "SA": "sa_medio", "LNS": "lns_medio"}
    ys = range(len(ORDEM))[::-1]
    for i, (rot, c) in enumerate(cols.items()):
        r = t[c] / t.ub_lit
        ax.scatter(r, list(ys), s=34, marker=MARCA[rot], color=COR[rot], edgecolor="#fcfcfb", linewidth=0.8,
                   zorder=3, label=rot)
    ax.set_xscale("log")
    ax.set_xticks([1, 1.25, 1.5, 2, 3, 5, 10, 13]); ax.set_xticklabels(["1", "1,25", "1,5", "2", "3", "5", "10", "13"])
    ax.minorticks_off()
    ax.axvline(1, color=TXT2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.set_yticks(list(ys)); ax.set_yticklabels(ORDEM, color=TXT)
    ax.set_xlabel("custo da escala ÷ melhor valor publicado (escala log; 1 = melhor conhecido)", color=TXT2, fontsize=9)
    ax.legend(loc="lower right", fontsize=8.5, frameon=True, facecolor="#fcfcfb", edgecolor=GRADE, ncol=4,
              bbox_to_anchor=(1.0, 1.0), borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_gap.png"), facecolor=fig.get_facecolor())
    plt.close(fig)


def fig_convergencia(inst="n040w8"):
    """Melhor custo ao longo do tempo (media das 2 sementes nao faz sentido em degraus: mostra a semente 1)."""
    conv = {}
    for f in glob.glob(os.path.join(AQUI, "v2_*_convergencia.json")):
        conv.update(json.load(open(f)))
    plt.rcParams["font.family"] = "Times New Roman"
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
    fig.patch.set_facecolor("#fcfcfb"); estilo(ax)
    teto = None
    for rot, m in [("GRASP", "grasp"), ("SA", "sa"), ("LNS", "lns")]:
        k = next(k for k in conv if k.startswith(inst) and f"|{m}|1" in k)
        pts = [(t_, c) for t_, c in conv[k] if c < 1e9 and c != float("inf")]
        pts = [(t_, c) for t_, c in pts if c < 10000 * 2]          # descarta o trecho inviavel inicial
        xs = [p[0] for p in pts] + [300]; ys = [p[1] for p in pts] + [pts[-1][1]]
        ax.step(xs, ys, where="post", color=COR[rot], linewidth=2, label=rot)
        ax.annotate(f"{rot}  {ys[-1]:.0f}", (300, ys[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=9, color=TXT)
        teto = max(teto or 0, min(ys[:max(1, len(ys) // 6)]))
    gur = pd.read_csv(os.path.join(AQUI, "resultados_ampl_final.csv"), sep=";")
    g = gur[gur.instancia.str.startswith(inst)].custo.iloc[0]
    lit = pd.read_csv(os.path.join(AQUI, "referencias_literatura.csv"))
    ub = lit[lit.instancia.str.startswith(inst)].ub_literatura.iloc[0]
    ax.axhline(ub, color=TXT2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.annotate(f"melhor publicado {ub:.0f}", (5, ub), xytext=(0, 3), textcoords="offset points", fontsize=8.5, color=TXT2)
    ax.set_ylim(ub * 0.9, min(teto * 1.05, g * 1.05) if teto else None)
    ax.annotate(f"Gurobi (300 s): {g:.0f}, fora da escala", (150, ax.get_ylim()[1]), xytext=(0, -10),
                textcoords="offset points", fontsize=8.5, color=TXT2, ha="center")
    ax.set_xlim(0, 300); ax.set_xlabel("tempo (s)", color=TXT2, fontsize=9)
    ax.set_ylabel("melhor custo encontrado", color=TXT2, fontsize=9)
    ax.legend(loc="upper right", fontsize=8.5, frameon=True, facecolor="#fcfcfb", edgecolor=GRADE)
    fig.tight_layout(rect=(0, 0, 0.93, 1))
    fig.savefig(os.path.join(FIG, "fig_convergencia.png"), facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    t, v2 = carregar()
    pd.set_option("display.width", 250)
    print(t.drop(columns=["lb_lit"]).to_string())
    fig_gap(t)
    fig_convergencia()
    print("figuras em", os.path.abspath(FIG))
