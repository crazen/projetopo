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


# ---------------------------------------------------------------- etapa 5: linhas do exato (300 s e 1 hora)
G1H = "gurobi_1h" in T and T.gurobi_1h.notna().all()
linhas = []
for k, (i, r) in enumerate(T.iterrows()):
    tam = TAM.get(i)
    vr = f"{f(tam['colunas'] / 1000, 1)} / {f(tam['linhas'] / 1000, 1)}" if tam else "–"
    sep = ' class="sep"' if k == 4 else ""
    cel = (f'<tr{sep}><td class="l">{i}</td><td>{vr}</td><td>{f(r.pl)}</td>'
           f'<td>{f(r.gurobi)}</td><td>{f(r.gurobi_gap, 1)}%</td><td>{f(r.gurobi_t)}</td><td>{pct(r.dev_gurobi)}</td>')
    if G1H:
        ot = " (ótimo)" if str(r.gurobi_1h_otimo) == "True" else ""
        cel += (f'<td>{f(r.gurobi_1h)}{ot}</td><td>{f(r.gurobi_1h_lb)}</td><td>{f(r.gurobi_1h_gap, 1)}%</td>'
                f'<td>{f(r.gurobi_1h_t)}</td><td>{pct(r.dev_gurobi_1h)}</td>')
    linhas.append(cel + f'<td>{ub(i)}</td></tr>')
inserir("etapa5_resultados_metodo_exato.html", "LINHAS_EXATO", "\n".join(linhas))

# instancias de teste: 60 s (resultados_ampl.csv) e 1 hora (resultados_gurobi_longo_teste.csv)
REF_COMP = {"n005w4_H0": 1695, "n005w4_H1": 2010, "n005w4_H2": 1720, "n012w8_H0": 3295, "n012w8_H1": 3805,
            "n012w8_H2": 3745, "n021w4_H0": 2305, "n021w4_H1": 2305, "n021w4_H2": 2345}   # solucoes de referencia
a60 = pd.read_csv(os.path.join(NR, "resultados_ampl.csv"), sep=";").set_index("instancia")
arq1h = os.path.join(NR, "resultados_gurobi_longo_teste.csv")
t1h = pd.read_csv(arq1h).set_index("instancia") if os.path.exists(arq1h) else None
linhas = []
for k, (inst, r) in enumerate(a60.iterrows()):
    nome, h, wd = inst.split("_")
    rot = f"{nome} ({h[1:]}; {wd[2:]})"
    sep = ' class="sep"' if k in (3, 6) else ""
    cel = (f'<tr{sep}><td class="l">{rot}</td><td>{f(r.custo)}</td><td>{f(r.limite_inferior)}</td>'
           f'<td>{f(r["gap_%"], 1)}%</td><td>{f(r.tempo_s)}</td>')
    if t1h is not None and inst in t1h.index:
        q = t1h.loc[inst]
        cel += (f'<td>{f(q.custo)}</td><td>{f(q.limite_inferior)}</td><td>{f(q["gap_%"], 1)}%</td>'
                f'<td>{f(q.tempo_s)}</td>')
    else:
        cel += '<td>–</td><td>–</td><td>–</td><td>–</td>'
    linhas.append(cel + f'<td>{f(REF_COMP[nome + "_" + h])}</td></tr>')
inserir("etapa5_resultados_metodo_exato.html", "LINHAS_TESTE", "\n".join(linhas))

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
TEM_1H = "gurobi_1h" in T and T.gurobi_1h.notna().all()
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
if TEM_1H:
    n_ot = int(T.gurobi_1h_otimo.astype(str).eq("True").sum())
    linhas.insert(1, f'<tr><td class="l">Exato (Gurobi), 1 hora</td><td>3.600 s</td><td>–</td>'
                     f'<td>{pct(T.dev_gurobi_1h.mean())}</td><td>–</td><td class="l">mesmo método, 12 vezes mais tempo; '
                     + ('não provou ótimo em nenhuma' if n_ot == 0 else f'provou ótimo em {n_ot} de 8') + '</td></tr>')
