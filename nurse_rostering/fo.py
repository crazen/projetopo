"""fo.py - matheuristica Fix-and-Optimize (F&O) para o Nurse Rostering (INRC-II).

Fix-and-Optimize (Helber e Sahling, 2010) e uma heuristica de melhoria baseada no proprio modelo de PLI:
  - as variaveis binarias x[n,d,s,k] sao divididas em subconjuntos por DECOMPOSICOES fixas do problema;
  - cada subproblema libera so um subconjunto, FIXA todas as outras variaveis binarias nos valores da solucao
    atual e resolve o MIP resultante (bem menor) com o solver, ate o otimo ou um limite de tempo;
  - os subproblemas sao resolvidos em SEQUENCIA, sempre a partir da solucao atual; como a solucao atual e
    viavel para cada subproblema (e entra como solucao inicial do solver), o custo nunca piora;
  - uma PASSADA percorre todos os subproblemas de todas as decomposicoes; o metodo repete passadas ate uma
    passada inteira nao melhorar nada: a solucao e entao um otimo local em relacao a essas decomposicoes.

Decomposicoes usadas (nesta ordem em cada passada):
  1. por DIAS: janelas de L dias seguidos com todos os enfermeiros livres; janelas com 50% de sobreposicao
     (inicios 0, L/2, L, ...). Reotimiza a cobertura de cada periodo, trocando turnos entre enfermeiros.
  2. por ENFERMEIROS: grupos de k enfermeiros com todos os dias livres. Os enfermeiros sao ordenados por
     conjunto de habilidades e contrato, entao cada grupo junta enfermeiros que podem substituir uns aos
     outros; grupos com 50% de sobreposicao. Reotimiza as sequencias, fins de semana e totais de cada um.
Quando uma passada nao melhora, os subproblemas sao aumentados (L += 7 dias, k += 2 enfermeiros) e as
passadas recomecam, ate acabar o tempo. Isso nao muda a logica do F&O: so troca as decomposicoes por outras
mais grossas, que contem as anteriores.

Solucao inicial: Simulated Annealing (sa.py) por uma fracao do tempo (frac_inicial). O F&O e, portanto, a
fase de intensificacao exata de uma heuristica hibrida SA + F&O.
Subproblemas: o mesmo nurse.mod, traduzido uma vez pelo GLPK e resolvido pelo HiGHS (exato.ModeloPLI),
mudando so os limites das variaveis x a cada subproblema.

Uso:  python fo.py <pasta_dataset> <h> <semanas> [limite_s] [semente]
Ex.:  python fo.py ../dados/n030w4 1 6,2,9,1 300 1
"""
import sys, time
from inrc2 import load_instance, evaluate, is_feasible, print_schedule
from exato import ModeloPLI
from sa import sa


