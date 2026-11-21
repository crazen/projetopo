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
Referencia de aplicacao ao mesmo problema: Ceschia, Guido e Schaerf (2020), Annals of Operations Research 288.

Restricoes hard (cobertura minima H2, sucessao proibida H3): o SA minimiza  soft + lam * (numero de violacoes hard).
  penalidade="fixa"     (versao 3): lam = 10000 sempre. Com T <= 40, o SA nunca aceita violar uma regra hard e
                        so anda por escalas viaveis.
  penalidade="dinamica" (versao 4, sugestao do professor): lam se ajusta pela VIABILIDADE RECENTE, como em
                        Gendreau, Hertz e Laporte (1994): a cada lote de movimentos, se a escala ficou viavel em
                        quase todo o lote (> viab_alta), lam diminui (lam /= beta) e o SA pode atravessar escalas
                        inviaveis; se ficou inviavel em boa parte (< viab_baixa), lam aumenta (lam *= beta) e o SA
                        e empurrado de volta. O resultado e uma OSCILACAO ESTRATEGICA em torno da fronteira da
                        viabilidade. Na fase final (ultimos frac_final do tempo) lam volta a 10000. A melhor escala
                        guardada e sempre a melhor VIAVEL.
Desempate (desempate=True, sugestao do professor): um movimento de custo igual (delta = 0) so e aceito se nao
  piorar a GRAVIDADE (nucleo.GRAV_PADRAO: cobertura > folgas > dias de trabalho seguidos > fins de semana >
  turnos e totais > pedidos); entre duas melhores escalas de mesmo custo, fica a de menor gravidade.

Uso:  python sa.py <pasta_dataset> <h> <semanas> [limite_s] [semente] [T0] [Tf] [fixa|dinamica] [0|1 desempate]
Ex.:  python sa.py ../dados/n005w4 0 1,2,3,3 60 1 40 2 dinamica 1
"""
import random, sys, time
import numpy as np
from inrc2 import load_instance, evaluate, is_feasible, print_schedule
import nucleo as C
from grasp import construir

LOTE = 20000      # movimentos por chamada ao codigo compilado (temperatura, lam e relogio mudam entre lotes)


def sa(inst, limite=60, semente=0, T0=40.0, Tf=2.0, alpha=0.15, verbose=True, inicial=None,
       penalidade="fixa", desempate=False, lam_min=1.0, beta=1.1, viab_alta=0.9, viab_baixa=0.5,
       frac_final=0.1, grav=None):
    """inicial (opcional): escala (sched) de partida; senao, usa a construcao do GRASP.
    penalidade: 'fixa' (lam = 10000) ou 'dinamica' (lam entre lam_min e 10000, ajustado pela viabilidade recente).
    desempate: movimentos de mesmo custo decididos pela gravidade das violacoes."""
    rng = random.Random(semente)
    t0 = time.time()
    P = C.dados(inst, grav)
    sid, skl = C.de_sched(inicial) if inicial is not None else construir(inst, alpha, rng)
    E = C.Escala(P, sid, skl)
    C.semear(semente)
    best_sid, best_skl, best_tot = E.sid.copy(), E.skl.copy(), E.tot.copy()
    historico = [(round(time.time() - t0, 2), int(E.tot[0]) if E.tot[1] == 0 else float("inf"))]
    movs = aceitos = viaveis = 0
    lam = float(C.GRANDE); lams = []
    dinamica = penalidade == "dinamica"
    while True:
        agora = time.time() - t0
        if agora >= limite:
            break
        T = T0 * (Tf / T0) ** (agora / limite)
        a, m, v = C.sa_passos(P, *E.estado(), best_sid, best_skl, best_tot, LOTE, T, lam, desempate)
        movs += LOTE; aceitos += a; viaveis += v
        if dinamica:                                     # penalidade dinamica pela viabilidade recente
            if agora >= (1 - frac_final) * limite:
                lam = float(C.GRANDE)
            elif v > viab_alta * LOTE:
                lam = max(lam_min, lam / beta)
            elif v < viab_baixa * LOTE:
                lam = min(float(C.GRANDE), lam * beta)
            lams.append(lam)
        if m and best_tot[1] == 0:
            historico.append((round(time.time() - t0, 2), int(best_tot[0])))
            if verbose and len(historico) % 20 == 0:
                print(f"  t={time.time() - t0:6.1f}s  T={T:6.2f}  lam={lam:8.1f}  melhor={best_tot[0]}", flush=True)
    melhor = C.Escala(P, best_sid, best_skl)
    sched = melhor.sched()
    hard, comp, custo = evaluate(inst, sched)
    if is_feasible(hard) and custo != best_tot[0]:
        print(f"  AVISO: custo incremental ({best_tot[0]}) != avaliador ({custo})")
    return dict(sched=sched, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                iteracoes=movs, aceitos=aceitos, frac_viavel=viaveis / max(1, movs), tempo=time.time() - t0,
                historico=historico, custo_incremental=int(best_tot[0]),
                lam_mediana=float(np.median(lams)) if lams else float(C.GRANDE))


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    semente = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    T0 = float(sys.argv[6]) if len(sys.argv) > 6 else 40.0
    Tf = float(sys.argv[7]) if len(sys.argv) > 7 else 2.0
    pen = sys.argv[8] if len(sys.argv) > 8 else "fixa"
    des = len(sys.argv) > 9 and sys.argv[9] == "1"
    inst = load_instance(folder, h, wds)
    r = sa(inst, limite, semente, T0, Tf, penalidade=pen, desempate=des)
    print(f"{inst.name}: custo={r['custo']} viavel={r['viavel']} movimentos={r['iteracoes']} "
          f"aceitos={r['aceitos']} viavel em {100 * r['frac_viavel']:.0f}% dos passos "
          f"(lam mediano {r['lam_mediana']:.0f}) tempo={r['tempo']:.1f}s")
    print("  componentes:", r["componentes"])
    print_schedule(inst, r["sched"])
