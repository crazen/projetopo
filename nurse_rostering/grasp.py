"""grasp.py - metaheuristica GRASP com busca local VND para o Nurse Rostering (INRC-II).

GRASP (Greedy Randomized Adaptive Search Procedure; Feo e Resende, 1995) repete, ate acabar o tempo:
  1. CONSTRUCAO gulosa-aleatorizada: monta a escala dia a dia; para cada vaga de demanda (turno, habilidade)
     calcula o custo incremental de cada enfermeiro candidato e sorteia um da Lista Restrita de Candidatos:
        RCL = { candidatos com custo <= c_min + alpha * (c_max - c_min) }
     alpha = 0 -> guloso puro (sempre o melhor);  alpha = 1 -> totalmente aleatorio.
     Variante AMOSTRAL ("sampled greedy", Resende e Ribeiro, 2016, cap. 7; sugestao do professor): em vez da
     RCL, sorteia uma amostra de p candidatos e escolhe, de forma gulosa, o melhor da amostra
     (p inteiro >= 1 = numero de candidatos; 0 < p < 1 = fracao dos candidatos).
  2. BUSCA LOCAL VND (Variable Neighborhood Descent; Mladenovic e Hansen, 1997), da vizinhanca mais barata
     para a mais cara, com primeira melhora e ordem aleatoria dos movimentos:
        N1 troca : muda a atribuicao de um enfermeiro em um dia (outro turno/habilidade, ou folga)
        N2 swap  : dois enfermeiros trocam suas atribuicoes em um dia (a cobertura nao muda)
        N3 bloco : um enfermeiro recebe o mesmo turno (ou folga) em L dias seguidos (L = 2..5)
        N4 swap de bloco : dois enfermeiros trocam suas atribuicoes em L dias seguidos (L = 2, 3, 4, 5, 7)
     Quando uma vizinhanca encontra melhora, volta para N1; termina num otimo local das quatro vizinhancas.
     As vizinhancas sao percorridas POR COMPLETO (nucleo.py, compilado com numba).
     Com desempate=True (sugestao do professor), um movimento de mesmo custo que reduz a GRAVIDADE das
     violacoes (nucleo.GRAV_PADRAO) tambem e aceito: a busca anda no plato rumo a violacoes menos graves.
  3. Guarda a melhor solucao encontrada em todas as iteracoes.
As iteracoes sao independentes: a diversificacao vem so da aleatorizacao da construcao (alpha).

Representacao: sid[n][d] = turno (-1 = folga) e skl[n][d] = habilidade usada (-1 = folga).
Restricoes hard (cobertura minima, sucessao proibida) entram no custo com peso GRANDE; a busca as elimina
primeiro. Habilidade (H4) e um turno por dia (H1) sao garantidos pela propria representacao.

Uso:  python grasp.py <pasta_dataset> <h> <semanas> [limite_s] [alpha] [semente] [amostra p] [0|1 desempate]
Ex.:  python grasp.py ../dados/n005w4 0 1,2,3,3 30 0.15 1 3 1
"""
import math, sys, time, random
from inrc2 import load_instance, evaluate, is_feasible, print_schedule, W_S1, W_TOTAL
from custo_rapido import custo_enf
import nucleo as C

GRANDE = C.GRANDE        # peso de cada violacao hard dentro da heuristica


