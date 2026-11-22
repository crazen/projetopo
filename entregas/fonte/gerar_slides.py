"""gerar_slides.py - gera a apresentacao da Etapa 7 (PowerPoint 16:9, 15 min) a partir dos resultados.

Le ../../nurse_rostering/comparacao_final.csv e as figuras fig_*.png desta pasta.
Cada slide tem o roteiro de fala nas anotacoes (Exibir > Anotacoes no PowerPoint).
Uso:  python gerar_slides.py
"""
import os
import pandas as pd
from pptx import Presentation
from pptx.util import Cm, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

AQUI = os.path.dirname(os.path.abspath(__file__))
SAIDA = os.path.join(AQUI, "..", "etapa7_apresentacao.pptx")
T = pd.read_csv(os.path.join(AQUI, "..", "..", "nurse_rostering", "comparacao_final.csv"), index_col=0)

AZUL = RGBColor(0x1F, 0x4E, 0x8C); TXT = RGBColor(0x1A, 0x1A, 0x1A); CINZA = RGBColor(0x5A, 0x5A, 0x5A)
CLARO = RGBColor(0xEE, 0xF2, 0xF8); BRANCO = RGBColor(0xFF, 0xFF, 0xFF); VERDE = RGBColor(0x0E, 0x7A, 0x52)
FONTE = "Calibri"

prs = Presentation()
prs.slide_width, prs.slide_height = Cm(33.867), Cm(19.05)
BRANCO_LAYOUT = prs.slide_layouts[6]
W, H = prs.slide_width, prs.slide_height
num = [0]


def fmt(x, casas=0):
    s = f"{x:,.{casas}f}"
    return s.replace(",", "X").replace(".", ",").replace("X", ".")


def texto(sl, x, y, w, h, linhas, tam=20, cor=TXT, negrito=False, alinh=PP_ALIGN.LEFT, ancora=MSO_ANCHOR.TOP):
    """linhas: lista de str ou (str, dict) com chaves tam/cor/negrito/nivel/italico."""
    tb = sl.shapes.add_textbox(x, y, w, h); tf = tb.text_frame; tf.word_wrap = True
    tf.vertical_anchor = ancora
    for m in ("margin_left", "margin_right", "margin_top", "margin_bottom"):
        setattr(tf, m, Cm(0.1))
    for i, ln in enumerate(linhas):
        s, o = (ln, {}) if isinstance(ln, str) else ln
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = alinh
        nivel = o.get("nivel", 0)
        marcador = o.get("marcador", nivel > 0 or o.get("bullet", False))
        r = p.add_run(); r.text = ("•  " if marcador and nivel <= 1 else "–  " if marcador else "") + s
        f = r.font; f.name = FONTE; f.size = Pt(o.get("tam", tam - 2 * max(0, nivel - 1)))
        f.bold = o.get("negrito", negrito); f.italic = o.get("italico", False)
        f.color.rgb = o.get("cor", cor)
        p.space_after = Pt(o.get("depois", 6))
        if nivel > 1:
            p.level = 1
    return tb


def slide(titulo, notas, secao=None):
    sl = prs.slides.add_slide(BRANCO_LAYOUT); num[0] += 1
    faixa = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, Cm(0.35)); faixa.fill.solid()
    faixa.fill.fore_color.rgb = AZUL; faixa.line.fill.background()
    texto(sl, Cm(1.5), Cm(0.9), Cm(30), Cm(2), [titulo], tam=30, cor=AZUL, negrito=True)
    if secao:
        texto(sl, Cm(1.5), Cm(0.55), Cm(20), Cm(0.6), [secao.upper()], tam=11, cor=CINZA)
    texto(sl, Cm(30.5), Cm(17.9), Cm(2.5), Cm(0.8), [str(num[0])], tam=12, cor=CINZA, alinh=PP_ALIGN.RIGHT)
    texto(sl, Cm(1.5), Cm(17.9), Cm(25), Cm(0.8), ["Nurse Rostering (INRC-II): PLI e metaheurísticas · UNIFESP"],
          tam=11, cor=CINZA)
    sl.notes_slide.notes_text_frame.text = notas
    return sl


