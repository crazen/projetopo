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
| `nucleo.py` | O mesmo custo e os movimentos N1–N4 compilados com numba (~1 milhão de movimentos/s); usado por GRASP e SA |
| `grasp.py` | GRASP: construção gulosa-aleatorizada (RCL com `alpha`) + VND completo (N1 troca, N2 swap, N3 bloco, N4 swap de bloco) |
| `sa.py` | Simulated Annealing: um movimento aleatório de N1–N4 por passo, critério de Metropolis, resfriamento geométrico no tempo |
| `fo.py` | Matheurística Fix-and-Optimize: parte do SA e resolve em sequência subproblemas do `nurse.mod` (janelas de dias e grupos de enfermeiros) com o resto fixado |
| `experimentos.py` | Roda exato/GRASP/SA/F&O numa lista de instâncias e grava um CSV linha a linha |
| `rodar_experimentos.py` | Roda GRASP, SA e F&O nas 8 instâncias finais em paralelo (vários processos de 1 thread) e atualiza tabelas, figuras e PDFs |
| `consolidar.py` | Junta Gurobi, HiGHS, relaxação linear e heurísticas em `comparacao_final.csv` e gera as figuras |
| `testes.py` | Testes automáticos (deve terminar em `TUDO CERTO`) |
| `calibracao/` | Calibração de T0 e Tf do SA em 4 instâncias que **não** estão no conjunto final |
| `instancias_final.txt` | Conjunto final: 8 instâncias da literatura (30 a 60 enfermeiros, 4 e 8 semanas) |
| `instancias_literatura.txt`, `referencias_literatura.csv` | As 40 instâncias estáticas de Legrain e Omer (2023) e os melhores limites publicados |
| `resultados/` | Uma linha de CSV (+ convergência e log) por execução das heurísticas |
| `resultados_antigos/` | Resultados da versão anterior (só histórico; ver o LEIAME de lá) |
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

Para a Etapa 5 (modelo AMPL com Gurobi), rodem `include rodar_final.run;` no AMPL (troque `CFG` para escolher a configuração).

## Parâmetros principais

* **GRASP** (`grasp.py`): `alpha` = tamanho da RCL (0 = guloso puro, 1 = aleatório); padrão 0,15.
* **SA** (`sa.py`): `T0 = 40`, `Tf = 2` (calibrados em `calibracao/`, em instâncias fora do conjunto final).
* **F&O** (`fo.py`): `frac_inicial` = fração do tempo para o SA inicial (0,5); `L0 = 7` dias por janela; `k0` = enfermeiros por grupo; `sub_limite` = tempo máximo de cada subproblema (30 s). Quando uma passada inteira não melhora, `L += 7` e `k += 2`.

## Observações

* **Referências da literatura:** para as 40 instâncias estáticas, `experimentos.py` preenche `ub_literatura` (melhor solução publicada) e `gap_ub_lit_%`. Todas as de 4 semanas têm ótimo provado. Fonte: Legrain e Omer (2023), Les Cahiers du GERAD G-2023-02 (Tabelas 5 e 7).
* **Comparabilidade:** o horizonte é resolvido de uma vez, com toda a demanda conhecida. A competição resolve semana a semana, então os custos não são diretamente comparáveis com o ranking oficial.
* **Viabilidade:** um custo só vale se `viavel=True`, ou seja, sem violar cobertura mínima, sucessão proibida ou habilidade.
* **Mesma máquina:** compare métodos sempre com o mesmo tempo, 1 thread e na mesma máquina.
