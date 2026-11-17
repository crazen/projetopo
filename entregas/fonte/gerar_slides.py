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
sl = prs.slides.add_slide(BRANCO_LAYOUT); num[0] += 1
fundo = sl.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, W, H); fundo.fill.solid(); fundo.fill.fore_color.rgb = AZUL
fundo.line.fill.background()
texto(sl, Cm(2.5), Cm(4.2), Cm(29), Cm(5), ["Escalonamento de Enfermeiros com Regras Trabalhistas",
      ("Programação Inteira e Metaheurísticas nas Instâncias do INRC-II", {"tam": 26, "negrito": False})],
      tam=38, cor=BRANCO, negrito=True)
texto(sl, Cm(2.5), Cm(11), Cm(29), Cm(3), ["Eduardo Lopes · Jorge Dourado",
      ("Pesquisa Operacional · UNIFESP – Instituto de Ciência e Tecnologia", {"tam": 18})], tam=22, cor=BRANCO)
sl.notes_slide.notes_text_frame.text = (
    "(~20 s) Boa tarde. Somos Eduardo e Jorge e vamos apresentar nosso trabalho sobre escalonamento de "
    "enfermeiros: como montar a escala mensal de uma equipe de enfermagem respeitando regras trabalhistas, "
    "comparando um método exato com metaheurísticas.")

# ------------------------------------------------------------------ 2. motivacao
sl = slide("O problema real", secao="Motivação", notas=(
    "(~1 min) Todo hospital precisa montar, todo mês, a escala de enfermagem: quem trabalha em cada dia, em "
    "qual turno e em qual função. Ela precisa cobrir a demanda, respeitar contratos e legislação (descanso "
    "entre turnos, dias seguidos) e, se possível, atender pedidos de folga. Feita à mão, consome horas da "
    "chefia e gera escalas ruins, com horas extras e cansaço, o que afeta a segurança do paciente. Na PO esse "
    "é o Nurse Rostering Problem, um dos problemas de escalonamento de pessoal mais estudados."))
texto(sl, Cm(1.5), Cm(3.5), Cm(18), Cm(13), [
    ("Hospitais funcionam 24 h × 7 dias", {"bullet": True}),
    ("Todo mês: quem trabalha, em que dia, em qual turno e em qual função?", {"bullet": True}),
    ("Cobrir a demanda e respeitar contratos, descanso e pedidos de folga", {"bullet": True}),
    ("Escala ruim → horas extras, cansaço, rotatividade, risco ao paciente", {"bullet": True}),
    ("Na PO: Nurse Rostering Problem (NRP)", {"bullet": True, "negrito": True, "cor": AZUL}),
    ("Burke et al. (2004); Van den Bergh et al. (2013)", {"tam": 14, "cor": CINZA, "italico": True}),
], tam=22)
caixa = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(20.5), Cm(4), Cm(11.5), Cm(9.5))
caixa.fill.solid(); caixa.fill.fore_color.rgb = CLARO; caixa.line.color.rgb = AZUL
texto(sl, Cm(21.2), Cm(4.6), Cm(10.2), Cm(8.5), [("De onde viemos", {"negrito": True, "cor": AZUL}),
      ("Etapas 1–4: dimensionamento de equipes como cobertura de conjuntos", {"tam": 16}),
      ("Feedback: “o Gurobi resolve isso fácil”", {"tam": 16, "italico": True}),
      ("Agora: a escala individual, bem mais difícil", {"tam": 16, "negrito": True})], tam=18)

