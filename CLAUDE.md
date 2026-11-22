# Projeto de Pesquisa Operacional: Nurse Rostering (INRC-II)

Contexto completo do projeto, para qualquer sessão do Claude (Claude Code no VS Code ou chat) continuar o trabalho.

## 1. Disciplina e equipe

- **Disciplina:** Pesquisa Operacional, optativa de Ciência da Computação, UNIFESP (ICT, São José dos Campos).
- **Dupla:** Jorge Dourado (168900) e Eduardo Lopes (168804).
- **Ambiente:** Windows (sem `unzip`/`grep`; usar Python ou PowerShell). PC com i5-13400 (6 núcleos P + 4 E) e 16 GB de RAM. Também usamos o Google Colab.
- **Licença AMPL for Academics** (com Gurobi) ativa via `amplpy`. A chave não fica neste arquivo.

## 2. Etapas da disciplina (requisitos do professor)

1. **Etapa 1, definição do problema:** título do trabalho e explicação geral sobre o problema. PDF, no máximo 2 páginas.
2. **Etapa 2, revisão bibliográfica:** revisão dos artigos mais recentes sobre o problema. PDF, no máximo 2 páginas. Todos os trabalhos citados no texto devem ser referenciados no final; as referências não contam no limite de 2 páginas.
3. **Etapa 3, apresentação dos dados:** apresentar os dados disponíveis para o problema e uma breve explicação deles. PDF, no máximo 2 páginas.
4. **Etapa 4, proposta de solução:** explicar como o problema será resolvido, com a formulação do problema para obter a solução ótima e a descrição da metaheurística escolhida. PDF, no máximo 4 páginas.
5. **Etapa 5, implementação:** resultados do método exato (modelo AMPL). A entrega é uma tabela com os resultados do método exato, mostrando a qualidade da solução e o tempo gasto em cada instância. PDF, no máximo 2 páginas.
6. **Etapa 6, implementação:** resultados do método aproximado (metaheurística). Tabela comparando os métodos exato e aproximado nos mesmos exemplares, com qualidade da solução e tempo gasto por método. PDF, no máximo 2 páginas.
7. **Etapa 7, apresentação:** apresentar o artigo como num simpósio, no máximo 15 minutos.
8. **Etapa 8, artigo:** formatação do SBPO-2021, PDF, no máximo 12 páginas.

Todas as entregas precisam de referências reais e conhecidas, citadas no texto e listadas no final. (Revisão de 15/11/2026: números conferidos contra os CSVs, citações × referências conferidas nos dois sentidos, limites de páginas ok.)

**Formato dos PDFs** (igual às etapas já entregues): fonte Times, título centralizado em negrito, autores em itálico abaixo do título ("Eduardo Lopes - 168804, Jorge Dourado - 168900"), seções numeradas em negrito ("1. ...") e texto justificado.

## 3. Histórico e decisões

- **Tema antigo:** as Etapas 1 a 4 foram feitas com o tema "Dimensionamento de equipes via Problema de Cobertura de Conjuntos (SCP)", com PLI e GRASP, dados sintéticos e a OR-Library de Beasley.
- **Feedback do orientador:** o Gurobi resolve com facilidade instâncias desse problema; o objetivo não seria fazer o scheduling da equipe de trabalho?
- **Decisão:** trocar para escala individual com regras trabalhistas, ou seja, **Nurse Rostering com as instâncias reais do INRC-II** (Second International Nurse Rostering Competition). Critério da dupla: o problema não pode ser trivial (o solver não deve resolver em menos de 30 s), precisa ser bem estabelecido, com referências reais, e precisa rodar modelos matemáticos de verdade.
- **Pendência:** as Etapas 1 a 4 precisam ser reescritas para o tema novo. Verificar com o professor e o orientador o que precisa ser reentregue.
- **Horizonte estático:** resolvemos o horizonte inteiro (4 ou 8 semanas) de uma vez, com toda a demanda conhecida. A competição original é semana a semana. Por isso os custos não se comparam ao ranking oficial, mas se comparam à literatura da versão estática (seção 6).
- **Crítica do professor à Etapa 4 (16/11/2026):** a matheurística chamada "LNS (fix-and-optimize)" não era um Fix-and-Optimize (sorteava pedaços: é uma LNS). Corrigido com `fo.py` (decomposições fixas percorridas sistematicamente; Helber e Sahling, 2010) e textos revisados.
- **Reunião com o professor (18/11/2026):** GRASP, SA e SA + F&O estão ok; o F&O agora atende a crítica. Pediu: mais tempo para o Gurobi (provar ótimos), tratar empates (decidir pela gravidade das violações), penalidades dinâmicas (viabilidade recente / oscilação estratégica) e, no GRASP, a construção que sorteia alguns candidatos e pega o melhor (gulosa-amostral). A dupla quer manter os métodos como estão (fácil de explicar), sem combinar mais métodos.
- **Versão 4 (21/11/2026):** implementadas as três estratégias como opções (`des`, `din`/`dinS`, `amN`), calibradas em 4 instâncias fora do conjunto final (`calibracao/v4`). Escolhas: GRASP amostral (p = 3) + desempate; SA e SA + F&O com penalidade dinâmica suave (`dinS`). No SA o desempate piorou, então não é usado. Sem opções, o código v4 reproduz a v3 exatamente (teste 6 de `testes.py`).
- **Uso de IA:** a disciplina permite IA e qualquer ferramenta. A dupla precisa entender o problema, o modelo, as heurísticas e a solução para a apresentação.

