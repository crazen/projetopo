"""nucleo.py - nucleo compilado (numba) das metaheuristicas: custo incremental e movimentos.

O calculo e EXATAMENTE o de custo_rapido.custo_enf / inrc2.evaluate (conferido em testes.py), mas escrito
com arrays NumPy e compilado pelo numba (JIT). Isso deixa cada movimento ~50x mais rapido que em Python puro,
o que permite ao SA e ao GRASP avaliar centenas de milhoes de movimentos em poucos minutos.

Representacao da escala (igual a do grasp.py):
  sid[n, d] = turno do enfermeiro n no dia d (-1 = folga)
  skl[n, d] = habilidade usada (-1 = folga)

Custo separado em tres partes (versao 4, 21/11/2026), mantidas em cache (avaliacao incremental):
  soft      = penalidades S1..S7 com os pesos oficiais (o custo de verdade da escala)
  hard      = numero de violacoes hard (falta na cobertura minima H2, sucessao proibida H3)
  gravidade = as mesmas penalidades soft multiplicadas por um fator de GRAVIDADE de cada tipo de regra;
              so e usada para DESEMPATAR dois movimentos de mesmo custo (sugestao do professor)
  cnt[d, s, k]              = quantos enfermeiros cobrem (dia, turno, habilidade)
  ns[n], nh[n], nv[n]       = soft, hard e gravidade individuais do enfermeiro n
  tot[0], tot[1], tot[2]    = soft, hard e gravidade da escala inteira
A funcao de avaliacao das metaheuristicas e  soft + lam * hard.  Na versao 3, lam = GRANDE = 10000 fixo; agora
lam pode mudar durante a busca (penalidade dinamica, em sa.py). Com lam = GRANDE e sem desempate, o resultado
e identico ao da versao 3 (conferido em testes.py, mesma semente -> mesma escala).

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

GRANDE = 10000      # peso fixo de cada violacao hard (versao 3); continua sendo o teto da penalidade dinamica
NADA = 1 << 40      # "movimento invalido ou sem efeito"

# Tipos de penalidade soft (indice no vetor de gravidade)
TIPOS = ["S1 cobertura otima", "S2 turnos seguidos", "S2 dias de trabalho seguidos", "S3 folgas seguidas",
         "S4 pedidos de folga", "S5 fim de semana completo", "S6 total de turnos", "S7 fins de semana"]
# Gravidade usada no desempate: quanto maior, pior a violacao para o hospital. Ordem: cobertura (seguranca do
# paciente) > descanso (folgas seguidas) > fadiga (dias de trabalho seguidos) > fins de semana > organizacao
# (turnos seguidos, total de turnos) > pedidos individuais. So decide EMPATES do custo oficial.
GRAV_PADRAO = np.array([6, 2, 4, 5, 1, 3, 2, 3], dtype=np.int64)
GRAV_NEUTRA = np.ones(8, dtype=np.int64)       # gravidade = custo: o desempate nao muda nada

Dados = namedtuple("Dados", "N D S K minS maxS minW maxW minO maxO minA maxA maxWE comp "
                            "hlast hcS hcW hcO hnA hnWE forb reqA reqS dmin dopt habs nhab temhab grav")


def dados(inst, grav=None):
    """Converte a Instance (inrc2) em arrays para o codigo compilado. grav: fatores de gravidade (8 tipos)."""
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
    g = GRAV_PADRAO if grav is None else np.array(grav, dtype=np.int64)
    return Dados(N, D, S, K, i64(inst.min_cons_shift), i64(inst.max_cons_shift),
                 i64([c["minW"] for c in ct]), i64([c["maxW"] for c in ct]),
                 i64([c["minO"] for c in ct]), i64([c["maxO"] for c in ct]),
                 i64([c["minA"] for c in ct]), i64([c["maxA"] for c in ct]),
                 i64([c["maxWE"] for c in ct]), i64([c["complete"] for c in ct]),
                 i64([x["last"] for x in h]), i64([x["cS"] for x in h]), i64([x["cW"] for x in h]),
                 i64([x["cO"] for x in h]), i64([x["nA"] for x in h]), i64([x["nWE"] for x in h]),
                 np.array(inst.forb, dtype=np.bool_), reqA, reqS,
                 np.array(inst.dmin, dtype=np.int64), np.array(inst.dopt, dtype=np.int64), habs, nhab, temhab, g)


# ====================================================================== custo
@njit(cache=True)
def custo_linha3(P, n, row):
    """Custo individual do enfermeiro n com a linha row (turno por dia, -1 = folga): (soft, hard, gravidade).
    soft + GRANDE * hard e igual a custo_rapido.custo_enf."""
    D = row.shape[0]
    if D == 0:
        return 0, 0, 0
    minW, maxW, minO, maxO = P.minW[n], P.maxW[n], P.minO[n], P.maxO[n]
    last, cS, cW, cO = P.hlast[n], P.hcS[n], P.hcW[n], P.hcO[n]
    cT = 0; cWk = 0; cO_ = 0; cP = 0; cF = 0; cTot = 0; cM = 0; hard = 0     # por tipo de regra
    if last >= 0 and cS > 0 and row[0] != last:
        cT += W_SHIFT * max(0, P.minS[last] - cS)
    if cW > 0 and row[0] < 0:
        cWk += W_WORK * max(0, minW - cW)
    if cO > 0 and row[0] >= 0:
        cO_ += W_OFF * max(0, minO - cO)
    d = 0
    while d < D:
        e = d + 1
        if row[d] >= 0:
            while e < D and row[e] >= 0:
                e += 1
            hp = cW if d == 0 else 0
            tot = e - d + hp
            cWk += W_WORK * (max(0, tot - maxW) - max(0, hp - maxW))
            if e < D:
                cWk += W_WORK * max(0, minW - tot)
            i = d
            while i < e:
                s = row[i]; j = i + 1
                while j < e and row[j] == s:
                    j += 1
                hps = cS if (i == 0 and last == s) else 0
                tot = j - i + hps
                cT += W_SHIFT * (max(0, tot - P.maxS[s]) - max(0, hps - P.maxS[s]))
                if j < D:
                    cT += W_SHIFT * max(0, P.minS[s] - tot)
                i = j
        else:
            while e < D and row[e] < 0:
                e += 1
            hp = cO if d == 0 else 0
            tot = e - d + hp
            cO_ += W_OFF * (max(0, tot - maxO) - max(0, hp - maxO))
            if e < D:
                cO_ += W_OFF * max(0, minO - tot)
        d = e
    trab = 0; nwe = 0; prev = last
    for d in range(D):
        x = row[d]
        if x >= 0:
            trab += 1
            cP += W_PREF * (P.reqA[n, d] + P.reqS[n, d, x])
            if prev >= 0 and P.forb[prev, x]:
                hard += 1
        prev = x
    for wk in range(D // 7):
        sat = row[7 * wk + 5] >= 0; sun = row[7 * wk + 6] >= 0
        if P.comp[n] == 1 and sat != sun:
            cF += W_WEEKEND
        if sat or sun:
            nwe += 1
    tot = P.hnA[n] + trab
    cTot += W_TOTAL * (max(0, P.minA[n] - tot) + max(0, tot - P.maxA[n]))
    cM += W_MAXWE * max(0, P.hnWE[n] + nwe - P.maxWE[n])
    g = P.grav
    soft = cT + cWk + cO_ + cP + cF + cTot + cM
    grav = g[1] * cT + g[2] * cWk + g[3] * cO_ + g[4] * cP + g[5] * cF + g[6] * cTot + g[7] * cM
    return soft, hard, grav


@njit(cache=True)
def custo_linha(P, n, row):
    """Custo individual com as violacoes hard pesando GRANDE (igual a custo_rapido.custo_enf e a versao 3)."""
    s, h, g = custo_linha3(P, n, row)
    return s + GRANDE * h


@njit(cache=True)
def cob(P, d, s, k, c):
    """Cobertura da celula (dia, turno, habilidade) com c enfermeiros: (soft S1, numero de faltas hard H2)."""
    return W_S1 * max(0, P.dopt[d, s, k] - c), max(0, P.dmin[d, s, k] - c)


@njit(cache=True)
def custo_total(P, sid, skl, cnt, ns, nh, nv, tot):
    """Recalcula do zero cnt, ns, nh, nv e tot = [soft, hard, gravidade]."""
    cnt[:] = 0
    for n in range(P.N):
        for d in range(P.D):
            if sid[n, d] >= 0:
                cnt[d, sid[n, d], skl[n, d]] += 1
    ts = 0; th = 0; tv = 0
    for d in range(P.D):
        for s in range(P.S):
            for k in range(P.K):
                a, b = cob(P, d, s, k, cnt[d, s, k])
                ts += a; th += b; tv += P.grav[0] * a
    for n in range(P.N):
        a, b, c = custo_linha3(P, n, sid[n])
        ns[n] = a; nh[n] = b; nv[n] = c
        ts += a; th += b; tv += c
    tot[0] = ts; tot[1] = th; tot[2] = tv


# ====================================================================== movimentos
@njit(cache=True)
def delta_bloco(P, sid, skl, cnt, ns, nh, nv, n, d0, L, s, buf, novk):
    """Delta de dar o turno s (ou folga) ao enfermeiro n nos dias d0..d0+L-1.
    Preenche novk[0:L] com as habilidades escolhidas e devolve
    (d_soft, d_hard, d_gravidade, novo soft, novo hard e nova gravidade do enfermeiro); d_soft = NADA se nao muda."""
    igual = True
    for d in range(d0, d0 + L):
        if sid[n, d] != s:
            igual = False
            break
    if igual:
        return NADA, 0, 0, 0, 0, 0
    dcs = 0; dch = 0
    for i in range(L):
        d = d0 + i
        s0 = sid[n, d]; k0 = skl[n, d]
        if s0 >= 0:
            c0 = cnt[d, s0, k0]
            a1, b1 = cob(P, d, s0, k0, c0 - 1); a0, b0 = cob(P, d, s0, k0, c0)
            dcs += a1 - a0; dch += b1 - b0
            cnt[d, s0, k0] -= 1
        if s >= 0:                         # habilidade que mais ajuda a cobertura neste dia (hard pesa GRANDE)
            mk = -1; md = NADA; ma = 0; mb = 0
            for j in range(P.nhab[n]):
                k = P.habs[n, j]
                a1, b1 = cob(P, d, s, k, cnt[d, s, k] + 1); a0, b0 = cob(P, d, s, k, cnt[d, s, k])
                v = (a1 - a0) + GRANDE * (b1 - b0)
                if v < md:
                    md = v; mk = k; ma = a1 - a0; mb = b1 - b0
            dcs += ma; dch += mb; novk[i] = mk
        else:
            novk[i] = -1
        if s0 >= 0:
            cnt[d, s0, k0] += 1
    for d in range(P.D):
        buf[d] = sid[n, d]
    for d in range(d0, d0 + L):
        buf[d] = s
    cs, chh, cv = custo_linha3(P, n, buf)
    return dcs + cs - ns[n], dch + chh - nh[n], P.grav[0] * dcs + cv - nv[n], cs, chh, cv


@njit(cache=True)
def aplicar_bloco(sid, skl, cnt, ns, nh, nv, tot, n, d0, L, s, novk, ds, dh, dv, cs, ch, cv):
    for i in range(L):
        d = d0 + i
        s0 = sid[n, d]
        if s0 >= 0:
            cnt[d, s0, skl[n, d]] -= 1
        if s >= 0:
            cnt[d, s, novk[i]] += 1
        sid[n, d] = s; skl[n, d] = novk[i]
    ns[n] = cs; nh[n] = ch; nv[n] = cv
    tot[0] += ds; tot[1] += dh; tot[2] += dv


@njit(cache=True)
def delta_troca(P, sid, skl, ns, nh, nv, n1, n2, d0, L, b1, b2):
    """Delta de n1 e n2 trocarem as atribuicoes nos dias d0..d0+L-1.
    Devolve (d_soft, d_hard, d_grav, soft1, hard1, grav1, soft2, hard2, grav2); d_soft = NADA se invalido."""
    igual = True
    for d in range(d0, d0 + L):
        if sid[n1, d] != sid[n2, d]:
            igual = False
        if sid[n2, d] >= 0 and not P.temhab[n1, skl[n2, d]]:
            return NADA, 0, 0, 0, 0, 0, 0, 0, 0
        if sid[n1, d] >= 0 and not P.temhab[n2, skl[n1, d]]:
            return NADA, 0, 0, 0, 0, 0, 0, 0, 0
    if igual:
        return NADA, 0, 0, 0, 0, 0, 0, 0, 0
    for d in range(P.D):
        b1[d] = sid[n1, d]; b2[d] = sid[n2, d]
    for d in range(d0, d0 + L):
        b1[d] = sid[n2, d]; b2[d] = sid[n1, d]
    s1, h1, v1 = custo_linha3(P, n1, b1); s2, h2, v2 = custo_linha3(P, n2, b2)
    return (s1 + s2 - ns[n1] - ns[n2], h1 + h2 - nh[n1] - nh[n2], v1 + v2 - nv[n1] - nv[n2],
            s1, h1, v1, s2, h2, v2)


@njit(cache=True)
def aplicar_troca(sid, skl, ns, nh, nv, tot, n1, n2, d0, L, ds, dh, dv, s1, h1, v1, s2, h2, v2):
    for d in range(d0, d0 + L):
        a = sid[n1, d]; sid[n1, d] = sid[n2, d]; sid[n2, d] = a
        a = skl[n1, d]; skl[n1, d] = skl[n2, d]; skl[n2, d] = a
    ns[n1] = s1; nh[n1] = h1; nv[n1] = v1; ns[n2] = s2; nh[n2] = h2; nv[n2] = v2
    tot[0] += ds; tot[1] += dh; tot[2] += dv


@njit(cache=True)
def semear(seed):
    np.random.seed(seed)


@njit(cache=True)
def melhor_que(tot, best, desempate):
    """A escala atual (tot) e melhor que a melhor guardada? Ordem: menos violacoes hard, depois menor custo soft,
    depois (com desempate) menor gravidade."""
    if tot[1] != best[1]:
        return tot[1] < best[1]
    if tot[0] != best[0]:
        return tot[0] < best[0]
    return desempate and tot[2] < best[2]


# ====================================================================== Simulated Annealing
TAM_TROCA = np.array([2, 3, 4, 5, 7], dtype=np.int64)


@njit(cache=True)
def sa_passos(P, sid, skl, cnt, ns, nh, nv, tot, best_sid, best_skl, best_tot, nmov, T, lam, desempate,
              tam_troca=TAM_TROCA):
    """nmov passos do SA na temperatura T (criterio de Metropolis sobre soft + lam * hard). Atualiza a melhor escala.
    Escolha do movimento: N1 40%, N3 20%, N2 20%, N4 20%.
    desempate: um movimento de custo igual (delta = 0) so e aceito se nao piorar a gravidade.
    Devolve (movimentos aceitos, melhorias da melhor escala, passos que terminaram numa escala viavel)."""
    N, D, S = P.N, P.D, P.S
    buf = np.empty(D, np.int64); b2 = np.empty(D, np.int64); novk = np.empty(8, np.int64)
    aceitos = 0; melhoras = 0; viaveis = 0
    for _ in range(nmov):
        r = np.random.random()
        if r < 0.6:
            L = 1 if r < 0.4 else np.random.randint(2, 6)
            n = np.random.randint(N); d0 = np.random.randint(D - L + 1); s = np.random.randint(-1, S)
            ds, dh, dv, cs, ch, cv = delta_bloco(P, sid, skl, cnt, ns, nh, nv, n, d0, L, s, buf, novk)
            if ds != NADA:
                delta = ds + lam * dh
                if (delta < 0 or (delta == 0 and (not desempate or dv <= 0))
                        or (delta > 0 and np.random.random() < np.exp(-delta / T))):
                    aplicar_bloco(sid, skl, cnt, ns, nh, nv, tot, n, d0, L, s, novk, ds, dh, dv, cs, ch, cv)
                    aceitos += 1
                    if melhor_que(tot, best_tot, desempate):
                        best_tot[:] = tot; best_sid[:] = sid; best_skl[:] = skl; melhoras += 1
        else:
            L = 1 if r < 0.8 else tam_troca[np.random.randint(tam_troca.shape[0])]
            n1 = np.random.randint(N); n2 = np.random.randint(N - 1)
            if n2 >= n1:
                n2 += 1
            d0 = np.random.randint(D - L + 1)
            ds, dh, dv, s1, h1, v1, s2, h2, v2 = delta_troca(P, sid, skl, ns, nh, nv, n1, n2, d0, L, buf, b2)
            if ds != NADA:
                delta = ds + lam * dh
                if (delta < 0 or (delta == 0 and (not desempate or dv <= 0))
                        or (delta > 0 and np.random.random() < np.exp(-delta / T))):
                    aplicar_troca(sid, skl, ns, nh, nv, tot, n1, n2, d0, L, ds, dh, dv, s1, h1, v1, s2, h2, v2)
                    aceitos += 1
                    if melhor_que(tot, best_tot, desempate):
                        best_tot[:] = tot; best_sid[:] = sid; best_skl[:] = skl; melhoras += 1
        if tot[1] == 0:
            viaveis += 1
    return aceitos, melhoras, viaveis


# ====================================================================== busca local (VND) do GRASP
@njit(cache=True)
def _aceita_vnd(ds, dh, dv, desempate):
    """Na busca local so entra o que melhora: custo menor, ou (desempate) mesmo custo e gravidade menor."""
    delta = ds + GRANDE * dh
    return delta < 0 or (desempate and delta == 0 and dv < 0)


@njit(cache=True)
def _n1(P, sid, skl, cnt, ns, nh, nv, tot, buf, novk, desempate):
    """N1 completa: para cada (enfermeiro, dia), em ordem aleatoria, aplica a melhor troca se melhorar."""
    N, D, S = P.N, P.D, P.S
    melhorou = False
    for idx in np.random.permutation(N * D):
        n = idx // D; d = idx % D
        md = 0; mv = 0; ms = -2; mk = -1
        bs = 0; bh = 0; bv = 0; bcs = 0; bch = 0; bcv = 0
        for s in range(-1, S):
            ds, dh, dv, cs, ch, cv = delta_bloco(P, sid, skl, cnt, ns, nh, nv, n, d, 1, s, buf, novk)
            if ds == NADA:
                continue
            delta = ds + GRANDE * dh
            if delta < md or (desempate and delta == md and dv < mv):
                md = delta; mv = dv; ms = s; mk = novk[0]
                bs = ds; bh = dh; bv = dv; bcs = cs; bch = ch; bcv = cv
        if ms > -2:
            novk[0] = mk
            aplicar_bloco(sid, skl, cnt, ns, nh, nv, tot, n, d, 1, ms, novk, bs, bh, bv, bcs, bch, bcv)
            melhorou = True
    return melhorou


@njit(cache=True)
def _n3(P, sid, skl, cnt, ns, nh, nv, tot, buf, novk, desempate):
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
        ds, dh, dv, cs, ch, cv = delta_bloco(P, sid, skl, cnt, ns, nh, nv, n, d0, L, s, buf, novk)
        if ds != NADA and _aceita_vnd(ds, dh, dv, desempate):
            aplicar_bloco(sid, skl, cnt, ns, nh, nv, tot, n, d0, L, s, novk, ds, dh, dv, cs, ch, cv)
            melhorou = True
    return melhorou


@njit(cache=True)
def _troca(P, sid, skl, ns, nh, nv, tot, b1, b2, tamanhos, desempate):
    """N2 (tamanhos = [1]) ou N4 (tamanhos = [2,3,4,5,7]) completas, em ordem aleatoria."""
    N, D = P.N, P.D
    nT = tamanhos.shape[0]; npar = N * (N - 1) // 2
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
        ds, dh, dv, s1, h1, v1, s2, h2, v2 = delta_troca(P, sid, skl, ns, nh, nv, n1, n2, d0, L, b1, b2)
        if ds != NADA and _aceita_vnd(ds, dh, dv, desempate):
            aplicar_troca(sid, skl, ns, nh, nv, tot, n1, n2, d0, L, ds, dh, dv, s1, h1, v1, s2, h2, v2)
            melhorou = True
    return melhorou


UM = np.array([1], dtype=np.int64)


@njit(cache=True)
def vnd(P, sid, skl, cnt, ns, nh, nv, tot, desempate=False):
    """VND: N1 -> N2 -> N3 -> N4; volta para N1 sempre que uma vizinhanca melhora. Termina num otimo local
    (nenhum movimento das quatro vizinhancas melhora a escala). Com desempate, um movimento de mesmo custo que
    reduz a gravidade tambem conta como melhora (a busca anda no 'plato' na direcao das violacoes menos graves;
    como (custo, gravidade) sempre diminui, o VND continua terminando). Devolve o numero de rodadas."""
    D = P.D
    buf = np.empty(D, np.int64); b2 = np.empty(D, np.int64); novk = np.empty(8, np.int64)
    rodadas = 0
    while True:
        rodadas += 1
        if _n1(P, sid, skl, cnt, ns, nh, nv, tot, buf, novk, desempate):
            continue
        if _troca(P, sid, skl, ns, nh, nv, tot, buf, b2, UM, desempate):
            continue
        if _n3(P, sid, skl, cnt, ns, nh, nv, tot, buf, novk, desempate):
            continue
        if _troca(P, sid, skl, ns, nh, nv, tot, buf, b2, TAM_TROCA, desempate):
            continue
        break
    return rodadas


# ====================================================================== utilidades Python
class Escala:
    """Escala + caches, em arrays NumPy (para usar com as funcoes compiladas)."""

    def __init__(self, P, sid, skl):
        self.P = P
        self.sid = np.array(sid, dtype=np.int64); self.skl = np.array(skl, dtype=np.int64)
        self.cnt = np.zeros((P.D, P.S, P.K), np.int64)
        self.ns = np.zeros(P.N, np.int64); self.nh = np.zeros(P.N, np.int64); self.nv = np.zeros(P.N, np.int64)
        self.tot = np.zeros(3, np.int64)
        custo_total(P, self.sid, self.skl, self.cnt, self.ns, self.nh, self.nv, self.tot)

    def estado(self):
        """Argumentos das funcoes compiladas: (sid, skl, cnt, ns, nh, nv, tot)."""
        return self.sid, self.skl, self.cnt, self.ns, self.nh, self.nv, self.tot

    @property
    def custo(self):
        """Custo com hard pesando GRANDE (o mesmo numero da versao 3)."""
        return int(self.tot[0] + GRANDE * self.tot[1])

    def sched(self):
        return [[None if self.sid[n, d] < 0 else (int(self.sid[n, d]), int(self.skl[n, d]))
                 for d in range(self.P.D)] for n in range(self.P.N)]

    def recalcular(self):
        """(soft, hard, gravidade) recalculados do zero (para conferir o incremental)."""
        cnt = np.zeros_like(self.cnt); a = np.zeros_like(self.ns); b = np.zeros_like(self.nh)
        c = np.zeros_like(self.nv); t = np.zeros(3, np.int64)
        custo_total(self.P, self.sid, self.skl, cnt, a, b, c, t)
        return tuple(int(x) for x in t)


def de_sched(sched):
    """sched (lista de listas de (s, k) ou None) -> (sid, skl) em listas."""
    sid = [[-1 if a is None else a[0] for a in r] for r in sched]
    skl = [[-1 if a is None else a[1] for a in r] for r in sched]
    return sid, skl
