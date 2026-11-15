"""custo_rapido.py - custo individual de um enfermeiro calculado em UMA passada pelos dias.

Faz o mesmo calculo de inrc2.nurse_breakdown (S2..S7 + violacoes de sucessao), mas sobre uma lista de
inteiros sid[d] (turno do dia d; -1 = folga) e sem criar listas auxiliares. E chamado milhares de vezes
por segundo pelo GRASP. A equivalencia com o avaliador e testada em testes.py.
"""
from inrc2 import W_SHIFT, W_WORK, W_OFF, W_PREF, W_WEEKEND, W_TOTAL, W_MAXWE


def custo_enf(inst, n, sid, peso_hard):
    D = len(sid); c = inst.ct[n]; h = inst.hist[n]
    minS, maxS = inst.min_cons_shift, inst.max_cons_shift
    minW, maxW, minO, maxO = c["minW"], c["maxW"], c["minO"], c["maxO"]
    custo = 0
    if D == 0:
        return 0
    # fronteira com o historico: sequencias que terminaram logo antes do dia 0
    last, cS = h["last"], h["cS"]
    if last >= 0 and cS > 0 and sid[0] != last:
        custo += W_SHIFT * max(0, minS[last] - cS)
    if h["cW"] > 0 and sid[0] < 0:
        custo += W_WORK * max(0, minW - h["cW"])
    if h["cO"] > 0 and sid[0] >= 0:
        custo += W_OFF * max(0, minO - h["cO"])
    # sequencias de trabalho / folga e, dentro do trabalho, sequencias do mesmo turno
    d = 0
    while d < D:
        e = d + 1
        if sid[d] >= 0:
            while e < D and sid[e] >= 0:
                e += 1
            hp = h["cW"] if d == 0 else 0
            tot = e - d + hp
            custo += W_WORK * (max(0, tot - maxW) - max(0, hp - maxW))
            if e < D:
                custo += W_WORK * max(0, minW - tot)
            i = d
            while i < e:
                s = sid[i]; j = i + 1
                while j < e and sid[j] == s:
                    j += 1
                hps = cS if (i == 0 and last == s) else 0
                tot = j - i + hps
                custo += W_SHIFT * (max(0, tot - maxS[s]) - max(0, hps - maxS[s]))
                if j < D:
                    custo += W_SHIFT * max(0, minS[s] - tot)
                i = j
        else:
            while e < D and sid[e] < 0:
                e += 1
            hp = h["cO"] if d == 0 else 0
            tot = e - d + hp
            custo += W_OFF * (max(0, tot - maxO) - max(0, hp - maxO))
            if e < D:
                custo += W_OFF * max(0, minO - tot)
        d = e
    # S4 pedidos
    for d, q in inst.req_any[n].items():
        if d < D and sid[d] >= 0:
            custo += W_PREF * q
    for (d, s), q in inst.req_sh[n].items():
        if d < D and sid[d] == s:
            custo += W_PREF * q
    # S5 fim de semana completo, S7 fins de semana trabalhados, S6 total de turnos
    nwe = 0
    for wk in range(D // 7):
        sat, sun = sid[7 * wk + 5] >= 0, sid[7 * wk + 6] >= 0
        if c["complete"] and sat != sun:
            custo += W_WEEKEND
        if sat or sun:
            nwe += 1
    tot = h["nA"] + sum(1 for x in sid if x >= 0)
    custo += W_TOTAL * (max(0, c["minA"] - tot) + max(0, tot - c["maxA"]))
    custo += W_MAXWE * max(0, h["nWE"] + nwe - c["maxWE"])
    # H3 sucessoes proibidas (inclui a fronteira com o historico)
    prev, forb = last, inst.forb
    for x in sid:
        if prev >= 0 and x >= 0 and forb[prev][x]:
            custo += peso_hard
        prev = x
    return custo