# ------------------------------------------------------------------ 3. definicao
sl = slide("O que decidir", secao="O problema (INRC-II)", notas=(
    "(~1 min 15 s) Usamos a definição da Segunda Competição Internacional de Nurse Rostering, o INRC-II. Para "
    "cada enfermeiro e cada dia decidimos: folga ou um turno (Early, Day, Late, Night) com uma habilidade "
    "(chefe, enfermeiro, cuidador, estagiário). As regras rígidas, que nunca podem ser violadas, são quatro: um "
    "turno por dia, cobertura mínima, sucessões proibidas (quem fez noite não pode fazer manhã no dia seguinte) e "
    "habilidade. As flexíveis podem ser violadas, mas custam pontos: cobertura ótima, sequências mínimas e máximas, "
    "pedidos de folga, fim de semana completo, total de turnos e de fins de semana. O objetivo é minimizar a soma "
    "das penalidades. Resolvemos a versão estática: o horizonte inteiro de uma vez."))
texto(sl, Cm(1.5), Cm(3.4), Cm(31), Cm(2), ["Para cada enfermeiro e cada dia: folga  ou  (turno, habilidade)   ·   "
      "4 turnos × 4 habilidades   ·   horizonte de 4 ou 8 semanas"], tam=18, cor=CINZA)
tabela(sl, Cm(1.5), Cm(5.2), Cm(14.5), [
    ["Rígidas (hard)", ""], ["H1  um turno por dia", ""], ["H2  cobertura mínima", ""],
    ["H3  sucessões proibidas (Night → Early)", ""], ["H4  só funções habilitadas", ""]],
    [Cm(13.5), Cm(1.0)], tam=15)
tabela(sl, Cm(17.3), Cm(5.2), Cm(15), [
    ["Flexíveis (soft)", "peso"], ["S1  cobertura ótima", "30"], ["S2  dias seguidos: mesmo turno / trabalho", "15 / 30"],
    ["S3  folgas seguidas", "30"], ["S4  pedidos de folga", "10"], ["S5  fim de semana completo", "30"],
    ["S6  total de turnos do contrato", "20"], ["S7  máx. fins de semana", "30"]], [Cm(12.2), Cm(2.8)], tam=15)
texto(sl, Cm(1.5), Cm(10.5), Cm(14.5), Cm(4), [("Objetivo", {"negrito": True, "cor": AZUL}),
      ("minimizar a soma ponderada das penalidades S1–S7, respeitando H1–H4", {"tam": 17}),
      ("Versão estática: todo o horizonte conhecido (Ceschia et al., 2019)", {"tam": 14, "cor": CINZA, "italico": True})],
      tam=20)

# ------------------------------------------------------------------ 4. dificuldade + literatura
sl = slide("Por que é difícil, e o que a literatura faz", secao="Contexto", notas=(
    "(~1 min) Com 30 enfermeiros e 28 dias já são da ordem de 10^800 escalas possíveis, e o problema é NP-difícil. "
    "Pior: as regras de sequência acoplam os dias, então mudar um dia de um enfermeiro mexe em várias penalidades. "
    "Na literatura recente, quem resolve essas instâncias até o ótimo usa branch-and-price especializado, com horas "
    "de CPU (Legrain e Omer, 2023). Do lado heurístico, Ceschia e colegas usaram Simulated Annealing nesta mesma "
    "versão. A nossa pergunta: com ferramentas acessíveis (um modelo compacto + Gurobi) e 5 minutos, até onde "
    "chegamos? E quanto as metaheurísticas melhoram?"))
texto(sl, Cm(1.5), Cm(3.5), Cm(15.5), Cm(13), [
    ("Dificuldade", {"negrito": True, "cor": AZUL}),
    ("NP-difícil (Cheang et al., 2003)", {"bullet": True}),
    ("30 enf. × 28 dias ≈ 10⁸⁰⁰ escalas", {"bullet": True}),
    ("Regras de sequência acoplam dias vizinhos", {"bullet": True}),
    ("Simetria entre enfermeiros iguais", {"bullet": True}),
], tam=21)
texto(sl, Cm(17.5), Cm(3.5), Cm(15), Cm(13), [
    ("Literatura", {"negrito": True, "cor": AZUL}),
    ("INRC-II: instâncias públicas de referência (Ceschia et al., 2019)", {"bullet": True, "tam": 18}),
    ("Exato: branch-and-price, horas de CPU (Legrain et al., 2020; Legrain e Omer, 2023)", {"bullet": True, "tam": 18}),
    ("Heurístico: Simulated Annealing (Ceschia et al., 2020)", {"bullet": True, "tam": 18}),
    ("Nossa pergunta: modelo compacto + Gurobi em 5 min vs. metaheurísticas, mesma máquina",
     {"bullet": True, "tam": 18, "negrito": True}),
], tam=21)