def tabela(sl, x, y, w, linhas, larguras, tam=14, altura=Cm(0.85), destaque=None):
    nl, nc = len(linhas), len(linhas[0])
    shp = sl.shapes.add_table(nl, nc, x, y, w, altura * nl); tb = shp.table
    for j, lw in enumerate(larguras):
        tb.columns[j].width = lw
    for i, ln in enumerate(linhas):
        for j, v in enumerate(ln):
            c = tb.cell(i, j); c.text = str(v)
            c.margin_left = c.margin_right = Cm(0.15); c.margin_top = c.margin_bottom = Cm(0.05)
            c.vertical_anchor = MSO_ANCHOR.MIDDLE
            p = c.text_frame.paragraphs[0]; p.alignment = PP_ALIGN.LEFT if j == 0 else PP_ALIGN.CENTER
            run = p.runs[0] if p.runs else p.add_run()
            f = run.font; f.name = FONTE; f.size = Pt(tam); f.bold = i == 0
            c.fill.solid()
            if i == 0:
                c.fill.fore_color.rgb = AZUL; f.color.rgb = BRANCO
            else:
                c.fill.fore_color.rgb = CLARO if i % 2 else BRANCO; f.color.rgb = TXT
                if destaque and destaque(i, j):
                    f.bold = True; f.color.rgb = VERDE
    return tb


def imagem(sl, nome, x, y, w=None, h=None):
    return sl.shapes.add_picture(os.path.join(AQUI, nome), x, y, width=w, height=h)


# ------------------------------------------------------------------ 1. titulo
TEM_1H = "fo_1h" in T and "sa_1h" in T and T.fo_1h.notna().all() and T.sa_1h.notna().all()
TEM_G1H = "gurobi_1h" in T and T.gurobi_1h.notna().all()
TEM_V3 = all(f"{m}_v3_medio" in T for m in ["grasp", "sa", "fo"])
sl = prs.slides.add_slide(BRANCO_LAYOUT); num[0] += 1
fundo = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H); fundo.fill.solid(); fundo.fill.fore_color.rgb = AZUL
fundo.line.fill.background()
texto(sl, Cm(2.5), Cm(4.2), Cm(29), Cm(5), ["Escalonamento de Enfermeiros com Regras Trabalhistas",
      ("Programação Inteira e Metaheurísticas nas Instâncias do INRC-II", {"tam": 26, "negrito": False})],
      tam=38, cor=BRANCO, negrito=True)
texto(sl, Cm(2.5), Cm(11), Cm(29), Cm(3), ["Eduardo Lopes · Jorge Dourado",
      ("Pesquisa Operacional · UNIFESP – Instituto de Ciência e Tecnologia", {"tam": 18})], tam=22, cor=BRANCO)
sl.notes_slide.notes_text_frame.text = (
    "(~15 s) Boa tarde. Somos Eduardo e Jorge. Vamos mostrar como montar a escala de uma equipe de enfermagem "
    "respeitando regras trabalhistas, comparando um método exato com metaheurísticas.")

# ------------------------------------------------------------------ 2. problema
sl = slide("O problema: a escala de enfermagem", secao="Problema (INRC-II)", notas=(
    "(~1 min 15 s) Todo hospital monta, todo mês, a escala de enfermagem. Para cada enfermeiro e cada dia decidimos: "
    "folga, ou um turno (manhã, dia, tarde, noite) com uma função (chefe, enfermeiro, cuidador, estagiário). Há regras "
    "rígidas, que nunca podem ser quebradas, como a cobertura mínima e não fazer manhã depois de tarde. E há regras "
    "flexíveis, que podem ser quebradas, mas custam pontos: dias seguidos, folgas, fins de semana, pedidos de folga. "
    "O objetivo é a escala com menos pontos de penalidade. Usamos a definição da competição internacional INRC-II, "
    "na versão estática: o horizonte inteiro, 4 ou 8 semanas, de uma vez."))
texto(sl, Cm(1.5), Cm(3.4), Cm(31), Cm(2), ["Para cada enfermeiro e cada dia: folga  ou  (turno, função)   ·   "
      "4 turnos × 4 funções   ·   4 ou 8 semanas"], tam=18, cor=CINZA)
tabela(sl, Cm(1.5), Cm(5.2), Cm(14.5), [
    ["Rígidas (nunca violar)", ""], ["H1  um turno por dia", ""], ["H2  cobertura mínima", ""],
    ["H3  sucessões proibidas (Late → Early)", ""], ["H4  só funções habilitadas", ""]],
    [Cm(13.5), Cm(1.0)], tam=15)
