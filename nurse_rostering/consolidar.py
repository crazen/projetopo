"""consolidar.py - junta os resultados finais (Gurobi/AMPL, HiGHS, relaxacao linear e metaheuristicas v3) numa
tabela por instancia e gera as figuras dos documentos.

Entradas (nesta pasta):
  resultados_ampl_final.csv          Gurobi via AMPL, parametros padrao (rodar_final.run com CFG = 'padrao'), 300 s
  resultados_ampl_ajustado.csv       Gurobi via AMPL, parametros ajustados (CFG = 'ajustado'), 300 s  [opcional]
  resultados_highs_final.csv         mesmo modelo no HiGHS (exato.py), 300 s
  relaxacao_linear.csv               limite da relaxacao linear do modelo (relaxacao.py)
  resultados/v4_*.csv                GRASP, SA e Fix-and-Optimize da VERSAO 4 (estrategias novas: FINAL abaixo) e,
                                     na mesma maquina, as configuracoes da versao 3 (BASE), 300 s, 3 sementes
  resultados/v3_*.csv                execucoes da versao 3 no servidor anterior (so se faltar a v4)
  resultados/*_convergencia.json     historico (tempo, melhor custo) de cada execucao heuristica
  resultados_gurobi_longo.csv        Gurobi com 3600 s (rodar_gurobi_longo.py no PC)   [opcional]
Saidas:
  resultados_v4.csv                  todas as execucoes heuristicas usadas
  comparacao_final.csv               uma linha por instancia, todos os metodos
  ../entregas/fonte/fig_gap.png      custo / melhor valor publicado, por instancia e metodo
  ../entregas/fonte/fig_convergencia.png
"""
import glob, json, os
import pandas as pd
import logging
import matplotlib
matplotlib.use("Agg")
logging.getLogger("matplotlib.font_manager").setLevel(logging.ERROR)   # sem Times New Roman: usa DejaVu Serif
import matplotlib.pyplot as plt

AQUI = os.path.dirname(os.path.abspath(__file__))
RES = os.path.join(AQUI, "resultados")
FIG = os.path.join(AQUI, "..", "entregas", "fonte")
ORDEM = ["n030w4", "n040w4", "n050w4", "n060w4", "n030w8", "n040w8", "n050w8", "n060w8"]
METODOS = ["grasp", "sa", "fo"]
# Versao 4: configuracao final de cada metaheuristica, escolhida na calibracao (calibracao/v4, instancias FORA do
# conjunto final). Opcoes: din = penalidade dinamica, des = desempate por gravidade, amN = GRASP amostral.
FINAL = {"grasp": "grasp+am3+des", "sa": "sa+dinS", "fo": "fo+dinS"}
BASE = {"grasp": "grasp", "sa": "sa", "fo": "fo"}          # versao 3 (sem as estrategias novas), mesma maquina
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


def agregar(df):
    return df.groupby(["inst", "metodo"]).agg(medio=("custo", "mean"), melhor=("custo", "min"), dp=("custo", "std"),
                                              n=("semente", "nunique"), it=("iteracoes", "mean"),
                                              tmelhor=("tempo_melhor_s", "mean")).unstack()


