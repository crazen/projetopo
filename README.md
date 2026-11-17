# Nurse Rostering (INRC-II): PLI e metaheurísticas

Projeto da disciplina de Pesquisa Operacional (UNIFESP/ICT) — Eduardo Lopes e Jorge Dourado.

Escalonamento de enfermeiros na versão estática da Second International Nurse Rostering Competition (INRC-II):
modelo de Programação Linear Inteira (AMPL + Gurobi) comparado com GRASP, Simulated Annealing e uma matheurística Fix-and-Optimize.

- `nurse_rostering/` — código (modelo `nurse.mod`, `nucleo.py`, `grasp.py`, `sa.py`, `fo.py`, `experimentos.py`, `testes.py`) e resultados (`comparacao_final.csv`). Ver `nurse_rostering/LEIAME.md`.
- `entregas/` — PDFs das Etapas 1–6 e 8 (artigo SBPO), apresentação da Etapa 7 (`.pptx`) e guia de estudo. Fontes em `entregas/fonte/`.
- `entregas/explicacao_para_estudo.md` — explicação em linguagem simples de cada método, glossário de siglas (H1–H4, S1–S7, N1–N4, T0, Tf…), por que cada método foi melhor ou pior, e preparação para a reunião com o professor.
- `*.zip` — instâncias oficiais do INRC-II (JSON).
- `CLAUDE.md` — contexto completo do projeto, decisões e resultados.

## Como rodar

```
python -m venv .venv
.venv\Scripts\pip install highspy swiglpk numba pandas matplotlib amplpy pypdf python-pptx
cd nurse_rostering
python organizar_dados.py ../dados ../test_datasets_json.zip ../datasets_json.zip
python testes.py ../dados                     # deve terminar em TUDO CERTO
python rodar_experimentos.py --processos 6        # GRASP, SA e SA+F&O, 8 instâncias x 3 sementes, 300 s (~1 h)
```

O método exato com Gurobi exige licença AMPL (não incluída): `include rodar_final.run;` no AMPL.
