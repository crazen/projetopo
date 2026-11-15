"""grasp.py - metaheuristica GRASP com busca local VND para o Nurse Rostering (INRC-II).

GRASP (Greedy Randomized Adaptive Search Procedure) repete, ate acabar o tempo:
  1. CONSTRUCAO gulosa-aleatorizada: monta a escala dia a dia; para cada vaga de demanda (turno, habilidade)
     calcula o custo incremental de cada enfermeiro candidato e sorteia um da Lista Restrita de Candidatos:
        RCL = { candidatos com custo <= c_min + alpha * (c_max - c_min) }
     alpha = 0 -> guloso puro (sempre o melhor);  alpha = 1 -> totalmente aleatorio.
  2. BUSCA LOCAL VND (Variable Neighborhood Descent), da vizinhanca mais barata para a mais cara:
        N1 troca : muda a atribuicao de um enfermeiro em um dia (outro turno/habilidade, ou folga)
        N2 swap  : dois enfermeiros trocam suas atribuicoes em um dia (a cobertura nao muda)
        N3 bloco : um enfermeiro recebe o mesmo turno (ou folga) em L dias seguidos (L = 2..5)
        N4 swap de bloco : dois enfermeiros trocam suas atribuicoes em L dias seguidos (L = 2..7)
     Quando uma vizinhanca encontra melhora, volta para N1; termina quando nenhuma melhora (otimo local).
  3. FASE ILS (melhoria do otimo local): perturba a solucao com alguns movimentos aleatorios de bloco,
     roda um VND LOCAL (so nos enfermeiros e dias que a perturbacao mudou, mais uma margem) e aceita se
     melhorou; para apos 'ils' tentativas seguidas sem melhora ou quando gasta 'frac_ils' do tempo total.
     (Com ils = 0 o algoritmo e o GRASP classico, so com VND.)
  4. Guarda a melhor solucao encontrada em todas as iteracoes.

Representacao: sid[n][d] = turno (-1 = folga) e skl[n][d] = habilidade usada (-1 = folga).
Restricoes hard (cobertura minima, sucessao proibida) entram no custo com peso GRANDE; a busca as elimina
primeiro. Habilidade (H4) e um turno por dia (H1) sao garantidos pela propria representacao.

Uso:  python grasp.py <pasta_dataset> <h> <semanas> [limite_s] [alpha] [semente]
Ex.:  python grasp.py dados/n005w4 0 1,2,3,3 30 0.15 1
"""
import sys, time, random
from inrc2 import load_instance, evaluate, is_feasible, print_schedule, W_S1, W_TOTAL
from custo_rapido import custo_enf

GRANDE = 10000          # peso de cada violacao hard dentro da heuristica


class Estado:
    """Escala atual + custos em cache, com avaliacao incremental (delta) dos movimentos."""

    def __init__(self, inst, sid, skl):
        self.inst = inst
        self.S, self.K = len(inst.shifts), len(inst.skills)
        self.sid = [r[:] for r in sid]
        self.skl = [r[:] for r in skl]
        self.cnt = [[[0] * self.K for _ in range(self.S)] for _ in range(inst.D)]
        for n in range(inst.N):
            for d in range(inst.D):
                if self.sid[n][d] >= 0:
                    self.cnt[d][self.sid[n][d]][self.skl[n][d]] += 1
        self.ncost = [custo_enf(inst, n, self.sid[n], GRANDE) for n in range(inst.N)]
        cov = sum(self.cob(d, s, k, self.cnt[d][s][k])
                  for d in range(inst.D) for s in range(self.S) for k in range(self.K))
        self.total = cov + sum(self.ncost)
        self.habs = [sorted(inst.nurse_skills[n]) for n in range(inst.N)]

    def cob(self, d, s, k, c):
        """Custo de cobertura da celula (dia, turno, habilidade) com c enfermeiros alocados."""
        i = self.inst
        return W_S1 * max(0, i.dopt[d][s][k] - c) + GRANDE * max(0, i.dmin[d][s][k] - c)

    def d_cob(self, d, s, k, mais):
        """Variacao do custo de cobertura ao somar (mais=+1) ou tirar (mais=-1) um enfermeiro da celula."""
        c = self.cnt[d][s][k]
        return self.cob(d, s, k, c + mais) - self.cob(d, s, k, c)

    def sched(self):
        return [[None if self.sid[n][d] < 0 else (self.sid[n][d], self.skl[n][d]) for d in range(self.inst.D)]
                for n in range(self.inst.N)]

    def copia(self):
        e = Estado.__new__(Estado)
        e.inst, e.S, e.K, e.habs = self.inst, self.S, self.K, self.habs
        e.sid = [r[:] for r in self.sid]; e.skl = [r[:] for r in self.skl]
        e.cnt = [[c[:] for c in dd] for dd in self.cnt]
        e.ncost = self.ncost[:]; e.total = self.total
        return e

    # ---- aplica uma nova atribuicao para o enfermeiro n nos dias de 'dias' (listas de turnos/habilidades)
    def aplicar(self, n, dias, novos_s, novos_k, novo_custo_enf, delta):
        for d, s, k in zip(dias, novos_s, novos_k):
            s0, k0 = self.sid[n][d], self.skl[n][d]
            if s0 >= 0:
                self.cnt[d][s0][k0] -= 1
            if s >= 0:
                self.cnt[d][s][k] += 1
            self.sid[n][d], self.skl[n][d] = s, k
        self.ncost[n] = novo_custo_enf
        self.total += delta