def decomposicao_dias(D, L):
    """Janelas [a, b) de L dias com 50% de sobreposicao, cobrindo 0..D-1."""
    L = min(L, D); passo = max(1, L // 2)
    inicios = list(range(0, D - L + 1, passo))
    if inicios[-1] != D - L:
        inicios.append(D - L)
    return [(a, a + L) for a in inicios]


def ordem_enfermeiros(inst):
    """Enfermeiros ordenados por habilidades e contrato (vizinhos na ordem podem substituir um ao outro)."""
    chave = lambda n: (sorted(inst.nurse_skills[n]), inst.ct[n]["minA"], inst.ct[n]["maxA"], n)
    return sorted(range(inst.N), key=chave)


def decomposicao_enfermeiros(ordem, k):
    """Grupos de k enfermeiros consecutivos na ordem, com 50% de sobreposicao."""
    N = len(ordem); k = min(k, N); passo = max(1, k // 2)
    inicios = list(range(0, N - k + 1, passo))
    if inicios[-1] != N - k:
        inicios.append(N - k)
    return [frozenset(ordem[a:a + k]) for a in inicios]


def fo(inst, limite=300, semente=0, frac_inicial=0.5, sub_limite=30, threads=1, L0=7, k0=2,
       verbose=True, sched_inicial=None, sa_kw=None):
    """sa_kw: opcoes do SA da fase inicial (por exemplo penalidade='dinamica', desempate=True)."""
    t0 = time.time(); prazo = t0 + limite
    # ---- solucao inicial
    historico = []
    if sched_inicial is None:
        r0 = sa(inst, limite=frac_inicial * limite, semente=semente, verbose=False, **(sa_kw or {}))
        atual = r0["sched"]
        historico = [hc for hc in r0["historico"] if hc[1] != float("inf")]   # fase SA (mesmo relogio)
    else:
        atual = sched_inicial
    hard, _, custo = evaluate(inst, atual)
    custo_ini = custo
    historico.append((round(time.time() - t0, 2), custo))
    if verbose:
        print(f"  inicial: custo={custo} viavel={is_feasible(hard)} ({time.time() - t0:.1f}s)", flush=True)
    m = ModeloPLI(inst, threads=threads)
    col, _ = m.completar(atual)
    if col is None:                          # escala inicial viola alguma restricao hard
        col, custo = None, float("inf")
    ordem = ordem_enfermeiros(inst)
    L, k = L0, k0
    passadas = subproblemas = otimos = melhoras = 0
    while time.time() < prazo - 1:
        passadas += 1
        subs = ([("dias", jan) for jan in decomposicao_dias(inst.D, L)] +
                [("enf", g) for g in decomposicao_enfermeiros(ordem, k)])
        melhorou_passada = False
        for tipo, parte in subs:
            resta = prazo - time.time()
            if resta < 1:
                break
            if tipo == "dias":
                a, b = parte
                livre = lambda n, d, a=a, b=b: a <= d < b
            else:
                livre = lambda n, d, g=parte: n in g
            m.fixar(atual, livre)
            r = m.resolver(limite=min(sub_limite, resta), inicio=col)
            subproblemas += 1; otimos += r["status"] == "Optimal"
            if r["tem_solucao"]:
                novo = evaluate(inst, r["sched"])[2]          # custo real (avaliador independente)
                if novo < custo - 1e-6:
                    atual, col, custo = r["sched"], r["col_value"], novo
                    melhoras += 1; melhorou_passada = True
                    historico.append((round(time.time() - t0, 2), custo))
                    if verbose:
                        desc = f"dias {parte[0]}-{parte[1] - 1}" if tipo == "dias" else f"{len(parte)} enfermeiros"
                        print(f"  passada {passadas} (L={L}, k={k})  t={time.time() - t0:6.1f}s  {desc:16s} -> {custo}",
                              flush=True)
        if not melhorou_passada and time.time() < prazo - 1:
            if L >= inst.D and k >= inst.N:
                break                                       # nada mais a aumentar
            L = min(inst.D, L + 7); k = min(inst.N, k + 2)  # otimo local: subproblemas maiores
            if verbose:
                print(f"  passada {passadas} sem melhora: L={L}, k={k}", flush=True)
    m.liberar_todos()
    hard, comp, custo = evaluate(inst, atual)
    return dict(sched=atual, custo=custo, viavel=is_feasible(hard), hard=hard, componentes=comp,
                custo_inicial=custo_ini, iteracoes=subproblemas, passadas=passadas, otimos=otimos,
                melhoras=melhoras, L_final=L, k_final=k, tempo=time.time() - t0, historico=historico)


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 300
    semente = int(sys.argv[5]) if len(sys.argv) > 5 else 0
    inst = load_instance(folder, h, wds)
    r = fo(inst, limite, semente)
    print(f"{inst.name}: custo={r['custo']} (inicial {r['custo_inicial']}) viavel={r['viavel']} "
          f"subproblemas={r['iteracoes']} (otimos {r['otimos']}) passadas={r['passadas']} melhoras={r['melhoras']} "
          f"tempo={r['tempo']:.1f}s")
    print("  componentes:", r["componentes"])
    print_schedule(inst, r["sched"])