# ==================================================================== construcao
def construir(inst, alpha, rng, peso_ritmo=W_TOTAL / 2, amostra=None):
    """Constroi uma escala dia a dia (gulosa-aleatorizada).
    Custo incremental de colocar o enfermeiro n no turno s no dia d =
        custo_enf(escala parcial dos dias 0..d com s em d) - custo_enf(mesma escala com folga em d)
      + peso_ritmo * (quanto n ficaria adiantado em relacao ao ritmo medio de turnos do seu contrato)."""
    N, D, S, K = inst.N, inst.D, len(inst.shifts), len(inst.skills)
    sid = [[-1] * D for _ in range(N)]
    skl = [[-1] * D for _ in range(N)]
    trabalhados = [0] * N
    aptos = [sum(1 for n in range(N) if k in inst.nurse_skills[n]) for k in range(K)]
    for d in range(D):
        g = [[0.0] * S for _ in range(N)]
        for n in range(N):
            parcial = sid[n][:d + 1]                    # dia d ainda e folga
            base = custo_enf(inst, n, parcial, GRANDE)
            c = inst.ct[n]
            ritmo = (c["minA"] + c["maxA"]) / 2 * (d + 1) / D
            adiantado = peso_ritmo * (inst.hist[n]["nA"] + trabalhados[n] + 1 - ritmo)
            for s in range(S):
                parcial[d] = s
                g[n][s] = custo_enf(inst, n, parcial, GRANDE) - base + adiantado
        livre = [True] * N
        ordem = sorted(((s, k) for s in range(S) for k in range(K)), key=lambda sk: (aptos[sk[1]], rng.random()))
        vagas = [(s, k, True) for (s, k) in ordem for _ in range(inst.dmin[d][s][k])]
        vagas += [(s, k, False) for (s, k) in ordem for _ in range(inst.dopt[d][s][k] - inst.dmin[d][s][k])]
        for (s, k, obrigatoria) in vagas:
            cand = [(g[n][s], n) for n in range(N) if livre[n] and k in inst.nurse_skills[n]]
            if not obrigatoria:                         # vaga opcional: so se compensar a penalidade S1 (30)
                cand = [(c, n) for (c, n) in cand if c < W_S1]
            if not cand:
                continue
            if amostra:                                 # gulosa-amostral: o melhor de p sorteados
                p = amostra if amostra >= 1 else max(1, math.ceil(amostra * len(cand)))
                am = rng.sample(cand, min(int(p), len(cand)))
                n = min(am, key=lambda cn: cn[0])[1]
            else:                                       # RCL classica
                cmin = min(c for c, _ in cand); cmax = max(c for c, _ in cand)
                rcl = [n for c, n in cand if c <= cmin + alpha * (cmax - cmin)]
                n = rng.choice(rcl)
            sid[n][d], skl[n][d] = s, k
            livre[n] = False; trabalhados[n] += 1
    return sid, skl


# ==================================================================== GRASP
def grasp(inst, limite=60, alpha=0.15, semente=0, verbose=True, amostra=None, desempate=False, grav=None):
    """Executa o GRASP por 'limite' segundos. Retorna a melhor escala e o historico de convergencia."""
    rng = random.Random(semente)
    t0 = time.time(); prazo = t0 + limite
    P = C.dados(inst, grav)
    C.semear(semente)
    melhor, it, historico = None, 0, []
    custos_constr, custos_vnd = [], []
    while time.time() < prazo:
        E = C.Escala(P, *construir(inst, alpha, rng, amostra=amostra))
        c_constr = E.custo
        C.vnd(P, *E.estado(), desempate)
        if time.time() > prazo and melhor is not None:
            break                                   # iteracao terminou depois do prazo: descartada
        it += 1
        custos_constr.append(c_constr); custos_vnd.append(E.custo)
        if melhor is None or C.melhor_que(E.tot, melhor.tot, desempate):
            melhor = E
            historico.append((round(time.time() - t0, 2), E.custo))
            if verbose:
                print(f"  it {it:4d}  t={time.time() - t0:6.1f}s  construcao={c_constr:>7}  VND={E.custo:>6}  *",
                      flush=True)
    sched = melhor.sched()
    hard, comp, custo = evaluate(inst, sched)
    if is_feasible(hard) and custo != melhor.custo:
        print(f"  AVISO: custo incremental ({melhor.custo}) != avaliador ({custo})")
    return dict(sched=sched, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                iteracoes=it, tempo=time.time() - t0, historico=historico,
                custo_incremental=melhor.custo, custos_construcao=custos_constr, custos_vnd=custos_vnd)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    alpha = float(sys.argv[5]) if len(sys.argv) > 5 else 0.15
    semente = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    am = float(sys.argv[7]) if len(sys.argv) > 7 else None
    des = len(sys.argv) > 8 and sys.argv[8] == "1"
    inst = load_instance(folder, h, wds)
    r = grasp(inst, limite, alpha, semente, amostra=am or None, desempate=des)
    print(f"{inst.name}: custo={r['custo']} viavel={r['viavel']} iteracoes={r['iteracoes']} tempo={r['tempo']:.1f}s")
    print("  componentes:", r["componentes"])
    print_schedule(inst, r["sched"])