# ==================================================================== vizinhancas
# 'foco' (opcional) restringe uma vizinhanca ao que pode ter mudado depois de uma perturbacao do ILS:
#   foco = (enfermeiros perturbados, dias perturbados com margem). Sem foco, a vizinhanca e a completa.
# Um movimento so pode ter delta diferente do que tinha no otimo local anterior se envolver a linha de um
# enfermeiro perturbado ou a cobertura de um dia perturbado; o resto ja foi testado pelo VND anterior.

def n1_troca(est, rng, prazo, foco=None):
    """Para cada (enfermeiro, dia), em ordem aleatoria, aplica a melhor troca de atribuicao se ela melhorar."""
    inst = est.inst; melhorou = False
    if foco is None:
        celulas = [(n, d) for n in range(inst.N) for d in range(inst.D)]
    else:
        enfs, dias = foco
        celulas = list({(n, d) for n in range(inst.N) for d in dias} |
                       {(n, d) for n in enfs for d in range(inst.D)})
    rng.shuffle(celulas)
    for i, (n, d) in enumerate(celulas):
        if i % 50 == 0 and time.time() > prazo:
            break
        row = est.sid[n]; s0, k0 = row[d], est.skl[n][d]
        tira = est.d_cob(d, s0, k0, -1) if s0 >= 0 else 0
        melhor = None
        for s in range(-1, est.S):
            row[d] = s
            cn = custo_enf(inst, n, row, GRANDE)          # custo do enfermeiro so depende do turno
            for k in (est.habs[n] if s >= 0 else [-1]):
                if s == s0 and k == k0:
                    continue
                if s >= 0:
                    est.cnt[d][s0][k0] -= (1 if s0 >= 0 else 0)
                    poe = est.d_cob(d, s, k, +1)
                    est.cnt[d][s0][k0] += (1 if s0 >= 0 else 0)
                else:
                    poe = 0
                delta = tira + poe + cn - est.ncost[n]
                if delta < -1e-9 and (melhor is None or delta < melhor[0]):
                    melhor = (delta, s, k, cn)
        row[d] = s0
        if melhor:
            delta, s, k, cn = melhor
            est.aplicar(n, [d], [s], [k], cn, delta)
            melhorou = True
    return melhorou


