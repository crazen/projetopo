"""gen_dat.py - converte uma instancia INRC-II (JSON) no arquivo .dat do modelo nurse.mod (AMPL).

Uso:  python gen_dat.py <pasta_dataset> <h> <semanas> <saida.dat>
Ex.:  python gen_dat.py dados/n005w4 0 1,2,3,3 n005w4_H0_WD1-2-3-3.dat

O historico (semana anterior ao horizonte) vira H dias "virtuais" -H..-1 no modelo:
  - hw[n,d] = 1 se o enfermeiro trabalhou no dia virtual d (reconstruido a partir das sequencias do historico)
  - hs[n,d,s] = 1 se fez o turno s no dia virtual d
Isso permite que as restricoes de sequencia (min/max consecutivos) e de sucessao enxerguem a fronteira.
"""
import sys
from inrc2 import load_instance


def q(s):
    return "'" + s + "'"


def write_dat(inst, path):
    N, W, D = inst.N, inst.W, inst.D
    S, K = len(inst.shifts), len(inst.skills)
    lim = [max(inst.max_cons_shift), max(inst.min_cons_shift)]
    for c in inst.ct:
        lim += [c["maxW"], c["minW"], c["maxO"], c["minO"]]
    H = max(lim) + 2                       # dias virtuais suficientes para as janelas mais longas
    L = ["data;", f"param W := {W};", f"param H := {H};"]
    L.append("set NURSES := " + " ".join(q(n) for n in inst.nurses) + ";")
    L.append("set SKILLS := " + " ".join(q(k) for k in inst.skills) + ";")
    L.append("set SHIFTS := " + " ".join(q(s) for s in inst.shifts) + ";")
    L.append("set FORB := " + " ".join(f"({q(inst.shifts[a])},{q(inst.shifts[b])})" for a, b in sorted(inst.forbidden)) + ";")
    L.append("param minS := " + " ".join(f"{q(s)} {v}" for s, v in zip(inst.shifts, inst.min_cons_shift)) + ";")
    L.append("param maxS := " + " ".join(f"{q(s)} {v}" for s, v in zip(inst.shifts, inst.max_cons_shift)) + ";")
    for name, key in (("minA", "minA"), ("maxA", "maxA"), ("minW", "minW"), ("maxW", "maxW"),
                      ("minO", "minO"), ("maxO", "maxO"), ("maxWE", "maxWE"), ("comp", "complete")):
        L.append(f"param {name} := " + " ".join(f"{q(inst.nurses[n])} {inst.ct[n][key]}" for n in range(N)) + ";")
    L.append("param nA0 := " + " ".join(f"{q(inst.nurses[n])} {inst.hist[n]['nA']}" for n in range(N)) + ";")
    L.append("param nWE0 := " + " ".join(f"{q(inst.nurses[n])} {inst.hist[n]['nWE']}" for n in range(N)) + ";")
    L.append("param has := " + " ".join(f"{q(inst.nurses[n])} {q(inst.skills[k])} 1"
                                        for n in range(N) for k in sorted(inst.nurse_skills[n])) + ";")
    for name, arr in (("dmin", inst.dmin), ("dopt", inst.dopt)):
        L.append(f"param {name} := " + " ".join(f"{d} {q(inst.shifts[s])} {q(inst.skills[k])} {arr[d][s][k]}"
                                                for d in range(D) for s in range(S) for k in range(K) if arr[d][s][k]) + ";")
    L.append("param reqAny := " + " ".join(f"{q(inst.nurses[n])} {d} {v}"
                                           for n in range(N) for d, v in sorted(inst.req_any[n].items())) + ";")
    L.append("param reqSh := " + " ".join(f"{q(inst.nurses[n])} {d} {q(inst.shifts[s])} {v}"
                                          for n in range(N) for (d, s), v in sorted(inst.req_sh[n].items())) + ";")
    hw, hs = [], []
    for n in range(N):
        h = inst.hist[n]
        if (h["cW"] > 0) == (h["cO"] > 0):
            raise ValueError(f"historico inesperado para {inst.nurses[n]}: exatamente um entre "
                             f"dias trabalhados ({h['cW']}) e folgas consecutivas ({h['cO']}) deve ser > 0")
        run, val = (h["cW"], 1) if h["cW"] > 0 else (h["cO"], 0)
        for d in range(-H, 0):                         # sequencia do historico; antes dela, o estado oposto
            hw.append(f"{q(inst.nurses[n])} {d} {val if d >= -run else 1 - val}")
        if h["last"] >= 0 and h["cS"] > 0:
            for d in range(-h["cS"], 0):
                hs.append(f"{q(inst.nurses[n])} {d} {q(inst.shifts[h['last']])} 1")
    L.append("param hw := " + " ".join(hw) + ";")
    L.append("param hs := " + " ".join(hs) + ";")
    L.append("end;")
    with open(path, "w") as f:
        f.write("\n".join(L) + "\n")


if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit(__doc__)
    folder, h, wds, out = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")], sys.argv[4]
    write_dat(load_instance(folder, h, wds), out)
    print("escrito", out)
