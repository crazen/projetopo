"""inrc2.py - leitura de instancias do INRC-II (JSON), avaliador de custo e utilidades.

Uma INSTANCIA = cenario (Sc-*.json) + historico inicial (H0-*.json) + sequencia de semanas (WD-*.json).
Neste projeto o horizonte inteiro (4 ou 8 semanas) e resolvido de uma vez ("offline"), com a demanda de
todas as semanas conhecida. O custo e calculado como no validador oficial do INRC-II.

Representacao de uma escala:  sched[n][d] = (s, k)  -> enfermeiro n faz o turno s com a habilidade k no dia d
                              sched[n][d] = None    -> folga
(n, d, s, k sao indices inteiros; d = 0 e a segunda-feira da primeira semana.)

Pesos do INRC-II:
  S1 cobertura otima 30 | S2 consecutivos (turno 15, dias de trabalho 30) | S3 folgas consecutivas 30
  S4 preferencias 10    | S5 fim de semana completo 30 | S6 total de turnos 20 | S7 fins de semana trabalhados 30
Restricoes hard: H1 um turno por dia (garantido pela representacao), H2 cobertura minima,
                 H3 sucessoes proibidas, H4 habilidade exigida.
"""
import json, os, re, glob
from dataclasses import dataclass, field

DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
W_S1, W_SHIFT, W_WORK, W_OFF, W_PREF, W_WEEKEND, W_TOTAL, W_MAXWE = 30, 15, 30, 30, 10, 30, 20, 30
SOFT_KEYS = ["S1", "S2shift", "S2work", "S3off", "S4pref", "S5weekend", "S6total", "S7maxwe"]


def _day_idx(name):
    return [d.lower() for d in DAYS].index(name[:3].lower())


@dataclass
class Instance:
    name: str
    N: int; W: int; D: int
    nurses: list            # ids (strings)
    skills: list
    shifts: list
    nurse_skills: list      # [n] -> conjunto de indices de habilidade
    min_cons_shift: list; max_cons_shift: list          # por tipo de turno
    forbidden: set          # {(s1, s2)}: s1 no dia d nao pode ser seguido de s2 no dia d+1
    ct: list                # [n] -> dict do contrato
    dmin: list; dopt: list  # [d][s][k]
    requests: list          # (n, d, s); s = -1 => pedido de folga no dia ("Any")
    hist: list              # [n] -> dict do historico
    req_any: list = field(default_factory=list)   # [n] -> {d: quantidade}
    req_sh: list = field(default_factory=list)    # [n] -> {(d, s): quantidade}
    forb: list = field(default_factory=list)      # [s1][s2] -> bool


def load_instance(folder, h_idx, wd_seq, name=None):
    """folder: pasta do dataset (ex.: .../n005w4). h_idx: indice do historico. wd_seq: lista de indices das semanas."""
    scf = glob.glob(os.path.join(folder, "Sc-*.json"))
    if not scf:
        raise FileNotFoundError(f"nenhum Sc-*.json em {folder}")
    sc = json.load(open(scf[0]))
    ds = os.path.basename(os.path.normpath(folder))   # nome = pasta (o id interno pode diferir, ex.: n021w4_2)
    hist = json.load(open(os.path.join(folder, f"H0-{ds}-{h_idx}.json")))
    wds = [json.load(open(os.path.join(folder, f"WD-{ds}-{i}.json"))) for i in wd_seq]
    return build_instance(sc, hist, wds, name or f"{ds}_H{h_idx}_WD{'-'.join(map(str, wd_seq))}")


