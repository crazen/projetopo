# Nurse Rostering – resumo dos métodos e preparação para a reunião

17/11/2026 · Jorge Dourado (cópia do doc de estudo no claude.ai)

Montamos a escala de 4 ou 8 semanas de 30 a 60 enfermeiros com quatro métodos; o melhor (SA + Fix-and-Optimize) ficou, em média, 17% acima do ótimo publicado, e o Gurobi, 354%.

## Como estudar este documento

1. Leia "O problema em 2 minutos" e consulte o glossário sempre que aparecer uma sigla.
2. Leia os dados e a representação da solução: são a base de todos os métodos.
3. Leia um método por vez (Gurobi, GRASP, SA, SA + F&O) e tente contar cada um em voz alta, com suas palavras.
4. Veja os resultados e a seção "Por que um método foi melhor que o outro".
5. Treine com as perguntas e respostas e com o teste rápido do final.
6. Releia "Para a reunião de quarta" antes de falar com o professor.

## O problema em 2 minutos

Um hospital precisa decidir, para cada enfermeiro e cada dia de um mês ou dois, se ele folga ou em qual turno trabalha (Early = manhã, Day = dia, Late = tarde, Night = noite) e em qual função (HeadNurse = chefe, Nurse = enfermeiro, Caretaker = cuidador, Trainee = estagiário).

Algumas regras não podem ser quebradas, como ter gente suficiente em cada turno. Outras podem, mas custam pontos, como atender um pedido de folga ou não trabalhar mais de 5 dias seguidos. O objetivo é a escala com **menos pontos de penalidade**.

Por que é difícil: com 30 enfermeiros e 28 dias, cada célula da tabela tem cerca de 9 opções; são 9 elevado a 840 escalas possíveis, impossível testar todas. E mudar um único dia mexe nas sequências, no fim de semana, no total de turnos daquela pessoa e na cobertura do dia.

Usamos dados oficiais de uma competição internacional (INRC-II), para os quais pesquisadores já publicaram a melhor escala conhecida. Assim dá para medir o quão perto do ótimo cada método chegou.

Os quatro métodos, numa frase cada:

- **Gurobi (exato):** escreve tudo como equações e tenta provar qual é a melhor escala.
- **GRASP:** monta uma escala com um pouco de sorteio, melhora até travar e repete muitas vezes.
- **SA:** faz milhões de pequenas mudanças e às vezes aceita piorar, para não travar.
- **SA + F&O:** usa o SA e depois o solver para reorganizar, de forma ótima, um pedaço de cada vez (uma semana, ou dois enfermeiros).

## Glossário: o que significa cada sigla

**Regras do problema** (H = *hard*, obrigatória; S = *soft*, pode ser descumprida pagando penalidade; o número entre parênteses é o peso por ocorrência):

| Sigla | Significado | Exemplo |
| --- | --- | --- |
| H1 | No máximo um turno por enfermeiro por dia | Ninguém faz Early e Late no mesmo dia |
| H2 | Cobertura mínima: cada dia, turno e habilidade precisa de pelo menos o número mínimo de pessoas | Segunda à noite: no mínimo 2 Nurses |
| H3 | Sucessão proibida entre dias seguidos | Late hoje e Early amanhã (descanso curto demais) |
| H4 | Só pode trabalhar numa habilidade que a pessoa tem | Trainee não cobre vaga de HeadNurse |
| S1 (30) | Cobertura ótima: cada pessoa faltando para o número ideal | Ideal 3, escalados 2: paga 30 |
| S2 (15 e 30) | Dias seguidos no mesmo turno (15) e dias seguidos de trabalho (30) fora do mínimo/máximo do contrato | Máximo de 5 dias seguidos; trabalhou 7: paga 2 × 30 |
| S3 (30) | Folgas seguidas fora do mínimo/máximo | Mínimo de 2 folgas seguidas; teve 1 só: paga 30 |
| S4 (10) | Pedido de folga não atendido | Pediu folga na sexta e foi escalado |
| S5 (30) | Fim de semana incompleto: trabalhou só sábado ou só domingo, quando o contrato pede os dois juntos | |
| S6 (20) | Total de turnos no horizonte fora do mínimo/máximo do contrato | Máximo 20, fez 22: paga 2 × 20 |
| S7 (30) | Fins de semana trabalhados acima do máximo | Máximo 2, trabalhou 3: paga 30 |

