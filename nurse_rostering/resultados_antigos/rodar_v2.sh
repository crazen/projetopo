#!/bin/sh
# Experimentos v2 (GRASP com VND local no ILS + SA + LNS): 6 processos, 300 s, 2 sementes, 1 thread.
cd "$(dirname "$0")"
PY=../.venv/Scripts/python.exe
for k in 1 2 3 4; do
  $PY -u experimentos.py --dados ../dados --instancias parte$k.txt --metodos grasp,sa --tempo 300 --sementes 2 --threads 1 --saida v2_gs_$k.csv > log_v2_gs_$k.txt 2>&1 &
done
$PY -u experimentos.py --dados ../dados --instancias parteA.txt --metodos lns --tempo 300 --sementes 2 --threads 1 --saida v2_lns_A.csv > log_v2_lns_A.txt 2>&1 &
$PY -u experimentos.py --dados ../dados --instancias parteB.txt --metodos lns --tempo 300 --sementes 2 --threads 1 --saida v2_lns_B.csv > log_v2_lns_B.txt 2>&1 &
wait
echo FIM