tabela(sl, Cm(17.3), Cm(5.2), Cm(15), [
    ["Flexíveis (custam pontos)", "peso"], ["S1  cobertura ótima", "30"], ["S2  dias seguidos: turno / trabalho", "15 / 30"],
    ["S3  folgas seguidas", "30"], ["S4  pedidos de folga", "10"], ["S5  fim de semana completo", "30"],
    ["S6  total de turnos do contrato", "20"], ["S7  máx. fins de semana", "30"]], [Cm(12.2), Cm(2.8)], tam=15)
texto(sl, Cm(1.5), Cm(10.5), Cm(14.5), Cm(4), [("Objetivo", {"negrito": True, "cor": AZUL}),
      ("minimizar a soma das penalidades S1–S7 respeitando H1–H4", {"tam": 17}),
      ("Ceschia et al. (2019); Burke et al. (2004)", {"tam": 14, "cor": CINZA, "italico": True})], tam=20)

# ------------------------------------------------------------------ 3. dados e dificuldade
sl = slide("Dados e por que é difícil", secao="Dados", notas=(
    "(~1 min) Usamos 8 instâncias oficiais da competição, com 30 a 60 enfermeiros e 4 ou 8 semanas. São as mesmas "
    "estudadas por Legrain e Omer, que publicam o ótimo ou o melhor valor conhecido, então dá para dizer o quão longe "
    "do ótimo cada método ficou. O problema é NP-difícil, e as regras de sequência acoplam os dias: mudar um dia de um "
    "enfermeiro mexe em várias penalidades. Quem prova esses ótimos usa branch-and-price especializado, por horas. "
    "Nossa pergunta: com um modelo simples e um solver comercial, até onde chegamos? E as metaheurísticas?"))
linhas = [["Instância", "Enf.", "Sem.", "Melhor publicado"]]
OTIMO = {"n030w4", "n040w4", "n050w4", "n060w4", "n030w8"}
for i, r in T.iterrows():
    linhas.append([i, int(r.N), int(r["sem"]), fmt(r.ub_lit) + (" *" if i in OTIMO else "")])
tabela(sl, Cm(1.5), Cm(3.4), Cm(13.5), linhas, [Cm(4.0), Cm(2.4), Cm(2.4), Cm(4.7)], tam=14, altura=Cm(0.82))
texto(sl, Cm(16.5), Cm(3.4), Cm(16.3), Cm(13), [
    ("Por que é difícil", {"negrito": True, "cor": AZUL}),
    ("NP-difícil; 30 enfermeiros × 28 dias ≈ 10⁸⁰⁰ escalas", {"bullet": True, "tam": 18}),
    ("Regras de sequência acoplam dias vizinhos", {"bullet": True, "tam": 18}),
    ("Modelo: de 26 mil a 108 mil variáveis", {"bullet": True, "tam": 18}),
    ("Literatura", {"negrito": True, "cor": AZUL}),
    ("Ótimos publicados: branch-and-price, horas de CPU (Legrain e Omer, 2023)", {"bullet": True, "tam": 18}),
    ("Nossa pergunta: modelo compacto + Gurobi × metaheurísticas, mesmo tempo", {"bullet": True, "tam": 18, "negrito": True}),
    ("* ótimo provado", {"tam": 14, "cor": CINZA}),
], tam=20)

# ------------------------------------------------------------------ 4. modelo
sl = slide("Modelo de Programação Linear Inteira", secao="Método exato", notas=(
    "(~1 min) A variável x vale 1 se o enfermeiro n faz o turno s com a função k no dia d; ela só existe para funções "
    "que ele tem, então H4 sai de graça. As regras rígidas viram restrições diretas. O ponto interessante é linearizar "
    "as sequências. Máximo de 5 dias seguidos: cada janela de 6 dias toda trabalhada custa 1. Mínimo de 3: detectamos "
    "o padrão folga, j dias de trabalho, folga, com j menor que 3. Validamos o modelo contra o avaliador oficial da "
    "competição."))
