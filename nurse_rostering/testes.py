"""testes.py - testes automaticos de correcao (rodar sempre que mudar o modelo ou as heuristicas).

  1. modelo x avaliador nas solucoes de referencia do INRC-II
  2. modelo x avaliador em escalas aleatorias (cobertura minima desligada para qualquer escala ser viavel)
  3. custo_rapido (usado pela construcao do GRASP) x avaliador
  4. nucleo compilado (numba, usado por GRASP e SA) x custo_rapido; custo incremental x recalculo do zero
  5. GRASP, SA e Fix-and-Optimize curtos: o custo reportado bate com o avaliador e o F&O nunca piora
     (tambem com as opcoes novas: GRASP amostral, desempate por gravidade e penalidade dinamica no SA)
  6. regressao: sem as opcoes novas, o nucleo da versao 4 faz EXATAMENTE os mesmos movimentos que o da versao 3
     (resultados_antigos/v3/nucleo_v3.py), com a mesma semente

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

print("4) nucleo compilado (numba) x custo rapido, e custo total incremental x recalculo")
import numpy as np
import nucleo as C
ok = tot = 0
for base, h, wd, p in instancias:
    inst = load_instance(base, h, wd); P = C.dados(inst)
    for _ in range(200):
        n = rng.randrange(inst.N); D = rng.randrange(1, inst.D + 1)
        sid = [rng.choice(range(-1, len(inst.shifts))) for _ in range(D)]
        ok += C.custo_linha(P, n, np.array(sid, np.int64)) == custo_enf(inst, n, sid, C.GRANDE); tot += 1
        a, b, g = C.custo_linha3(P._replace(grav=C.GRAV_NEUTRA), n, np.array(sid, np.int64))
        ok += g == a; tot += 1                       # gravidade neutra = custo soft
    for lam, des in [(float(C.GRANDE), False), (5.0, True)]:
        E = C.Escala(P, *G.construir(inst, 0.15, rng))
        bs, bk, bt = E.sid.copy(), E.skl.copy(), E.tot.copy()
        C.semear(1)
        C.sa_passos(P, *E.estado(), bs, bk, bt, 100000, 20.0, lam, des)
        ok += tuple(E.tot) == E.recalcular(); tot += 1
        C.vnd(P, *E.estado(), des)
        ok += tuple(E.tot) == E.recalcular(); tot += 1
falhas += tot - ok
print(f"   {ok}/{tot} iguais")

print("5) GRASP, SA e Fix-and-Optimize curtos: custo reportado x avaliador")
from sa import sa as _sa
from fo import fo as _fo
for base, h, wd, p in instancias[::3]:
    inst = load_instance(base, h, wd)
    novas = [i % 2 == 1 for i in range(2)]
    for nova in novas:
        kw_g = dict(amostra=3, desempate=True) if nova else {}
        kw_s = dict(penalidade="dinamica", desempate=True) if nova else {}
        rg = G.grasp(inst, limite=3, semente=1, verbose=False, **kw_g)
        rs = _sa(inst, limite=3, semente=1, verbose=False, **kw_s)
        rf = _fo(inst, limite=20, semente=1, frac_inicial=0.25, verbose=False, sa_kw=kw_s)
        ok_g = rg["custo_incremental"] == rg["custo"] if rg["viavel"] else (rg["custo_incremental"] - rg["custo"]) % G.GRANDE == 0
        ok_s = rs["viavel"] and rs["custo_incremental"] == rs["custo"]
        ok_f = rf["custo"] <= rf["custo_inicial"] and all(b[1] <= a[1] for a, b in zip(rf["historico"], rf["historico"][1:]))
        falhas += (not ok_g) + (not ok_s) + (not ok_f)
        print(f"   {inst.name:30s} {'v4' if nova else 'v3'}  GRASP={rg['custo']} {'OK' if ok_g else 'FALHOU'}   "
              f"SA={rs['custo']} {'OK' if ok_s else 'FALHOU'}   F&O={rf['custo_inicial']}->{rf['custo']} "
              f"{'OK' if ok_f else 'FALHOU'}", flush=True)

print("6) regressao: nucleo v4 sem as opcoes novas = nucleo v3 (mesmos movimentos, mesma semente)")
import importlib.util
esp = importlib.util.spec_from_file_location("nucleo_v3", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                                    "resultados_antigos", "v3", "nucleo_v3.py"))
V3 = importlib.util.module_from_spec(esp); esp.loader.exec_module(V3)
ok = tot = 0
for base, h, wd, p in instancias[::2]:
    inst = load_instance(base, h, wd)
    sid, skl = G.construir(inst, 0.15, random.Random(7))
    P4 = C.dados(inst); E4 = C.Escala(P4, sid, skl)
    P3 = V3.dados(inst); E3 = V3.Escala(P3, sid, skl)
    b4 = (E4.sid.copy(), E4.skl.copy(), E4.tot.copy()); b3 = (E3.sid.copy(), E3.skl.copy(), E3.tot.copy())
    for T in (30.0, 5.0):
        C.semear(11); C.sa_passos(P4, *E4.estado(), *b4, 200000, T, float(C.GRANDE), False)
        V3.semear(11); V3.sa_passos(P3, E3.sid, E3.skl, E3.cnt, E3.ncost, E3.tot, *b3, 200000, T)
        ok += bool((E4.sid == E3.sid).all() and (E4.skl == E3.skl).all() and E4.custo == E3.tot[0]); tot += 1
    C.semear(5); C.vnd(P4, *E4.estado(), False)
    V3.semear(5); V3.vnd(P3, E3.sid, E3.skl, E3.cnt, E3.ncost, E3.tot)
    ok += bool((E4.sid == E3.sid).all() and E4.custo == E3.tot[0]); tot += 1
falhas += tot - ok
print(f"   {ok}/{tot} iguais")

print("\nTUDO CERTO" if falhas == 0 else f"\n{falhas} FALHA(S)")
sys.exit(1 if falhas else 0)