# ------------------------------------------------------------------ 5. dados
sl = slide("Dados: instâncias oficiais do INRC-II", secao="Dados", notas=(
    "(~1 min) Os dados são as instâncias públicas da competição, em JSON. Cada instância combina um cenário "
    "(turnos, habilidades, contratos, enfermeiros), um histórico (a semana anterior) e uma sequência de semanas "
    "de demanda e pedidos de folga. Escolhemos 8 instâncias, com 30 a 60 enfermeiros e 4 ou 8 semanas, que "
    "são exatamente as estudadas por Legrain e Omer, que publicam o ótimo ou os melhores limites. Isso permite "
    "dizer o quão longe do ótimo cada método ficou. O modelo vai de 26 mil a 108 mil variáveis."))
linhas = [["Instância", "Enf.", "Sem.", "Var. x", "Melhor publicado"]]
VARX = {"n030w4": "5.488", "n040w4": "7.168", "n050w4": "8.736", "n060w4": "10.864", "n030w8": "10.976",
        "n040w8": "14.336", "n050w8": "17.472", "n060w8": "20.160"}
OTIMO = {"n030w4", "n040w4", "n050w4", "n060w4", "n030w8"}
for i, r in T.iterrows():
    linhas.append([i, int(r.N), int(r["sem"]), VARX[i], fmt(r.ub_lit) + (" *" if i in OTIMO else "")])
tabela(sl, Cm(1.5), Cm(3.4), Cm(16.5), linhas, [Cm(4.2), Cm(2.4), Cm(2.4), Cm(3.2), Cm(4.3)], tam=14, altura=Cm(0.82))
texto(sl, Cm(19.2), Cm(3.4), Cm(13), Cm(13), [
    ("Instância = cenário + histórico + semanas", {"negrito": True, "cor": AZUL}),
    ("Cenário: turnos, habilidades, contratos, enfermeiros", {"bullet": True, "tam": 17}),
    ("Histórico: estado no fim do período anterior", {"bullet": True, "tam": 17}),
    ("Semanas: demanda mínima e ótima, pedidos de folga", {"bullet": True, "tam": 17}),
    ("* ótimo provado; demais: melhor solução conhecida (Legrain e Omer, 2023)", {"tam": 14, "cor": CINZA}),
    ("Modelo: 26 mil a 108 mil variáveis e restrições", {"tam": 17, "negrito": True}),
], tam=19)

# ------------------------------------------------------------------ 6. modelo
sl = slide("Modelo de Programação Linear Inteira", secao="Método exato", notas=(
    "(~1 min 30 s) A variável principal x vale 1 se o enfermeiro n faz o turno s com a habilidade k no dia d; ela só "
    "existe para habilidades que ele tem, então H4 sai de graça. As regras rígidas viram restrições diretas. O ponto "
    "interessante é linearizar as sequências. Para um máximo de 5 dias seguidos: cada janela de 6 dias toda trabalhada "
    "custa 1, o que conta exatamente os dias em excesso. Para um mínimo de 3: detectamos o padrão folga, j dias de "
    "trabalho, folga, com j menor que 3, e cobramos 3 menos j. Como minimizamos, cada variável de violação fica no "
    "menor valor possível, e o objetivo é exatamente a penalidade. Validamos isso comparando com o avaliador oficial "
    "nas soluções de referência da competição."))
