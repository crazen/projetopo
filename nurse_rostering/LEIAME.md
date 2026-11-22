# Nurse Rostering (INRC-II): PLI, GRASP, Simulated Annealing e Fix-and-Optimize

Escalonamento de enfermagem com as regras do INRC-II, resolvendo o horizonte inteiro (4 ou 8 semanas) de uma vez.

## Arquivos

| Arquivo | O que é |
|---|---|
| `nurse.mod` | Modelo de PLI em AMPL (regras hard H1–H4, penalidades S1–S7) |
| `rodar.run` | Script AMPL: 9 instâncias de teste (60 s), grava `resultados_ampl.csv` |
| `rodar_final.run` | Script AMPL: 8 instâncias finais (300 s). `CFG = 'padrao'` grava `resultados_ampl_final.csv`; `CFG = 'ajustado'` (barreira no nó raiz, foco em viabilidade, heurística NoRel) grava `resultados_ampl_ajustado.csv` |
| `dat/` | Dados das instâncias em formato AMPL |
| `gen_dat.py` | Converte uma instância JSON do INRC-II em `.dat` |
| `inrc2.py` | Leitura das instâncias e avaliador de custo (mesmo cálculo do validador oficial) |
| `exato.py` | O mesmo `nurse.mod` traduzido pelo GLPK e resolvido pelo HiGHS (sem licença). Também é o "motor" do F&O |
| `relaxacao.py` | Limite da relaxação linear do modelo em cada instância (`relaxacao_linear.csv`) |
| `custo_rapido.py` | Custo de um enfermeiro em uma passada (Python; usado pela construção do GRASP) |
| `nucleo.py` | O mesmo custo e os movimentos N1–N4 compilados com numba (~1 milhão de movimentos/s); usado por GRASP e SA. Versão 4: custo separado em soft, hard e gravidade (para a penalidade dinâmica e o desempate) |
| `grasp.py` | GRASP: construção gulosa-aleatorizada (RCL com `alpha`, ou gulosa-amostral com `amostra`) + VND completo (N1 troca, N2 swap, N3 bloco, N4 swap de bloco), com desempate opcional |
| `sa.py` | Simulated Annealing: um movimento aleatório de N1–N4 por passo, critério de Metropolis, resfriamento geométrico no tempo. Opções da versão 4: `penalidade='dinamica'` (peso das regras hard ajustado pela viabilidade recente) e `desempate=True` (empates decididos pela gravidade) |
| `fo.py` | Matheurística Fix-and-Optimize: parte do SA e resolve em sequência subproblemas do `nurse.mod` (janelas de dias e grupos de enfermeiros) com o resto fixado; `sa_kw` repassa as opções da versão 4 ao SA |
| `experimentos.py` | Roda exato/GRASP/SA/F&O numa lista de instâncias e grava um CSV linha a linha. Métodos com opções: `sa+din+des`, `grasp+am3+des`, `fo+din+des` (sem opções = versão 3) |
| `rodar_experimentos.py` | Roda GRASP, SA e F&O nas 8 instâncias finais em paralelo (vários processos de 1 thread) e atualiza tabelas, figuras e PDFs |
| `consolidar.py` | Junta Gurobi, HiGHS, relaxação linear e heurísticas em `comparacao_final.csv` e gera as figuras |
| `testes.py` | Testes automáticos (deve terminar em `TUDO CERTO`) |
| `calibracao/` | Calibração de T0 e Tf do SA e, em `v4/`, das estratégias da versão 4 (penalidade dinâmica, desempate, construção amostral), em 4 instâncias que **não** estão no conjunto final |
| `instancias_final.txt` | Conjunto final: 8 instâncias da literatura (30 a 60 enfermeiros, 4 e 8 semanas) |
| `instancias_literatura.txt`, `referencias_literatura.csv` | As 40 instâncias estáticas de Legrain e Omer (2023) e os melhores limites publicados |
| `resultados/` | Uma linha de CSV (+ convergência e log) por execução das heurísticas (300 s) |
| `resultados_1h/` | Execuções de 1 hora do SA e do SA + F&O (mesmos parâmetros, 1 semente), em rodadas de 2 instâncias (`rodada_n0X0.txt`) |
| `resultados_antigos/` | Resultados da versão 2 (só histórico; ver o LEIAME de lá) e, em `v3/`, o código do núcleo, SA e GRASP da versão 3 (usado no teste de regressão) |
| `rodar_gurobi_longo.py` | Gurobi com tempos maiores (ex.: 3600 s), mesmo método da Etapa 5 (1 thread, mipgap 0, custo real com x fixo); grava o log completo de cada execução em `logs_gurobi/` e `resultados_gurobi_longo*.csv`; impede o PC de dormir; `--push` envia cada resultado ao GitHub; `--saida` permite 2 processos. Opções: `--threads`, `--cfg inicio` (MIP start) |
| `analisar_logs_gurobi.py` | Lê os logs de 3600 s e extrai incumbente e limite inferior em 60, 300, 900 e 1800 s da mesma execução (o Gurobi é determinístico) → `resultados_gurobi_tempos.csv` |
| `gerar_inicio_mip.py`, `inicio_mip/` | Escalas iniciais do SA + F&O (300 s) para o MIP start do Gurobi, em comandos `let x[...] := 1;` do AMPL |
| `organizar_dados.py` | Junta os zips do INRC-II em `dados/`, com uma pasta por dataset |