def mov_swap(est, n1, n2, d0, L):
    """Delta de trocar as atribuicoes de n1 e n2 nos dias d0..d0+L-1 (a cobertura nao muda)."""
    r1, r2 = est.sid[n1], est.sid[n2]
    k1, k2 = est.skl[n1], est.skl[n2]
    h1, h2 = est.inst.nurse_skills[n1], est.inst.nurse_skills[n2]
    dias = range(d0, d0 + L)
    if all(r1[d] == r2[d] for d in dias):
        return None
    for d in dias:              # cada um precisa ter a habilidade da atribuicao que recebe
        if (r2[d] >= 0 and k2[d] not in h1) or (r1[d] >= 0 and k1[d] not in h2):
            return None
    a1, a2 = r1[:], r2[:]
    for d in dias:
        a1[d], a2[d] = r2[d], r1[d]
    c1 = custo_enf(est.inst, n1, a1, GRANDE); c2 = custo_enf(est.inst, n2, a2, GRANDE)
    return c1 + c2 - est.ncost[n1] - est.ncost[n2], c1, c2


def aplicar_swap(est, n1, n2, d0, L, mov):
    delta, c1, c2 = mov
    for d in range(d0, d0 + L):
        est.sid[n1][d], est.sid[n2][d] = est.sid[n2][d], est.sid[n1][d]
        est.skl[n1][d], est.skl[n2][d] = est.skl[n2][d], est.skl[n1][d]
    est.ncost[n1], est.ncost[n2] = c1, c2
    est.total += delta


def _movimentos(rng, total, gerar_todos, sortear, limite_enum):
    """Gera os movimentos de uma vizinhanca: todos (em ordem aleatoria) se forem poucos, senao uma amostra."""
    if total <= limite_enum:
        movs = gerar_todos(); rng.shuffle(movs); return movs
    return [sortear() for _ in range(limite_enum)]


def n_swap(est, rng, prazo, tamanhos, limite_enum, foco=None):
    """N2 (tamanhos=[1]) e N4 (blocos): troca as atribuicoes de dois enfermeiros em L dias seguidos.
    Com foco: um dos dois enfermeiros e perturbado (o swap nao muda a cobertura, so as duas linhas)."""
    N, D = est.inst.N, est.inst.D; melhorou = False
    if foco is None:
        total = N * (N - 1) // 2 * sum(D - L + 1 for L in tamanhos)

        def todos():
            return [(n1, n2, d0, L) for n1 in range(N) for n2 in range(n1 + 1, N)
                    for L in tamanhos for d0 in range(D - L + 1)]

        def sortear():
            n1, n2 = rng.sample(range(N), 2); L = rng.choice(tamanhos)
            return n1, n2, rng.randrange(D - L + 1), L
    else:
        enfs = sorted(foco[0])
        inicios = _inicios(foco[1], tamanhos, D)
        total = len(enfs) * (N - 1) * sum(map(len, inicios.values()))

        def todos():
            return [(n1, n2, d0, L) for n1 in enfs for n2 in range(N) if n2 != n1
                    for L in tamanhos for d0 in inicios[L]]

        def sortear():
            n1 = rng.choice(enfs); n2 = rng.randrange(N - 1); n2 += n2 >= n1
            L = rng.choice(tamanhos)
            return n1, n2, rng.choice(inicios[L]), L

    movs = _movimentos(rng, total, todos, sortear, limite_enum)
    for i, (n1, n2, d0, L) in enumerate(movs):
        if i % 50 == 0 and time.time() > prazo:
            break
        mov = mov_swap(est, n1, n2, d0, L)
        if mov is not None and mov[0] < -1e-9:
            aplicar_swap(est, n1, n2, d0, L, mov)
            melhorou = True
    return melhorou


def n3_bloco(est, rng, prazo, limite_enum, foco=None):
    """N3: um enfermeiro recebe o mesmo turno s (ou folga) em L dias seguidos. Em cada dia usa a habilidade
    (entre as que ele possui) que mais ajuda a cobertura.
    Com foco: blocos (de qualquer enfermeiro) que tocam um dia perturbado."""
    inst = est.inst; N, D = inst.N, inst.D; melhorou = False
    tamanhos = [2, 3, 4, 5]
    inicios = ({L: range(D - L + 1) for L in tamanhos} if foco is None else _inicios(foco[1], tamanhos, D))
    total = N * (est.S + 1) * sum(map(len, inicios.values()))

    def todos():
        return [(n, d0, L, s) for n in range(N) for L in tamanhos for d0 in inicios[L]
                for s in range(-1, est.S)]

    def sortear():
        L = rng.choice(tamanhos)
        return rng.randrange(N), rng.choice(inicios[L]), L, rng.randrange(-1, est.S)

    movs = _movimentos(rng, total, todos, sortear, limite_enum)
    for i, (n, d0, L, s) in enumerate(movs):
        if i % 50 == 0 and time.time() > prazo:
            break
        mov = mov_bloco(est, n, d0, L, s)
        if mov is not None and mov[0] < -1e-9:
            aplicar_bloco(est, n, d0, L, s, mov)
            melhorou = True
    return melhorou