**Movimentos das heurísticas** (N = vizinhança, o conjunto de escalas que se alcança com uma pequena mudança): N1 troca, N2 swap, N3 bloco e N4 swap de bloco, detalhados na seção "A solução e as regras".

**Outros termos:**

| Termo | Significado |
| --- | --- |
| n, d, s, k | Enfermeiro (*nurse*), dia, turno (*shift*), habilidade (*skill*) |
| x[n,d,s,k] | Variável do modelo: vale 1 se o enfermeiro n faz o turno s com a habilidade k no dia d, e 0 se não |
| PLI | Programação Linear Inteira: modelo com equações lineares e variáveis inteiras (aqui, 0 ou 1) |
| PL / relaxação linear | O mesmo modelo deixando as variáveis assumirem frações (ex.: 0,5). É fácil de resolver e dá um limite inferior: nenhuma escala real custa menos que ele |
| LB (limite inferior) | Valor que o solver garante que o ótimo não fica abaixo |
| Gap | (custo da escala − LB) / custo da escala: quanto, no pior caso, a escala pode estar acima do ótimo |
| Nó (*branch-and-bound*) | Cada subproblema da árvore de busca do solver; mais nós = mais busca |
| T | Temperatura do SA: quanto ele aceita piorar. T0 = temperatura inicial (40), Tf = temperatura final (2) |
| Δ | Variação do custo causada por um movimento (negativo = melhora) |
| α (alfa) | Parâmetro do GRASP que controla o sorteio: 0 = sempre o melhor candidato, 1 = qualquer um (usamos 0,15) |
| RCL | Lista restrita de candidatos do GRASP: os candidatos bons o bastante para serem sorteados |
| VND | Busca local que alterna as vizinhanças N1 → N4 até nenhuma melhorar |
| GRASP, SA, F&O, LNS | *Greedy Randomized Adaptive Search Procedure*, *Simulated Annealing*, *Fix-and-Optimize*, *Large Neighborhood Search* |
| L, k (no F&O) | Tamanho da janela de dias (L = 7) e do grupo de enfermeiros (k = 2) de cada subproblema |
| Semente | Número que fixa o sorteio aleatório; cada método rodou 3 vezes com sementes diferentes |
| n040w8, H0, WD | Instância com 40 enfermeiros e 8 semanas; H0 = arquivo de histórico; WD = arquivos de demanda de cada semana |
| AMPL, Gurobi, HiGHS | Linguagem de modelagem; solver comercial; solver gratuito (usado dentro do F&O) |

## Os dados

Cada instância junta três arquivos JSON do INRC-II: um cenário, um histórico e uma semana de demanda para cada semana do horizonte.

| Arquivo | O que tem | Onde é usado |
| --- | --- | --- |
| Cenário (Sc-…) | Enfermeiros, habilidades de cada um, contrato (mín./máx. de turnos, dias seguidos de trabalho e de folga, fins de semana), turnos e sucessões proibidas | Regras de cada enfermeiro (H3, H4, S2, S3, S5, S6, S7) |
| Histórico (H0-…) | Como cada enfermeiro terminou a semana anterior: último turno, quantos dias seguidos já trabalhou ou folgou, turnos já feitos | Vira "dias virtuais" antes do dia 1, para as sequências começarem certas |
| Semanas (WD-…) | Demanda mínima e ótima por dia, turno e habilidade; pedidos de folga | Cobertura (H2, S1) e pedidos (S4) |

Todos os métodos leem os mesmos arquivos pelo `inrc2.py`, e todo custo reportado é recalculado pelo mesmo avaliador, que reproduz o validador oficial da competição. O conjunto final tem 8 instâncias (30 a 60 enfermeiros, 4 e 8 semanas) que têm o ótimo, ou o melhor valor conhecido, publicado por Legrain e Omer (2023).

## A solução e as regras

Uma escala é uma tabela enfermeiro × dia; cada célula guarda "folga" ou um par (turno, habilidade). Exemplo: o enfermeiro 3 no dia 10 faz o turno da noite como Nurse.