texto(sl, Cm(1.5), Cm(3.4), Cm(15.5), Cm(13.5), [
    ("x[n,d,s,k] ∈ {0,1}: enfermeiro n faz o turno s com a habilidade k no dia d", {"negrito": True, "tam": 18}),
    ("H1: ∑ turnos do dia ≤ 1", {"bullet": True}),
    ("H2: ∑ x ≥ demanda mínima", {"bullet": True}),
    ("H3: a[n,d,Late] + a[n,d+1,Early] ≤ 1", {"bullet": True}),
    ("H4: x só existe se n tem a habilidade k", {"bullet": True}),
    ("Objetivo = ∑ peso × violação (S1–S7)", {"bullet": True, "negrito": True}),
    ("AMPL + Gurobi 13 (Fourer et al., 2003)", {"tam": 14, "cor": CINZA, "italico": True}),
], tam=19)
caixa = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(17.5), Cm(3.4), Cm(15), Cm(12.5))
caixa.fill.solid(); caixa.fill.fore_color.rgb = CLARO; caixa.line.color.rgb = AZUL
texto(sl, Cm(18.1), Cm(3.8), Cm(13.9), Cm(11.8), [
    ("Linearizando as sequências", {"negrito": True, "cor": AZUL, "tam": 20}),
    ("Máximo de 5 dias seguidos:", {"negrito": True, "tam": 17}),
    ("e[n,d] ≥ (w nos 6 dias até d) − 5", {"tam": 17}),
    ("7 dias seguidos → 2 janelas cheias → custo 2 × 30", {"tam": 15, "cor": CINZA}),
    ("Mínimo de 3 dias seguidos:", {"negrito": True, "tam": 17}),
    ("v[n,d,j] detecta  folga | j dias | folga , j < 3", {"tam": 17}),
    ("custo (3 − j) × 30", {"tam": 15, "cor": CINZA}),
    ("Minimização ⇒ objetivo = penalidade exata (testado contra o avaliador oficial)", {"tam": 15, "negrito": True}),
], tam=17)

# ------------------------------------------------------------------ 7. resultado exato
sl = slide("Método exato: o Gurobi trava nas instâncias reais", secao="Método exato – resultados", notas=(
    "(~1 min 15 s) Com 5 minutos e 1 thread, o Gurobi não provou a otimalidade de nenhuma instância. Nas de 4 "
    "semanas ele chega perto do ótimo em algumas (n030w4 a 7%), mas nas de 8 semanas o gap passa de 60%, chegando "
    "a 97%, e a escala é várias vezes pior que o ótimo publicado: ele mal sai do nó raiz. O gap é a garantia de pior "
    "caso: diferença entre a escala e o limite inferior. Por isso também comparamos com o melhor valor publicado. "
    "Por que ele trava: a relaxação linear do modelo é fraca. Resolvendo o PL, o limite fica entre 20% e 70% do "
    "ótimo, porque uma escala fracionária, como trabalhar meio turno todo dia, satisfaz as regras de sequência sem "
    "pagar penalidade. E o PL é caro: o log mostra centenas de milhares de iterações do simplex e 1 a 3 nós de "
    "branch-and-bound em 5 minutos. Conclusão: o problema não é trivial para o solver, e isso justifica as "
    "metaheurísticas."))
linhas = [["Instância", "Custo", "Limite inf.", "Limite PL", "Gap", "Melhor publ.", "Distância"]]
for i, r in T.iterrows():
    linhas.append([i, fmt(r.gurobi), fmt(r.gurobi_lb), fmt(r.pl), f"{fmt(r.gurobi_gap, 1)}%",
                   fmt(r.ub_lit), f"+{fmt(r.dev_gurobi, 0)}%"])
tabela(sl, Cm(1.5), Cm(3.4), Cm(20), linhas, [Cm(3.4), Cm(2.6), Cm(3.0), Cm(2.8), Cm(2.4), Cm(3.0), Cm(2.8)],
       tam=14, altura=Cm(0.82))