def mov_bloco(est, n, d0, L, s):
    """Delta de colocar o turno s (ou folga, s = -1) para o enfermeiro n nos dias d0..d0+L-1."""
    dias = range(d0, d0 + L)
    row = est.sid[n]
    if all(row[d] == s for d in dias):
        return None
    dcob = 0; novos_k = []
    for d in dias:                                   # tira a atribuicao antiga e poe a nova
        s0, k0 = row[d], est.skl[n][d]
        if s0 >= 0:
            dcob += est.d_cob(d, s0, k0, -1); est.cnt[d][s0][k0] -= 1
        if s >= 0:
            k = min(est.habs[n], key=lambda kk: est.d_cob(d, s, kk, +1))
            dcob += est.d_cob(d, s, k, +1); novos_k.append(k)
        else:
            novos_k.append(-1)
        if s0 >= 0:
            est.cnt[d][s0][k0] += 1
    novo = row[:]
    for d in dias:
        novo[d] = s
    cn = custo_enf(est.inst, n, novo, GRANDE)
    return dcob + cn - est.ncost[n], novos_k, cn


def aplicar_bloco(est, n, d0, L, s, mov):
    delta, novos_k, cn = mov
    est.aplicar(n, list(range(d0, d0 + L)), [s] * L, novos_k, cn, delta)


def vnd(est, rng, prazo, foco=None):
    """VND completo (foco=None) ou restrito ao que uma perturbacao mudou (foco = (enfermeiros, dias)).
    O foco cresce com cada melhora aplicada, para que a busca acompanhe as mudancas em cascata."""
    # vizinhancas com ate LIMITE movimentos sao enumeradas por completo; maiores sao amostradas
    lim = max(20000, 5 * est.inst.N * est.inst.D) if foco is None else LIM_LOCAL
    while time.time() < prazo:
        antes = [r[:] for r in est.sid] if foco is not None else None
        if (n1_troca(est, rng, prazo, foco) or n_swap(est, rng, prazo, [1], lim, foco)
                or n3_bloco(est, rng, prazo, lim, foco) or n_swap(est, rng, prazo, [2, 3, 4, 5, 7], lim, foco)):
            if foco is not None:               # inclui no foco o que a melhora acabou de mudar
                for n in range(est.inst.N):
                    mud = [d for d in range(est.inst.D) if antes[n][d] != est.sid[n][d]]
                    if mud:
                        foco[0].add(n); foco[1].update(_com_margem(mud, est.inst.D))
            continue
        break                                  # nenhuma vizinhanca melhora: otimo local
    return est


MARGEM = 3        # dias vizinhos a um dia perturbado que tambem entram no foco do VND local
LIM_LOCAL = 3000  # maximo de movimentos avaliados por vizinhanca no VND local (acima disso, amostra)


def _com_margem(dias, D):
    return {x for d in dias for x in range(max(0, d - MARGEM), min(D, d + MARGEM + 1))}


def _inicios(dias, tamanhos, D):
    """Para cada tamanho de bloco L, os dias iniciais d0 cujo bloco d0..d0+L-1 toca algum dia de 'dias'."""
    return {L: [d0 for d0 in range(D - L + 1) if any(d in dias for d in range(d0, d0 + L))] for L in tamanhos}