- **Regras hard (não podem ser violadas):** H1, no máximo um turno por dia, e H4, só habilidades que o enfermeiro tem, já vêm garantidas pelo formato da tabela. H2 (cobertura mínima) e H3 (sucessão proibida, como Late seguido de Early) podem ser violadas durante a busca, mas cada violação custa 10.000.
- **Regras soft (penalidades):** cada descumprimento soma pontos com os pesos da competição: cobertura ótima 30, sequências de turno 15, sequências de trabalho e de folga 30, pedido de folga 10, fim de semana completo 30, total de turnos 20, fins de semana trabalhados 30.
- **Custo de uma escala** = soma das penalidades soft + 10.000 × violações hard.
- **Avaliação incremental:** quando um movimento muda só 1 ou 2 enfermeiros, o programa recalcula só a linha deles e os contadores de cobertura daquele dia. Esse cálculo está em `nucleo.py`, compilado com numba: cerca de 1 milhão de movimentos por segundo.

Os quatro tipos de movimento (vizinhanças) usados pelo GRASP e pelo SA:

| Nome | O que muda |
| --- | --- |
| N1 troca | O que um enfermeiro faz em um dia (outro turno, outra habilidade ou folga) |
| N2 swap | Dois enfermeiros trocam o que fazem em um dia (a cobertura do dia não muda) |
| N3 bloco | Um enfermeiro recebe o mesmo turno, ou folga, em 2 a 5 dias seguidos |
| N4 swap de bloco | Dois enfermeiros trocam o que fazem em 2, 3, 4, 5 ou 7 dias seguidos |

## Método exato: Gurobi

O modelo de PLI (`nurse.mod`) escreve as mesmas regras como equações, e o Gurobi procura a escala de custo mínimo e prova que é a melhor.

1. `gen_dat.py` converte os JSON da instância no arquivo de dados do AMPL (`.dat`), incluindo o histórico como dias virtuais.
2. O AMPL monta o modelo: uma variável binária x[n,d,s,k] = 1 se o enfermeiro n faz o turno s com a habilidade k no dia d, mais variáveis que medem cada penalidade. São 26 mil a 108 mil variáveis e restrições.
3. O Gurobi resolve por branch-and-bound por até 300 s com 1 thread: resolve a relaxação linear (o que dá o limite inferior), ramifica em variáveis fracionárias e guarda a melhor escala achada.
4. No fim, `rodar_final.run` fixa as variáveis x e resolve de novo (menos de 1 s) para obter o custo real da escala, que bate com o avaliador oficial.

**Por que trava.** A relaxação linear vale só 20% a 70% do ótimo: uma escala fracionária, como trabalhar "meio turno" todos os dias, cumpre as regras de sequência sem pagar penalidade. E o próprio PL é caro: o log mostra de 280 mil a 1 milhão de iterações do simplex e de 1 a 3 nós de branch-and-bound em 300 s em 7 das 8 instâncias (a n030w4 teve 1.041 nós). Ou seja, o Gurobi passa os 300 s no nó raiz, e a escala que devolve vem das heurísticas internas dele. O modelo está certo: ele prova o ótimo das instâncias pequenas de teste (n005w4) e, com a escala fixada, reproduz o custo do validador.

## GRASP

O GRASP repete "construir uma escala nova e melhorar até não dar mais", e guarda a melhor. Fez em média 209 repetições em 300 s.

1. **Construção, dia a dia.** Para cada vaga de demanda do dia (primeiro as mínimas, depois as ótimas), calcula quanto o custo de cada enfermeiro disponível subiria se ele pegasse a vaga, mais um termo que evita gastar logo os turnos de quem tem contrato curto.
2. **Sorteio controlado (RCL).** Separa os candidatos com custo até c_mín + 0,15 × (c_máx − c_mín) e sorteia um deles. Com 0 seria sempre o mesmo (guloso); com 1, aleatório.
3. **Busca local VND.** Testa todos os movimentos N1, em ordem aleatória, aplicando os que baixam o custo. Se algum melhorou, volta para N1; se não, passa para N2, depois N3, depois N4. Para quando nenhum dos quatro melhora (ótimo local).
4. **Repete** com outra construção e fica com a melhor escala.

