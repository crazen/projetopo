"""lns.py - matheuristica Fix-and-Optimize / LNS (Large Neighborhood Search) para o Nurse Rostering.

Ideia: o solver MIP nao consegue resolver a instancia inteira rapido, mas resolve muito bem um PEDACO dela.
  1. Solucao inicial: GRASP (uma fracao do tempo).
  2. Repete ate acabar o tempo:
       - escolhe uma vizinhanca grande: um grupo de enfermeiros (todos os dias) OU uma janela de dias
         (todos os enfermeiros);
       - FIXA as variaveis x[n,d,s,k] fora da vizinhanca nos valores da solucao atual;
       - resolve o MIP (nurse.mod) so com as variaveis livres, partindo da solucao atual (warm start),
         com um limite de tempo curto;
       - se o solver achar uma escala melhor, ela vira a solucao atual.
  3. O tamanho da vizinhanca se adapta: cresce quando o subproblema e resolvido ate o otimo sem melhora
     (vizinhanca facil demais), diminui quando o subproblema estoura o tempo (dificil demais).

Uso:  python lns.py <pasta_dataset> <h> <semanas> [limite_s] [semente]
"""
import sys, time, random
from inrc2 import load_instance, evaluate, is_feasible, print_schedule
from exato import ModeloPLI
from grasp import grasp


def lns(inst, limite=120, semente=0, frac_grasp=0.2, sub_limite=10, threads=1, verbose=True, sched_inicial=None):
    rng = random.Random(semente)
    t0 = time.time(); prazo = t0 + limite
    if sched_inicial is None:
        g = grasp(inst, limite=frac_grasp * limite, semente=semente, verbose=False)
        atual, custo_ini = g["sched"], g["custo"]
        if verbose:
            print(f"  GRASP inicial: custo={g['custo']} viavel={g['viavel']} ({time.time() - t0:.1f}s)", flush=True)
    else:
        atual = sched_inicial
        custo_ini = evaluate(inst, atual)[2]
    m = ModeloPLI(inst, threads=threads)
    col, _ = m.completar(atual)               # vetor completo de variaveis, usado como ponto de partida do solver
    hard, _, obj = evaluate(inst, atual)
    if col is None or not is_feasible(hard):
        col, obj = None, float("inf")          # escala inicial viola restricao hard: o LNS tenta repara-la
    historico = [(round(time.time() - t0, 2), obj)]
    q = max(2, inst.N // 5)                    # tamanho da vizinhanca de enfermeiros
    J = 7                                      # tamanho da janela de dias
    it = melhoras = 0
    while time.time() < prazo - 0.5:
        it += 1
        if col is None or rng.random() < 0.5:  # janela de dias (todos os enfermeiros)
            d0 = rng.randrange(0, inst.D - J + 1)
            livre = lambda n, d, a=d0, b=d0 + J: a <= d < b
            tipo = f"janela dias {d0}-{d0 + J - 1}"
        else:                                  # grupo de enfermeiros (todos os dias)
            grupo = set(rng.sample(range(inst.N), min(q, inst.N)))
            livre = lambda n, d, g=grupo: n in g
            tipo = f"{len(grupo)} enfermeiros"
        m.fixar(atual, livre)
        r = m.resolver(limite=min(sub_limite, prazo - time.time()), inicio=col)
        # compara pelo custo real (avaliador): o objetivo de uma solucao nao otima do solver pode estar inflado
        novo = evaluate(inst, r["sched"])[2] if r["tem_solucao"] else None
        if novo is not None and novo < obj - 1e-6:
            atual, col, obj = r["sched"], r["col_value"], novo
            melhoras += 1
            historico.append((round(time.time() - t0, 2), obj))
            if verbose:
                print(f"  it {it:3d}  t={time.time() - t0:6.1f}s  {tipo:22s}  -> {obj:.0f}", flush=True)
        # adaptacao do tamanho da vizinhanca
        if r["status"] == "Optimal":
            q = min(inst.N, q + 1); J = min(inst.D, J + 1)
        elif r["status"] == "Time limit reached":
            q = max(2, q - 1); J = max(3, J - 1)
    m.liberar_todos()
    hard, comp, custo = evaluate(inst, atual)
    return dict(sched=atual, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                custo_inicial=custo_ini, iteracoes=it, melhoras=melhoras, tempo=time.time() - t0,
                historico=historico)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 120
    semente = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    inst = load_instance(folder, h, wds)
    r = lns(inst, limite, semente)
    print(f"{inst.name}: custo={r['custo']} (inicial {r['custo_inicial']}) viavel={r['viavel']} "
          f"iteracoes={r['iteracoes']} melhoras={r['melhoras']} tempo={r['tempo']:.1f}s")
    print("  componentes:", r["componentes"])
    print_schedule(inst, r["sched"])