def carregar():
    os.chdir(AQUI)
    ler = lambda pad: pd.concat([pd.read_csv(f) for f in sorted(glob.glob(os.path.join(RES, pad)))], ignore_index=True) \
        if glob.glob(os.path.join(RES, pad)) else pd.DataFrame(columns=["instancia", "metodo"])
    v4 = ler("v4_*.csv"); v3 = ler("v3_*.csv")
    for df in (v4, v3):
        if len(df):
            assert df.viavel.all(), "ha execucao inviavel"
            dup = df.duplicated(["instancia", "metodo", "semente"])
            assert not dup.any(), f"execucoes repetidas: {df[dup].values.tolist()}"
        df["inst"] = df.instancia.map(curto)
    usados = []
    origem = {}

    def pegar(metodo, papel):
        """Execucoes de um metodo: da v4 (mesma maquina) se completas; senao, da v3 antiga."""
        a = v4[v4.metodo == metodo]
        if len(a) and set(a.inst) >= set(ORDEM):
            origem[papel] = "v4"; usados.append(a); return a
        b = v3[v3.metodo == metodo]
        if len(b):
            origem[papel] = "v3 (servidor anterior)"; usados.append(b); return b
        origem[papel] = "faltando"; return None

    hig = pd.read_csv("resultados_highs_final.csv").assign(inst=lambda d: d.instancia.map(curto)).set_index("inst")
    gur = ler_ampl("resultados_ampl_final.csv")
    pl = pd.read_csv("relaxacao_linear.csv").assign(inst=lambda d: d.instancia.map(curto)).set_index("inst")
    lit = pd.read_csv("referencias_literatura.csv").assign(inst=lambda d: d.instancia.map(curto))
    lit = lit[lit.instancia.isin(gur.instancia)].set_index("inst")
    t = pd.DataFrame(index=ORDEM)
    t["lb_lit"] = lit.lb_literatura; t["ub_lit"] = lit.ub_literatura
    t["N"] = [int(i[1:4]) for i in ORDEM]; t["sem"] = [int(i[-1]) for i in ORDEM]
    t["pl"] = pl.limite_pl; t["pl_sobre_ub"] = pl.pl_sobre_melhor
    t["gurobi"] = gur.custo; t["gurobi_lb"] = gur.limite_inferior.round(0); t["gurobi_gap"] = gur["gap_%"]
    t["gurobi_t"] = gur.tempo_s; t["gurobi_status"] = gur.status
    if os.path.exists("resultados_ampl_ajustado.csv"):
        aj = ler_ampl("resultados_ampl_ajustado.csv")
        t["gurobi_aj"] = aj.custo; t["gurobi_aj_lb"] = aj.limite_inferior.round(0); t["gurobi_aj_gap"] = aj["gap_%"]
        t["gurobi_aj_t"] = aj.tempo_s; t["gurobi_aj_status"] = aj.status
    if os.path.exists("resultados_gurobi_longo.csv"):          # Gurobi com 1 hora (mesmo metodo da Etapa 5)
        gl = pd.read_csv("resultados_gurobi_longo.csv")
        gl = gl[(gl.cfg == "puro") & (gl.threads == 1) & (gl.tempo_limite_s == 3600)]
        gl = gl.assign(inst=gl.instancia.map(curto)).drop_duplicates("inst", keep="last").set_index("inst")
        t["gurobi_1h"] = gl.custo; t["gurobi_1h_lb"] = gl.limite_inferior.round(0); t["gurobi_1h_gap"] = gl["gap_%"]
        t["gurobi_1h_t"] = gl.tempo_s; t["gurobi_1h_otimo"] = gl.otimo_provado
    t["highs"] = hig.custo; t["highs_lb"] = hig.limite_inferior
    nsem = []
    for papel, mapa in (("", FINAL), ("base_", BASE)):
        for m in METODOS:
            df = pegar(mapa[m], papel + m)
            if df is None:
                continue
            agg = agregar(df)
            pre = f"{m}_" if papel == "" else f"{m}_v3_"
            t[pre + "medio"] = agg[("medio", mapa[m])]; t[pre + "melhor"] = agg[("melhor", mapa[m])]
            t[pre + "it"] = agg[("it", mapa[m])]; t[pre + "dp"] = agg[("dp", mapa[m])].round(1)
            t[pre + "tmelhor"] = agg[("tmelhor", mapa[m])].round(0)
            nsem.append(int(agg[("n", mapa[m])].min()))
    t["n_sem"] = min(nsem) if nsem else 0
    cols = ["gurobi", "highs"] + [c for c in ("gurobi_aj", "gurobi_1h") if c in t] + \
           [c for m in METODOS for c in (f"{m}_medio", f"{m}_melhor", f"{m}_v3_medio", f"{m}_v3_melhor") if c in t]
    for m in cols:
        t[f"dev_{m}"] = (100 * (t[m] - t.ub_lit) / t.ub_lit).round(1)
    t.index.name = "instancia"
    t.to_csv("comparacao_final.csv")
    if usados:
        pd.concat(usados, ignore_index=True).to_csv("resultados_v4.csv", index=False)
    print("origem das execucoes:", origem)
    return t, pd.concat(usados, ignore_index=True) if usados else None


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
    for f in sorted(glob.glob(os.path.join(RES, "v3_*_convergencia.json"))) + \
             sorted(glob.glob(os.path.join(RES, "v4_*_convergencia.json"))):
        conv.update(json.load(open(f)))
    plt.rcParams["font.family"] = ["Times New Roman", "DejaVu Serif"]
    fig, ax = plt.subplots(figsize=(6.4, 3.2), dpi=200)
    fig.patch.set_facecolor("#fcfcfb"); estilo(ax)
    teto = 0; finais = []
    for m in METODOS:
        rot = ROTULO[m]
        k = next(k for k in conv if k.startswith(inst) and k.endswith(f"|{FINAL[m]}|1"))
        pts = [(t_, c) for t_, c in conv[k] if c != float("inf") and c < 10000]   # so o trecho viavel
        if not pts:
            continue
        xs = [p[0] for p in pts] + [limite]; ys = [p[1] for p in pts] + [pts[-1][1]]
        ax.step(xs, ys, where="post", color=COR[rot], linewidth=2, label=rot)
        finais.append((ys[-1], rot))
        teto = max(teto, ys[min(len(ys) - 1, max(1, len(ys) // 8))])
    lit = pd.read_csv(os.path.join(AQUI, "referencias_literatura.csv"))
    ub = lit[lit.instancia.str.startswith(inst)].ub_literatura.iloc[0]
    gur = pd.read_csv(os.path.join(AQUI, "resultados_ampl_final.csv"), sep=";")
    g = gur[gur.instancia.str.startswith(inst)].custo.iloc[0]
    ax.axhline(ub, color=TXT2, linewidth=0.8, linestyle=(0, (3, 2)))
    ax.annotate(f"melhor publicado {ub:.0f}", (5, ub), xytext=(0, 3), textcoords="offset points", fontsize=8.5, color=TXT2)
    ax.set_ylim(ub * 0.95, min(teto * 1.05, g * 1.05))
    # rotulos do valor final, afastados para nao se sobreporem
    y0, y1 = ax.get_ylim(); sep = 0.045 * (y1 - y0); ult = None
    for y, rot in sorted(finais):
        yl = y if ult is None else max(y, ult + sep); ult = yl
        ax.annotate(f"{rot}  {y:.0f}", (limite, y), xytext=(limite + 4, yl), textcoords="data",
                    va="center", fontsize=9, color=TXT, annotation_clip=False)
    ax.set_title(f"{inst} (semente 1). Gurobi em 300 s: {g:.0f}, fora da escala", loc="left", fontsize=9, color=TXT2)
    ax.set_xlim(0, limite); ax.set_xlabel("tempo (s)", color=TXT2, fontsize=9)
    ax.set_ylabel("melhor custo encontrado", color=TXT2, fontsize=9)
    ax.legend(loc="lower left", bbox_to_anchor=(0.01, 0.12), fontsize=8.5, frameon=True, facecolor="#fcfcfb",
              edgecolor=GRADE)
    fig.tight_layout(rect=(0, 0, 0.86, 1))
    fig.savefig(os.path.join(FIG, "fig_convergencia.png"), facecolor=fig.get_facecolor())
    plt.close(fig)


if __name__ == "__main__":
    t, v3 = carregar()
    pd.set_option("display.width", 250)
    cols = [c for c in ["ub_lit", "pl", "gurobi", "gurobi_1h"] + [f"{m}{v}_medio" for m in METODOS for v in ("_v3", "")]
            if c in t]
    print(t[cols].round(0).to_string())
    print("distancia media ao melhor publicado (%):",
          {c: round(t[f"dev_{c}"].mean(), 1) for c in cols[2:] if f"dev_{c}" in t})
    fig_gap(t)
    fig_convergencia()
    print("figuras em", os.path.abspath(FIG))