texto(sl, Cm(22.5), Cm(3.4), Cm(10.3), Cm(13.5), [
    ("Gurobi 13 · 300 s · 1 thread", {"negrito": True, "cor": AZUL}),
    ("Nenhuma instância com ótimo provado", {"bullet": True}),
    ("4 semanas: às vezes perto do ótimo", {"bullet": True}),
    ("8 semanas: gap de 66% a 97%; escalas várias vezes piores que o ótimo", {"bullet": True}),
    ("Causa: relaxação linear fraca (PL = 20%–70% do ótimo) e 1 a 3 nós em 300 s", {"bullet": True, "negrito": True}),
    ("Gap = (custo − LB) / custo", {"tam": 15, "cor": CINZA}),
    ("Distância = (custo − melhor publicado) / melhor publicado", {"tam": 15, "cor": CINZA}),
], tam=18)

# ------------------------------------------------------------------ 8. base das heuristicas
sl = slide("Métodos aproximados: a base comum", secao="Metaheurísticas", notas=(
    "(~1 min) As três heurísticas compartilham a mesma base. A escala é uma matriz enfermeiro por dia; H1 e H4 são "
    "garantidas pela representação, e H2 e H3 viram penalidade de 10 mil, então a busca elimina violações primeiro. "
    "O segredo de desempenho é a avaliação incremental: um movimento mexe em 1 ou 2 enfermeiros, então recalculamos só "
    "o custo deles e os contadores de cobertura do dia. Isso permite milhões de movimentos. Usamos quatro "
    "vizinhanças: trocar um dia, trocar dois enfermeiros num dia, um bloco de dias com o mesmo turno, e trocar "
    "blocos entre dois enfermeiros."))
texto(sl, Cm(1.5), Cm(3.4), Cm(15.5), Cm(13), [
    ("Representação: matriz enfermeiro × dia", {"bullet": True}),
    ("H1, H4 garantidas; H2, H3 com penalidade 10.000", {"bullet": True}),
    ("Avaliação incremental: recalcula só os enfermeiros afetados (μs por movimento)", {"bullet": True, "negrito": True}),
    ("Custo das heurísticas conferido pelo avaliador oficial", {"bullet": True}),
], tam=20)
tabela(sl, Cm(17.5), Cm(3.6), Cm(15), [["Vizinhança", "Movimento"],
       ["N1 troca", "muda a atribuição de 1 enfermeiro em 1 dia"],
       ["N2 swap", "2 enfermeiros trocam o que fazem em 1 dia"],
       ["N3 bloco", "1 enfermeiro: mesmo turno em 2–5 dias seguidos"],
       ["N4 swap de bloco", "2 enfermeiros trocam 2–7 dias seguidos"]], [Cm(4.2), Cm(10.8)], tam=15, altura=Cm(1.1))

# ------------------------------------------------------------------ 9. GRASP
sl = slide("GRASP com VND", secao="Metaheurísticas", notas=(
    "(~1 min 15 s) O GRASP é um método de múltiplas partidas: cada iteração constrói uma escala nova e a melhora "
    "com busca local. A construção vai dia a dia, vaga a vaga: calcula o custo de colocar cada enfermeiro e sorteia "
    "entre os melhores, a lista restrita de candidatos, controlada por alfa = 0,15. A busca local é um VND: percorre "
    "por completo N1, N2, N3 e N4, voltando a N1 a cada melhoria, até um ótimo local das quatro vizinhanças. "
    "Na primeira versão, em Python puro, o VND era tão lento que o GRASP fazia só 2 iterações em 5 minutos, o que "
    "não é um GRASP de fato. Compilamos o cálculo de custo e os movimentos com o numba: cerca de 1 milhão de "
    "movimentos por segundo, e o GRASP passou a fazer " + fmt(T.grasp_it.mean()) + " iterações em média."))
