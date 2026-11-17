# Resultados antigos (versão 2, até 15/11/2026)

Arquivos guardados só como histórico. **Não são usados** pelas tabelas e figuras atuais.

- `final_*.csv`, `log_final_*.txt`: primeira rodada do conjunto final. Só as linhas `exato` (HiGHS) continuam
  válidas; elas foram copiadas para `../resultados_highs_final.csv`.
- `v2_*.csv`, `resultados_v2.csv`, `comparacao_final.csv`, `tabela_*.csv`, `parte*.txt`, `rodar_v2.sh`: GRASP-ILS,
  SA e "LNS" da versão 2, em Python puro.

Por que foram substituídos (revisão de 16/11/2026):

1. A matheurística chamada de "LNS (fix-and-optimize)" sorteava a cada iteração um grupo de enfermeiros ou uma
   janela de dias e ajustava o tamanho da vizinhança. Isso é uma LNS com reparo por PLI, **não** um
   Fix-and-Optimize, que percorre de forma sistemática subproblemas de decomposições fixas até não melhorar mais
   (Helber e Sahling, 2010). Ela foi substituída por `fo.py`.
2. GRASP e SA eram Python puro (~50 mil movimentos/s). O GRASP completava só 2 ou 3 iterações em 300 s, o que
   não é um GRASP de fato (multi-partida). O custo incremental foi reescrito em `nucleo.py` (numba,
   ~1 milhão de movimentos/s, mesmo cálculo, conferido em `testes.py`).
