"""sa.py - metaheuristica Simulated Annealing (SA) para o Nurse Rostering (INRC-II).

Simulated Annealing (Kirkpatrick, Gelatt e Vecchi, 1983) imita o resfriamento lento de um metal:
  1. Parte de uma escala construida pela mesma construcao gulosa-aleatorizada do GRASP.
  2. Repete, ate acabar o tempo:
       - sorteia UM movimento aleatorio de uma das vizinhancas do GRASP:
           N1 troca (40%), N2 swap de um dia (20%), N3 bloco (20%), N4 swap de bloco (20%);
       - calcula o delta de custo de forma incremental (so o(s) enfermeiro(s) e a cobertura afetados);
       - se delta <= 0, aceita; se delta > 0, aceita com probabilidade exp(-delta / T)   (criterio de Metropolis).
  3. A temperatura T cai geometricamente com o TEMPO decorrido:  T(t) = T0 * (Tf / T0) ^ (t / limite).
     No inicio (T alta) aceita pioras com frequencia e explora; no fim (T ~ Tf) quase so aceita melhoras.
  4. Guarda a melhor escala encontrada.

As restricoes hard (cobertura minima, sucessao proibida) entram no custo com peso GRANDE (10000), como no GRASP;
com T <= T0 << GRANDE, uma piora hard praticamente nunca e aceita depois que a escala fica viavel.
Referencia de aplicacao ao mesmo problema: Ceschia, Guido e Schaerf (2020), Annals of Operations Research 288.

Uso:  python sa.py <pasta_dataset> <h> <semanas> [limite_s] [semente] [T0] [Tf]
Ex.:  python sa.py dados/n005w4 0 1,2,3,3 60 1
"""
import math, random, sys, time
from inrc2 import load_instance, evaluate, is_feasible, print_schedule
from grasp import Estado, construir, mov_bloco, aplicar_bloco, mov_swap, aplicar_swap


def sa(inst, limite=60, semente=0, T0=40.0, Tf=2.0, alpha=0.15, verbose=True):
    rng = random.Random(semente)
    t0 = time.time(); prazo = t0 + limite
    est = Estado(inst, *construir(inst, alpha, rng))
    N, D, S = inst.N, inst.D, est.S
    melhor_total = est.total
    melhor = ([r[:] for r in est.sid], [r[:] for r in est.skl])
    historico = [(0.0, est.total)]
    movs = aceitos = 0
    T = T0
    while True:
        if movs % 1000 == 0:                       # atualiza a temperatura e confere o tempo
            agora = time.time()
            if agora >= prazo:
                break
            T = T0 * (Tf / T0) ** ((agora - t0) / limite)
        movs += 1
        r = rng.random()
        if r < 0.6:                                # N1 (L=1) ou N3 (L=2..5): mudar a atribuicao de um enfermeiro
            L = 1 if r < 0.4 else rng.randint(2, 5)
            n, d0, s = rng.randrange(N), rng.randrange(D - L + 1), rng.randrange(-1, S)
            mov = mov_bloco(est, n, d0, L, s)
            if mov is None:
                continue
            delta = mov[0]
            if delta <= 0 or rng.random() < math.exp(-delta / T):
                aplicar_bloco(est, n, d0, L, s, mov); aceitos += 1
            else:
                continue
        else:                                      # N2 (L=1) ou N4 (L=2..7): dois enfermeiros trocam atribuicoes
            L = 1 if r < 0.8 else rng.choice((2, 3, 4, 5, 7))
            n1, n2 = rng.sample(range(N), 2); d0 = rng.randrange(D - L + 1)
            mov = mov_swap(est, n1, n2, d0, L)
            if mov is None:
                continue
            delta = mov[0]
            if delta <= 0 or rng.random() < math.exp(-delta / T):
                aplicar_swap(est, n1, n2, d0, L, mov); aceitos += 1
            else:
                continue
        if est.total < melhor_total - 1e-9:
            melhor_total = est.total
            melhor = ([r[:] for r in est.sid], [r[:] for r in est.skl])
            historico.append((round(time.time() - t0, 2), est.total))
            if verbose and len(historico) % 50 == 0:
                print(f"  t={time.time() - t0:6.1f}s  T={T:6.2f}  melhor={melhor_total}", flush=True)
    final = Estado(inst, *melhor)
    sched = final.sched()
    hard, comp, custo = evaluate(inst, sched)
    if is_feasible(hard) and custo != final.total:
        print(f"  AVISO: custo incremental ({final.total}) != avaliador ({custo})")
    return dict(sched=sched, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                iteracoes=movs, aceitos=aceitos, tempo=time.time() - t0, historico=historico,
                custo_incremental=melhor_total)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    semente = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    T0 = float(sys.argv[6]) if len(sys.argv) > 6 else 40.0
    Tf = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0
    inst = load_instance(folder, h, wds)
    r = sa(inst, limite, semente, T0, Tf)
    print(f"{inst.name}: custo={r['custo']} viavel={r['viavel']} movimentos={r['iteracoes']} "
          f"aceitos={r['aceitos']} tempo={r['tempo']:.1f}s")
    print("  componentes:", r["componentes"])
    print_schedule(inst, r["sched"])