def perturbar(est, rng, forca):
    """Aplica 'forca' movimentos aleatorios de bloco (N3) ou de swap de bloco (N4), mesmo que piorem a solucao.
    Devolve o foco (enfermeiros tocados, dias tocados com margem) para o VND local."""
    inst = est.inst; N, D = inst.N, inst.D
    feitos = 0; enfs, dias = set(), set()
    while feitos < forca:
        L = rng.choice([2, 3, 4, 5])
        d0 = rng.randrange(D - L + 1)
        if rng.random() < 0.5:
            n, s = rng.randrange(N), rng.randrange(-1, est.S)
            mov = mov_bloco(est, n, d0, L, s)
            if mov is not None:
                aplicar_bloco(est, n, d0, L, s, mov); feitos += 1
                enfs.add(n); dias.update(range(d0, d0 + L))
        else:
            n1, n2 = rng.sample(range(N), 2)
            mov = mov_swap(est, n1, n2, d0, L)
            if mov is not None:
                aplicar_swap(est, n1, n2, d0, L, mov); feitos += 1
                enfs.update((n1, n2)); dias.update(range(d0, d0 + L))
    return enfs, _com_margem(dias, D)


def fase_ils(est, rng, prazo, max_sem_melhora, forca):
    """Melhoria do otimo local do GRASP: perturba + VND local (so em torno do que foi perturbado); aceita se
    melhorar. Para apos 'max_sem_melhora' tentativas seguidas sem melhora (ou quando acaba o tempo)."""
    sem = 0
    while sem < max_sem_melhora and time.time() < prazo:
        cand = est.copia()
        foco = perturbar(cand, rng, forca)
        vnd(cand, rng, prazo, foco)
        if cand.total < est.total - 1e-9:
            est, sem = cand, 0
        else:
            sem += 1
    return est


# ==================================================================== construcao
def construir(inst, alpha, rng, peso_ritmo=W_TOTAL / 2):
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
            cmin = min(c for c, _ in cand); cmax = max(c for c, _ in cand)
            rcl = [n for c, n in cand if c <= cmin + alpha * (cmax - cmin)]
            n = rng.choice(rcl)
            sid[n][d], skl[n][d] = s, k
            livre[n] = False; trabalhados[n] += 1
    return sid, skl


# ==================================================================== GRASP
def grasp(inst, limite=60, alpha=0.15, semente=0, verbose=True, ils=30, forca=4, frac_ils=0.5):
    """Executa o GRASP por 'limite' segundos. Retorna a melhor escala e o historico de convergencia.
    ils   : tentativas seguidas sem melhora na fase ILS de cada iteracao (0 = GRASP puro, so VND)
    forca : numero de movimentos aleatorios em cada perturbacao
    frac_ils : tempo maximo de cada fase ILS, como fracao do limite total (garante varias construcoes)"""
    rng = random.Random(semente)
    t0 = time.time(); prazo = t0 + limite
    melhor, it, historico = None, 0, []
    while time.time() < prazo:
        est = Estado(inst, *construir(inst, alpha, rng))
        c_constr = est.total
        vnd(est, rng, prazo)
        c_vnd = est.total
        if ils > 0:
            est = fase_ils(est, rng, min(prazo, time.time() + frac_ils * limite), ils, forca)
        it += 1
        if melhor is None or est.total < melhor.total:
            melhor = est.copia()
            historico.append((round(time.time() - t0, 2), est.total))
            if verbose:
                print(f"  it {it:4d}  t={time.time() - t0:6.1f}s  construcao={c_constr:>7}  VND={c_vnd:>6}  ILS={est.total:>6}  *",
                      flush=True)
    sched = melhor.sched()
    hard, comp, custo = evaluate(inst, sched)
    if is_feasible(hard) and custo != melhor.total:
        print(f"  AVISO: custo incremental ({melhor.total}) != avaliador ({custo})")
    return dict(sched=sched, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                iteracoes=it, tempo=time.time() - t0, historico=historico)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    alpha = float(sys.argv[5]) if len(sys.argv) > 5 else 0.15
    semente = int(sys.argv[6]) if len(sys.argv) > 6 else 0
    inst = load_instance(folder, h, wds)
    r = grasp(inst, limite, alpha, semente)
    print(f"{inst.name}: custo={r['custo']} viavel={r['viavel']} iteracoes={r['iteracoes']} tempo={r['tempo']:.1f}s")
    print("  componentes:", r["componentes"])
    print_schedule(inst, r["sched"])