**Resultado:** cada ótimo local custa cerca de 2,5 vezes o ótimo publicado. A busca local só aceita melhoras, e as regras de sequência criam muitos "vales" ruins; recomeçar não basta para sair deles.

## Simulated Annealing (SA)

O SA anda de escala em escala com um movimento aleatório por vez e, às vezes, aceita piorar, para não ficar preso. Fez cerca de 250 milhões de movimentos em 300 s.

1. Parte de uma escala da construção do GRASP.
2. Sorteia um movimento: N1 (40%), N3, N2 ou N4 (20% cada).
3. Calcula a variação de custo Δ. Se Δ ≤ 0, aceita. Se piora, aceita com probabilidade e^(−Δ/T). Exemplo: com T = 40, uma piora de 30 é aceita 47% das vezes; com T = 2, quase nunca.
4. A temperatura T cai de 40 para 2 ao longo dos 300 s: no começo explora, no fim só refina.
5. Guarda a melhor escala visitada.

T0 = 40 e Tf = 2 foram calibrados em 4 instâncias da literatura que não estão no conjunto final.

**Resultado:** 22% acima do ótimo em média. Medimos que, nas instâncias n040w4 e n040w8, a escala atual fica viável o tempo todo, mas na primeira metade do tempo, com T alto, o custo soft sobe para 16 mil a 31 mil e só desce depois: boa parte do tempo é gasta "passeando". Isso é assunto para a reunião.

## SA + Fix-and-Optimize (F&O)

O F&O usa o próprio modelo de PLI do Gurobi, mas em pedaços pequenos que o solver resolve rápido. É o método que o professor apontou como errado na versão anterior (era uma LNS, que sorteava os pedaços) e que foi refeito.

1. Roda o SA na primeira metade do tempo (150 s) para ter uma boa escala inicial.
2. Monta o modelo completo uma vez no HiGHS (solver gratuito).
3. Define duas decomposições fixas: **janelas de 7 dias** (dias 0–6, 3–9, 6–12, …, com todos os enfermeiros) e **pares de enfermeiros** com as mesmas habilidades e o mesmo contrato (com todos os dias).
4. Para cada pedaço, em ordem: fixa todas as variáveis fora dele nos valores da escala atual e manda o solver resolver o que sobrou (até o ótimo ou 30 s), começando da escala atual. Se achar escala melhor, ela vira a atual. Nunca piora.
5. Uma passada = todos os pedaços. Repete passadas até uma passada inteira não melhorar nada; aí aumenta os pedaços (janelas de 14 dias, grupos de 4) e continua até o tempo acabar.

**Diferença para a LNS:** na LNS o pedaço é sorteado a cada iteração; no F&O os pedaços são fixos e percorridos sistematicamente, e o critério de parada é uma passada sem melhora (Helber e Sahling, 2010).

**Resultado:** 17% acima do ótimo em média, o melhor nas 8 instâncias. Resolveu em média 68 subproblemas (142 na n030w8, só 12 na n060w8, porque cada subproblema é resolvido sobre o modelo inteiro).

## Resultados

Custo médio de 3 sementes nas heurísticas, 300 s e 1 thread por execução (menor é melhor). * = ótimo provado na literatura.

| Instância | Melhor publicado | Gurobi | GRASP | SA | SA + F&O |
| --- | --- | --- | --- | --- | --- |
| n030w4 | 1.670* | 1.785 | 2.868 | 1.792 | **1.752** |
| n040w4 | 1.565* | 2.435 | 3.340 | 1.830 | **1.740** |
| n050w4 | 1.315* | 1.810 | 3.477 | 1.595 | **1.530** |
| n060w4 | 2.450* | 8.110 | 5.193 | 2.800 | **2.797** |
| n030w8 | 2.010* | 4.580 | 4.885 | 2.298 | **2.180** |
| n040w8 | 2.515 | 21.655 | 7.132 | 3.322 | **3.193** |
| n050w8 | 4.810 | 27.065 | 9.585 | 5.538 | **5.352** |
| n060w8 | 2.150 | 26.830 | 8.187 | 3.383 | **3.122** |
| Distância média ao melhor publicado | | +354% | +146% | +22% | **+17%** |