## Instalação

```
pip install highspy swiglpk numba pandas matplotlib
```

Os dados vão numa pasta `dados/` com uma subpasta por dataset:

```
python organizar_dados.py ../dados ../test_datasets_json.zip ../datasets_json.zip ../hidden-JSON.zip
```

## Como rodar

```
python testes.py ../dados                                  # confere que está tudo certo (TUDO CERTO)
python exato.py ../dados/n005w4 0 1,2,3,3 60               # exato (HiGHS), 60 s
python grasp.py ../dados/n005w4 0 1,2,3,3 60               # GRASP, 60 s
python sa.py    ../dados/n005w4 0 1,2,3,3 60               # Simulated Annealing, 60 s
python fo.py    ../dados/n021w4 0 5,4,1,2 120              # SA + Fix-and-Optimize, 120 s
python rodar_experimentos.py --processos 6                 # conjunto final: 8 instâncias x 3 métodos x 3 sementes, 300 s (~1 h)
python relaxacao.py ../dados instancias_final.txt          # limite da relaxação linear
```

Na primeira execução, o numba compila o `nucleo.py` (alguns segundos); depois fica em cache.

Uma instância é dada por `pasta historico semanas`. Por exemplo, `n005w4 0 1,2,3,3` usa o histórico `H0-n005w4-0.json` e as semanas `WD-n005w4-1, -2, -3, -3`.

Para a Etapa 5 (modelo AMPL com Gurobi), rodem `include rodar_final.run;` no AMPL (troque `CFG` para escolher a configuração). Para dar mais tempo ao Gurobi, com o mesmo método:

```
python rodar_gurobi_longo.py --estimar --grupo final --tempos 900,1800,3600   # mostra quantas horas leva
python rodar_gurobi_longo.py --grupo teste --tempos 300,900,1800,3600
python rodar_gurobi_longo.py --grupo final --tempos 900,1800,3600
```

## Versão 4 (21/11/2026): estratégias sugeridas pelo professor

* **Desempate por gravidade** (`des`): quando dois movimentos têm o mesmo custo, decide a gravidade das violações. Ordem usada (`nucleo.GRAV_PADRAO`): cobertura (6) > folgas seguidas (5) > dias de trabalho seguidos (4) > fins de semana (3) > turnos seguidos e total de turnos (2) > pedidos de folga (1). No SA, um movimento de custo igual só é aceito se não piorar a gravidade; no VND do GRASP, um movimento de custo igual que reduz a gravidade conta como melhora.
* **Penalidade dinâmica** (`din`): o peso λ das violações hard (cobertura mínima, sucessão proibida) muda durante o SA conforme a viabilidade recente (Gendreau, Hertz e Laporte, 1994). Escala viável quase o lote todo → λ cai; inviável boa parte do lote → λ sobe. Isso produz uma oscilação estratégica em torno da fronteira da viabilidade. Nos últimos 10% do tempo λ volta a 10.000, e a melhor escala guardada é sempre viável.
* **GRASP amostral** (`amN`): em vez da RCL, sorteia N candidatos e pega o melhor deles ("sampled greedy", Resende e Ribeiro, 2016, cap. 7).
* Sem nenhuma opção, o código da versão 4 faz exatamente os mesmos movimentos da versão 3 (teste 6 de `testes.py`).
* A configuração final de cada metaheurística (`FINAL` em `consolidar.py`) foi escolhida na calibração (`calibracao/v4`), e as execuções finais ficam em `resultados/v4_*` (versão 4 e, para comparação na mesma máquina, a configuração da versão 3).

## Parâmetros principais

* **GRASP** (`grasp.py`): `alpha` = tamanho da RCL (0 = guloso puro, 1 = aleatório); padrão 0,15.
* **SA** (`sa.py`): `T0 = 40`, `Tf = 2` (calibrados em `calibracao/`, em instâncias fora do conjunto final).
* **F&O** (`fo.py`): `frac_inicial` = fração do tempo para o SA inicial (0,5); `L0 = 7` dias por janela; `k0` = enfermeiros por grupo; `sub_limite` = tempo máximo de cada subproblema (30 s). Quando uma passada inteira não melhora, `L += 7` e `k += 2`.

## Observações

* **Referências da literatura:** para as 40 instâncias estáticas, `experimentos.py` preenche `ub_literatura` (melhor solução publicada) e `gap_ub_lit_%`. Todas as de 4 semanas têm ótimo provado. Fonte: Legrain e Omer (2023), Les Cahiers du GERAD G-2023-02 (Tabelas 5 e 7).
* **Comparabilidade:** o horizonte é resolvido de uma vez, com toda a demanda conhecida. A competição resolve semana a semana, então os custos não são diretamente comparáveis com o ranking oficial.
* **Viabilidade:** um custo só vale se `viavel=True`, ou seja, sem violar cobertura mínima, sucessão proibida ou habilidade.
* **Mesma máquina:** compare métodos sempre com o mesmo tempo, 1 thread e na mesma máquina.