# mesmo metodo com 1 hora (1 semente), quando ja houver resultados
for m, desc in [("sa", lambda: f"{f(T.sa_1h_it.mean() / 1e6, 0)} milhões de movimentos em média"),
                ("fo", lambda: f"{f(T.fo_1h_it.mean(), 0)} subproblemas em média (após 30 min de SA)")]:
    if f"{m}_1h" in T and T[f"{m}_1h"].notna().all():
        linhas.append(f'<tr><td class="l">{nomes[m]}, 1 hora</td><td>3.600 s</td><td>{f(T[m + "_1h_tmelhor"].mean())} s</td>'
                      f'<td>{pct(T[f"dev_{m}_1h"].mean())}</td><td>–</td><td class="l">{desc()}; 1 semente</td></tr>')
inserir("etapa6_comparacao_exato_aproximado.html", "LINHAS_RESUMO", "\n".join(linhas))

# efeito das estrategias novas (versao 3 x versao 4, mesma maquina, mesmas sementes)
CFG = {"grasp": "desempate por gravidade", "sa": "penalidade dinâmica + desempate", "fo": "SA da versão 4 + F&amp;O"}
try:
    import importlib.util as _u
    _e = _u.spec_from_file_location("consolidar", os.path.join(NR, "consolidar.py"))
    _K = _u.module_from_spec(_e); _e.loader.exec_module(_K)
    DESC = {"din": "penalidade dinâmica", "dinS": "penalidade dinâmica", "des": "desempate por gravidade"}
    for m in ["grasp", "sa", "fo"]:
        partes = _K.FINAL[m].split("+")[1:]
        d = [DESC.get(x, f"construção amostral ({x[2:].replace('p', '%')})" if x.startswith("am") else x) for x in partes]
        CFG[m] = " + ".join(d) if d else "igual à versão 3"
except Exception as e:
    print("aviso: configuracao final nao lida de consolidar.py:", e)
if all(f"{m}_v3_medio" in T for m in ["grasp", "sa", "fo"]):
    ab = []
    for m in ["grasp", "sa", "fo"]:
        melhorou = int((T[f"{m}_medio"] < T[f"{m}_v3_medio"]).sum())
        ab.append(f'<tr><td class="l">{nomes[m]}</td><td class="l">{CFG[m]}</td><td>{pct(T[f"dev_{m}_v3_medio"].mean())}</td>'
                  f'<td>{pct(T[f"dev_{m}_medio"].mean())}</td><td>{melhorou} de 8</td></tr>')
    inserir("etapa6_comparacao_exato_aproximado.html", "LINHAS_ESTRATEGIAS", "\n".join(ab))

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

ex = ['<table class="nw"><thead><tr><th class="l">Instância</th><th>Custo</th><th>LB Gurobi</th><th>Limite PL</th><th>Gap</th>'
      '<th>Tempo (s)</th><th>Dist. UB publ.</th><th>HiGHS: custo</th><th>Dist. UB publ.</th></tr></thead><tbody>']
for k, (i, r) in enumerate(T.iterrows()):
    sep = ' class="sep"' if k == 4 else ""
    ex.append(f'<tr{sep}><td class="l">{i}</td><td>{f(r.gurobi)}</td><td>{f(r.gurobi_lb)}</td><td>{f(r.pl)}</td><td>{f(r.gurobi_gap, 1)}%</td>'
              f'<td>{f(r.gurobi_t)}</td><td>{pct(r.dev_gurobi)}</td><td>{f(r.highs)}</td><td>{pct(r.dev_highs)}</td></tr>')
ex.append('</tbody></table><p class="legenda">Tabela 2. Método exato (modelo da Seção 4), 300 s, 1 thread. '
          'Limite PL: valor da relaxação linear do modelo. Nenhuma instância teve a otimalidade provada.</p>')
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