## 4. O problema

Atribuir a cada enfermeiro, em cada dia, um turno (Early, Day, Late, Night) com uma habilidade (HeadNurse, Nurse, Caretaker, Trainee), ou uma folga.

- **Restrições hard:**
  - H1: no máximo um turno por dia.
  - H2: cobertura mínima por dia, turno e habilidade.
  - H3: sucessões de turno proibidas (por exemplo, Late seguido de Early).
  - H4: só se usa uma habilidade que o enfermeiro possui.
- **Penalidades soft:**
  - S1: cobertura ótima (peso 30).
  - S2: mínimo e máximo de dias consecutivos no mesmo turno (15) e de trabalho (30).
  - S3: mínimo e máximo de folgas consecutivas (30).
  - S4: pedidos de folga (10).
  - S5: fim de semana completo (30).
  - S6: total de turnos no horizonte (20).
  - S7: máximo de fins de semana trabalhados (30).
- **Objetivo:** minimizar a soma das penalidades.
- **Histórico:** o histórico inicial (semana anterior) entra como dias virtuais anteriores ao horizonte.

## 5. Dados

- **Fonte:** https://mobiz.vives.be/inrc2/?page_id=20 (formato JSON). Uma instância é um cenário (`Sc-*.json`), mais um histórico (`H0-*-h.json`), mais uma sequência de semanas (`WD-*-i.json`).
- **Pacotes:**
  - `testdatasets_json.zip`: n005w4, n012w8 e n021w4, com 9 soluções de referência.
  - `datasets_json.zip` (competição): 30 a 120 enfermeiros, 4 ou 8 semanas.
  - `hidden-JSON.zip`: n035, n070 e n110.
  - `late-extended-dataset.zip`: 16 e 32 semanas.
- **Organização:** `organizar_dados.py` junta os zips em `dados/<dataset>/`.

## 6. Referências principais (conferir dados bibliográficos antes de citar)