O Gurobi rodou no i5-13400; as heurísticas, num servidor mais lento por núcleo (o que não as favorece).

## Por que um método foi melhor que o outro

A ordem foi SA + F&O > SA > GRASP > Gurobi. A diferença entre eles está em como cada um consegue sair de uma escala "boa, mas não ótima".

**Por que o Gurobi foi tão ruim (+354%)**

1. **A relaxação linear é fraca.** O Gurobi se guia pelo PL, em que as variáveis podem valer frações. Uma escala "meio trabalha, meio folga" todo dia cumpre no papel as regras de sequência (S2, S3), fins de semana (S5, S7) e total (S6) sem pagar nada. Por isso o PL vale só 20% a 70% do ótimo (319 contra 1.565 na n040w4), e o solver não consegue podar a árvore de busca.
2. **O PL é caro.** Com 26 mil a 108 mil variáveis e restrições, só resolver o PL do primeiro nó leva quase todo o tempo: o log mostra de 280 mil a 1 milhão de iterações do simplex e 1 a 3 nós em 300 s.
3. **Simetria.** Enfermeiros com o mesmo contrato e as mesmas habilidades são intercambiáveis: trocar dois deles dá uma escala com o mesmo custo. O solver explora muitas dessas cópias inúteis.
4. **Pouco tempo e 1 thread.** 300 s é pouco para um modelo desse tamanho; quem resolve até o ótimo (Legrain e Omer, 2023) usa *branch-and-price* e horas.

Resultado: em 300 s o Gurobi só entrega a escala que as heurísticas internas dele acharam enquanto ainda resolvia o primeiro nó. Por isso o resultado é irregular (a n050w4 ficou a 38% e a n060w4, a 231%) e piora muito em 8 semanas, com o dobro de dias e de restrições de sequência. Na menor instância (n030w4) ele chega perto (+7%), porque o modelo é pequeno o bastante para explorar 1.041 nós.

**Por que o GRASP ficou atrás do SA (+146% contra +22%)**

O GRASP só aceita movimentos que melhoram. Ele para no primeiro ponto em que nenhum movimento de N1 a N4 melhora (ótimo local), e esses pontos custam cerca de 2,5 vezes o ótimo: para melhorar, seria preciso piorar um pouco antes, por exemplo desmontar uma sequência de trabalho para montar outra melhor. Recomeçar com outra construção (209 vezes) só leva a outros ótimos locais parecidos, porque cada repetição começa do zero, sem aproveitar o que aprendeu. O SA aceita piorar com probabilidade controlada por T e, com 250 milhões de movimentos, atravessa esses "vales".

Mesmo assim, o GRASP ganha do Gurobi nas quatro maiores instâncias (n060w4, n040w8, n050w8 e n060w8), porque sempre entrega um ótimo local razoável em poucos segundos, enquanto o Gurobi fica preso no primeiro nó.

**Por que o SA + F&O ganhou do SA puro (+17% contra +22%)**

Um movimento do SA mexe em no máximo 2 enfermeiros e 7 dias. Algumas melhoras exigem mudar vários enfermeiros ao mesmo tempo, por exemplo redistribuir os turnos de uma semana inteira entre 40 pessoas. O SA teria de acertar essa sequência de movimentos por sorte. O F&O resolve exatamente esse tipo de subproblema: fixa o resto e pede ao solver a melhor reorganização daquela semana, ou de dois enfermeiros, de uma vez. Com o mesmo tempo total, ficou de 2% a 8% abaixo do SA puro em 7 das 8 instâncias. A exceção foi a n060w4, onde empataram. A fase de SA dele também esfria em 150 s em vez de 300 s, e isso ajuda.

Nas maiores instâncias, o F&O consegue resolver poucos subproblemas (12 na n060w8), porque cada um é resolvido sobre o modelo inteiro; por isso o ganho ali é menor.

**Por que ninguém chegou ao ótimo**

Os ótimos publicados vieram de um método exato especializado rodando por horas. Com 5 minutos e 1 núcleo, chegar a 17% em média, e a menos de 4% na n030w4, é razoável. Num teste de 20 minutos, o SA puro parou de melhorar, enquanto o SA + F&O chegou a 7% do ótimo: a parte exata é a que mais aproveita tempo extra.

