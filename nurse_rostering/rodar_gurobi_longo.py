"""rodar_gurobi_longo.py - roda o modelo exato (nurse.mod) no Gurobi com tempos maiores, guardando a saida completa.

Pedido do professor: 300 s e pouco para o Gurobi; com mais tempo ele deve provar mais otimos.

MESMO METODO DA ETAPA 5 (padrao deste script): o mesmo nurse.mod, os mesmos .dat de dat/, Gurobi via AMPL com
mipgap = 0 (so para antes do limite se provar o otimo), 1 thread e, no fim, x fixado e o modelo resolvido de novo
para obter o custo real da escala (exatamente como rodar_final.run). Muda SO o limite de tempo: cada instancia e
resolvida uma vez para CADA tempo de --tempos (execucoes independentes, que comecam do zero).

Opcoes extras (desligadas por padrao, para nao mudar o metodo):
  --threads 6    usa mais nucleos (o i5-13400 tem 6 rapidos); deixa de ser comparavel com a Etapa 5 (1 thread)
  --cfg inicio   o Gurobi recebe como solucao inicial (MIP start) a escala do SA + F&O de inicio_mip/<inst>.run
                 (ja gerada por gerar_inicio_mip.py). Continua exato; o limite superior so comeca melhor.

Saidas (todas nesta pasta):
  logs_gurobi/<instancia>_<cfg>_<tempo>s_<threads>t.log       log COMPLETO do Gurobi (presolve, no raiz, arvore)
  logs_gurobi/<instancia>_<cfg>_<tempo>s_<threads>t_ampl.txt  tudo o que o AMPL imprimiu nessa execucao
  resultados_gurobi_longo.csv                                  uma linha por execucao

Uso (no PC, dentro de nurse_rostering, com a licenca do AMPL/Gurobi):
  python rodar_gurobi_longo.py --grupo teste --tempos 300,900,1800,3600
  python rodar_gurobi_longo.py --grupo final --tempos 900,1800,3600
  python rodar_gurobi_longo.py --instancias n030w4_H1_WD6-2-9-1 n005w4_H1_WD5-3-1-0 --tempos 3600,7200
  python rodar_gurobi_longo.py --grupo final --tempos 3600 --threads 6 --cfg inicio      # opcoes extras
  python rodar_gurobi_longo.py --estimar --grupo todas --tempos 300,900,1800,3600        # so mostra o tempo total
Licenca: se o AMPL ainda nao estiver ativado no PC, use --licenca <uuid> (ou a variavel AMPL_LICENSE_UUID).

Tempo total, no pior caso = instancias x soma dos tempos (as que provarem o otimo terminam antes):
  teste (9)  x (300+900+1800+3600 s) = 16,5 h      final (8) x (900+1800+3600 s) = 14 h
Da para interromper (Ctrl+C) e rodar de novo: as execucoes ja gravadas no CSV sao puladas.
Dica: rode os tempos curtos primeiro (a ordem de --tempos e respeitada), para ter resultados parciais cedo.
"""
import argparse, csv, os, sys, time

AQUI = os.path.dirname(os.path.abspath(__file__))
TESTE = ["n005w4_H0_WD1-2-3-3", "n005w4_H1_WD5-3-1-0", "n005w4_H2_WD6-7-8-9",
         "n012w8_H0_WD3-5-0-2-0-4-5-2", "n012w8_H1_WD7-7-0-8-9-3-2-6", "n012w8_H2_WD4-5-6-7-2-1-2-1",
         "n021w4_H0_WD5-4-1-2", "n021w4_H1_WD0-6-1-6", "n021w4_H2_WD8-1-4-3"]
FINAL = ["n030w4_H1_WD6-2-9-1", "n040w4_H0_WD2-0-6-1", "n050w4_H0_WD0-4-8-7", "n060w4_H1_WD6-1-1-5",
         "n030w8_H1_WD2-7-0-9-3-6-0-6", "n040w8_H0_WD0-6-8-9-2-6-6-4", "n050w8_H1_WD1-7-8-5-7-4-1-8",
         "n060w8_H0_WD6-2-9-9-0-8-1-3"]
CAMPOS = ["instancia", "cfg", "tempo_limite_s", "threads", "status", "custo", "limite_inferior", "gap_%",
          "tempo_s", "otimo_provado", "custo_inicial", "log"]
SAIDA = os.path.join(AQUI, "resultados_gurobi_longo.csv")


def abrir_ampl(licenca):
    from amplpy import AMPL, modules
    if licenca:
        modules.activate(licenca)
    return AMPL()


def ja_feitas():
    if not os.path.exists(SAIDA):
        return set()
    return {(r["instancia"], r["cfg"], r["tempo_limite_s"], r["threads"]) for r in csv.DictReader(open(SAIDA))}