# artigo, Tabela 4: efeito das estrategias novas (versao 3 x versao 4, mesma maquina)
if all(f"{m}_v3_medio" in T for m in ["grasp", "sa", "fo"]):
    es = ['<table class="nw"><thead><tr><th class="l">Método</th><th class="l">Estratégias (Seção 5)</th>'
          '<th>Sem as estratégias</th><th>Com as estratégias</th><th>Melhor em</th></tr></thead><tbody>']
    for m in ["grasp", "sa", "fo"]:
        melhorou = int((T[f"{m}_medio"] < T[f"{m}_v3_medio"]).sum())
        es.append(f'<tr><td class="l">{nomes[m]}</td><td class="l">{CFG[m]}</td><td>{pct(T[f"dev_{m}_v3_medio"].mean())}</td>'
                  f'<td>{pct(T[f"dev_{m}_medio"].mean())}</td><td>{melhorou} de 8</td></tr>')
    es.append('</tbody></table><p class="legenda">Tabela 4. Efeito das estratégias: distância média ao UB publicado sem e '
              'com as estratégias, na mesma máquina, com as mesmas 3 sementes e 300 s. Melhor em: instâncias em que o custo '
              'médio com as estratégias foi menor.</p>')
    inserir("etapa8_artigo_sbpo.html", "TAB_ESTRAT", "\n".join(es))

# artigo, Tabela 5: 1 hora por instancia (mesmo metodo, 1 semente)
if "fo_1h" in T and "sa_1h" in T and T.fo_1h.notna().all() and T.sa_1h.notna().all():
    tem_g = "gurobi_1h" in T and T.gurobi_1h.notna().all()
    h = ['<table class="nw"><thead><tr><th class="l">Instância</th><th>UB publ.</th><th>SA + F&amp;O<br>300 s (média)</th>'
         + ('<th>Gurobi<br>1 h</th>' if tem_g else '') +
         '<th>SA<br>1 h</th><th>SA + F&amp;O<br>1 h</th><th>Dist.<br>UB publ.</th><th>Última melhora<br>do SA + F&amp;O</th></tr></thead><tbody>']
    for k, (i, r) in enumerate(T.iterrows()):
        sep = ' class="sep"' if k == 4 else ""
        sa_b = f"<b>{f(r.sa_1h)}</b>" if r.sa_1h < r.fo_1h else f(r.sa_1h)
        fo_b = f"<b>{f(r.fo_1h)}</b>" if r.fo_1h <= r.sa_1h else f(r.fo_1h)
        h.append(f'<tr{sep}><td class="l">{i}</td><td>{f(r.ub_lit)}</td><td>{f(r.fo_medio)}</td>'
                 + (f'<td>{f(r.gurobi_1h)}</td>' if tem_g else '') +
                 f'<td>{sa_b}</td><td>{fo_b}</td><td>{pct(r.dev_fo_1h)}</td><td>{f(r.fo_1h_tmelhor)} s</td></tr>')
    h.append(f'<tr class="sep"><td class="l">Dist. média</td><td></td><td>{pct(T.dev_fo_medio.mean())}</td>'
             + (f'<td>{pct(T.dev_gurobi_1h.mean())}</td>' if tem_g else '') +
             f'<td>{pct(T.dev_sa_1h.mean())}</td><td>{pct(T.dev_fo_1h.mean())}</td><td></td><td></td></tr>')
    nota_g = ""
    if tem_g:
        nota_g = (' Gurobi: mesmo método da Etapa 5 (1 thread), no i5 com duas execuções simultâneas; vale a escala devolvida.')
        if "gurobi_1h_no_limite" in T:
            for i, r in T[T.gurobi_1h_no_limite.notna()].iterrows():
                nota_g += (f' Na {i}, o Gurobi só parou aos {f(r.gurobi_1h_t)} s (confere o relógio ao fim de cada nó); '
                           f'aos 3.600 s tinha {f(r.gurobi_1h_no_limite)}.')
    h.append('</tbody></table><p class="legenda">Tabela 5. Execuções de 1 hora por instância, com os mesmos parâmetros '
             '(1 semente). No SA + F&amp;O, 30 min de SA e 30 min de F&amp;O. Em negrito, o melhor entre SA e SA + F&amp;O.'
             + nota_g + '</p>')
    inserir("etapa8_artigo_sbpo.html", "TAB_1H", "\n".join(h))

print("vitorias:", vit)
print("distancia media:", {k: round(v, 1) for k, v in dev.items()})
print("iteracoes medias:", T[["grasp_it", "sa_it", "fo_it"]].mean().round(1).to_dict())