## Três ideias que o professor citou

### 1. Relaxação

**O que é.** Relaxar é resolver uma versão mais fácil do problema, afrouxando alguma regra. A mais comum é a **relaxação linear**: deixar as variáveis 0/1 assumirem qualquer valor entre 0 e 1. Como há mais liberdade, o custo da versão relaxada nunca é maior que o da melhor escala real. Por isso ela dá um **limite inferior**: "o ótimo não pode custar menos que isto".

**Exemplo simples.** Regra: "quem trabalha precisa trabalhar no mínimo 3 dias seguidos". Na escala real, trabalhar 1 dia isolado paga penalidade. Na relaxada, o enfermeiro pode "trabalhar 0,5" todo dia: a regra fica satisfeita no papel e não paga nada. A relaxação fica barata demais.

**Como aparece no projeto.** O Gurobi resolve a relaxação linear em cada nó do branch-and-bound. A nossa vale só 20% a 70% do ótimo (319 contra 1.565 na n040w4). Isso é uma relaxação **fraca**: o limite inferior fica muito baixo, o gap fica alto e o solver não consegue descartar partes da busca.

**Como melhorar.** Com uma relaxação mais forte (mais próxima do ótimo), o solver prova o ótimo muito mais rápido. Caminhos: (a) acrescentar desigualdades válidas (cortes), que eliminam soluções fracionárias sem eliminar escalas reais; (b) reformular, como Legrain e Omer (2023), em que cada variável é a escala inteira de um enfermeiro (geração de colunas, ou *branch-and-price*): aí as regras de sequência já vêm cumpridas em cada coluna e a relaxação fica quase igual ao ótimo. Outra relaxação conhecida é a **lagrangiana**: tirar uma regra difícil (por exemplo, a cobertura) do conjunto de restrições e colocá-la na função objetivo com um preço; o problema se separa em um subproblema por enfermeiro.

### 2. Otimização das instâncias (provar ótimos)

**O que é.** Resolver uma instância "até o ótimo" significa achar uma escala e provar que nenhuma é melhor: o custo da escala encontrada fica igual ao limite inferior (gap = 0%). Hoje o Gurobi só provou isso em instâncias de 5 enfermeiros; nas 8 finais o tempo acabou antes.

**O que o professor sugeriu.** Dar mais tempo ao Gurobi para provar mais ótimos. Plano concreto:

- Rodar com 1 hora (ou mais) e 6 threads nas 9 instâncias de teste e na n030w4, onde há chance real de fechar o gap.
- Começar o Gurobi pela escala do SA + F&O (*MIP start*). O limite superior já nasce bom, e o solver gasta o tempo subindo o limite inferior.
- Reportar, para cada instância, se provou o ótimo e em quanto tempo. Nas que não fecharem, reportar o gap final.

Com isso, a Etapa 5 passa a ter ótimos provados por vocês, e nas instâncias em que o Gurobi provar o ótimo dá para medir a distância exata de cada heurística. Nas de 8 semanas, com a relaxação tão fraca, provar o ótimo em 1 hora é improvável; o esperado é o gap cair, não zerar.

### 3. Piorar a solução para depois melhorar

**Por que funciona.** Uma busca que só aceita melhoras para no primeiro ótimo local: o fundo de um vale, sem saber que existe um vale mais fundo ao lado. Para chegar ao outro vale, é preciso subir um pouco antes, isto é, aceitar uma escala pior por alguns passos.

**Como cada método faz isso no projeto:**

| Método | Aceita piorar? | Como |
| --- | --- | --- |
| GRASP | Não, na busca local | Só escapa recomeçando de outra construção. Por isso trava em escalas ruins (+146%) |
| SA | Sim | Aceita uma piora Δ com probabilidade e^(−Δ/T): muitas no começo (T alto), quase nenhuma no fim. É o principal motivo de ele ir tão melhor que o GRASP (+22%) |
| F&O | Não precisa | Cada subproblema já enxerga mudanças grandes de uma vez, que seriam vários passos piores e depois melhores para o SA |

**Outras formas conhecidas, para a conversa:**

