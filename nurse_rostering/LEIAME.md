# Nurse Rostering (INRC-II): PLI, GRASP e matheurística

Escalonamento de enfermagem com as regras do INRC-II, resolvendo o horizonte inteiro (4 ou 8 semanas) de uma vez.

## Arquivos

| Arquivo | O que é |
|---|---|
| `nurse.mod` | Modelo de PLI em AMPL (regras hard H1–H4, penalidades S1–S7) |
| `rodar.run` | Script AMPL: resolve as instâncias de `dat/` e grava `resultados_ampl.csv` |
| `dat/` | Dados das 9 instâncias de teste em formato AMPL |
| `gen_dat.py` | Converte uma instância JSON do INRC-II em `.dat` |
| `inrc2.py` | Leitura das instâncias e avaliador de custo (mesmo cálculo do validador oficial) |
| `exato.py` | Método exato: `nurse.mod` traduzido pelo GLPK e resolvido pelo HiGHS (sem precisar de licença AMPL) |
| `grasp.py` | GRASP: construção gulosa-aleatorizada + VND (4 vizinhanças) + fase ILS |
| `custo_rapido.py` | Custo de um enfermeiro em uma passada (usado pelo GRASP) |
| `lns.py` | Matheurística fix-and-optimize: parte do GRASP e reotimiza pedaços com o solver |
| `experimentos.py` | Roda os métodos numa lista de instâncias e grava `resultados.csv` |
| `check_model.py` | Prova de correção: modelo × avaliador nas soluções de referência |
| `testes.py` | Testes automáticos (modelo, avaliador rápido, escalas aleatórias) |
| `instancias.txt` | Lista curta: 3 instâncias de teste |
| `instancias_final.txt` | Conjunto final: 8 instâncias da literatura (30 a 60 enfermeiros, 4 e 8 semanas) |
| `instancias_literatura.txt` | As 40 instâncias estáticas de Legrain, Omer e Rosat (GERAD G-2023-02) |
| `referencias_literatura.csv` | Melhores limites inferior e superior publicados para essas 40 instâncias |
| `rodar_final.run` | Script AMPL do conjunto final (300 s por instância) |
| `organizar_dados.py` | Junta os zips do INRC-II em `dados/`, com uma pasta por dataset |

## Instalação

```
pip install highspy swiglpk
```

Os dados vão numa pasta `dados/` com uma subpasta por dataset. O `organizar_dados.py` monta isso a partir dos zips do site do INRC-II (teste, competição, hidden e extended):

```
python organizar_dados.py ../dados testdatasets_json.zip datasets_json.zip hidden-JSON.zip late-extended-dataset.zip
```

## Como rodar

```
python testes.py dados                                   # confere que está tudo certo
python exato.py dados/n005w4 0 1,2,3,3 60                # exato, 60 s
python grasp.py dados/n005w4 0 1,2,3,3 60                # GRASP, 60 s
python lns.py   dados/n021w4 0 5,4,1,2 120               # matheurística, 120 s
python experimentos.py --dados dados --tempo 60          # todos os métodos, todas as instâncias de teste
python experimentos.py --dados dados --instancias instancias.txt --tempo 300 --sementes 3
```

Para o conjunto final, comparável com a literatura:

```
python experimentos.py --dados dados --instancias instancias_final.txt --tempo 300 --sementes 2 --saida resultados_final.csv
```

Isso leva cerca de 3,5 h. O CSV é gravado linha a linha, então dá para rodar em partes.

Uma instância é dada por `pasta historico semanas`. Por exemplo, `n005w4 0 1,2,3,3` usa o histórico `H0-n005w4-0.json` e as semanas `WD-n005w4-1, -2, -3, -3`. Os conjuntos de teste trazem soluções de referência para as combinações das pastas `Solution_H_*`. Para as instâncias da competição, escolham o histórico (0 a 2) e uma sequência de semanas (0 a 9).

Para a Etapa 5 (modelo AMPL), rodem `rodar.run` no AMPL. Para instâncias maiores, gerem o `.dat` com `gen_dat.py`. O AMPL gratuito sem licença só aceita até 500 variáveis, e estas instâncias têm milhares. Usem a licença Community Edition (gratuita, em ampl.com/ce) ou a acadêmica. O `exato.py` resolve exatamente o mesmo modelo sem AMPL.

## Parâmetros principais

* **GRASP** (`grasp.py`):
  * `alpha`: tamanho da RCL. 0 é guloso puro, 1 é aleatório.
  * `ils`: número de perturbações seguidas sem melhora antes de reconstruir. Com 0, vira GRASP clássico.
  * `forca`: número de movimentos por perturbação.
  * `frac_ils`: tempo máximo de cada fase ILS, como fração do tempo total.
* **LNS** (`lns.py`):
  * `frac_grasp`: fração do tempo dada ao GRASP inicial.
  * `sub_limite`: tempo máximo de cada subproblema.
  * O tamanho da vizinhança se ajusta sozinho.

## Observações

* **Referências da literatura:** para as 40 instâncias estáticas, `experimentos.py` preenche `ub_literatura` (melhor solução publicada) e `gap_ub_lit_%`. Todas as de 4 semanas têm ótimo provado. Fonte: Legrain, Omer e Rosat, "A rotation-based branch-and-price approach for the nurse scheduling problem", GERAD G-2023-02 (Tabelas 5 e 7). Confiram no artigo antes de citar.
* **Comparabilidade:** o horizonte é resolvido de uma vez, com toda a demanda conhecida. A competição resolve semana a semana, então os custos não são diretamente comparáveis com o ranking oficial. As soluções de referência servem só como ordem de grandeza.
* **Viabilidade:** um custo só vale se `viavel=True`, ou seja, sem violar cobertura mínima, sucessão proibida ou habilidade.
