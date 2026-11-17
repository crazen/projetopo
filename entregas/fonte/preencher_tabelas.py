"""preencher_tabelas.py - gera as linhas das tabelas de resultados a partir de comparacao_final.csv (e de
resultados_ampl_teste.csv, se existir) e as insere nos HTML das entregas, entre marcadores <!--X--> ... <!--/X-->.
Pode ser executado de novo: o conteudo entre os marcadores e substituido.
"""
import json, os, re
import pandas as pd

AQUI = os.path.dirname(os.path.abspath(__file__))
NR = os.path.join(AQUI, "..", "..", "nurse_rostering")
T = pd.read_csv(os.path.join(NR, "comparacao_final.csv"), index_col=0)
TAM = {s["inst"].split("_")[0]: s for s in json.load(open(os.path.join(AQUI, "..", "..", "nurse_rostering", "tamanho_modelos.json")))} \
    if os.path.exists(os.path.join(AQUI, "..", "..", "nurse_rostering", "tamanho_modelos.json")) else {}
OTIMO = {"n030w4", "n040w4", "n050w4", "n060w4", "n030w8"}


def f(x, casas=0):
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def pct(x):
    return ("+" if x >= 0 else "−") + f(abs(x), 1) + "%"


def inserir(arquivo, marca, html):
    p = os.path.join(AQUI, arquivo); t = open(p, encoding="utf-8").read()
    ini, fim = f"<!--{marca}-->", f"<!--/{marca}-->"
    if fim in t:
        t = re.sub(re.escape(ini) + ".*?" + re.escape(fim), lambda m: ini + "\n" + html + "\n" + fim, t, flags=re.S)
    elif ini in t:
        t = t.replace(ini, ini + "\n" + html + "\n" + fim)
    else:
        raise KeyError(f"marcador {marca} nao encontrado em {arquivo}")
    open(p, "w", encoding="utf-8").write(t)


def ub(i):
    return f(T.ub_lit[i]) + ("*" if i in OTIMO else "")


# ---------------------------------------------------------------- etapa 5: linhas do exato
linhas = []
for k, (i, r) in enumerate(T.iterrows()):
    tam = TAM.get(i)
    vr = f"{f(tam['colunas'] / 1000, 1)} / {f(tam['linhas'] / 1000, 1)} mil" if tam else "–"
    sep = ' class="sep"' if k == 4 else ""
    linhas.append(f'<tr{sep}><td class="l">{i}</td><td>{int(r.N)}</td><td>{int(r["sem"])}</td><td>{vr}</td>'
                  f'<td>{f(r.gurobi)}</td><td>{f(r.gurobi_lb)}</td><td>{f(r.pl)}</td><td>{f(r.gurobi_gap, 1)}%</td>'
                  f'<td>{f(r.gurobi_t)}</td><td>limite</td><td>{ub(i)}</td><td>{pct(r.dev_gurobi)}</td></tr>')
inserir("etapa5_resultados_metodo_exato.html", "LINHAS_EXATO", "\n".join(linhas))

# ---------------------------------------------------------------- etapa 6: comparacao
linhas = []
for k, (i, r) in enumerate(T.iterrows()):
    medios = {"gurobi": r.gurobi, "grasp": r.grasp_medio, "sa": r.sa_medio, "fo": r.fo_medio}
    best = min(medios, key=medios.get)
    b = lambda m, s: f"<b>{s}</b>" if m == best else s
    sep = ' class="sep"' if k == 4 else ""
    cel = [f'<td class="l">{i}</td><td>{ub(i)}</td>',
           f"<td>{b('gurobi', f(r.gurobi))}</td><td>{pct(r.dev_gurobi)}</td>"]
    for m in ["grasp", "sa", "fo"]:
        cel.append(f"<td>{b(m, f(r[m + '_medio'], 0))} ({f(r[m + '_melhor'])})</td><td>{pct(r['dev_' + m + '_medio'])}</td>")
    linhas.append(f"<tr{sep}>" + "".join(cel) + "</tr>")
inserir("etapa6_comparacao_exato_aproximado.html", "LINHAS_COMP", "\n".join(linhas))

vit = {"gurobi": 0, "grasp": 0, "sa": 0, "fo": 0}
for i, r in T.iterrows():
    medios = {"gurobi": r.gurobi, "grasp": r.grasp_medio, "sa": r.sa_medio, "fo": r.fo_medio}
    vit[min(medios, key=medios.get)] += 1
esforco = {
    "gurobi": "branch-and-bound; não provou ótimo em nenhuma",
    "grasp": f"{f(T.grasp_it.mean(), 0)} iterações (construção + VND) em média",
    "sa": f"{f(T.sa_it.mean() / 1e6, 0)} milhões de movimentos em média",
    "fo": f"{f(T.fo_it.mean(), 0)} subproblemas de PLI em média (após o SA)",
}
nomes = {"gurobi": "Exato (Gurobi)", "grasp": "GRASP", "sa": "Simulated Annealing", "fo": "SA + Fix-and-Optimize"}
dev = {"gurobi": T.dev_gurobi.mean(), "grasp": T.dev_grasp_medio.mean(), "sa": T.dev_sa_medio.mean(),
       "fo": T.dev_fo_medio.mean()}