texto(sl, Cm(1.5), Cm(3.4), Cm(15.5), Cm(13.5), [
    ("x[n,d,s,k] ∈ {0,1}: enfermeiro n faz o turno s com a função k no dia d", {"negrito": True, "tam": 18}),
    ("H1: ∑ turnos do dia ≤ 1", {"bullet": True}),
    ("H2: ∑ x ≥ demanda mínima", {"bullet": True}),
    ("H3: a[n,d,Late] + a[n,d+1,Early] ≤ 1", {"bullet": True}),
    ("H4: x só existe se n tem a função k", {"bullet": True}),
    ("Objetivo = ∑ peso × violação (S1–S7)", {"bullet": True, "negrito": True}),
    ("AMPL + Gurobi 13 (Fourer et al., 2003)", {"tam": 14, "cor": CINZA, "italico": True}),
], tam=19)
caixa = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(17.5), Cm(3.4), Cm(15), Cm(12.5))
caixa.fill.solid(); caixa.fill.fore_color.rgb = CLARO; caixa.line.color.rgb = AZUL
texto(sl, Cm(18.1), Cm(3.8), Cm(13.9), Cm(11.8), [
    ("Linearizando as sequências", {"negrito": True, "cor": AZUL, "tam": 20}),
    ("Máximo de 5 dias seguidos:", {"negrito": True, "tam": 17}),
    ("e[n,d] ≥ (dias trabalhados na janela de 6 até d) − 5", {"tam": 17}),
    ("Mínimo de 3 dias seguidos:", {"negrito": True, "tam": 17}),
    ("v[n,d,j] detecta  folga | j dias | folga , j < 3", {"tam": 17}),
    ("custo (3 − j) × 30", {"tam": 15, "cor": CINZA}),
    ("Testado contra o avaliador oficial", {"tam": 15, "negrito": True}),
], tam=17)

# ------------------------------------------------------------------ 5. resultado exato
nota_1h = ""
linhas_g = [("Gurobi 13 · 300 s · 1 thread", {"negrito": True, "cor": AZUL}),
            ("Nenhuma instância com ótimo provado", {"bullet": True}),
            ("8 semanas: escalas várias vezes piores que o ótimo", {"bullet": True}),
            ("Relaxação linear fraca: PL = 20%–70% do ótimo", {"bullet": True, "negrito": True}),
            ("Simplex caro: só 1 a 3 nós em 300 s", {"bullet": True, "negrito": True})]
if TEM_G1H:
    n_ot = int(T.gurobi_1h_otimo.astype(str).eq("True").sum())
    linhas_g.append((f"Com 1 hora: +{fmt(T.dev_gurobi_1h.mean(), 0)}% em média; ótimo provado em {n_ot} de 8",
                     {"bullet": True}))
    nota_1h = (f" Com 1 hora, a pedido do professor, ficou a {fmt(T.dev_gurobi_1h.mean(), 0)}% em média e provou o "
               f"ótimo em {n_ot} de 8.")
sl = slide("Método exato: o Gurobi não dá conta das instâncias reais", secao="Método exato – resultados", notas=(
    "(~1 min 15 s) Com 5 minutos e 1 thread, o Gurobi não provou a otimalidade de nenhuma instância. Nas de 4 semanas "
    "às vezes chega perto, como a n030w4 a 7%, mas nas de 8 semanas as escalas são várias vezes piores que o ótimo. "
    "Não é erro do modelo, que bate com o avaliador oficial. São dois motivos: a relaxação linear é fraca, porque "
    "uma escala fracionária, como meio turno todo dia, satisfaz as regras de sequência sem pagar penalidade, então o "
    "limite fica entre 20% e 70% do ótimo e quase nada é podado; e o PL é caro, então em 5 minutos ele resolve só 1 a 3 "
    "nós da árvore." + nota_1h))
linhas = [["Instância", "Custo", "Limite PL", "Gap", "Melhor publ.", "Distância"]]
for i, r in T.iterrows():
    linhas.append([i, fmt(r.gurobi), fmt(r.pl), f"{fmt(r.gurobi_gap, 0)}%", fmt(r.ub_lit), f"+{fmt(r.dev_gurobi, 0)}%"])
tabela(sl, Cm(1.5), Cm(3.4), Cm(18), linhas, [Cm(3.4), Cm(3.0), Cm(3.0), Cm(2.4), Cm(3.2), Cm(3.0)],
       tam=14, altura=Cm(0.82))
texto(sl, Cm(20.5), Cm(3.4), Cm(12.3), Cm(13.5), linhas_g, tam=18)

