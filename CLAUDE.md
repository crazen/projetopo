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

**Formato dos PDFs** (igual às etapas já entregues): fonte Times, título centralizado em negrito, autores em itálico abaixo do título ("Eduardo Lopes - 168804, Jorge Dourado - 168900"), seções numeradas em negrito ("1. ...") e texto justificado.

## 3. Histórico e decisões

- **Tema antigo:** as Etapas 1 a 4 foram feitas com o tema "Dimensionamento de equipes via Problema de Cobertura de Conjuntos (SCP)", com PLI e GRASP, dados sintéticos e a OR-Library de Beasley.
- **Feedback do orientador:** o Gurobi resolve com facilidade instâncias desse problema; o objetivo não seria fazer o scheduling da equipe de trabalho?
- **Decisão:** trocar para escala individual com regras trabalhistas, ou seja, **Nurse Rostering com as instâncias reais do INRC-II** (Second International Nurse Rostering Competition). Critério da dupla: o problema não pode ser trivial (o solver não deve resolver em menos de 30 s), precisa ser bem estabelecido, com referências reais, e precisa rodar modelos matemáticos de verdade.
- **Pendência:** as Etapas 1 a 4 precisam ser reescritas para o tema novo. Verificar com o professor e o orientador o que precisa ser reentregue.
- **Horizonte estático:** resolvemos o horizonte inteiro (4 ou 8 semanas) de uma vez, com toda a demanda conhecida. A competição original é semana a semana. Por isso os custos não se comparam ao ranking oficial, mas se comparam à literatura da versão estática (seção 6).
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
- Lista completa e conferida de referências: ver `entregas/fonte/etapa8_artigo_sbpo.html`.
- **Chaves, Resende et al.,** "A Random-Key Optimizer for Combinatorial Optimization" (RKO), arXiv:2411.04293, Journal of Heuristics 2025. É a base de um possível 4º método.
- **Da revisão anterior** (reaproveitar o que couber, conferindo): Strandmark, Qu e Curtois (2020); Santos et al. (2016, MIPLIB nursesched); Man Ngoo et al. (2022); Faasse (2024); Beasley (2024, local branching); Reyes e Araya (2021, GRASP); Vasko et al. (2025).

## 7. Implementação (pasta `nurse_rostering/`)

| Arquivo | Função |
|---|---|
| `nurse.mod` | Modelo PLI em AMPL. Variável x[n,d,s,k] binária; restrições H1–H4; S1–S7 linearizadas (janelas para máximos, padrões de sequência para mínimos) |
| `gen_dat.py` | JSON → `.dat` do AMPL |
| `rodar.run` / `rodar_final.run` | AMPL + Gurobi: 9 instâncias de teste (60 s) / 8 instâncias finais (300 s). Grava `resultados_ampl*.csv`. Depois de resolver, fixa x e resolve de novo para obter o custo real da escala |
| `inrc2.py` | Leitor das instâncias e avaliador (mesmo cálculo do validador oficial) |
| `exato.py` | Mesmo `nurse.mod` via tradutor GLPK + HiGHS (sem licença) |
| `grasp.py` | GRASP: construção dia a dia com RCL (alpha), VND com N1 troca, N2 swap, N3 bloco de um enfermeiro e N4 swap de bloco, e fase ILS (perturbação + **VND local**: após perturbar, só revisita enfermeiros/dias afetados com margem de 3 dias; alterado em 14/11/2026 com autorização, ILS 3–4× mais rápido) |
| `sa.py` | Simulated Annealing (criado em 14/11/2026): reaproveita Estado e movimentos do GRASP; Metropolis; T cai geometricamente com o tempo, T0 = 40, Tf = 2 (calibrado só nas instâncias de teste) |
| `consolidar.py` | Junta Gurobi + HiGHS + heurísticas v2 em `comparacao_final.csv` e gera `entregas/fonte/fig_*.png` |
| `custo_rapido.py` | Custo de um enfermeiro em uma passada (usado pelo GRASP) |
| `lns.py` | Matheurística fix-and-optimize: parte do GRASP, fixa x fora de uma vizinhança (grupo de enfermeiros ou janela de dias) e o HiGHS reotimiza, com warm start e vizinhança adaptativa |
| `experimentos.py` | Roda exato, GRASP, SA (`--metodos ...,sa`) e LNS numa lista de instâncias e grava CSV linha a linha, com colunas de gap contra a literatura |
| `testes.py` | Modelo × avaliador (referências e escalas aleatórias), custo rápido × avaliador, GRASP incremental × avaliador. Deve terminar em `TUDO CERTO` |
| `instancias_final.txt` | Conjunto final: n030w4, n040w4, n050w4, n060w4, n030w8, n040w8, n050w8, n060w8 (combinações da literatura) |

