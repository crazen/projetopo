"""consolidar.py - junta os resultados finais (Gurobi/AMPL, HiGHS, relaxacao linear e metaheuristicas v3) numa
tabela por instancia e gera as figuras dos documentos.

Entradas (nesta pasta):
  resultados_ampl_final.csv          Gurobi via AMPL, parametros padrao (rodar_final.run com CFG = 'padrao'), 300 s
  resultados_ampl_ajustado.csv       Gurobi via AMPL, parametros ajustados (CFG = 'ajustado'), 300 s  [opcional]
  resultados_highs_final.csv         mesmo modelo no HiGHS (exato.py), 300 s
  relaxacao_linear.csv               limite da relaxacao linear do modelo (relaxacao.py)
  resultados/v3_*.csv                GRASP, SA e Fix-and-Optimize, 300 s, varias sementes (rodar_experimentos.py)
  resultados/v3_*_convergencia.json  historico (tempo, melhor custo) de cada execucao heuristica
Saidas:
  resultados_v3.csv                  todas as execucoes heuristicas
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
RES = os.path.join(AQUI, "resultados")
FIG = os.path.join(AQUI, "..", "entregas", "fonte")
ORDEM = ["n030w4", "n040w4", "n050w4", "n060w4", "n030w8", "n040w8", "n050w8", "n060w8"]
METODOS = ["grasp", "sa", "fo"]
ROTULO = {"gurobi": "Gurobi", "grasp": "GRASP", "sa": "SA", "fo": "SA+F&O"}
# paleta categorica de referencia (validada: adjacente CVD >= 9,1; contraste baixo compensado por rotulos)
COR = {"Gurobi": "#2a78d6", "GRASP": "#eb6834", "SA": "#1baf7a", "SA+F&O": "#eda100"}
MARCA = {"Gurobi": "s", "GRASP": "o", "SA": "D", "SA+F&O": "^"}
TXT, TXT2, GRADE = "#0b0b0b", "#52514e", "#e4e3df"


def curto(nome):
    return nome.split("_")[0]


def ler_ampl(arq):
    g = pd.read_csv(os.path.join(AQUI, arq), sep=";")
    return g.assign(inst=g.instancia.map(curto)).set_index("inst")


def carregar():
    os.chdir(AQUI)
    v3 = pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(RES, "v3_*.csv")))], ignore_index=True)
    v3.to_csv("resultados_v3.csv", index=False)
    assert v3.viavel.all(), "ha execucao inviavel"
    dup = v3.duplicated(["instancia", "metodo", "semente"])
    assert not dup.any(), f"execucoes repetidas (mesma instancia, metodo e semente): {v3[dup].values.tolist()}"
    v3["inst"] = v3.instancia.map(curto)
    hig = pd.read_csv("resultados_highs_final.csv").assign(inst=lambda d: d.instancia.map(curto)).set_index("inst")
    gur = ler_ampl("resultados_ampl_final.csv")
    pl = pd.read_csv("relaxacao_linear.csv").assign(inst=lambda d: d.instancia.map(curto)).set_index("inst")
    lit = v3.groupby("inst")[["enfermeiros", "semanas", "lb_literatura", "ub_literatura"]].first()
    agg = v3.groupby(["inst", "metodo"]).agg(medio=("custo", "mean"), melhor=("custo", "min"),
                                             dp=("custo", "std"), n=("semente", "nunique"),
                                             it=("iteracoes", "mean"), tmelhor=("tempo_melhor_s", "mean")).unstack()
    t = pd.DataFrame(index=ORDEM)
    t["N"] = lit.enfermeiros; t["sem"] = lit.semanas
    t["lb_lit"] = lit.lb_literatura; t["ub_lit"] = lit.ub_literatura
    t["pl"] = pl.limite_pl; t["pl_sobre_ub"] = pl.pl_sobre_melhor
    t["gurobi"] = gur.custo; t["gurobi_lb"] = gur.limite_inferior.round(0); t["gurobi_gap"] = gur["gap_%"]
    t["gurobi_t"] = gur.tempo_s; t["gurobi_status"] = gur.status
    if os.path.exists("resultados_ampl_ajustado.csv"):
        aj = ler_ampl("resultados_ampl_ajustado.csv")
        t["gurobi_aj"] = aj.custo; t["gurobi_aj_lb"] = aj.limite_inferior.round(0); t["gurobi_aj_gap"] = aj["gap_%"]
        t["gurobi_aj_t"] = aj.tempo_s; t["gurobi_aj_status"] = aj.status
    t["highs"] = hig.custo; t["highs_lb"] = hig.limite_inferior
    for m in METODOS:
        t[f"{m}_medio"] = agg[("medio", m)]; t[f"{m}_melhor"] = agg[("melhor", m)]; t[f"{m}_it"] = agg[("it", m)]
        t[f"{m}_dp"] = agg[("dp", m)].round(1); t[f"{m}_tmelhor"] = agg[("tmelhor", m)].round(0)
    t["n_sem"] = int(agg["n"].min().min())              # sementes por (instancia, metodo); o minimo, por seguranca
    cols = ["gurobi", "highs"] + (["gurobi_aj"] if "gurobi_aj" in t else []) + \
           [f"{m}_{q}" for m in METODOS for q in ("medio", "melhor")]
    for m in cols:
        t[f"dev_{m}"] = (100 * (t[m] - t.ub_lit) / t.ub_lit).round(1)
    t.index.name = "instancia"
    t.to_csv("comparacao_final.csv")
    return t, v3


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
    plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Serif"]
    fig, ax = plt.subplots(figsize=(6.4, 3.6), dpi=200)
    fig.patch.set_facecolor("#fcfcfb"); estilo(ax); ax.grid(axis="y", visible=False)
    cols = {"Gurobi": "gurobi", "GRASP": "grasp_medio", "SA": "sa_medio", "SA+F&O": "fo_medio"}
    ys = range(len(ORDEM))[::-1]
    for rot, c in cols.items():
        r = t[c] / t.ub_lit
        ax.scatter(r, list(ys), s=34, marker=MARCA[rot], color=COR[rot], edgecolor="#fcfcfb", linewidth=0.8,
                   zorder=3, label=rot)
    ax.set_xscale("log")
    xmax = float((t[list(cols.values())].max(axis=1) / t.ub_lit).max())
    ticks = [x for x in [1, 1.1, 1.25, 1.5, 2, 3, 5, 10, 13] if x <= xmax * 1.05]
    ax.set_xticks(ticks); ax.set_xticklabels([f"{x:g}".replace(".", ",") for x in ticks])
    ax.minorticks_off()
    ax.axvline(1, color=TXT2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.set_yticks(list(ys)); ax.set_yticklabels(ORDEM, color=TXT)
    ax.set_xlabel("custo da escala ÷ melhor valor publicado (escala log; 1 = melhor conhecido)", color=TXT2, fontsize=9)
    ax.legend(loc="lower right", fontsize=8.5, frameon=True, facecolor="#fcfcfb", edgecolor=GRADE, ncol=4,
              bbox_to_anchor=(1.0, 1.0), borderaxespad=0.2)
    fig.tight_layout()
    fig.savefig(os.path.join(FIG, "fig_gap.png"), facecolor=fig.get_facecolor())
    plt.close(fig)


def fig_convergencia(inst="n040w8", limite=300):
    """Melhor custo ao longo do tempo, semente 1 de cada metodo."""
    conv = {}
    for f in glob.glob(os.path.join(RES, "v3_*_convergencia.json")):
        conv.update(json.load(open(f)))
    plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Serif"]
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
    fig.patch.set_facecolor("#fcfcfb"); estilo(ax)
    teto = 0
    for m in METODOS:
        rot = ROTULO[m]
        k = next(k for k in conv if k.startswith(inst) and k.endswith(f"|{m}|1"))
        pts = [(t_, c) for t_, c in conv[k] if c != float("inf") and c < 10000]   # so o trecho viavel
        xs = [p[0] for p in pts] + [limite]; ys = [p[1] for p in pts] + [pts[-1][1]]
        ax.step(xs, ys, where="post", color=COR[rot], linewidth=2, label=rot)
        ax.annotate(f"{rot}  {ys[-1]:.0f}", (limite, ys[-1]), xytext=(4, 0), textcoords="offset points",
                    va="center", fontsize=9, color=TXT)
        teto = max(teto, ys[min(len(ys) - 1, max(1, len(ys) // 8))])
    lit = pd.read_csv(os.path.join(AQUI, "referencias_literatura.csv"))
    ub = lit[lit.instancia.str.startswith(inst)].ub_literatura.iloc[0]
    gur = pd.read_csv(os.path.join(AQUI, "resultados_ampl_final.csv"), sep=";")
    g = gur[gur.instancia.str.startswith(inst)].custo.iloc[0]
    ax.axhline(ub, color=TXT2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.annotate(f"melhor publicado {ub:.0f}", (5, ub), xytext=(0, 3), textcoords="offset points", fontsize=8.5, color=TXT2)
    ax.set_ylim(ub * 0.95, min(teto * 1.05, g * 1.05))
    ax.annotate(f"Gurobi (300 s): {g:.0f}, fora da escala", (limite / 2, ax.get_ylim()[1]), xytext=(0, -10),
                textcoords="offset points", fontsize=8.5, color=TXT2, ha="center")
    ax.set_xlim(0, limite); ax.set_xlabel("tempo (s)", color=TXT2, fontsize=9)
    ax.set_ylabel("melhor custo encontrado", color=TXT2, fontsize=9)
    ax.legend(loc="upper right", fontsize=8.5, frameon=True, facecolor="#fcfcfb", edgecolor=GRADE)
    fig.tight_layout(rect=(0, 0, 0.9, 1))
    fig.savefig(os.path.join(FIG, "fig_convergencia.png"), facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    t, v3 = carregar()
    pd.set_option("display.width", 250)
    print(t[["N", "sem", "ub_lit", "pl", "gurobi", "highs"] + [f"{m}_medio" for m in METODOS]
            + [f"dev_{m}_medio" for m in METODOS]].to_string())
    print("distancia media ao melhor publicado (%):",
          {m: round(t[f"dev_{m}"].mean(), 1) for m in ["gurobi", "highs"] + [f"{x}_medio" for x in METODOS]})
    fig_gap(t)
    fig_convergencia()
    print("figuras em", os.path.abspath(FIG))