texto(sl, Cm(1.5), Cm(3.4), Cm(16), Cm(13), [
    ("1. Construção gulosa-aleatorizada", {"negrito": True, "cor": AZUL}),
    ("RCL = {n : c(n) ≤ c_mín + α (c_máx − c_mín)}, α = 0,15", {"tam": 17}),
    ("2. Busca local VND completa: N1 → N2 → N3 → N4", {"negrito": True, "cor": AZUL}),
    ("volta a N1 a cada melhoria; para no ótimo local", {"tam": 17}),
    ("3. Repete com uma nova construção (múltiplas partidas)", {"negrito": True, "cor": AZUL}),
    ("Feo e Resende (1995); Mladenović e Hansen (1997)", {"tam": 13, "cor": CINZA, "italico": True}),
], tam=20)
caixa = sl.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Cm(18.3), Cm(3.4), Cm(14.2), Cm(10.5))
caixa.fill.solid(); caixa.fill.fore_color.rgb = CLARO; caixa.line.color.rgb = VERDE
texto(sl, Cm(18.9), Cm(3.8), Cm(13), Cm(9.8), [
    ("Melhoria: núcleo compilado (numba)", {"negrito": True, "cor": VERDE, "tam": 20}),
    ("Problema: em Python puro, ~50 mil movimentos/s → só 2 iterações do GRASP em 300 s", {"tam": 16}),
    ("Solução: mesmo cálculo de custo, compilado; conferido contra o avaliador por testes automáticos", {"tam": 16}),
    (f"Resultado: ~1 milhão de movimentos/s; {fmt(T.grasp_it.mean())} iterações do GRASP em média",
     {"tam": 16, "negrito": True}),
], tam=16)

# ------------------------------------------------------------------ 10. SA + F&O
sl = slide("Simulated Annealing e matheurística Fix-and-Optimize", secao="Metaheurísticas", notas=(
    "(~1 min 45 s) O Simulated Annealing sorteia um movimento por vez: se melhora, aceita; se piora em delta, aceita "
    "com probabilidade e elevado a menos delta sobre T. No começo, com T alta, aceita pioras e explora; no fim só "
    "refina. A temperatura cai de 40 para 2 ao longo dos 5 minutos, calibrada em instâncias fora do conjunto de "
    "avaliação. A matheurística Fix-and-Optimize usa o próprio modelo de PLI: dividimos as variáveis por decomposições "
    "fixas, janelas de 7 dias com todos os enfermeiros e pares de enfermeiros parecidos com todos os dias. Cada "
    "subproblema fixa todo o resto e é resolvido pelo solver. Percorremos todos os subproblemas em ordem e repetimos "
    "até uma passada inteira não melhorar; aí aumentamos os subproblemas. Diferente de uma LNS, nada é sorteado: a "
    "busca é sistemática. Começamos da escala do SA, na metade do tempo."))
texto(sl, Cm(1.5), Cm(3.4), Cm(15.3), Cm(13.5), [
    ("Simulated Annealing", {"negrito": True, "cor": AZUL, "tam": 22}),
    ("Sorteia 1 movimento (N1–N4)", {"bullet": True}),
    ("Melhora → aceita;  piora Δ → aceita com prob. e^(−Δ/T)", {"bullet": True}),
    ("T cai de 40 → 2 ao longo do tempo: explora → refina", {"bullet": True}),
    (f"~{fmt(T.sa_it.mean() / 1e6)} milhões de movimentos em 300 s", {"bullet": True, "negrito": True}),
    ("Kirkpatrick et al. (1983); Ceschia et al. (2020)", {"tam": 13, "cor": CINZA, "italico": True}),
], tam=18)
texto(sl, Cm(17.5), Cm(3.4), Cm(15.3), Cm(13.5), [
    ("Matheurística Fix-and-Optimize", {"negrito": True, "cor": AZUL, "tam": 22}),
    ("Parte da escala do SA (metade do tempo)", {"bullet": True}),
    ("Decomposições fixas: janelas de 7 dias; pares de enfermeiros", {"bullet": True}),
    ("Cada subproblema: fixa o resto, o solver (HiGHS) resolve", {"bullet": True}),
    ("Passadas em ordem até nenhuma melhorar → subproblemas maiores", {"bullet": True}),
    ("Helber e Sahling (2010)", {"tam": 13, "cor": CINZA, "italico": True}),
], tam=18)