# ------------------------------------------------------------------ 6. base comum
sl = slide("Metaheurísticas: a base comum", secao="Métodos aproximados", notas=(
    "(~1 min) As três heurísticas compartilham a mesma base. A escala é uma matriz enfermeiro por dia. A avaliação é "
    "incremental: um movimento mexe em 1 ou 2 enfermeiros, então recalculamos só o custo deles; compilado com numba, "
    "isso dá cerca de 1 milhão de movimentos por segundo. São quatro vizinhanças: trocar um dia, trocar dois "
    "enfermeiros num dia, um bloco de dias com o mesmo turno, e trocar blocos entre dois enfermeiros. Seguindo a "
    "sugestão do professor, quando dois movimentos empatam no custo, um segundo critério, a gravidade, decide: "
    "faltar cobertura é pior que um fim de semana incompleto, que é pior que um pedido de folga negado."))
texto(sl, Cm(1.5), Cm(3.4), Cm(15.5), Cm(13), [
    ("Representação: matriz enfermeiro × dia", {"bullet": True}),
    ("Avaliação incremental compilada: ~1 milhão de movimentos/s", {"bullet": True, "negrito": True}),
    ("Regras rígidas violadas pagam um peso λ", {"bullet": True}),
    ("Desempate por gravidade (sugestão do professor):", {"bullet": True, "negrito": True, "cor": VERDE}),
    ("cobertura > folgas > dias seguidos > fins de semana > totais > pedidos", {"tam": 16}),
], tam=20)
tabela(sl, Cm(17.5), Cm(3.6), Cm(15), [["Vizinhança", "Movimento"],
       ["N1 troca", "muda 1 enfermeiro em 1 dia"],
       ["N2 swap", "2 enfermeiros trocam 1 dia"],
       ["N3 bloco", "mesmo turno em 2–5 dias seguidos"],
       ["N4 swap de bloco", "2 enfermeiros trocam 2–7 dias"]], [Cm(4.2), Cm(10.8)], tam=15, altura=Cm(1.1))

# ------------------------------------------------------------------ 7. tres metodos
sl = slide("GRASP, Simulated Annealing e Fix-and-Optimize", secao="Métodos aproximados", notas=(
    "(~1 min 45 s) O GRASP constrói muitas escalas e melhora cada uma com uma busca local completa, o VND. Na "
    "construção, como o professor sugeriu, sorteamos 3 candidatos e pegamos o melhor; e na busca local o desempate deixa "
    "andar por movimentos de mesmo custo. O Simulated Annealing aceita pioras com probabilidade que cai com a "
    "temperatura, de 40 até 2. Aqui usamos a penalidade dinâmica: o peso das regras rígidas cai quando a escala está "
    "viável há algum tempo e sobe quando não está, então a busca oscila na fronteira da viabilidade. O Fix-and-Optimize "
    "parte da escala do SA e usa o próprio modelo de PLI: fixa quase tudo e deixa o solver reotimizar uma semana de "
    "todos, ou a escala inteira de dois enfermeiros parecidos. Percorre esses pedaços em ordem até nenhum melhorar. "
    "Todos os parâmetros foram escolhidos em instâncias fora do teste."))
col = [(Cm(1.2), "GRASP", [
    ("Construção gulosa-amostral: sorteia 3 candidatos, pega o melhor", {"bullet": True}),
    ("Busca local VND: N1 → N2 → N3 → N4", {"bullet": True}),
    ("Desempate: anda no platô", {"bullet": True}),
    (f"~{fmt(T.grasp_it.mean())} iterações em 300 s", {"bullet": True, "negrito": True}),
    ("Feo e Resende (1995); Resende e Ribeiro (2016)", {"tam": 12, "cor": CINZA, "italico": True})]),
    (Cm(11.9), "Simulated Annealing", [
    ("Aceita piora Δ com prob. e^(−Δ/T)", {"bullet": True}),
    ("T: 40 → 2 ao longo do tempo", {"bullet": True}),
    ("Penalidade dinâmica: λ cai quando viável, sobe quando não", {"bullet": True}),
    (f"~{fmt(T.sa_it.mean() / 1e6)} milhões de movimentos", {"bullet": True, "negrito": True}),
    ("Kirkpatrick et al. (1983); Gendreau et al. (1994)", {"tam": 12, "cor": CINZA, "italico": True})]),
    (Cm(22.6), "SA + Fix-and-Optimize", [
    ("Metade do tempo: SA", {"bullet": True}),
    ("Depois: subproblemas do próprio PLI (janela de 7 dias; par de enfermeiros), o resto fixo", {"bullet": True}),
    ("Em ordem, até nenhum melhorar", {"bullet": True}),
    (f"~{fmt(T.fo_it.mean())} subproblemas em 300 s", {"bullet": True, "negrito": True}),
    ("Helber e Sahling (2010)", {"tam": 12, "cor": CINZA, "italico": True})])]
