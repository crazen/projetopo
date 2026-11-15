"""exato.py - metodo exato: resolve o modelo de PLI nurse.mod com um solver MIP.

Fluxo:  instancia JSON --gen_dat--> .dat  --(tradutor MathProg do GLPK)-->  MPS  --> HiGHS
O mesmo nurse.mod roda no AMPL (ver rodar.run); aqui usamos o tradutor do GLPK so para nao depender
de licenca do AMPL. A solucao do solver e conferida pelo avaliador independente (inrc2.evaluate).

Uso:  python exato.py <pasta_dataset> <h> <semanas> [limite_s] [threads]
Ex.:  python exato.py dados/n005w4 0 1,2,3,3 60
"""
import sys, os, re, time, tempfile
import numpy as np
import swiglpk as glpk
import highspy
from inrc2 import load_instance, evaluate, is_feasible, print_schedule
from gen_dat import write_dat

AQUI = os.path.dirname(os.path.abspath(__file__))
PADRAO_X = re.compile(r"x\[(.+),(-?\d+),(.+),(.+)\]")


class ModeloPLI:
    """Modelo nurse.mod instanciado para uma instancia, carregado no HiGHS (uma vez)."""

    def __init__(self, inst, threads=1, mod=os.path.join(AQUI, "nurse.mod"), workdir=None, verbose=False):
        self.inst = inst
        workdir = workdir or tempfile.mkdtemp(prefix="nr_")
        os.makedirs(workdir, exist_ok=True)
        dat = os.path.join(workdir, inst.name + ".dat")
        mps = os.path.join(workdir, inst.name + ".mps")
        t0 = time.time()
        write_dat(inst, dat)
        glpk.glp_term_out(glpk.GLP_ON if verbose else glpk.GLP_OFF)
        tran = glpk.glp_mpl_alloc_wksp()
        if glpk.glp_mpl_read_model(tran, mod, 1) != 0:
            raise RuntimeError("erro de sintaxe em " + mod)
        if glpk.glp_mpl_read_data(tran, dat) != 0:
            raise RuntimeError("erro lendo " + dat)
        if glpk.glp_mpl_generate(tran, None) != 0:
            raise RuntimeError("erro gerando o modelo")
        P = glpk.glp_create_prob()
        glpk.glp_mpl_build_prob(tran, P)
        self.nrows, self.ncols = glpk.glp_get_num_rows(P), glpk.glp_get_num_cols(P)
        names = [glpk.glp_get_col_name(P, j) for j in range(1, self.ncols + 1)]
        glpk.glp_write_mps(P, glpk.GLP_MPS_FILE, None, mps)
        glpk.glp_delete_prob(P); glpk.glp_mpl_free_wksp(tran)
        self.t_geracao = time.time() - t0

        # mapeia as colunas x[n,d,s,k] -> indice de coluna
        nidx = {n: i for i, n in enumerate(inst.nurses)}
        sidx = {s: i for i, s in enumerate(inst.shifts)}
        kidx = {k: i for i, k in enumerate(inst.skills)}
        self.xcol = {}                                       # (n,d,s,k) -> coluna
        for j, nm in enumerate(names):
            if nm.startswith("x["):
                n, d, s, k = PADRAO_X.match(nm).groups()
                self.xcol[(nidx[n.strip("'")], int(d), sidx[s.strip("'")], kidx[k.strip("'")])] = j
        self.xkeys = list(self.xcol.keys())
        self.xidx = np.array([self.xcol[t] for t in self.xkeys], dtype=np.int32)

        self.h = highspy.Highs()
        self.h.setOptionValue("output_flag", verbose)
        self.h.setOptionValue("threads", int(threads))   # o HiGHS so aceita definir isso antes da 1a execucao
        self.h.readModel(mps)
        self.h.setOptionValue("mip_rel_gap", 0.0)

    # -------------------------------------------------------------- utilidades
    def decodificar(self, col_value):
        sched = [[None] * self.inst.D for _ in range(self.inst.N)]
        for (n, d, s, k), j in self.xcol.items():
            if col_value[j] > 0.5:
                sched[n][d] = (s, k)
        return sched

    def valores_x(self, sched):
        return np.array([1.0 if sched[n][d] == (s, k) else 0.0 for (n, d, s, k) in self.xkeys])

    def liberar_todos(self):
        z = np.zeros(len(self.xidx)); o = np.ones(len(self.xidx))
        self.h.changeColsBounds(len(self.xidx), self.xidx, z, o)

    def fixar(self, sched, livre):
        """Fixa x na escala dada, exceto onde livre(n, d) for True (essas ficam 0..1)."""
        v = self.valores_x(sched)
        lo, up = v.copy(), v.copy()
        for i, (n, d, s, k) in enumerate(self.xkeys):
            if livre(n, d):
                lo[i], up[i] = 0.0, 1.0
        self.h.changeColsBounds(len(self.xidx), self.xidx, lo, up)

    def completar(self, sched, limite=30):
        """Dada uma escala (so x), obtem o vetor completo de variaveis (a, w, folgas...) fixando x e resolvendo.
        Retorna (col_value, objetivo) ou (None, None) se a escala viola alguma restricao hard."""
        self.fixar(sched, lambda n, d: False)
        self.h.setOptionValue("time_limit", float(limite))
        self.h.run()
        info = self.h.getInfo()
        ok = info.primal_solution_status == 2
        res = (list(self.h.getSolution().col_value), info.objective_function_value) if ok else (None, None)
        self.liberar_todos()
        return res

    def resolver(self, limite=60, inicio=None):
        """Resolve o MIP (com as fronteiras atuais das variaveis). inicio: vetor completo para warm start."""
        self.h.setOptionValue("time_limit", float(limite))
        if inicio is not None:
            sol = highspy.HighsSolution()
            sol.col_value = list(inicio)
            sol.value_valid = True
            self.h.setSolution(sol)
        t0 = time.time()
        st = self.h.run()
        t = time.time() - t0
        if st == highspy.HighsStatus.kError:
            raise RuntimeError("o HiGHS retornou erro ao resolver")
        info = self.h.getInfo()
        tem_sol = info.primal_solution_status == 2
        col = list(self.h.getSolution().col_value) if tem_sol else None
        return dict(status=self.h.modelStatusToString(self.h.getModelStatus()),
                    tem_solucao=tem_sol,
                    objetivo=info.objective_function_value if tem_sol else None,
                    limite_inferior=info.mip_dual_bound,
                    gap=info.mip_gap if tem_sol else None,
                    tempo=t, col_value=col,
                    sched=self.decodificar(col) if tem_sol else None)