- **Perturbação (ILS, *Iterated Local Search*):** num ótimo local, aplicar de propósito alguns movimentos aleatórios que pioram e rodar a busca local de novo. A versão anterior do GRASP fazia isso.
- **Aceitar empates (Δ = 0):** andar por escalas de mesmo custo até achar uma saída. O SA já faz; o VND do GRASP não.
- **Oscilação estratégica (penalidades dinâmicas):** deixar a escala ficar inviável por um tempo, com peso de violação mais baixo, e depois subir o peso para voltar à região viável. É "piorar" em viabilidade para chegar a escalas melhores do outro lado. Hoje, com peso fixo de 10.000, o SA nunca faz isso.
- **Reaquecimento no SA:** quando a busca estagna, subir a temperatura de novo por um tempo.

## Perguntas prováveis e respostas

**Por que trocaram de tema?** O professor observou que o Gurobi resolvia o problema de cobertura de conjuntos com facilidade. O escalonamento individual (quem trabalha em cada turno, com regras de contrato) é mais difícil e tem dados e resultados publicados.

**O modelo está certo, já que o Gurobi foi tão mal?** Sim. Com a escala fixada, o modelo dá exatamente o mesmo custo que o avaliador oficial (testado em 9 soluções de referência e em escalas aleatórias), e o Gurobi prova o ótimo das instâncias pequenas. O problema é a formulação fraca, não um erro.

**O que é uma relaxação linear fraca?** É quando o modelo com variáveis fracionárias custa muito menos que a melhor escala real. Exemplo: a regra "no mínimo 3 dias seguidos de trabalho" não cobra nada de uma escala que trabalha 0,5 todo dia. O solver usa esse valor baixo como referência e não consegue descartar partes da busca.

**Por que o gap do Gurobi é tão alto se a escala não está tão ruim?** Na n030w4 o gap é 22%, mas a escala está a 7% do ótimo. O gap compara com o limite inferior, que é fraco; por isso comparamos também com o ótimo publicado.

**Qual a diferença entre heurística, metaheurística e matheurística?** Heurística: uma regra que acha uma solução boa, sem garantia de ótimo. Metaheurística: uma estratégia geral para guiar heurísticas e escapar de ótimos locais (GRASP, SA). Matheurística: uma heurística que usa um modelo matemático e um solver como peça (F&O).

**O que é um ótimo local?** Uma escala que nenhum movimento pequeno melhora, mas que não é a melhor de todas. É como estar no fundo de um vale sem saber que existe um vale mais fundo ao lado.

**Por que o SA aceita piorar?** Para conseguir sair de um vale e chegar a outro mais fundo. A temperatura controla isso: no começo aceita muitas pioras; no fim, quase nenhuma.

**Qual a diferença entre Fix-and-Optimize e LNS?** Os dois fixam parte da escala e reotimizam o resto com o solver. Na LNS o pedaço é sorteado a cada vez; no F&O os pedaços são fixos (janelas de 7 dias, pares de enfermeiros) e percorridos em ordem, até uma volta inteira não melhorar nada. A primeira versão era uma LNS; foi isso que o professor apontou e que corrigimos.

**Como as restrições obrigatórias entram nas heurísticas?** H1 e H4 nem podem ser quebradas, por causa do formato da tabela. H2 e H3 viram uma penalidade de 10.000 por violação, então qualquer escala viável é melhor que uma inviável. Todas as escalas reportadas são viáveis.

**Por que usaram numba?** Para o cálculo do custo ficar rápido (de 50 mil para 1 milhão de movimentos por segundo) sem mudar o algoritmo. O Gurobi e o HiGHS também são programas compilados, então isso deixa a comparação mais justa.

**Por que só 3 sementes?** Por tempo de máquina: são 72 execuções de 5 minutos. A diferença entre o custo médio e o melhor das 3 ficou abaixo de 5,2%, então os resultados são estáveis.

**Como os parâmetros foram escolhidos?** T0 e Tf do SA foram testados em 4 instâncias que não estão no conjunto final, para não ajustar o método às mesmas instâncias usadas na comparação. α = 0,15 deixa a construção quase gulosa, com um pouco de variação.

## Para a reunião de quarta

O professor levantou cinco pontos. Para cada um: como está hoje e o que propor.