for x, tit, lin in col:
    caixa = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, x, Cm(3.4), Cm(10.2), Cm(13.5))
    caixa.fill.solid(); caixa.fill.fore_color.rgb = CLARO; caixa.line.color.rgb = AZUL
    texto(sl, x + Cm(0.4), Cm(3.7), Cm(9.4), Cm(13), [(tit, {"negrito": True, "cor": AZUL, "tam": 21})] + lin, tam=16)

# ------------------------------------------------------------------ 8. comparacao 300 s
melhor_metodo = {}
for i, r in T.iterrows():
    vals = {"Gurobi": r.gurobi, "GRASP": r.grasp_medio, "SA": r.sa_medio, "SA+F&O": r.fo_medio}
    melhor_metodo[i] = min(vals, key=vals.get)
vit = pd.Series(melhor_metodo).value_counts()
sl = slide("Comparação com o mesmo tempo: 300 s, 1 thread", secao="Resultados", notas=(
    f"(~1 min 30 s) Esta é a tabela principal: custo médio de {int(T.n_sem.min())} sementes para as heurísticas, 300 "
    "segundos para todos. Em verde, o melhor de cada linha. O Gurobi só compete na menor instância. O GRASP para em "
    "ótimos locais ruins, de 1,6 a 3,5 vezes o ótimo. O SA chega perto. E o SA seguido do Fix-and-Optimize é o "
    f"melhor em {vit.get('SA+F&O', 0)} de 8, a {fmt(T.dev_fo_medio.mean(), 0)}% do melhor publicado em média: cada "
    "subproblema reorganiza de uma vez uma semana inteira, o que nenhum movimento simples do SA consegue. No gráfico, "
    "1 é o ótimo: SA e F&O ficam colados perto dele."))
linhas = [["Instância", "Gurobi", "GRASP", "SA", "SA+F&O", "Melhor publ."]]
cols = ["gurobi", "grasp_medio", "sa_medio", "fo_medio"]
for i, r in T.iterrows():
    linhas.append([i] + [fmt(r[c]) for c in cols] + [fmt(r.ub_lit)])
linhas.append(["Distância"] + [f"+{fmt(T['dev_' + c].mean(), 0)}%" for c in cols] + [""])
idx_best = {k + 1: 1 + ["Gurobi", "GRASP", "SA", "SA+F&O"].index(melhor_metodo[i]) for k, i in enumerate(T.index)}
tabela(sl, Cm(1.2), Cm(3.4), Cm(16.8), linhas, [Cm(3.2), Cm(2.7), Cm(2.7), Cm(2.6), Cm(2.8), Cm(2.8)], tam=14,
       altura=Cm(0.86), destaque=lambda i, j: idx_best.get(i) == j or (i == 9 and j == 4))
imagem(sl, "fig_gap.png", Cm(18.3), Cm(3.6), w=Cm(15))
texto(sl, Cm(18.6), Cm(12.4), Cm(14.5), Cm(4.5), [
    (f"SA + F&O: melhor em {vit.get('SA+F&O', 0)} de 8", {"bullet": True, "negrito": True}),
    ("Gurobi só compete na menor instância", {"bullet": True}),
    (f"Custo médio de {int(T.n_sem.min())} sementes; todas as escalas viáveis", {"tam": 14, "cor": CINZA}),
], tam=17)

# ------------------------------------------------------------------ 9. sugestoes e 1 hora
partes = []
if TEM_V3:
    partes.append(f"O GRASP melhorou nas 8 instâncias, de {fmt(T.dev_grasp_v3_medio.mean(), 0)}% para "
                  f"{fmt(T.dev_grasp_medio.mean(), 0)}%, principalmente pelo desempate. A penalidade dinâmica ajudou na "
                  "calibração, mas no teste empatou: a diferença ficou dentro da variação entre sementes. E no SA o "
                  "desempate piorou, porque recusar movimentos de mesmo custo tira diversificação; por isso não o usamos.")
if TEM_1H:
    partes.append(f"Com 1 hora, sem mudar nada, o SA + F&O foi para {fmt(T.dev_fo_1h.mean(), 0)}% e o SA para "
                  f"{fmt(T.dev_sa_1h.mean(), 0)}%. O F&O converge cedo, entre 32 e 40 minutos, num ótimo local das "
                  "decomposições; por isso, na menor instância, o SA sozinho, que resfria a hora toda, ganhou.")
