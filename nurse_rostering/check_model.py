"""check_model.py - prova de que o modelo nurse.mod calcula o mesmo custo que o avaliador oficial.

Para cada instancia de teste que vem com solucao de referencia (pastas Solution_H_*), fixa as variaveis x
na solucao de referencia, resolve o resto do modelo e compara o objetivo com o avaliador (inrc2.evaluate).
Se todas derem OK, o modelo representa corretamente as regras e os custos do INRC-II.

Uso:  python check_model.py <pasta_com_os_datasets>      (ex.: dados, contendo n005w4, n012w8, n021w4)
"""
import sys, os, glob
from inrc2 import load_instance, list_reference_instances, load_solution_dir, evaluate, is_feasible
from exato import ModeloPLI

if len(sys.argv) != 2:
    sys.exit(__doc__)
ok = tot = 0
for base in sorted(glob.glob(os.path.join(sys.argv[1], "n*"))):
    for h, wd, p in list_reference_instances(base):
        inst = load_instance(base, h, wd)
        sched = load_solution_dir(inst, p)
        hard, _, custo = evaluate(inst, sched)
        _, obj = ModeloPLI(inst).completar(sched)
        igual = obj is not None and abs(obj - custo) < 1e-6
        ok += igual; tot += 1
        print(f"{inst.name:30s} avaliador={custo:6d} (hard ok={is_feasible(hard)})  modelo={obj}  "
              f"{'OK' if igual else 'DIFERENTE'}", flush=True)
print(f"\n{ok}/{tot} instancias conferem")
