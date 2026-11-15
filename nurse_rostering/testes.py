"""testes.py - testes automaticos de correcao (rodar sempre que mudar o modelo ou as heuristicas).

  1. modelo x avaliador nas solucoes de referencia do INRC-II
  2. modelo x avaliador em escalas aleatorias (cobertura minima desligada para qualquer escala ser viavel)
  3. custo_rapido (usado pelo GRASP) x avaliador
  4. GRASP curto: o custo mantido incrementalmente bate com o avaliador

Uso:  python testes.py <pasta_com_os_datasets>
"""
import sys, os, glob, random
from inrc2 import load_instance, list_reference_instances, load_solution_dir, evaluate, nurse_breakdown
from custo_rapido import custo_enf
from exato import ModeloPLI
import grasp as G

if len(sys.argv) != 2:
    sys.exit(__doc__)
rng = random.Random(1)
instancias = []
for base in sorted(glob.glob(os.path.join(sys.argv[1], "n*"))):
    for h, wd, p in list_reference_instances(base):
        instancias.append((base, h, wd, p))
if not instancias:
    sys.exit("nenhuma instancia com solucao de referencia encontrada em " + sys.argv[1])
falhas = 0


def escala_aleatoria(inst):
    sched = [[None] * inst.D for _ in range(inst.N)]
    dens = rng.choice([0.3, 0.6, 0.9])
    for n in range(inst.N):
        prev = inst.hist[n]["last"]
        for d in range(inst.D):
            if rng.random() < dens:
                ok = [s for s in range(len(inst.shifts)) if not (prev >= 0 and inst.forb[prev][s])]
                s = prev if (prev in ok and rng.random() < 0.6) else rng.choice(ok)
                sched[n][d] = (s, rng.choice(sorted(inst.nurse_skills[n]))); prev = s
            else:
                prev = -1
    return sched


print("1) modelo x avaliador nas solucoes de referencia")
for base, h, wd, p in instancias:
    inst = load_instance(base, h, wd)
    sched = load_solution_dir(inst, p)
    custo = evaluate(inst, sched)[2]
    _, obj = ModeloPLI(inst).completar(sched)
    ok = obj is not None and abs(obj - custo) < 1e-6
    falhas += not ok
    print(f"   {inst.name:30s} avaliador={custo:5d} modelo={obj}  {'OK' if ok else 'FALHOU'}", flush=True)

print("2) modelo x avaliador em escalas aleatorias")
for base, h, wd, p in instancias:
    inst = load_instance(base, h, wd)
    inst.dmin = [[[0] * len(inst.skills) for _ in inst.shifts] for _ in range(inst.D)]
    m = ModeloPLI(inst); res = []
    for _ in range(3):
        sched = escala_aleatoria(inst)
        custo = evaluate(inst, sched)[2]
        _, obj = m.completar(sched)
        res.append(obj is not None and abs(obj - custo) < 1e-6)
    falhas += res.count(False)
    print(f"   {inst.name:30s} {res.count(True)}/3 OK", flush=True)

print("3) custo rapido x avaliador")
iguais = total = 0
for base, h, wd, p in instancias:
    inst = load_instance(base, h, wd)
    for _ in range(200):
        n = rng.randrange(inst.N); D = rng.randrange(1, inst.D + 1)
        sid = [rng.choice(range(-1, len(inst.shifts))) for _ in range(D)]
        b = nurse_breakdown(inst, n, [None if x < 0 else (x, 0) for x in sid])
        esperado = sum(v for k, v in b.items() if k != "succ") + 10000 * b["succ"]
        iguais += custo_enf(inst, n, sid, 10000) == esperado; total += 1
falhas += total - iguais
print(f"   {iguais}/{total} iguais")

print("4) GRASP curto: custo incremental x avaliador")
base, h, wd, p = instancias[0]
inst = load_instance(base, h, wd)
est = G.Estado(inst, *G.construir(inst, 0.15, rng))
G.vnd(est, rng, __import__("time").time() + 5)
custo = evaluate(inst, est.sched())[2]
hard_peso = est.total - custo
ok = hard_peso == 0 or hard_peso % G.GRANDE == 0
falhas += not ok
print(f"   incremental={est.total} avaliador={custo}  {'OK' if ok else 'FALHOU'}")

print("5) ILS (VND local) e Simulated Annealing: custo incremental x recalculo do zero")
import time as _t
from sa import sa as _sa
for base, h, wd, p in instancias[::3]:
    inst = load_instance(base, h, wd)
    est = G.Estado(inst, *G.construir(inst, 0.15, rng))
    G.vnd(est, rng, _t.time() + 3)
    est = G.fase_ils(est, rng, _t.time() + 3, 50, 4)
    ok_ils = est.total == G.Estado(inst, est.sid, est.skl).total
    r = _sa(inst, limite=3, semente=1, verbose=False)
    ok_sa = r["custo_incremental"] == r["custo"] if r["viavel"] else (r["custo_incremental"] - r["custo"]) % G.GRANDE == 0
    falhas += (not ok_ils) + (not ok_sa)
    print(f"   {inst.name:30s} ILS {'OK' if ok_ils else 'FALHOU'}   SA custo={r['custo']} viavel={r['viavel']} "
          f"{'OK' if ok_sa else 'FALHOU'}", flush=True)

print("\nTUDO CERTO" if falhas == 0 else f"\n{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