# ------------------------------------------------------------------ 11. comparacao
melhor_metodo = {}
for i, r in T.iterrows():
    vals = {"Gurobi": r.gurobi, "GRASP": r.grasp_medio, "SA": r.sa_medio, "SA+F&O": r.fo_medio}
    melhor_metodo[i] = min(vals, key=vals.get)
sl = slide("Comparação: mesmo tempo (300 s), mesma máquina", secao="Resultados", notas=(
    "(~1 min 30 s) Esta é a tabela principal. Custo médio de " + str(int(T.n_sem.min())) + " sementes para as heurísticas, 300 segundos, mesma "
    "máquina. Em verde, o melhor de cada linha. " +
    "; ".join(f"{i}: melhor = {m}" for i, m in melhor_metodo.items()) + ". "
    "A leitura geral: o Gurobi só compete nas instâncias pequenas de 4 semanas; nas de 8 semanas as heurísticas são "
    "muito melhores, e o Simulated Annealing é o método mais forte na maioria das instâncias."))
linhas = [["Instância", "Gurobi", "GRASP", "SA", "SA+F&O", "Melhor publ."]]
cols = ["gurobi", "grasp_medio", "sa_medio", "fo_medio"]
for i, r in T.iterrows():
    linhas.append([i] + [fmt(r[c]) for c in cols] + [fmt(r.ub_lit)])
idx_best = {k + 1: 1 + ["Gurobi", "GRASP", "SA", "SA+F&O"].index(melhor_metodo[i]) for k, i in enumerate(T.index)}
tabela(sl, Cm(1.5), Cm(3.4), Cm(18.5), linhas, [Cm(3.6), Cm(3.0), Cm(3.0), Cm(3.0), Cm(3.0), Cm(2.9)], tam=15,
       altura=Cm(0.9), destaque=lambda i, j: idx_best.get(i) == j)
vit = pd.Series(melhor_metodo).value_counts()
texto(sl, Cm(21), Cm(3.4), Cm(11.8), Cm(13.5), [
    ("Melhor método por instância", {"negrito": True, "cor": AZUL}),
] + [(f"{m}: {n} de 8", {"bullet": True}) for m, n in vit.items()] + [
    (f"Custo médio de {int(T.n_sem.min())} sementes; todas as escalas viáveis", {"tam": 14, "cor": CINZA}),
    ("Distância média ao melhor publicado:", {"tam": 16, "negrito": True}),
    (f"Gurobi +{fmt(T.dev_gurobi.mean(), 0)}% · GRASP +{fmt(T.dev_grasp_medio.mean(), 0)}% · "
     f"SA +{fmt(T.dev_sa_medio.mean(), 0)}% · SA+F&O +{fmt(T.dev_fo_medio.mean(), 0)}%", {"tam": 16}),
], tam=19)

# ------------------------------------------------------------------ 12. graficos
sl = slide("Distância ao ótimo e convergência", secao="Resultados", notas=(
    "(~1 min) À esquerda, cada ponto é a razão entre o custo do método e o melhor valor publicado, em escala log: "
    "1 é o ótimo. O Gurobi (quadrado azul) se afasta muito nas instâncias de 8 semanas, enquanto o SA fica sempre "
    "mais perto. À direita, a evolução do melhor custo ao longo dos 5 minutos numa instância de 8 semanas: o SA desce "
    "rápido e continua melhorando até o fim, enquanto o GRASP e o LNS estabilizam mais acima."))