- **Ceschia et al.,** "The Second International Nurse Rostering Competition", arXiv:1501.04177. Especificação do problema.
- **Legrain e Omer (2023),** "A dedicated pricing algorithm to solve a large family of nurse scheduling problems with branch-and-price", Les Cahiers du GERAD G-2023-02 (https://www.gerad.ca/papers/G-2023-02.pdf). **Conferido no PDF:** é desse relatório (Tabela 5; nomes completos na Tabela 7) que vêm os limites de `referencias_literatura.csv`. Todas as instâncias de 4 semanas têm ótimo provado; das de 8 semanas, só algumas (ex.: n030w8). (Antes este arquivo atribuía o relatório, por engano, a "Legrain, Omer e Rosat".)
- **Legrain, Omer e Rosat (2020),** "A rotation-based branch-and-price approach for the nurse scheduling problem", Mathematical Programming Computation 12:417–450. É outro artigo (rotações), anterior.
- **Ceschia, Guido e Schaerf (2020),** "Solving the static INRC-II nurse rostering problem by simulated annealing based on large neighborhoods", Annals of OR 288(1):95–113. SA na mesma versão estática; justifica o nosso SA.
- **Ceschia et al. (2019),** "The Second International Nurse Rostering Competition", Annals of OR 274(1–2):171–186 (versão publicada da especificação).
- **Helber e Sahling (2010),** "A fix-and-optimize approach for the multi-level capacitated lot sizing problem", International Journal of Production Economics 123(2):247–256. Base do F&O (conferido no RePEc).
- **Lam, Pitrou e Seibert (2015),** "Numba: a LLVM-based Python JIT compiler", LLVM-HPC'15. Citado no artigo pelo numba.
- Lista completa e conferida de referências: ver `entregas/fonte/etapa8_artigo_sbpo.html`.
- **Chaves, Resende et al.,** "A Random-Key Optimizer for Combinatorial Optimization" (RKO), arXiv:2411.04293, Journal of Heuristics 2025. É a base de um possível 4º método.
- **Da revisão anterior** (reaproveitar o que couber, conferindo): Strandmark, Qu e Curtois (2020); Santos et al. (2016, MIPLIB nursesched); Man Ngoo et al. (2022); Faasse (2024); Beasley (2024, local branching); Reyes e Araya (2021, GRASP); Vasko et al. (2025).

## 7. Implementação (pasta `nurse_rostering/`)

| Arquivo | Função |
|---|---|
| `nurse.mod` | Modelo PLI em AMPL. Variável x[n,d,s,k] binária; restrições H1–H4; S1–S7 linearizadas (janelas para máximos, padrões de sequência para mínimos) |
| `gen_dat.py` | JSON → `.dat` do AMPL |
| `rodar.run` / `rodar_final.run` | AMPL + Gurobi: 9 instâncias de teste (60 s) / 8 instâncias finais (300 s). `rodar_final.run` tem `CFG = 'padrao'` (→ `resultados_ampl_final.csv`) ou `'ajustado'` (`method=2 mipfocus=1 norelheurtime=60` → `resultados_ampl_ajustado.csv`). Depois de resolver, fixa x e resolve de novo para obter o custo real da escala |
| `inrc2.py` | Leitor das instâncias e avaliador (mesmo cálculo do validador oficial) |
| `exato.py` | Mesmo `nurse.mod` via tradutor GLPK + HiGHS (sem licença); `ModeloPLI` também é o motor do F&O |
| `relaxacao.py` | Limite da relaxação linear do modelo → `relaxacao_linear.csv` (PL = 20%–70% do ótimo: formulação fraca) |
| `custo_rapido.py` | Custo de um enfermeiro em Python (usado pela construção do GRASP) |
| `nucleo.py` | (16/11/2026; v4 em 21/11) Mesmo custo + movimentos N1–N4, SA e VND compilados com numba (~1 milhão de movimentos/s). v4: custo separado em soft, hard e gravidade (`GRAV_PADRAO`); avaliação soft + λ·hard. Testado contra `custo_rapido`, o avaliador e a v3 (`resultados_antigos/v3/`) |
| `grasp.py` | (16/11/2026) GRASP clássico: construção dia a dia com RCL (alpha = 0,15) + VND completo (N1 troca, N2 swap, N3 bloco, N4 swap de bloco). Sem ILS. v4: `amostra=p` (gulosa-amostral, Resende e Ribeiro, 2016) e `desempate=True` no VND |
| `sa.py` | Simulated Annealing sobre o `nucleo.py`; Metropolis; T cai geometricamente com o tempo, T0 = 40, Tf = 2 (calibrados em `calibracao/`, 4 instâncias fora do conjunto final). v4: `penalidade='dinamica'` (λ ajustado pela viabilidade recente a cada lote de 20 mil movimentos: cai /1,1 se viável > `viab_alta`, sobe ×1,1 se < `viab_baixa`; λ ∈ [`lam_min`, 10000]; últimos 10% com λ = 10000; Gendreau, Hertz e Laporte, 1994) e `desempate=True`. `dinS` = viab 0,8–0,98, λ ≥ 10 |
| `fo.py` | (16/11/2026) Matheurística **Fix-and-Optimize** (Helber e Sahling, 2010): SA na 1ª metade do tempo, depois decomposições fixas (janelas de 7 dias com todos os enfermeiros, 50% de sobreposição; pares de enfermeiros com mesmas habilidades/contrato) resolvidas em sequência pelo HiGHS (até 30 s cada) até uma passada inteira sem melhora; então L += 7, k += 2. Substituiu `lns.py` |
| `experimentos.py` | Roda exato, GRASP, SA e F&O (`--metodos exato,grasp,sa,fo`) numa lista de instâncias; CSV linha a linha com gap contra a literatura e `tempo_melhor_s` |
| `rodar_experimentos.py` | Roda GRASP, SA e F&O nas 8 instâncias finais em vários processos de 1 thread → `resultados/v3_*.csv`; retoma se interrompido; no fim chama consolidar, preencher_tabelas, gerar_pdfs, gerar_slides |
| `consolidar.py` | Junta Gurobi, HiGHS, relaxação linear e `resultados/v3_*.csv` em `comparacao_final.csv` e gera `entregas/fonte/fig_*.png` |
| `testes.py` | Modelo × avaliador, custo rápido × avaliador, núcleo numba × custo rápido, GRASP/SA/F&O curtos. Deve terminar em `TUDO CERTO` |
| `rodar_gurobi_longo.py` | (17/11/2026) Gurobi com vários limites de tempo (`--tempos 300,900,1800,3600`), mesmo método da Etapa 5 por padrão (1 thread, mipgap 0, x fixo para o custo real); log completo em `logs_gurobi/`, resumo em `resultados_gurobi_longo*.csv`; retoma se interrompido; impede o PC de dormir; `--push` envia cada resultado ao GitHub; `--saida` para 2 processos. Extras: `--threads`, `--cfg inicio` (MIP start de `inicio_mip/`). Rodado no PC em 21/11/2026 (final e teste, 3600 s) |
| `analisar_logs_gurobi.py` | (21/11/2026) Do log de 3600 s, incumbente e limite em 60/300/900/1800/3600 s (Gurobi determinístico) → `resultados_gurobi_tempos.csv`; se a execução passou mais de 60 s do limite, o instante do limite vem do log. Atenção: os valores aos 300 s deste log não substituem os da Etapa 5 (rodou ~2 vezes mais devagar) |
| `instancias_final.txt` | Conjunto final: n030w4, n040w4, n050w4, n060w4, n030w8, n040w8, n050w8, n060w8 (combinações da literatura) |
| `resultados_antigos/` | Resultados da versão 2 (GRASP-ILS/SA em Python puro e a "LNS"); só histórico |

**Cuidados técnicos:**
- Quando o solver para por tempo, o objetivo reportado pode ser maior que o custo real, porque as variáveis de penalidade da solução incumbente não ficam apertadas. O custo e o gap vêm do avaliador.
- O HiGHS não aceita mudar `threads` depois da primeira execução; isso é definido no construtor do `ModeloPLI`.
- Todo resultado só vale com `viavel=True`.
- Na primeira execução o numba compila o `nucleo.py` (cache em `__pycache__`).

## 8. Resultados até agora

### 8.0 Resultados v4 (21/11/2026, 300 s, 1 thread, 3 sementes; servidor Xeon da nuvem, 2 processos)

Heurísticas na nuvem (Xeon 2,3 GHz, mais rápido por núcleo que o servidor da v3: ~330 milhões de movimentos do SA em 300 s, contra ~250). A versão 3 foi rodada de novo **na mesma máquina** (`resultados/v4_*_{grasp,sa,fo}_*`), para medir o efeito das estratégias. Gurobi: o mesmo da Etapa 5 (i5, 300 s). Arquivos: `comparacao_final.csv`, `resultados_v4.csv`, `resultados/v4_*`.

| Instância | Melhor publ. | Gurobi 300 s | GRASP v4 | SA v4 | SA+F&O v4 | (v3 mesma máquina: GRASP / SA / F&O) |
|---|---|---|---|---|---|---|
| n030w4 | 1670* | 1785 | 2715 | **1773** | 1782 | 2868 / 1755 / 1737 |
| n040w4 | 1565* | 2435 | 3242 | 1918 | **1747** | 3285 / 1845 / 1745 |
| n050w4 | 1315* | 1810 | 3428 | 1633 | **1545** | 3477 / 1633 / 1543 |
| n060w4 | 2450* | 8110 | 5165 | 2787 | **2703** | 5193 / 2785 / 2728 |
| n030w8 | 2010* | 4580 | 4407 | 2288 | **2167** | 4885 / 2313 / 2178 |
| n040w8 | 2515 | 21655 | 6805 | 3307 | **3100** | 7132 / 3267 / 3088 |
| n050w8 | 4810 | 27065 | 9097 | 5470 | **5367** | 9585 / 5468 / 5270 |
| n060w8 | 2150 | 26830 | 7615 | 3288 | **3003** | 8175 / 3298 / 3018 |

Distância média ao melhor publicado: Gurobi +353,8%; GRASP v4 +134,3% (v3: +145,5%, v4 melhor nas 8); SA v4 +22,3% (v3: +21,6%); **SA+F&O v4 +16,1%** (v3: +15,7%), melhor método em 7/8 (n030w4: SA). Conclusão honesta: o desempate (com a construção amostral) melhora o GRASP; a penalidade dinâmica, boa na calibração (12,8% → 10,5%), não se repetiu no teste (diferença dentro do ruído entre sementes); o desempate piora o SA. Etapa 6 refeita com esses números (`entregas/etapa6_comparacao_exato_aproximado.pdf`, 2 páginas).

**Atualizado em 22/11/2026:** Etapa 4 (estratégias da v4 e plano com 1 h), Etapa 6, artigo (Etapa 8: resumo, métodos, Tabelas 4 e 5, conclusões; 11 páginas), slides (Etapa 7: 10 slides + 3 de reserva, ~8 min de fala) e guia de estudo, todos com os números v4 e de 1 h (incluindo o Gurobi de 1 h, seção 8.0c).

### 8.0b Com 1 hora (21–22/11/2026; mesmo método e parâmetros da v4, só o tempo muda; 1 semente; nuvem)

`resultados_1h/h1_*` (rodadas de 2 instâncias, `rodada_n0X0.txt`). SA + F&O: 30 min de SA + 30 min de F&O.

| Instância | Melhor publ. | SA+F&O 300 s | SA 1 h | SA+F&O 1 h | últ. melhora F&O |
|---|---|---|---|---|---|
| n030w4 | 1670* | 1782 | **1720** | 1740 | 1910 s |
| n040w4 | 1565* | 1747 | 1735 | **1725** | 2119 s |
| n050w4 | 1315* | 1545 | 1515 | **1465** | 2399 s |
| n060w4 | 2450* | 2703 | 2680 | **2580** | 1926 s |
| n030w8 | 2010* | 2167 | 2150 | **2115** | 2118 s |
| n040w8 | 2515 | 3100 | 3155 | **2880** | 2296 s |
| n050w8 | 4810 | 5367 | 5345 | **5150** | 2200 s |
| n060w8 | 2150 | 3003 | 2945 | **2660** | 3258 s |

Média: SA 1 h +14,9%; **SA+F&O 1 h +10,2%** (4 semanas 7,8%, 8 semanas 12,6%); F&O vence em 7/8. O F&O converge em poucos minutos (ótimo local das decomposições); por isso, na menor instância, o SA sozinho (que resfria a hora toda) ganha. Testados e **não adotados** (calibração, instâncias fora do teste): janelas do F&O divididas em grupos (`max_livres`; n050w8 5280 × 5265) e ciclos SA → F&O (`cic`; soma 10830 × 10755, `calibracao/v4b`). Etapa 6 inclui as linhas de 1 h na Tabela 2.

### 8.0c Gurobi com 1 hora (21/11/2026, PC i5, 1 thread, mesmo método da Etapa 5; chegou ao GitHub em 22/11)

`resultados_gurobi_longo.csv` (finais), `resultados_gurobi_longo_teste.csv` (teste), logs em `logs_gurobi/`, instantes intermediários em `resultados_gurobi_tempos.csv` (`analisar_logs_gurobi.py`).

| Instância | Melhor publ. | Gurobi 300 s | Gurobi 1 h | Gap 1 h | Tempo | Dist. 1 h |
|---|---|---|---|---|---|---|
| n030w4 | 1670* | 1785 | 1725 | 9,0% | 3602 s | +3,3% |
| n040w4 | 1565* | 2435 | 1785 | 43,1% | 3604 s | +14,1% |
| n050w4 | 1315* | 1810 | 1565 | 43,5% | 3602 s | +19,0% |
| n060w4 | 2450* | 8110 | 2755 | 32,7% | 3648 s | +12,4% |
| n030w8 | 2010* | 4580 | 2370 | 31,9% | 3641 s | +17,9% |
| n040w8 | 2515 | 21655 | 6280 | 79,5% | 3602 s | +149,7% |
| n050w8 | 4810 | 27065 | 6660 | 47,1% | 5220 s | +38,5% |
| n060w8 | 2150 | 26830 | 9535 | 90,4% | 3602 s | +343,5% |

Média: +74,8% (4 semanas +12,2%, 8 semanas +137,4%); 300 s: +353,8%. **Nenhum ótimo provado** nas finais; o limite inferior quase não sobe (n060w8: 716 → 914). Teste: as três n005w4 com ótimo provado (H0 1470 em 73 s, H1 1600 em 766 s, H2 1430 em 26 s); n012w8 gap 20–24% (2820, 3450, 3285); n021w4 gap 3,6–9,0% (1730, 1755, 1675); as 9 abaixo das soluções de referência. Comparado às heurísticas: só supera o SA+F&O 1 h na n030w4 (1725 × 1740); nas de 4 semanas fica perto do SA+F&O de 300 s (12,2% × 11,5%).

**Cuidados (explicar se perguntarem):**
- **Velocidade:** as duas execuções de 1 h rodaram juntas no PC e andaram ~2 vezes mais devagar que as da Etapa 5. As escalas da Etapa 5 aparecem idênticas no log de 1 h entre 437 e 899 s (prova de que o Gurobi é determinístico); razão de ~2,05 na n040w4 e n050w4. Não houve suspensão do PC (trabalho/tempo ≈ 0,70 unidades/s constante em todos os logs).
- **Limite ultrapassado:** o Gurobi só confere o relógio ao fim de cada nó. Regra adotada (a mesma da Etapa 5): vale a escala devolvida, com o tempo real. n050w8 1 h parou aos 5220 s (aos 3600 s tinha 6995: coluna `gurobi_1h_no_limite`); na Etapa 5, n040w4 (345 s) e n050w4 (439 s) acharam a escala ao fim de um nó, depois dos 300 s (aos 300 s: 2710 e 2215). Tudo isso está nas notas da Etapa 5, no artigo (Seção 6.2) e no guia.
- O log de n005w4 H1 (1 h) foi apagado sem querer no PC e recuperado do histórico do git (commit 9ad5472).

### 8.1 Resultados finais v3 (16–17/11/2026, 300 s, 1 thread)

Gurobi: i5-13400 local (`resultados_ampl_final.csv`, CFG padrão). Heurísticas: 3 sementes, servidor Xeon 2,1 GHz com 2 processos (mais lento por núcleo que o i5 — se rodar de novo no PC com `rodar_experimentos.py --processos 6`, trocar a frase sobre a máquina nas Etapas 6 e 8). Arquivos: `comparacao_final.csv`, `resultados/v3_*.csv`, `relaxacao_linear.csv`.

| Instância | Melhor publ. | PL | Gurobi (gap) | GRASP | SA | SA+F&O |
|---|---|---|---|---|---|---|
| n030w4 | 1670* | 812 | 1785 (22%) | 2868 | 1792 | **1752** |
| n040w4 | 1565* | 319 | 2435 (71%) | 3340 | 1830 | **1740** |
| n050w4 | 1315* | 545 | 1810 (61%) | 3477 | 1595 | **1530** |
| n060w4 | 2450* | 1246 | 8110 (77%) | 5193 | 2800 | **2797** |
| n030w8 | 2010* | 1402 | 4580 (66%) | 4885 | 2298 | **2180** |
| n040w8 | 2515 | 1073 | 21655 (94%) | 7132 | 3322 | **3193** |
| n050w8 | 4810 | 2401 | 27065 (89%) | 9585 | 5538 | **5352** |
| n060w8 | 2150 | 631 | 26830 (97%) | 8187 | 3383 | **3122** |

Distância média ao melhor publicado: Gurobi +354%, GRASP +146%, SA +22,3%, **SA+F&O +17,3%** (vence 8/8; n060w4 empate prático com SA). GRASP ~209 iterações, SA ~250 milhões de movimentos, F&O ~68 subproblemas (142 na n030w8, 12 na n060w8). Calibração 1200 s (n040w4 H2, ótimo 1750): SA 1945 (estagna), SA+F&O 1880.

### 8.2 Diagnóstico do método exato (Etapa 5)

- Não é bug: modelo × avaliador batem (testes). A relaxação linear dá só 20%–70% do ótimo (`relaxacao_linear.csv`); o log do Gurobi mostra 280 mil–1 milhão de iterações do simplex e 1–3 nós em 300 s (exceto n030w4, 1041 nós). Por isso o resultado "salta" (n060w4, n060w8): depende da heurística interna do Gurobi.
- `rodar_final.run` com `CFG = 'ajustado'` (barreira, mipfocus=1, norelheurtime=60) ainda **não foi rodado**; se rodar, `consolidar.py` lê `resultados_ampl_ajustado.csv` (colunas gurobi_aj_*), mas os textos/tabelas ainda não usam.

### 8.2b Entregas geradas (`entregas/`)

PDFs das Etapas 1–6 e 8 (HTML em `entregas/fonte/` → `python gerar_pdfs.py`, acha Chrome no Windows ou Linux), `etapa7_apresentacao.pptx` (`python gerar_slides.py`), `guia_de_estudo.pdf`. Tabelas preenchidas por `preencher_tabelas.py` a partir de `comparacao_final.csv`. Textos revisados em 17/11/2026 para GRASP/SA/F&O e para o diagnóstico do PL. Falta: e-mails dos autores no artigo (`[e-mail]`). `entregas/explicacao_para_estudo.md` (17/11/2026) é a cópia do doc de estudo do claude.ai (glossário, passo a passo de cada método, por que cada um foi melhor, relaxação/provar ótimos/piorar para melhorar, perguntas e teste rápido, pontos do professor). `nurse_rostering.zip` refeito com o código atual (para o Colab).

### 8.3 Resultados antigos (referência)

**Etapa 5, Gurobi 13.0.3 via AMPL** (60 s, 1 thread, Colab, instâncias de teste). Colunas: custo, limite inferior, gap, tempo.

| Instância | Custo | LB | Gap | Tempo |
|---|---|---|---|---|
| n005w4 H0 | 1470 | 1415 | 3,7% | 60 s |
| n005w4 H1 | 1690 | 1455 | 13,9% | 60 s |
| n005w4 H2 | 1430 | 1430 | 0% | 22 s (ótimo) |
| n012w8 H0 | 10760 | 1743 | 83,8% | 60 s |
| n012w8 H1 | 11800 | 2331 | 80,2% | 60 s |
| n012w8 H2 | 24855 | 1829 | 92,6% | 60 s |
| n021w4 H0 | 2395 | 1520 | 36,5% | 60 s |
| n021w4 H1 | 2110 | 1420 | 32,7% | 121 s |
| n021w4 H2 | 2675 | 1510 | 43,6% | 97 s |

**Heurísticas com 60 s** (H0 de cada dataset de teste):

| Instância | GRASP | Matheurística (LNS) |
|---|---|---|
| n005w4 | 1650 | 1720 |
| n012w8 | 4125 | 3930 |
| n021w4 | 2885 | 2475 |

Com 120 s, o LNS chegou a 2240 na n021w4.

**Leitura dos resultados:**
- Com 4 semanas, o Gurobi empata ou vence as heurísticas.
- Com 8 semanas, o Gurobi trava no nó raiz e as heurísticas são muito melhores.
- Nas instâncias da literatura, com 60 s as heurísticas ficam longe do melhor valor publicado. Com 300 s, o LNS chegou a 1875 na n030w4, contra o ótimo publicado de 1670 (+12%).

## 9. Próximos passos

1. Preencher os e-mails dos autores no artigo (`[e-mail]`).
2. Confirmar com o professor se as Etapas 1 a 4 precisam ser reentregues.
3. Ideias (trabalho futuro, já no artigo): mais sementes e as 40 instâncias; decomposições mais variadas para o F&O (converge cedo); dividir o tempo SA/F&O pelo tamanho da instância; geração de colunas.

**Rotina da v4 (nuvem):** `rodar_experimentos.py --prefixo v4 --pasta resultados --metodos fo+dinS,sa+dinS,grasp+am3+des,fo,sa,grasp --processos 2` (as três últimas = versão 3 na mesma máquina, para a Tabela 3 da Etapa 6). Cuidado: não apagar `_tmp_*.txt` nem usar `git stash -u` com execuções rodando (perde resultados).

**Regras para o Claude:** não alterar `nucleo.py`, `grasp.py`, `sa.py`, `fo.py` ou `nurse.mod` sem perguntar. Rodar `testes.py` depois de qualquer mudança. Comparar métodos sempre com o mesmo tempo e na mesma máquina.