| Ponto | Como está hoje | O que propor |
| --- | --- | --- |
| Tempo do Gurobi pequeno; provar mais ótimos | 300 s e 1 thread. Prova o ótimo só em n005w4 (5 enfermeiros). | Rodar com 1 h e 6 threads nas 9 instâncias de teste e na n030w4, onde há chance de provar ótimos. Dar ao Gurobi a escala do SA + F&O como solução inicial (MIP start), para ele gastar o tempo no limite inferior. Nas de 8 semanas, com o PL a 20%–70% do ótimo, provar o ótimo em 1 h é improvável. |
| Representação da solução | Tabela enfermeiro × dia com (turno, habilidade) ou folga. H1 e H4 garantidas pelo formato. | Manter; explicar que só H2 e H3 viram penalidade. |
| Estruturas de vizinhança | N1 troca, N2 swap, N3 bloco (2–5 dias), N4 swap de bloco (2–7 dias). | Perguntar se vale um movimento de "semana inteira" ou de fim de semana. |
| Restrições: penalidades dinâmicas | Peso fixo de 10.000 por violação. A construção já sai viável e, como 10.000 é muito maior que T, o SA nunca aceita violar: na prática só anda dentro da região viável. | Peso dinâmico: começar baixo (por exemplo, 60) e ajustar durante a busca, subindo quando a escala atual fica muito tempo inviável e descendo quando fica viável. A busca pode atravessar escalas inviáveis como atalho e termina viável. |
| Empates na função objetivo | Pesos múltiplos de 5, então há muitos empates. Na escala final, 0,4%–0,5% dos movimentos têm Δ = 0 e nenhum melhora. O SA aceita Δ = 0; o VND do GRASP só aceita Δ < 0 e para no primeiro platô. | Aceitar movimentos laterais (Δ = 0) no VND, com um limite. Ou um critério de desempate: entre escalas de mesmo custo, preferir a que está mais longe de violar (por exemplo, cobertura com folga, menos sequências no limite). |

Outro achado para comentar: no SA, com T0 = 40 e 300 s, a primeira metade do tempo é gasta "passeando" com custo alto. Calibrar T0 pela taxa de aceitação inicial, em vez de um valor fixo, deve ajudar. O SA + F&O já se beneficia disso, porque seu SA esfria em 150 s.

Perguntas para levar:

- Qual limite de tempo e quantas threads ele considera justo para o Gurobi? Pode ser diferente do das heurísticas?
- Qual esquema de penalidade dinâmica ele recomenda (ajuste por viabilidade recente, oscilação estratégica)?
- Para os empates, ele prefere movimentos laterais ou um critério secundário?
- O F&O, como está agora, atende à crítica dele?
- Precisamos reentregar as Etapas 1 a 4 com o tema novo?

## Teste rápido

Tente responder antes de ler a resposta.

1. Qual é a diferença entre H2 e S1? — H2 é a cobertura mínima, obrigatória; S1 é a cobertura ideal, que se não for atingida custa 30 por pessoa faltando.
2. O que N2 muda na cobertura do dia? — Nada: dois enfermeiros só trocam o que fazem, então o total de cada turno continua igual.
3. Com T = 2, o SA aceita uma piora de 30? — Quase nunca: a chance é e^(−15), praticamente zero.
4. Por que o GRASP repete 209 vezes e mesmo assim fica longe do ótimo? — Porque cada repetição termina num ótimo local ruim e não aproveita nada das anteriores.
5. Por que o F&O nunca piora a escala? — Porque a escala atual é uma solução válida do subproblema e é dada ao solver como ponto de partida; ele só troca por algo melhor.
6. O que faria o Gurobi provar mais ótimos? — Mais tempo e threads, começar da escala das heurísticas (MIP start) e, a longo prazo, uma formulação mais forte (geração de colunas).
7. O que é uma penalidade dinâmica? — Um peso para as violações que muda durante a busca: sobe quando a escala fica inviável por muito tempo e desce quando ela está viável, permitindo atalhos por escalas inviáveis.
8. O que é um empate na função objetivo e por que importa? — Movimentos com Δ = 0, que mudam a escala sem mudar o custo. Se o método só aceita Δ < 0, ele para num platô mesmo havendo melhoras do outro lado.