def resolver_exato(inst, limite=60, threads=1, workdir=None, verbose=False):
    """Resolve a instancia ate o otimo ou ate o limite de tempo. Retorna dict com custo conferido pelo avaliador."""
    m = ModeloPLI(inst, threads=threads, workdir=workdir, verbose=verbose)
    r = m.resolver(limite=limite)
    r.update(variaveis=m.ncols, restricoes=m.nrows, t_geracao=m.t_geracao)
    if r["tem_solucao"]:
        # Custo real da escala = avaliador. Quando o solver para por tempo, as variaveis de penalidade da
        # solucao incumbente podem estar acima do minimo (so ficam "apertadas" no otimo), entao o objetivo
        # reportado pelo solver pode ser MAIOR que o custo real. Por isso o gap e recalculado com o custo real.
        hard, cost, tot = evaluate(inst, r["sched"])
        r.update(custo=tot, viavel=is_feasible(hard), componentes=cost,
                 gap=(tot - r["limite_inferior"]) / tot if tot > 0 else 0.0)
        if tot > r["objetivo"] + 1e-6:
            print(f"  ERRO: avaliador ({tot}) > objetivo do modelo ({r['objetivo']}): o modelo subestima o custo")
    else:
        r.update(custo=None, viavel=False, componentes=None)
    return r


if __name__ == "__main__":
    if len(sys.argv) < 4:
        sys.exit(__doc__)
    folder, h, wds = sys.argv[1], int(sys.argv[2]), [int(x) for x in sys.argv[3].split(",")]
    limite = float(sys.argv[4]) if len(sys.argv) > 4 else 60
    threads = int(sys.argv[5]) if len(sys.argv) > 5 else 1
    inst = load_instance(folder, h, wds)
    r = resolver_exato(inst, limite, threads)
    print(f"{inst.name}: {r['variaveis']} variaveis, {r['restricoes']} restricoes (geracao {r['t_geracao']:.1f}s)")
    print(f"  status={r['status']}  tempo={r['tempo']:.1f}s  limite_inferior={r['limite_inferior']:.1f}")
    if r["tem_solucao"]:
        print(f"  melhor solucao={r['custo']}  gap={100 * r['gap']:.1f}%  viavel={r['viavel']}")
        print("  componentes:", r["componentes"])
        print_schedule(inst, r["sched"])
    else:
        print("  nenhuma solucao viavel encontrada dentro do limite de tempo")
