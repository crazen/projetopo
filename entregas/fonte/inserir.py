"""inserir.py <arquivo.html> <MARCA> <trecho.html> - insere o trecho entre <!--MARCA--> e <!--/MARCA--> (idempotente)."""
import sys
from preencher_tabelas import inserir  # reaproveita a funcao (o import tambem regera as tabelas)
inserir(sys.argv[1], sys.argv[2], open(sys.argv[3], encoding="utf-8").read().strip())
