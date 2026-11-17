"""nucleo.py - nucleo compilado (numba) das metaheuristicas: custo incremental e movimentos.

O calculo e EXATAMENTE o de custo_rapido.custo_enf / inrc2.evaluate (conferido em testes.py), mas escrito
com arrays NumPy e compilado pelo numba (JIT). Isso deixa cada movimento ~50x mais rapido que em Python puro,
o que permite ao SA e ao GRASP avaliar centenas de milhoes de movimentos em poucos minutos.

Representacao da escala (igual a do grasp.py):
  sid[n, d] = turno do enfermeiro n no dia d (-1 = folga)
  skl[n, d] = habilidade usada (-1 = folga)
Estado mantido em cache (avaliacao incremental):
  cnt[d, s, k] = quantos enfermeiros cobrem (dia, turno, habilidade)
  ncost[n]     = custo individual do enfermeiro n (S2..S7 + sucessoes proibidas com peso GRANDE)
  tot[0]       = custo total = cobertura (S1 + H2 com peso GRANDE) + soma de ncost

Movimentos (os mesmos quatro do GRASP/SA):
  bloco(n, d0, L, s): o enfermeiro n recebe o turno s (ou folga, s = -1) nos dias d0..d0+L-1; em cada dia
                      usa a habilidade (entre as que possui) que mais reduz o custo de cobertura.
                      L = 1 e a vizinhanca N1 (troca); L = 2..5 e a N3 (bloco).
  troca(n1, n2, d0, L): n1 e n2 trocam suas atribuicoes nos dias d0..d0+L-1 (a cobertura nao muda).
                      L = 1 e a N2 (swap); L = 2..7 e a N4 (swap de bloco).
"""
from collections import namedtuple
import numpy as np
from numba import njit
from inrc2 import W_S1, W_SHIFT, W_WORK, W_OFF, W_PREF, W_WEEKEND, W_TOTAL, W_MAXWE

GRANDE = 10000      # peso de cada violacao hard (cobertura minima, sucessao proibida) dentro das heuristicas
NADA = 1 << 40      # "movimento invalido ou sem efeito"

Dados = namedtuple("Dados", "N D S K minS maxS minW maxW minO maxO minA maxA maxWE comp "
                            "hlast hcS hcW hcO hnA hnWE forb reqA reqS dmin dopt habs nhab temhab")


def dados(inst):
    """Converte a Instance (inrc2) em arrays para o codigo compilado."""
    N, D, S, K = inst.N, inst.D, len(inst.shifts), len(inst.skills)
    i64 = lambda v: np.array(v, dtype=np.int64)
    ct, h = inst.ct, inst.hist
    reqA = np.zeros((N, D), np.int64); reqS = np.zeros((N, D, S), np.int64)
    for n in range(N):
        for d, q in inst.req_any[n].items():
            reqA[n, d] += q
        for (d, s), q in inst.req_sh[n].items():
            reqS[n, d, s] += q
    habs = np.full((N, K), -1, np.int64); nhab = np.zeros(N, np.int64); temhab = np.zeros((N, K), np.bool_)
    for n in range(N):
        hs = sorted(inst.nurse_skills[n]); nhab[n] = len(hs); habs[n, :len(hs)] = hs; temhab[n, hs] = True
    return Dados(N, D, S, K, i64(inst.min_cons_shift), i64(inst.max_cons_shift),
                 i64([c["minW"] for c in ct]), i64([c["maxW"] for c in ct]),
                 i64([c["minO"] for c in ct]), i64([c["maxO"] for c in ct]),
                 i64([c["minA"] for c in ct]), i64([c["maxA"] for c in ct]),
                 i64([c["maxWE"] for c in ct]), i64([c["complete"] for c in ct]),
                 i64([x["last"] for x in h]), i64([x["cS"] for x in h]), i64([x["cW"] for x in h]),
                 i64([x["cO"] for x in h]), i64([x["nA"] for x in h]), i64([x["nWE"] for x in h]),
                 np.array(inst.forb, dtype=np.bool_), reqA, reqS,
                 np.array(inst.dmin, dtype=np.int64), np.array(inst.dopt, dtype=np.int64), habs, nhab, temhab)