def build_instance(sc, hist, wds, name):
    W = sc["numberOfWeeks"]
    if len(wds) != W:
        raise ValueError(f"o cenario tem {W} semanas, mas foram dados {len(wds)} arquivos WD")
    nurses = [n["id"] for n in sc["nurses"]]; N = len(nurses)
    skills = list(sc["skills"]); shifts = [s["id"] for s in sc["shiftTypes"]]
    sidx = {s: i for i, s in enumerate(shifts)}; kidx = {k: i for i, k in enumerate(skills)}
    nidx = {n: i for i, n in enumerate(nurses)}
    cons = {c["id"]: c for c in sc["contracts"]}
    ct = []
    for n in sc["nurses"]:
        c = cons[n["contract"]]
        ct.append(dict(minA=c["minimumNumberOfAssignments"], maxA=c["maximumNumberOfAssignments"],
                       minW=c["minimumNumberOfConsecutiveWorkingDays"], maxW=c["maximumNumberOfConsecutiveWorkingDays"],
                       minO=c["minimumNumberOfConsecutiveDaysOff"], maxO=c["maximumNumberOfConsecutiveDaysOff"],
                       maxWE=c["maximumNumberOfWorkingWeekends"], complete=int(c["completeWeekends"])))
    forb = set()
    for f in sc["forbiddenShiftTypeSuccessions"]:
        for s2 in f["succeedingShiftTypes"]:
            forb.add((sidx[f["precedingShiftType"]], sidx[s2]))
    D = 7 * W; S = len(shifts); K = len(skills)
    dmin = [[[0] * K for _ in range(S)] for _ in range(D)]
    dopt = [[[0] * K for _ in range(S)] for _ in range(D)]
    req = []
    for w, wd in enumerate(wds):
        for r in wd["requirements"]:
            s, k = sidx[r["shiftType"]], kidx[r["skill"]]
            for di, dn in enumerate(["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]):
                v = r["requirementOn" + dn]; d = 7 * w + di
                dmin[d][s][k] = v["minimum"]; dopt[d][s][k] = v["optimal"]
        for o in wd.get("shiftOffRequests", []):
            req.append((nidx[o["nurse"]], 7 * w + _day_idx(o["day"]),
                        -1 if o["shiftType"] == "Any" else sidx[o["shiftType"]]))
    hh = [None] * N
    for h in hist["nurseHistory"]:
        hh[nidx[h["nurse"]]] = dict(nA=h["numberOfAssignments"], nWE=h["numberOfWorkingWeekends"],
                                    last=(-1 if h["lastAssignedShiftType"] == "None" else sidx[h["lastAssignedShiftType"]]),
                                    cS=h["numberOfConsecutiveAssignments"], cW=h["numberOfConsecutiveWorkingDays"],
                                    cO=h["numberOfConsecutiveDaysOff"])
    inst = Instance(name, N, W, D, nurses, skills, shifts,
                    [{kidx[k] for k in n["skills"]} for n in sc["nurses"]],
                    [s["minimumNumberOfConsecutiveAssignments"] for s in sc["shiftTypes"]],
                    [s["maximumNumberOfConsecutiveAssignments"] for s in sc["shiftTypes"]],
                    forb, ct, dmin, dopt, req, hh)
    inst.req_any = [dict() for _ in range(N)]
    inst.req_sh = [dict() for _ in range(N)]
    for (n, d, s) in req:
        if s == -1:
            inst.req_any[n][d] = inst.req_any[n].get(d, 0) + 1
        else:
            inst.req_sh[n][(d, s)] = inst.req_sh[n].get((d, s), 0) + 1
    inst.forb = [[(a, b) in forb for b in range(S)] for a in range(S)]
    return inst


# ------------------------------------------------------------ instancias e solucoes
def parse_spec(spec):
    """'n005w4 0 1,2,3,3'  ->  ('n005w4', 0, [1,2,3,3])"""
    ds, h, wd = spec.split()
    return ds, int(h), [int(x) for x in wd.replace("-", ",").split(",")]


def list_reference_instances(folder):
    """Instancias de teste que vem com solucao de referencia: pastas Solution_H_<h>-WD_<a>-<b>-..."""
    out = []
    for p in sorted(glob.glob(os.path.join(folder, "Solution_H_*"))):
        m = re.match(r"Solution_H_(\d+)-WD_([\d-]+)$", os.path.basename(p))
        if m:
            out.append((int(m.group(1)), [int(x) for x in m.group(2).split("-")], p))
    return out


def load_solution_dir(inst, soldir):
    """Le os Sol-*.json (um por semana) -> sched."""
    sidx = {s: i for i, s in enumerate(inst.shifts)}; kidx = {k: i for i, k in enumerate(inst.skills)}
    nidx = {n: i for i, n in enumerate(inst.nurses)}
    sched = [[None] * inst.D for _ in range(inst.N)]
    for f in glob.glob(os.path.join(soldir, "Sol-*.json")):
        sol = json.load(open(f)); w = sol["week"]
        for a in sol["assignments"]:
            sched[nidx[a["nurse"]]][7 * w + _day_idx(a["day"])] = (sidx[a["shiftType"]], kidx[a["skill"]])
    return sched


def save_solution_json(inst, sched, outdir):
    """Grava a escala no formato de solucao do INRC-II (um arquivo por semana)."""
    os.makedirs(outdir, exist_ok=True)
    for w in range(inst.W):
        asg = [dict(nurse=inst.nurses[n], day=DAYS[d % 7], shiftType=inst.shifts[sched[n][d][0]],
                    skill=inst.skills[sched[n][d][1]])
               for n in range(inst.N) for d in range(7 * w, 7 * w + 7) if sched[n][d] is not None]
        json.dump(dict(scenario=inst.name, week=w, assignments=asg),
                  open(os.path.join(outdir, f"Sol-{inst.name}-week{w}.json"), "w"), indent=1)


def print_schedule(inst, sched):
    """Imprime a escala como tabela (linhas = enfermeiros, colunas = dias). Ex.: 'E' = Early, '-' = folga."""
    ab = [s[0] for s in inst.shifts]
    head = "".join(f"{DAYS[d % 7][0]}" for d in range(inst.D))
    print(f"{'':>12s} {head}")
    for n in range(inst.N):
        print(f"{inst.nurses[n]:>12s} " + "".join("-" if sched[n][d] is None else ab[sched[n][d][0]] for d in range(inst.D)))


# ------------------------------------------------------------ avaliador
def run_pen(a, c_prev, mn, mx):
    """Penalidade (em dias) das sequencias consecutivas do indicador a[d] em {0,1}, dado o historico c_prev
    (tamanho da sequencia ativa que vinha da semana anterior; 0 se a ultima situacao era inativa).
    max: conta so os dias do horizonte alem do limite (o excesso do historico ja foi contado antes).
    min: so para sequencias que TERMINAM dentro do horizonte (seguidas de um 0)."""
    D = len(a); over = under = 0
    d = 0
    while d < D:
        if a[d] == 1:
            e = d
            while e < D and a[e] == 1:
                e += 1
            L = e - d; hist_part = c_prev if d == 0 else 0
            tot = L + hist_part
            over += max(0, tot - mx) - max(0, hist_part - mx)
            if e < D:
                under += max(0, mn - tot)
            d = e
        else:
            if d == 0 and c_prev > 0:          # sequencia do historico terminou logo antes do dia 0
                under += max(0, mn - c_prev)
            d += 1
    return over + under


def nurse_breakdown(inst, n, row):
    """Custos individuais do enfermeiro n (S2..S7) e violacoes de sucessao (hard H3).
    row[d] = (s, k) ou None. E a MESMA funcao usada pelo avaliador e pelas heuristicas."""
    D = len(row); c = inst.ct[n]; h = inst.hist[n]
    sid = [-1 if r is None else r[0] for r in row]
    w = [0 if x < 0 else 1 for x in sid]
    out = dict(S2shift=0, S2work=0, S3off=0, S4pref=0, S5weekend=0, S6total=0, S7maxwe=0, succ=0)
    for s in range(len(inst.shifts)):
        a = [1 if x == s else 0 for x in sid]
        out["S2shift"] += W_SHIFT * run_pen(a, h["cS"] if h["last"] == s else 0,
                                            inst.min_cons_shift[s], inst.max_cons_shift[s])
    out["S2work"] = W_WORK * run_pen(w, h["cW"], c["minW"], c["maxW"])
    out["S3off"] = W_OFF * run_pen([1 - x for x in w], h["cO"], c["minO"], c["maxO"])
    for d, q in inst.req_any[n].items():
        if d < D and w[d]:
            out["S4pref"] += W_PREF * q
    for (d, s), q in inst.req_sh[n].items():
        if d < D and sid[d] == s:
            out["S4pref"] += W_PREF * q
    nwe = 0
    for wk in range(D // 7):
        sat, sun = w[7 * wk + 5], w[7 * wk + 6]
        if c["complete"] and sat != sun:
            out["S5weekend"] += W_WEEKEND
        nwe += 1 if (sat or sun) else 0
    tot = h["nA"] + sum(w)
    out["S6total"] = W_TOTAL * (max(0, c["minA"] - tot) + max(0, tot - c["maxA"]))
    out["S7maxwe"] = W_MAXWE * max(0, h["nWE"] + nwe - c["maxWE"])
    prev = h["last"]
    for d in range(D):
        if prev >= 0 and sid[d] >= 0 and inst.forb[prev][sid[d]]:
            out["succ"] += 1
        prev = sid[d]
    return out


def evaluate(inst, sched):
    """Retorna (violacoes_hard, custos_por_componente, custo_total). Custo valido so se todas as violacoes forem 0."""
    N, D, S, K = inst.N, inst.D, len(inst.shifts), len(inst.skills)
    hard = dict(min_coverage=0, skill=0, succession=0)
    cost = {k: 0 for k in SOFT_KEYS}
    cnt = [[[0] * K for _ in range(S)] for _ in range(D)]
    for n in range(N):
        for d in range(D):
            if sched[n][d] is not None:
                s, k = sched[n][d]; cnt[d][s][k] += 1
                if k not in inst.nurse_skills[n]:
                    hard["skill"] += 1
    for d in range(D):
        for s in range(S):
            for k in range(K):
                hard["min_coverage"] += max(0, inst.dmin[d][s][k] - cnt[d][s][k])
                cost["S1"] += W_S1 * max(0, inst.dopt[d][s][k] - cnt[d][s][k])
    for n in range(N):
        b = nurse_breakdown(inst, n, sched[n])
        hard["succession"] += b.pop("succ")
        for key, v in b.items():
            cost[key] += v
    return hard, cost, sum(cost.values())


def is_feasible(hard):
    return sum(hard.values()) == 0