sl = slide("Sugestões do professor e mais tempo", secao="Resultados", notas=(
    "(~1 min 30 s) Testamos as sugestões com calibração em instâncias fora do teste e comparamos com e sem elas na "
    "mesma máquina. " + " ".join(partes) + " Mostrar o que não funcionou também é resultado."))
if TEM_V3:
    tabela(sl, Cm(1.2), Cm(3.4), Cm(16), [["Método", "Sem", "Com", "Melhor em"],
           ["GRASP (amostral + desempate)", f"+{fmt(T.dev_grasp_v3_medio.mean(), 0)}%", f"+{fmt(T.dev_grasp_medio.mean(), 0)}%",
            f"{int((T.grasp_medio < T.grasp_v3_medio).sum())} de 8"],
           ["SA (penalidade dinâmica)", f"+{fmt(T.dev_sa_v3_medio.mean(), 1)}%", f"+{fmt(T.dev_sa_medio.mean(), 1)}%",
            f"{int((T.sa_medio < T.sa_v3_medio).sum())} de 8"],
           ["SA + F&O (penalidade dinâmica)", f"+{fmt(T.dev_fo_v3_medio.mean(), 1)}%", f"+{fmt(T.dev_fo_medio.mean(), 1)}%",
            f"{int((T.fo_medio < T.fo_v3_medio).sum())} de 8"]],
           [Cm(7.6), Cm(2.6), Cm(2.6), Cm(3.2)], tam=14, altura=Cm(1.0))
    texto(sl, Cm(1.2), Cm(8.0), Cm(16), Cm(8.5), [
        ("Distância média ao melhor publicado; mesma máquina, mesmas sementes, 300 s", {"tam": 13, "cor": CINZA}),
        ("Desempate: ajuda o GRASP; no SA piorou (não usado)", {"bullet": True}),
        ("Penalidade dinâmica: neutra no teste (dentro do ruído)", {"bullet": True}),
        ("Testado e não adotado: F&O em ciclos; janelas menores", {"bullet": True, "cor": CINZA}),
    ], tam=17)
if TEM_1H:
    lin = [["Instância", "SA 1 h", "SA+F&O 1 h", "Dist."]]
    for i, r in T.iterrows():
        lin.append([i, fmt(r.sa_1h), fmt(r.fo_1h), f"+{fmt(r.dev_fo_1h, 1)}%"])
    lin.append(["Média", f"+{fmt(T.dev_sa_1h.mean(), 1)}%", f"+{fmt(T.dev_fo_1h.mean(), 1)}%", ""])
    tabela(sl, Cm(18.6), Cm(3.4), Cm(14.2), lin, [Cm(3.6), Cm(3.4), Cm(3.8), Cm(3.4)], tam=13, altura=Cm(0.8),
           destaque=lambda i, j: (1 <= i <= 8 and j in (1, 2) and
                                  (T.iloc[i - 1].sa_1h < T.iloc[i - 1].fo_1h) == (j == 1)))
    texto(sl, Cm(18.6), Cm(11.8), Cm(14.2), Cm(5), [
        ("Com 1 hora (mesmos parâmetros, 1 semente)", {"negrito": True, "cor": AZUL, "tam": 16}),
        ("F&O converge em 32–40 min (ótimo local das decomposições)", {"bullet": True, "tam": 15}),
    ], tam=16)

# ------------------------------------------------------------------ 10. conclusoes
sl = slide("Conclusões", secao="Conclusões", notas=(
    "(~1 min) Resumindo: o modelo compacto é correto, mas tem relaxação linear fraca, e o Gurobi sozinho não resolve "
    "as instâncias reais. As metaheurísticas, com avaliação incremental, encontram escalas muito melhores no mesmo "
    "tempo. O melhor método é o SA seguido do Fix-and-Optimize, que usa o próprio modelo em pedaços: o modelo exato, "
    "ruim sozinho, é ótimo como componente. Com 1 hora chegamos a cerca de 10% do ótimo publicado, que vem de "
    "branch-and-price com horas de CPU. Obrigado!"))