tb = {m: f"{f(T[m + '_tmelhor'].mean())} s" for m in ["grasp", "sa", "fo"]}
tb["gurobi"] = "–"
linhas = [f'<tr><td class="l">{nomes[m]}</td><td>300 s</td><td>{tb[m]}</td><td>{pct(dev[m])}</td><td>{vit[m]} de 8</td>'
          f'<td class="l">{esforco[m]}</td></tr>' for m in ["gurobi", "grasp", "sa", "fo"]]
inserir("etapa6_comparacao_exato_aproximado.html", "LINHAS_RESUMO", "\n".join(linhas))

# ---------------------------------------------------------------- artigo: tabelas
inst = ['<table class="nw"><thead><tr><th class="l">Instância</th><th>Histórico; semanas</th><th>N</th><th>Sem.</th>'
        '<th>Variáveis</th><th>Restrições</th><th>LB publ.</th><th>UB publ.</th></tr></thead><tbody>']
SEMS = {"n030w4": "1; 6-2-9-1", "n040w4": "0; 2-0-6-1", "n050w4": "0; 0-4-8-7", "n060w4": "1; 6-1-1-5",
        "n030w8": "1; 2-7-0-9-3-6-0-6", "n040w8": "0; 0-6-8-9-2-6-6-4", "n050w8": "1; 1-7-8-5-7-4-1-8",
        "n060w8": "0; 6-2-9-9-0-8-1-3"}
for k, (i, r) in enumerate(T.iterrows()):
    tam = TAM.get(i, {}); sep = ' class="sep"' if k == 4 else ""
    inst.append(f'<tr{sep}><td class="l">{i}</td><td>{SEMS[i]}</td><td>{int(r.N)}</td><td>{int(r["sem"])}</td>'
                f'<td>{f(tam.get("colunas", 0))}</td><td>{f(tam.get("linhas", 0))}</td>'
                f'<td>{f(r.lb_lit)}</td><td>{f(r.ub_lit)}</td></tr>')
inst.append('</tbody></table><p class="legenda">Tabela 1. Instâncias. LB/UB publ.: melhores limites inferior e '
            'superior publicados por Legrain e Omer [2023]; LB = UB indica ótimo provado.</p>')
inserir("etapa8_artigo_sbpo.html", "TAB_INSTANCIAS", "\n".join(inst))

ex = ['<table class="nw"><thead><tr><th class="l">Instância</th><th>Custo</th><th>LB Gurobi</th><th>Gap</th>'
      '<th>Tempo (s)</th><th>Dist. UB publ.</th><th>HiGHS: custo</th><th>Dist. UB publ.</th></tr></thead><tbody>']
for k, (i, r) in enumerate(T.iterrows()):
    sep = ' class="sep"' if k == 4 else ""
    ex.append(f'<tr{sep}><td class="l">{i}</td><td>{f(r.gurobi)}</td><td>{f(r.gurobi_lb)}</td><td>{f(r.gurobi_gap, 1)}%</td>'
              f'<td>{f(r.gurobi_t)}</td><td>{pct(r.dev_gurobi)}</td><td>{f(r.highs)}</td><td>{pct(r.dev_highs)}</td></tr>')
ex.append('</tbody></table><p class="legenda">Tabela 2. Método exato (modelo da Seção 4), 300 s, 1 thread. '
          'Nenhuma instância teve a otimalidade provada.</p>')
inserir("etapa8_artigo_sbpo.html", "TAB_EXATO", "\n".join(ex))

cp = ['<table class="nw"><thead><tr><th class="l" rowspan="2">Instância</th><th rowspan="2">UB publ.</th>'
      '<th rowspan="2">Gurobi</th><th colspan="2">GRASP</th><th colspan="2">SA</th><th colspan="2">SA + F&amp;O</th></tr>'
      '<tr><th>médio</th><th>melhor</th><th>médio</th><th>melhor</th><th>médio</th><th>melhor</th></tr></thead><tbody>']
for k, (i, r) in enumerate(T.iterrows()):
    medios = {"gurobi": r.gurobi, "grasp": r.grasp_medio, "sa": r.sa_medio, "fo": r.fo_medio}
    best = min(medios, key=medios.get)
    b = lambda m, s: f"<b>{s}</b>" if m == best else s
    sep = ' class="sep"' if k == 4 else ""
    cp.append(f'<tr{sep}><td class="l">{i}</td><td>{f(r.ub_lit)}</td><td>{b("gurobi", f(r.gurobi))}</td>' +
              "".join(f"<td>{b(m, f(r[m + '_medio']))}</td><td>{f(r[m + '_melhor'])}</td>" for m in ["grasp", "sa", "fo"])
              + "</tr>")
cp.append(f'<tr class="sep"><td class="l">Dist. média</td><td></td><td>{pct(dev["gurobi"])}</td>'
          f'<td>{pct(dev["grasp"])}</td><td></td><td>{pct(dev["sa"])}</td><td></td><td>{pct(dev["fo"])}</td><td></td></tr>')
cp.append('</tbody></table><p class="legenda">Tabela 3. Custo das escalas com 300 s por execução (heurísticas: média '
          f'e melhor de {int(T.n_sem.min())} sementes). Em negrito, o melhor custo médio da instância. Dist. média: distância média '
          'ao UB publicado.</p>')
inserir("etapa8_artigo_sbpo.html", "TAB_COMP", "\n".join(cp))

print("vitorias:", vit)
print("distancia media:", {k: round(v, 1) for k, v in dev.items()})
print("iteracoes medias:", T[["grasp_it", "sa_it", "fo_it"]].mean().round(1).to_dict())
