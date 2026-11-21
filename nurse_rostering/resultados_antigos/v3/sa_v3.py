"""sa.py - metaheuristica Simulated Annealing (SA) para o Nurse Rostering (INRC-II).

Simulated Annealing (Kirkpatrick, Gelatt e Vecchi, 1983) imita o resfriamento lento de um metal:
  1. Parte de uma escala construida pela construcao gulosa-aleatorizada do GRASP.
  2. Repete, ate acabar o tempo:
       - sorteia UM movimento aleatorio de uma das vizinhancas:
           N1 troca (40%), N3 bloco de 2-5 dias (20%), N2 swap de um dia (20%), N4 swap de bloco (20%);
       - calcula o delta de custo de forma incremental (so o(s) enfermeiro(s) e a cobertura afetados);
       - se delta <= 0, aceita; se delta > 0, aceita com probabilidade exp(-delta / T)   (criterio de Metropolis).
  3. A temperatura T cai geometricamente com o TEMPO decorrido:  T(t) = T0 * (Tf / T0) ^ (t / limite).
     No inicio (T alta) aceita pioras com frequencia e explora; no fim (T ~ Tf) quase so aceita melhoras.
  4. Guarda a melhor escala encontrada.

Os movimentos e o custo incremental estao em nucleo.py, compilado com numba (~1 milhao de movimentos/s).
As restricoes hard (cobertura minima, sucessao proibida) entram no custo com peso GRANDE (10000); com
T <= T0 << GRANDE, uma piora hard praticamente nunca e aceita depois que a escala fica viavel.
Referencia de aplicacao ao mesmo problema: Ceschia, Guido e Schaerf (2020), Annals of Operations Research 288.

Uso:  python sa.py <pasta_dataset> <h> <semanas> [limite_s] [semente] [T0] [Tf]
Ex.:  python sa.py ../dados/n005w4 0 1,2,3,3 60 1
"""
import random, sys, time
import numpy as np
from inrc2 import load_instance, evaluate, is_feasible, print_schedule
import nucleo as C
from grasp import construir

LOTE = 20000      # movimentos por chamada ao codigo compilado (a temperatura e o relogio sao atualizados entre lotes)


def sa(inst, limite=60, semente=0, T0=40.0, Tf=2.0, alpha=0.15, verbose=True, inicial=None):
    """inicial (opcional): escala (sched) de partida; senao, usa a construcao do GRASP."""
    rng = random.Random(semente)
    t0 = time.time()
    P = C.dados(inst)
    sid, skl = C.de_sched(inicial) if inicial is not None else construir(inst, alpha, rng)
    E = C.Escala(P, sid, skl)
    C.semear(semente)
    best_sid, best_skl, best_tot = E.sid.copy(), E.skl.copy(), E.tot.copy()
    historico = [(round(time.time() - t0, 2), int(E.tot[0]))]
    movs = aceitos = 0
    while True:
        agora = time.time() - t0
        if agora >= limite:
            break
        T = T0 * (Tf / T0) ** (agora / limite)
        a, m = C.sa_passos(P, E.sid, E.skl, E.cnt, E.ncost, E.tot, best_sid, best_skl, best_tot, LOTE, T)
        movs += LOTE; aceitos += a
        if m:
            historico.append((round(time.time() - t0, 2), int(best_tot[0])))
            if verbose and len(historico) % 20 == 0:
                print(f"  t={time.time() - t0:6.1f}s  T={T:6.2f}  melhor={best_tot[0]}", flush=True)
    melhor = C.Escala(P, best_sid, best_skl)
    sched = melhor.sched()
    hard, comp, custo = evaluate(inst, sched)
    if is_feasible(hard) and custo != best_tot[0]:
        print(f"  AVISO: custo incremental ({best_tot[0]}) != avaliador ({custo})")
    return dict(sched=sched, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                iteracoes=movs, aceitos=aceitos, tempo=time.time() - t0, historico=historico,
                custo_incremental=int(best_tot[0]))


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