imagem(sl, "fig_gap.png", Cm(0.8), Cm(3.3), w=Cm(16.2))
imagem(sl, "fig_convergencia.png", Cm(17.0), Cm(4.0), w=Cm(16.2))

# ------------------------------------------------------------------ 13. conclusoes
sl = slide("Conclusões", secao="Conclusões", notas=(
    "(~1 min 15 s) Resumindo: o modelo compacto é correto e validado, mas com 5 minutos o Gurobi não resolve as "
    "instâncias reais e se perde nas de 8 semanas. As metaheurísticas, com avaliação incremental, encontram escalas "
    "muito melhores no mesmo tempo, e o Simulated Annealing foi o mais forte. Mesmo assim ainda há distância para "
    "o ótimo publicado, que usa branch-and-price e horas de CPU. Como próximos passos: mais sementes e todas as 40 "
    "instâncias, combinar SA e LNS, e explorar geração de colunas. Obrigado, ficamos à disposição para perguntas."))
texto(sl, Cm(1.5), Cm(3.4), Cm(31), Cm(14), [
    ("Modelo compacto de PLI correto (validado contra o avaliador oficial), mas em 300 s o Gurobi não fecha "
     "nenhuma instância e se perde nas de 8 semanas", {"bullet": True}),
    ("Metaheurísticas com avaliação incremental encontram escalas muito melhores no mesmo tempo", {"bullet": True}),
    (f"Simulated Annealing: melhor método em {vit.get('SA', 0)} de 8 instâncias", {"bullet": True, "negrito": True}),
    ("VND local tornou a busca local iterada do GRASP 3–4× mais rápida", {"bullet": True}),
    ("Ainda há distância ao ótimo publicado (branch-and-price, horas de CPU)", {"bullet": True}),
    ("Próximos passos: mais sementes e as 40 instâncias; SA + LNS; geração de colunas", {"bullet": True, "cor": CINZA}),
    ("Obrigado!", {"negrito": True, "cor": AZUL, "tam": 26}),
], tam=21)

# ------------------------------------------------------------------ 14. referencias
sl = slide("Referências principais", secao="", notas="Slide de apoio para perguntas.")
texto(sl, Cm(1.5), Cm(3.2), Cm(31), Cm(14.5), [
    "Burke, E. K. et al. (2004). The state of the art of nurse rostering. Journal of Scheduling, 7(6):441–499.",
    "Ceschia, S. et al. (2019). The Second International Nurse Rostering Competition. Annals of OR, 274:171–186.",
    "Ceschia, S., Guido, R. e Schaerf, A. (2020). Solving the static INRC-II nurse rostering problem by simulated "
    "annealing based on large neighborhoods. Annals of OR, 288:95–113.",
    "Cheang, B. et al. (2003). Nurse rostering problems – a bibliographic survey. EJOR, 151(3):447–460.",
    "Feo, T. A. e Resende, M. G. C. (1995). Greedy randomized adaptive search procedures. J. Global Optim., 6:109–133.",
    "Kirkpatrick, S., Gelatt, C. D. e Vecchi, M. P. (1983). Optimization by simulated annealing. Science, 220:671–680.",
    "Legrain, A. e Omer, J. (2023). A dedicated pricing algorithm to solve a large family of nurse scheduling "
    "problems with branch-and-price. Les Cahiers du GERAD G-2023-02.",
    "Legrain, A., Omer, J. e Rosat, S. (2020). A rotation-based branch-and-price approach for the nurse scheduling "
    "problem. Math. Programming Computation, 12:417–450.",
    "Pisinger, D. e Ropke, S. (2010). Large neighborhood search. Handbook of Metaheuristics, 2. ed., p. 399–419.",
], tam=13)

prs.save(SAIDA)
print("salvo em", os.path.abspath(SAIDA), "-", num[0], "slides")