def rodar(ampl, inst, cfg, tempo, threads):
    nome = f"{inst}_{cfg}_{tempo:g}s_{threads}t"
    log = f"logs_gurobi/{nome}.log"                 # relativo a esta pasta (ampl.cd abaixo)
    if os.path.exists(os.path.join(AQUI, log)):
        os.remove(os.path.join(AQUI, log))
    ampl.reset()
    ampl.cd(AQUI)
    ampl.read(os.path.join(AQUI, "nurse.mod"))
    ampl.read_data(os.path.join(AQUI, "dat", inst + ".dat"))
    ampl.eval("suffix bestbound OUT;")
    ampl.set_option("solver", "gurobi")
    texto = [f"=== {inst}  cfg={cfg}  tempo={tempo:g}s  threads={threads}"]
    custo_ini = ""
    if cfg == "inicio":
        arq = os.path.join(AQUI, "inicio_mip", inst + ".run")
        if not os.path.exists(arq):
            sys.exit(f"falta {arq}: rode antes  python gerar_inicio_mip.py ../dados 300 6")
        ampl.eval(f"include '{arq.replace(chr(92), '/')}';")
        # completa a escala inicial: com x fixo, o modelo calcula a, w e as penalidades (rapido);
        # os valores ficam no AMPL e vao para o Gurobi como solucao inicial (mipstart)
        ampl.set_option("gurobi_options", "outlev=0")
        ampl.eval("fix x;")
        texto.append(ampl.get_output("solve;"))
        custo_ini = ampl.get_value("Penalidade")
        ampl.eval("unfix x;")
        texto.append(f"escala inicial (SA + F&O): custo = {custo_ini}")
    # mesmas opcoes de rodar_final.run (timelim, mipgap=0, threads, bestbound) + log completo
    opcoes = f"timelim={tempo:g} mipgap=0 threads={threads} bestbound=1 outlev=1 logfile={log}"
    if cfg == "inicio":
        opcoes += " mipstart=1"
    ampl.set_option("gurobi_options", opcoes)
    print(f"   gurobi_options: {opcoes}", flush=True)
    t0 = time.time()
    texto.append(ampl.get_output("solve;"))
    tt = time.time() - t0
    res = ampl.get_value("solve_result")
    lb = ampl.get_value("Penalidade.bestbound")
    # custo real da escala: fixa x e resolve de novo (as penalidades ficam apertadas), como em rodar_final.run
    ampl.set_option("gurobi_options", "outlev=0")
    ampl.eval("fix x;")
    texto.append(ampl.get_output("solve;"))
    custo = ampl.get_value("Penalidade") if ampl.get_value("solve_result") != "infeasible" else None
    ampl.eval("unfix x;")
    gap = round(100 * (custo - lb) / custo, 2) if custo and lb else ""
    otimo = res == "solved" or (gap != "" and gap <= 1e-6)
    texto.append(f"RESULTADO: status={res} custo={custo} limite_inferior={lb} gap={gap}% tempo={tt:.1f}s")
    open(os.path.join(AQUI, "logs_gurobi", nome + "_ampl.txt"), "w", encoding="utf-8").write("\n".join(texto))
    return {"instancia": inst, "cfg": cfg, "tempo_limite_s": f"{tempo:g}", "threads": str(threads),
            "status": res, "custo": custo if custo is not None else "", "limite_inferior": round(lb, 2) if lb else "",
            "gap_%": gap, "tempo_s": round(tt, 1), "otimo_provado": otimo, "custo_inicial": custo_ini, "log": log}


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--grupo", choices=["teste", "final", "todas"], default="teste")
    ap.add_argument("--instancias", nargs="*", help="nomes como em dat/ (sem .dat), em vez de --grupo")
    ap.add_argument("--tempos", default="300,900,1800,3600", help="limites de tempo em segundos, separados por virgula")
    ap.add_argument("--threads", type=int, default=1, help="1 = igual a Etapa 5")
    ap.add_argument("--cfg", choices=["puro", "inicio"], default="puro", help="puro = igual a Etapa 5")
    ap.add_argument("--licenca", default=os.environ.get("AMPL_LICENSE_UUID"))
    ap.add_argument("--estimar", action="store_true", help="so mostra quantas execucoes e o tempo maximo")
    a = ap.parse_args()
    lista = a.instancias or {"teste": TESTE, "final": FINAL, "todas": TESTE + FINAL}[a.grupo]
    for i in lista:
        if not os.path.exists(os.path.join(AQUI, "dat", i + ".dat")):
            sys.exit(f"nao existe dat/{i}.dat (gere com gen_dat.py)")
    tempos = [float(x) for x in a.tempos.split(",")]
    feitas = ja_feitas()
    tarefas = [(t, i) for t in tempos for i in lista                       # tempos curtos primeiro
               if (i, a.cfg, f"{t:g}", str(a.threads)) not in feitas]
    total = sum(t for t, _ in tarefas)
    print(f"{len(lista)} instancias x tempos {a.tempos} s, cfg={a.cfg}, {a.threads} thread(s): "
          f"{len(tarefas)} execucoes a fazer, no maximo {total / 3600:.1f} h", flush=True)
    if a.estimar or not tarefas:
        return
    os.makedirs(os.path.join(AQUI, "logs_gurobi"), exist_ok=True)
    ampl = abrir_ampl(a.licenca)
    novo = not os.path.exists(SAIDA)
    with open(SAIDA, "a", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CAMPOS)
        if novo:
            w.writeheader()
        for k, (t, inst) in enumerate(tarefas, 1):
            print(f"\n[{k}/{len(tarefas)}] {inst}  tempo={t:g}s", flush=True)
            r = rodar(ampl, inst, a.cfg, t, a.threads)
            w.writerow(r); f.flush()
            print("   ", {c: r[c] for c in ("status", "custo", "limite_inferior", "gap_%", "tempo_s", "otimo_provado")},
                  flush=True)
    print(f"\nresultados em {SAIDA}; logs completos em {os.path.join(AQUI, 'logs_gurobi')}")


if __name__ == "__main__":
    main()