# ====================================================================== custo
@njit(cache=True)
def custo_linha(P, n, row):
    """Custo individual do enfermeiro n com a linha row (turno por dia, -1 = folga). Igual a custo_enf."""
    D = row.shape[0]
    if D == 0:
        return 0
    minW, maxW, minO, maxO = P.minW[n], P.maxW[n], P.minO[n], P.maxO[n]
    last, cS, cW, cO = P.hlast[n], P.hcS[n], P.hcW[n], P.hcO[n]
    c = 0
    if last >= 0 and cS > 0 and row[0] != last:
        c += W_SHIFT * max(0, P.minS[last] - cS)
    if cW > 0 and row[0] < 0:
        c += W_WORK * max(0, minW - cW)
    if cO > 0 and row[0] >= 0:
        c += W_OFF * max(0, minO - cO)
    d = 0
    while d < D:
        e = d + 1
        if row[d] >= 0:
            while e < D and row[e] >= 0:
                e += 1
            hp = cW if d == 0 else 0
            tot = e - d + hp
            c += W_WORK * (max(0, tot - maxW) - max(0, hp - maxW))
            if e < D:
                c += W_WORK * max(0, minW - tot)
            i = d
            while i < e:
                s = row[i]; j = i + 1
                while j < e and row[j] == s:
                    j += 1
                hps = cS if (i == 0 and last == s) else 0
                tot = j - i + hps
                c += W_SHIFT * (max(0, tot - P.maxS[s]) - max(0, hps - P.maxS[s]))
                if j < D:
                    c += W_SHIFT * max(0, P.minS[s] - tot)
                i = j
        else:
            while e < D and row[e] < 0:
                e += 1
            hp = cO if d == 0 else 0
            tot = e - d + hp
            c += W_OFF * (max(0, tot - maxO) - max(0, hp - maxO))
            if e < D:
                c += W_OFF * max(0, minO - tot)
        d = e
    trab = 0; nwe = 0; prev = last
    for d in range(D):
        x = row[d]
        if x >= 0:
            trab += 1
            c += W_PREF * (P.reqA[n, d] + P.reqS[n, d, x])
            if prev >= 0 and P.forb[prev, x]:
                c += GRANDE
        prev = x
    for wk in range(D // 7):
        sat = row[7 * wk + 5] >= 0; sun = row[7 * wk + 6] >= 0
        if P.comp[n] == 1 and sat != sun:
            c += W_WEEKEND
        if sat or sun:
            nwe += 1
    tot = P.hnA[n] + trab
    c += W_TOTAL * (max(0, P.minA[n] - tot) + max(0, tot - P.maxA[n]))
    c += W_MAXWE * max(0, P.hnWE[n] + nwe - P.maxWE[n])
    return c


@njit(cache=True)
def cob(P, d, s, k, c):
    """Custo de cobertura da celula (dia, turno, habilidade) com c enfermeiros."""
    return W_S1 * max(0, P.dopt[d, s, k] - c) + GRANDE * max(0, P.dmin[d, s, k] - c)


@njit(cache=True)
def custo_total(P, sid, skl, cnt, ncost):
    """Recalcula do zero cnt, ncost e o custo total. Devolve o total."""
    cnt[:] = 0
    for n in range(P.N):
        for d in range(P.D):
            if sid[n, d] >= 0:
                cnt[d, sid[n, d], skl[n, d]] += 1
    t = 0
    for d in range(P.D):
        for s in range(P.S):
            for k in range(P.K):
                t += cob(P, d, s, k, cnt[d, s, k])
    for n in range(P.N):
        ncost[n] = custo_linha(P, n, sid[n])
        t += ncost[n]
    return t


# ====================================================================== movimentos
@njit(cache=True)
def delta_bloco(P, sid, skl, cnt, ncost, n, d0, L, s, buf, novk):
    """Delta de dar o turno s (ou folga) ao enfermeiro n nos dias d0..d0+L-1.
    Preenche novk[0:L] com as habilidades escolhidas e devolve (delta, novo custo do enfermeiro)."""
    igual = True
    for d in range(d0, d0 + L):
        if sid[n, d] != s:
            igual = False
            break
    if igual:
        return NADA, 0
    dc = 0
    for i in range(L):
        d = d0 + i
        s0 = sid[n, d]; k0 = skl[n, d]
        if s0 >= 0:
            c0 = cnt[d, s0, k0]
            dc += cob(P, d, s0, k0, c0 - 1) - cob(P, d, s0, k0, c0)
            cnt[d, s0, k0] -= 1
        if s >= 0:                         # habilidade que mais ajuda a cobertura neste dia
            mk = -1; md = NADA
            for j in range(P.nhab[n]):
                k = P.habs[n, j]
                v = cob(P, d, s, k, cnt[d, s, k] + 1) - cob(P, d, s, k, cnt[d, s, k])
                if v < md:
                    md = v; mk = k
            dc += md; novk[i] = mk
        else:
            novk[i] = -1
        if s0 >= 0:
            cnt[d, s0, k0] += 1
    for d in range(P.D):
        buf[d] = sid[n, d]
    for d in range(d0, d0 + L):
        buf[d] = s
    cn = custo_linha(P, n, buf)
    return dc + cn - ncost[n], cn


@njit(cache=True)
def aplicar_bloco(sid, skl, cnt, ncost, tot, n, d0, L, s, novk, delta, cn):
    for i in range(L):
        d = d0 + i
        s0 = sid[n, d]
        if s0 >= 0:
            cnt[d, s0, skl[n, d]] -= 1
        if s >= 0:
            cnt[d, s, novk[i]] += 1
        sid[n, d] = s; skl[n, d] = novk[i]
    ncost[n] = cn
    tot[0] += delta


@njit(cache=True)
def delta_troca(P, sid, skl, ncost, n1, n2, d0, L, b1, b2):
    """Delta de n1 e n2 trocarem as atribuicoes nos dias d0..d0+L-1. Devolve (delta, custo1, custo2)."""
    igual = True
    for d in range(d0, d0 + L):
        if sid[n1, d] != sid[n2, d]:
            igual = False
        if sid[n2, d] >= 0 and not P.temhab[n1, skl[n2, d]]:
            return NADA, 0, 0
        if sid[n1, d] >= 0 and not P.temhab[n2, skl[n1, d]]:
            return NADA, 0, 0
    if igual:
        return NADA, 0, 0
    for d in range(P.D):
        b1[d] = sid[n1, d]; b2[d] = sid[n2, d]
    for d in range(d0, d0 + L):
        b1[d] = sid[n2, d]; b2[d] = sid[n1, d]
    c1 = custo_linha(P, n1, b1); c2 = custo_linha(P, n2, b2)
    return c1 + c2 - ncost[n1] - ncost[n2], c1, c2


@njit(cache=True)
def aplicar_troca(sid, skl, ncost, tot, n1, n2, d0, L, delta, c1, c2):
    for d in range(d0, d0 + L):
        a = sid[n1, d]; sid[n1, d] = sid[n2, d]; sid[n2, d] = a
        a = skl[n1, d]; skl[n1, d] = skl[n2, d]; skl[n2, d] = a
    ncost[n1] = c1; ncost[n2] = c2
    tot[0] += delta


@njit(cache=True)
def semear(seed):
    np.random.seed(seed)


# ====================================================================== Simulated Annealing
TAM_TROCA = np.array([2, 3, 4, 5, 7], dtype=np.int64)


@njit(cache=True)
def sa_passos(P, sid, skl, cnt, ncost, tot, best_sid, best_skl, best_tot, nmov, T, tam_troca=TAM_TROCA):
    """nmov passos do SA na temperatura T (criterio de Metropolis). Atualiza a melhor escala.
    Escolha do movimento: N1 40%, N3 20%, N2 20%, N4 20% (como no sa.py original).
    Devolve (movimentos aceitos, melhorias da melhor solucao)."""
    N, D, S = P.N, P.D, P.S
    buf = np.empty(D, np.int64); b2 = np.empty(D, np.int64); novk = np.empty(8, np.int64)
    aceitos = 0; melhoras = 0
    for _ in range(nmov):
        r = np.random.random()
        if r < 0.6:
            L = 1 if r < 0.4 else np.random.randint(2, 6)
            n = np.random.randint(N); d0 = np.random.randint(D - L + 1); s = np.random.randint(-1, S)
            delta, cn = delta_bloco(P, sid, skl, cnt, ncost, n, d0, L, s, buf, novk)
            if delta == NADA:
                continue
            if delta <= 0 or np.random.random() < np.exp(-delta / T):
                aplicar_bloco(sid, skl, cnt, ncost, tot, n, d0, L, s, novk, delta, cn); aceitos += 1
            else:
                continue
        else:
            L = 1 if r < 0.8 else tam_troca[np.random.randint(tam_troca.shape[0])]
            n1 = np.random.randint(N); n2 = np.random.randint(N - 1)
            if n2 >= n1:
                n2 += 1
            d0 = np.random.randint(D - L + 1)
            delta, c1, c2 = delta_troca(P, sid, skl, ncost, n1, n2, d0, L, buf, b2)
            if delta == NADA:
                continue
            if delta <= 0 or np.random.random() < np.exp(-delta / T):
                aplicar_troca(sid, skl, ncost, tot, n1, n2, d0, L, delta, c1, c2); aceitos += 1
            else:
                continue
        if tot[0] < best_tot[0]:
            best_tot[0] = tot[0]; best_sid[:] = sid; best_skl[:] = skl; melhoras += 1
    return aceitos, melhoras


# ====================================================================== busca local (VND) do GRASP
@njit(cache=True)
def _n1(P, sid, skl, cnt, ncost, tot, buf, novk):
    """N1 completa: para cada (enfermeiro, dia), em ordem aleatoria, aplica a melhor troca se melhorar."""
    N, D, S = P.N, P.D, P.S
    melhorou = False
    for idx in np.random.permutation(N * D):
        n = idx // D; d = idx % D
        md = 0; ms = -2; mcn = 0; mk = -1
        for s in range(-1, S):
            delta, cn = delta_bloco(P, sid, skl, cnt, ncost, n, d, 1, s, buf, novk)
            if delta < md:
                md = delta; ms = s; mcn = cn; mk = novk[0]
        if ms > -2:
            novk[0] = mk
            aplicar_bloco(sid, skl, cnt, ncost, tot, n, d, 1, ms, novk, md, mcn)
            melhorou = True
    return melhorou


@njit(cache=True)
def _n3(P, sid, skl, cnt, ncost, tot, buf, novk):
    """N3 completa: blocos de L = 2..5 dias com o mesmo turno (ou folga), em ordem aleatoria."""
    N, D, S = P.N, P.D, P.S
    nL = 4; tot_mov = N * nL * D * (S + 1)
    melhorou = False
    for idx in np.random.permutation(tot_mov):
        s = idx % (S + 1) - 1; idx //= (S + 1)
        d0 = idx % D; idx //= D
        L = idx % nL + 2; n = idx // nL
        if d0 + L > D:
            continue
        delta, cn = delta_bloco(P, sid, skl, cnt, ncost, n, d0, L, s, buf, novk)
        if delta < 0:
            aplicar_bloco(sid, skl, cnt, ncost, tot, n, d0, L, s, novk, delta, cn)
            melhorou = True
    return melhorou


@njit(cache=True)
def _troca(P, sid, skl, ncost, tot, b1, b2, tamanhos):
    """N2 (tamanhos = [1]) ou N4 (tamanhos = [2,3,4,5,7]) completas, em ordem aleatoria."""
    N, D = P.N, P.D
    nT = tamanhos.shape[0]; npar = N * (N - 1) // 2
    # pares (n1 < n2) indexados de 0 a npar-1
    p1 = np.empty(npar, np.int64); p2 = np.empty(npar, np.int64); i = 0
    for a in range(N):
        for b in range(a + 1, N):
            p1[i] = a; p2[i] = b; i += 1
    melhorou = False
    for idx in np.random.permutation(npar * nT * D):
        d0 = idx % D; idx //= D
        L = tamanhos[idx % nT]; par = idx // nT
        if d0 + L > D:
            continue
        n1 = p1[par]; n2 = p2[par]
        delta, c1, c2 = delta_troca(P, sid, skl, ncost, n1, n2, d0, L, b1, b2)
        if delta < 0:
            aplicar_troca(sid, skl, ncost, tot, n1, n2, d0, L, delta, c1, c2)
            melhorou = True
    return melhorou


UM = np.array([1], dtype=np.int64)


@njit(cache=True)
def vnd(P, sid, skl, cnt, ncost, tot):
    """VND: N1 -> N2 -> N3 -> N4; volta para N1 sempre que uma vizinhanca melhora. Termina num otimo local
    (nenhum movimento das quatro vizinhancas melhora a escala). Devolve o numero de rodadas."""
    D = P.D
    buf = np.empty(D, np.int64); b2 = np.empty(D, np.int64); novk = np.empty(8, np.int64)
    rodadas = 0
    while True:
        rodadas += 1
        if _n1(P, sid, skl, cnt, ncost, tot, buf, novk):
            continue
        if _troca(P, sid, skl, ncost, tot, buf, b2, UM):
            continue
        if _n3(P, sid, skl, cnt, ncost, tot, buf, novk):
            continue
        if _troca(P, sid, skl, ncost, tot, buf, b2, TAM_TROCA):
            continue
        break
    return rodadas


# ====================================================================== utilidades Python
class Escala:
    """Escala + caches, em arrays NumPy (para usar com as funcoes compiladas)."""

    def __init__(self, P, sid, skl):
        self.P = P
        self.sid = np.array(sid, dtype=np.int64); self.skl = np.array(skl, dtype=np.int64)
        self.cnt = np.zeros((P.D, P.S, P.K), np.int64); self.ncost = np.zeros(P.N, np.int64)
        self.tot = np.array([custo_total(P, self.sid, self.skl, self.cnt, self.ncost)], np.int64)

    def sched(self):
        return [[None if self.sid[n, d] < 0 else (int(self.sid[n, d]), int(self.skl[n, d]))
                 for d in range(self.P.D)] for n in range(self.P.N)]

    def recalcular(self):
        """Custo recalculado do zero (para conferir o incremental)."""
        cnt = np.zeros_like(self.cnt); nc = np.zeros_like(self.ncost)
        return int(custo_total(self.P, self.sid, self.skl, cnt, nc))


def de_sched(sched):
    """sched (lista de listas de (s, k) ou None) -> (sid, skl) em listas."""
    sid = [[-1 if a is None else a[0] for a in r] for r in sched]
    skl = [[-1 if a is None else a[1] for a in r] for r in sched]
    return sid, skl
