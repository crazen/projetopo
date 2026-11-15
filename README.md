# Nurse Rostering (INRC-II): PLI e metaheurísticas

Projeto da disciplina de Pesquisa Operacional (UNIFESP/ICT) — Eduardo Lopes e Jorge Dourado.

Escalonamento de enfermeiros na versão estática da Second International Nurse Rostering Competition (INRC-II):
modelo de Programação Linear Inteira (AMPL + Gurobi) comparado com GRASP, Simulated Annealing e uma matheurística LNS.

- `nurse_rostering/` — código (modelo `nurse.mod`, `grasp.py`, `sa.py`, `lns.py`, `experimentos.py`, `testes.py`) e resultados (`comparacao_final.csv`). Ver `nurse_rostering/LEIAME.md`.
- `entregas/` — PDFs das Etapas 1–6 e 8 (artigo SBPO), apresentação da Etapa 7 (`.pptx`) e guia de estudo. Fontes em `entregas/fonte/`.
- `*.zip` — instâncias oficiais do INRC-II (JSON).
- `CLAUDE.md` — contexto completo do projeto, decisões e resultados.

## Como rodar

```
python -m venv .venv
.venv\Scripts\pip install highspy swiglpk pandas matplotlib amplpy pypdf python-pptx
cd nurse_rostering
python organizar_dados.py ../dados ../test_datasets_json.zip ../datasets_json.zip
python testes.py ../dados                     # deve terminar em TUDO CERTO
python experimentos.py --dados ../dados --instancias instancias_final.txt --metodos grasp,sa,lns --tempo 300 --sementes 2
```

O método exato com Gurobi exige licença AMPL (não incluída): `include rodar_final.run;` no AMPL.
