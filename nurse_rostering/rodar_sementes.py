"""rodar_sementes.py - roda sementes extras das metaheuristicas (GRASP, SA, LNS) nas 8 instancias finais e
atualiza tabelas, figuras, PDFs e slides.

Cada tarefa (instancia, metodo, semente) e um processo separado (1 thread) que grava
v2_seed_<instancia>_<metodo>_<semente>.csv. Esses arquivos sao lidos automaticamente por consolidar.py junto
com os v2_*.csv ja existentes (sementes 1 e 2). Se o script for interrompido, basta roda-lo de novo: as tarefas
ja concluidas sao puladas.

Uso (de dentro de nurse_rostering, com o .venv):
  python rodar_sementes.py                          # sementes 3 a 5, 300 s, 6 processos  (~60 min)
  python rodar_sementes.py --ate 10                 # sementes 3 a 10                      (~160 min)
  python rodar_sementes.py --de 3 --ate 5 --metodos sa --processos 4
  python rodar_sementes.py --so-consolidar          # so regenera tabelas/figuras/PDFs

Tempo estimado = instancias x metodos x sementes x tempo / processos
  (8 x 3 x 3 x 300 s / 6 = 60 min para o padrao).

Importante:
  - Use no maximo 6 processos (o i5-13400 tem 6 nucleos rapidos) e nao use o PC para tarefas pesadas enquanto
    roda, para os tempos continuarem comparaveis.
  - Os TEXTOS dos documentos citam "2 sementes" e numeros das analises (distancias medias, vitorias...).
    Depois de rodar, as TABELAS e FIGURAS sao atualizadas sozinhas, mas os textos precisam ser revisados
    (peca ao Claude para atualizar as analises com os novos numeros).
"""
import argparse, glob, os, subprocess, sys, time
from concurrent.futures import ThreadPoolExecutor, as_completed

AQUI = os.path.dirname(os.path.abspath(__file__))
PY = sys.executable
FONTE = os.path.join(AQUI, "..", "entregas", "fonte")


def instancias(arquivo):
    out = []
    for linha in open(os.path.join(AQUI, arquivo)):
        linha = linha.split("#")[0].strip()
        if linha:
            out.append(linha)
    return out


def nome_saida(spec, metodo, sem):
    return os.path.join(AQUI, f"v2_seed_{spec.split()[0]}_{metodo}_{sem}.csv")


def concluida(saida):
    try:
        with open(saida) as f:
            return sum(1 for _ in f) >= 2           # cabecalho + 1 linha de resultado
    except FileNotFoundError:
        return False


def tarefa(spec, metodo, sem, tempo, dados):
    saida = nome_saida(spec, metodo, sem)
    lista = os.path.join(AQUI, f"_tmp_{spec.split()[0]}_{metodo}_{sem}.txt")
    with open(lista, "w") as f:
        f.write(spec + "\n")
    log = os.path.splitext(saida)[0].replace("v2_seed_", "log_seed_") + ".txt"
    if os.path.exists(saida) and not concluida(saida):
        os.remove(saida)                            # execucao interrompida: recomeca do zero
    cmd = [PY, "-u", "experimentos.py", "--dados", dados, "--instancias", lista, "--metodos", metodo,
           "--tempo", str(tempo), "--sementes", "1", "--semente-inicial", str(sem), "--threads", "1",
           "--saida", saida]
    t0 = time.time()
    with open(os.path.join(AQUI, log), "w") as lg:
        r = subprocess.run(cmd, cwd=AQUI, stdout=lg, stderr=subprocess.STDOUT)
    os.remove(lista)
    return spec.split()[0], metodo, sem, r.returncode, time.time() - t0


def consolidar_tudo():
    print("\n== consolidando resultados, figuras, tabelas, PDFs e slides", flush=True)
    for cmd, cwd in [([PY, "consolidar.py"], AQUI), ([PY, "preencher_tabelas.py"], FONTE),
                     ([PY, "gerar_pdfs.py"], FONTE), ([PY, "gerar_slides.py"], FONTE)]:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        print(f"   {' '.join(os.path.basename(c) for c in cmd[1:])}: {'ok' if r.returncode == 0 else 'ERRO'}")
        if r.returncode != 0:
            print(r.stdout[-2000:], r.stderr[-2000:])
            return
        if "consolidar" in cmd[1]:
            print("\n".join("   " + l for l in r.stdout.splitlines()[:12]))
    print("\nTabelas e figuras atualizadas. Revise os TEXTOS das analises (numeros citados e '2 sementes').")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--de", type=int, default=3, help="primeira semente (1 e 2 ja foram rodadas)")
    ap.add_argument("--ate", type=int, default=5, help="ultima semente (inclusive)")
    ap.add_argument("--metodos", default="grasp,sa,lns")
    ap.add_argument("--tempo", type=float, default=300)
    ap.add_argument("--processos", type=int, default=6)
    ap.add_argument("--instancias", default="instancias_final.txt")
    ap.add_argument("--dados", default=os.path.join("..", "dados"))
    ap.add_argument("--so-consolidar", action="store_true")
    a = ap.parse_args()
    if a.processos > 6:
        sys.exit("use no maximo 6 processos (6 nucleos rapidos); mais que isso distorce os tempos")
    if not a.so_consolidar:
        if not os.path.isdir(os.path.join(AQUI, a.dados)):
            sys.exit(f"pasta de dados {a.dados} nao encontrada (rode organizar_dados.py antes)")
        todas = [(s, m, k) for s in instancias(a.instancias) for m in a.metodos.split(",")
                 for k in range(a.de, a.ate + 1)]
        pend = [t for t in todas if not concluida(nome_saida(*t))]
        # metodos mais longos de preparar (LNS monta o modelo) primeiro, para equilibrar o fim
        pend.sort(key=lambda t: (t[1] != "lns", t[0]))
        est = len(pend) * a.tempo / a.processos / 60
        print(f"{len(todas)} tarefas ({len(todas) - len(pend)} ja feitas), {len(pend)} a rodar com {a.processos} "
              f"processos: ~{est:.0f} min (+ preparacao dos modelos)", flush=True)
        feitas = 0
        with ThreadPoolExecutor(max_workers=a.processos) as ex:
            futs = [ex.submit(tarefa, s, m, k, a.tempo, a.dados) for s, m, k in pend]
            for f in as_completed(futs):
                inst, m, k, rc, dt = f.result(); feitas += 1
                st = "ok" if rc == 0 else f"ERRO (codigo {rc}; veja log_seed_{inst}_{m}_{k}.txt)"
                print(f"  [{feitas:3d}/{len(pend)}] {inst} {m} semente {k}: {st} ({dt / 60:.1f} min)", flush=True)
    consolidar_tudo()


if __name__ == "__main__":
    main()