fim = [
    ("Modelo de PLI correto, mas relaxação fraca: em 300 s o Gurobi não fecha nenhuma instância", {"bullet": True}),
    ("Metaheurísticas com avaliação incremental: escalas muito melhores no mesmo tempo", {"bullet": True}),
    (f"SA + Fix-and-Optimize: melhor em {vit.get('SA+F&O', 0)} de 8, a {fmt(T.dev_fo_medio.mean(), 0)}% do ótimo "
     "publicado com 300 s" + (f" e a {fmt(T.dev_fo_1h.mean(), 0)}% com 1 hora" if TEM_1H else ""),
     {"bullet": True, "negrito": True}),
    ("O modelo exato, ruim sozinho, é valioso como componente (subproblemas do F&O)", {"bullet": True}),
    ("Sugestões testadas: desempate ajuda o GRASP; penalidade dinâmica neutra", {"bullet": True}),
    ("Próximos passos: mais sementes e as 40 instâncias; decomposições mais variadas; geração de colunas",
     {"bullet": True, "cor": CINZA}),
    ("Obrigado!", {"negrito": True, "cor": AZUL, "tam": 26}),
]
texto(sl, Cm(1.5), Cm(3.4), Cm(31), Cm(14), fim, tam=21)

# ------------------------------------------------------------------ reserva
sl = slide("Reserva: convergência (n040w8)", secao="Slides de apoio", notas=(
    "Slide de apoio. O GRASP estagna cedo; o SA desce até o fim; o SA + F&O faz SA nos primeiros 150 s e depois o "
    "F&O desce em degraus, cada degrau é um subproblema resolvido pelo solver."))
imagem(sl, "fig_convergencia.png", Cm(4), Cm(3.4), w=Cm(26))

sl = slide("Reserva: calibração (instâncias fora do teste)", secao="Slides de apoio", notas=(
    "Slide de apoio. Todos os parâmetros foram escolhidos em 4 instâncias que não estão no conjunto de teste."))
texto(sl, Cm(1.5), Cm(3.4), Cm(31), Cm(14), [
    ("SA: T0 ∈ {20, 40, 100} × Tf ∈ {0,5; 2; 5} → T0 = 40, Tf = 2", {"bullet": True}),
    ("SA: fixa 12,8% · dinâmica 11,9% · dinâmica suave 10,5% (escolhida) · desempate 13,9%", {"bullet": True}),
    ("GRASP: RCL 110,9% · desempate 98,3% · amostral (p = 3) + desempate 97,6% (escolhida)", {"bullet": True}),
    ("F&O (20 min): sem ciclos 10.755 × com ciclos 10.830 (soma de 4 instâncias): ciclos não adotados", {"bullet": True}),
    ("F&O (150 s, n050w8): janelas inteiras 5.265 × divididas 5.280: mantidas inteiras", {"bullet": True}),
], tam=19)

sl = slide("Referências principais", secao="Slides de apoio", notas="Slide de apoio para perguntas.")
texto(sl, Cm(1.5), Cm(3.2), Cm(31), Cm(14.5), [
    "Burke, E. K. et al. (2004). The state of the art of nurse rostering. Journal of Scheduling, 7(6):441–499.",
    "Ceschia, S. et al. (2019). The Second International Nurse Rostering Competition. Annals of OR, 274:171–186.",
    "Ceschia, S., Guido, R. e Schaerf, A. (2020). Solving the static INRC-II nurse rostering problem by simulated "
    "annealing based on large neighborhoods. Annals of OR, 288:95–113.",
    "Feo, T. A. e Resende, M. G. C. (1995). Greedy randomized adaptive search procedures. J. Global Optim., 6:109–133.",
    "Gendreau, M., Hertz, A. e Laporte, G. (1994). A tabu search heuristic for the vehicle routing problem. "
    "Management Science, 40(10):1276–1290.",
    "Helber, S. e Sahling, F. (2010). A fix-and-optimize approach for the multi-level capacitated lot sizing problem. "
    "Int. J. Production Economics, 123(2):247–256.",
    "Kirkpatrick, S., Gelatt, C. D. e Vecchi, M. P. (1983). Optimization by simulated annealing. Science, 220:671–680.",
    "Legrain, A. e Omer, J. (2023). A dedicated pricing algorithm to solve a large family of nurse scheduling "
    "problems with branch-and-price. Les Cahiers du GERAD G-2023-02.",
    "Resende, M. G. C. e Ribeiro, C. C. (2016). Optimization by GRASP. Springer.",
], tam=13)

prs.save(SAIDA)
print("salvo em", os.path.abspath(SAIDA), "-", num[0], "slides")