**Cuidados técnicos:**
- Quando o solver para por tempo, o objetivo reportado pode ser maior que o custo real, porque as variáveis de penalidade da solução incumbente não ficam apertadas. O custo e o gap vêm do avaliador.
- O HiGHS não aceita mudar `threads` depois da primeira execução; isso é definido no construtor do `ModeloPLI`.
- Todo resultado só vale com `viavel=True`.

## 8. Resultados até agora

### 8.1 Resultados finais (14/11/2026, i5-13400 local, 300 s, 1 thread)

Arquivos: `nurse_rostering/comparacao_final.csv` (tabela por instância), `resultados_ampl_final.csv` (Gurobi), `resultados_v2.csv` (GRASP v2, SA e LNS, 2 sementes, 6 processos em paralelo), `final_*.csv` (só as linhas `exato` = HiGHS valem; GRASP/LNS desses arquivos são da versão antiga).

| Instância | Melhor publ. | Gurobi (gap) | GRASP | SA | LNS |
|---|---|---|---|---|---|
| n030w4 | 1670* | **1785** (22%) | 2565 | 1955 | 1868 |
| n040w4 | 1565* | 2435 (71%) | 3132 | **1998** | 2185 |
| n050w4 | 1315* | **1810** (61%) | 3425 | 1912 | 2332 |
| n060w4 | 2450* | 8110 (77%) | 5142 | **3000** | 4210 |
| n030w8 | 2010* | 4580 (66%) | 4812 | **2725** | 2940 |
| n040w8 | 2515 | 21655 (94%) | 6845 | **4018** | 5575 |
| n050w8 | 4810 | 27065 (89%) | 9710 | **6415** | 8612 |
| n060w8 | 2150 | 26830 (97%) | 9092 | **4268** | 7218 |

Heurísticas: média de 2 sementes. Distância média ao melhor publicado: Gurobi +354%, GRASP +145%, **SA +42,5%** (vence 6/8), LNS +85%. Gurobi não provou ótimo em nenhuma.

### 8.2 Entregas geradas (`entregas/`)

PDFs das Etapas 1–6 e 8 (HTML em `entregas/fonte/` → `python gerar_pdfs.py`), `etapa7_apresentacao.pptx` (`python gerar_slides.py`, roteiro nas anotações), `guia_de_estudo.pdf`. Tabelas preenchidas por `preencher_tabelas.py` a partir de `comparacao_final.csv`. Falta: e-mails dos autores no artigo (`[e-mail]`).

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

1. ~~Rodar conjunto final, Gurobi, tabela da Etapa 5, reescrever Etapas 1–4~~ (feito em 14/11/2026).
2. Revisar os documentos e os slides (abrir o .pptx; não havia PowerPoint para conferir o visual) e preencher os e-mails no artigo.
3. Opcional: mais sementes / mais instâncias; SA + LNS (SA como solução inicial); RKO foi descartado por ser complexo demais para a disciplina.

**Regras para o Claude:** não alterar `grasp.py`, `lns.py` ou `nurse.mod` sem perguntar. Rodar `testes.py` depois de qualquer mudança. Comparar métodos sempre com o mesmo tempo e na mesma máquina.
