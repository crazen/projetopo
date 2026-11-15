# =====================================================================
#  nurse.mod  --  Nurse Rostering (INRC-II), horizonte completo (offline)
#  Modelo de PLI em AMPL (escrito no subconjunto comum AMPL/MathProg, para
#  rodar tanto no AMPL quanto no tradutor do GLPK usado por exato.py).
#  Dados: gerados por gen_dat.py (um arquivo .dat por instancia).
# =====================================================================

# ------------------------------- conjuntos e parametros --------------
set NURSES;
set SKILLS;
set SHIFTS;
set FORB within {SHIFTS, SHIFTS};     # (p,q): turno p num dia nao pode ser seguido do turno q no dia seguinte

param W integer >= 1;                 # numero de semanas
param H integer >= 1;                 # dias de pre-historico (so para escrever as janelas)
param D := 7 * W;                     # dias do horizonte: 0..D-1 (0 = segunda)

set DAYS := 0 .. D-1;
set PRE  := -H .. -1;                 # dias "virtuais" anteriores ao horizonte (vem do historico)
set ALLD := -H .. D-1;

param has{NURSES, SKILLS} binary default 0;          # enfermeiro n possui a habilidade k

param minS{SHIFTS};  param maxS{SHIFTS};             # consecutivos do mesmo turno
param minA{NURSES};  param maxA{NURSES};             # total de turnos (contrato)
param minW{NURSES};  param maxW{NURSES};             # dias de trabalho consecutivos
param minO{NURSES};  param maxO{NURSES};             # folgas consecutivas
param maxWE{NURSES};                                 # max fins de semana trabalhados
param comp{NURSES} binary;                           # fim de semana completo?

param nA0{NURSES}  default 0;                        # historico: total de turnos
param nWE0{NURSES} default 0;                        # historico: fins de semana trabalhados

param dmin{DAYS, SHIFTS, SKILLS} default 0;          # cobertura minima (hard)
param dopt{DAYS, SHIFTS, SKILLS} default 0;          # cobertura otima  (soft)

param reqAny{NURSES, DAYS} default 0;                # pedido de folga no dia
param reqSh {NURSES, DAYS, SHIFTS} default 0;        # pedido de nao trabalhar um turno

param hw{NURSES, PRE} binary default 0;              # trabalhou no dia virtual?
param hs{NURSES, PRE, SHIFTS} binary default 0;      # fez o turno s no dia virtual?

# pesos (INRC-II)
param wS1 := 30;   param wShift := 15;  param wWork := 30;  param wOff := 30;
param wPref := 10; param wWeekend := 30; param wTotal := 20; param wMaxWE := 30;

# ------------------------------- variaveis ---------------------------
var x{n in NURSES, d in DAYS, s in SHIFTS, k in SKILLS: has[n,k] == 1} binary;  # n faz turno s, na funcao k, no dia d
var a{NURSES, ALLD, SHIFTS} binary;      # n faz o turno s no dia d (qualquer funcao)
var w{NURSES, ALLD} binary;              # n trabalha no dia d

var under{DAYS, SHIFTS, SKILLS} >= 0;                 # S1
var vmaxS{NURSES, DAYS, SHIFTS} >= 0;                 # S2 max mesmo turno
var vmaxW{NURSES, DAYS} >= 0;                         # S2 max dias de trabalho
var vmaxO{NURSES, DAYS} >= 0;                         # S3 max folgas
var vminS{n in NURSES, t in DAYS, s in SHIFTS, j in 1 .. minS[s]-1} >= 0;   # S2 min mesmo turno
var vminW{n in NURSES, t in DAYS, j in 1 .. minW[n]-1} >= 0;                # S2 min dias de trabalho
var vminO{n in NURSES, t in DAYS, j in 1 .. minO[n]-1} >= 0;                # S3 min folgas
var wkd{n in NURSES, wk in 0 .. W-1: comp[n] == 1} >= 0;                    # S5
var tUnder{NURSES} >= 0;                              # S6
var tOver{NURSES} >= 0;                               # S6
var ww{NURSES, 0 .. W-1} >= 0;                        # fim de semana trabalhado
var wExc{NURSES} >= 0;                                # S7

# ------------------------------- objetivo ----------------------------
minimize Penalidade:
      wS1    * sum{d in DAYS, s in SHIFTS, k in SKILLS} under[d,s,k]
    + wShift * ( sum{n in NURSES, d in DAYS, s in SHIFTS} vmaxS[n,d,s]
               + sum{n in NURSES, t in DAYS, s in SHIFTS, j in 1 .. minS[s]-1} (minS[s]-j) * vminS[n,t,s,j] )
    + wWork  * ( sum{n in NURSES, d in DAYS} vmaxW[n,d]
               + sum{n in NURSES, t in DAYS, j in 1 .. minW[n]-1} (minW[n]-j) * vminW[n,t,j] )
    + wOff   * ( sum{n in NURSES, d in DAYS} vmaxO[n,d]
               + sum{n in NURSES, t in DAYS, j in 1 .. minO[n]-1} (minO[n]-j) * vminO[n,t,j] )
    + wPref  * ( sum{n in NURSES, d in DAYS} reqAny[n,d] * w[n,d]
               + sum{n in NURSES, d in DAYS, s in SHIFTS} reqSh[n,d,s] * a[n,d,s] )
    + wWeekend * sum{n in NURSES, wk in 0 .. W-1: comp[n] == 1} wkd[n,wk]
    + wTotal * sum{n in NURSES} (tUnder[n] + tOver[n])
    + wMaxWE * sum{n in NURSES} wExc[n];

# ------------------------------- restricoes hard ---------------------
# vinculos entre variaveis (w binaria + soma a = w  =>  H1: no maximo um turno por dia)
s.t. link_a{n in NURSES, d in DAYS, s in SHIFTS}:
    a[n,d,s] = sum{k in SKILLS: has[n,k] == 1} x[n,d,s,k];
s.t. link_w{n in NURSES, d in DAYS}:
    w[n,d] = sum{s in SHIFTS} a[n,d,s];

# H2 (+H4: x so existe para habilidades que o enfermeiro possui)
s.t. cobertura_min{d in DAYS, s in SHIFTS, k in SKILLS}:
    sum{n in NURSES: has[n,k] == 1} x[n,d,s,k] >= dmin[d,s,k];

# H3: sucessoes proibidas (inclui a fronteira com o historico: d = -1)
s.t. sucessao{n in NURSES, d in -1 .. D-2, (p,q) in FORB}:
    a[n,d,p] + a[n,d+1,q] <= 1;

# dias virtuais fixados pelo historico
s.t. fix_w{n in NURSES, d in PRE}:            w[n,d] = hw[n,d];
s.t. fix_a{n in NURSES, d in PRE, s in SHIFTS}: a[n,d,s] = hs[n,d,s];

# ------------------------------- restricoes soft (linearizacao) -------
# S1: falta para a cobertura otima
s.t. s1_cob_otima{d in DAYS, s in SHIFTS, k in SKILLS}:
    under[d,s,k] >= dopt[d,s,k] - sum{n in NURSES: has[n,k] == 1} x[n,d,s,k];

# S2/S3 maximos: cada janela de (max+1) dias todos "ativos" custa 1
s.t. s2_max_turno{n in NURSES, d in DAYS, s in SHIFTS}:
    vmaxS[n,d,s] >= sum{i in d-maxS[s] .. d} a[n,i,s] - maxS[s];
s.t. s2_max_trab{n in NURSES, d in DAYS}:
    vmaxW[n,d] >= sum{i in d-maxW[n] .. d} w[n,i] - maxW[n];
s.t. s3_max_folga{n in NURSES, d in DAYS}:
    vmaxO[n,d] >= sum{i in d-maxO[n] .. d} (1 - w[n,i]) - maxO[n];

# S2/S3 minimos: uma sequencia de tamanho exato j (< minimo) terminando antes do dia t custa (min - j).
# O padrao e: [dia t-j-1 inativo] [dias t-j..t-1 ativos] [dia t inativo]; a soma abaixo vale 1 so nesse caso
# (a variavel v e o indicador do padrao; o peso (min - j) entra no objetivo).
s.t. s2_min_turno{n in NURSES, t in DAYS, s in SHIFTS, j in 1 .. minS[s]-1}:
    vminS[n,t,s,j] >= (1 - a[n,t-j-1,s]) + sum{i in t-j .. t-1} a[n,i,s] + (1 - a[n,t,s]) - (j+1);
s.t. s2_min_trab{n in NURSES, t in DAYS, j in 1 .. minW[n]-1}:
    vminW[n,t,j] >= (1 - w[n,t-j-1]) + sum{i in t-j .. t-1} w[n,i] + (1 - w[n,t]) - (j+1);
s.t. s3_min_folga{n in NURSES, t in DAYS, j in 1 .. minO[n]-1}:
    vminO[n,t,j] >= w[n,t-j-1] + sum{i in t-j .. t-1} (1 - w[n,i]) + w[n,t] - (j+1);

# S5: fim de semana completo (sabado = dia 5, domingo = dia 6 de cada semana)
s.t. s5_a{n in NURSES, wk in 0 .. W-1: comp[n] == 1}:  wkd[n,wk] >= w[n,7*wk+5] - w[n,7*wk+6];
s.t. s5_b{n in NURSES, wk in 0 .. W-1: comp[n] == 1}:  wkd[n,wk] >= w[n,7*wk+6] - w[n,7*wk+5];

# S6: total de turnos dentro dos limites do contrato (considera o historico)
s.t. s6_min{n in NURSES}: tUnder[n] >= minA[n] - (nA0[n] + sum{d in DAYS} w[n,d]);
s.t. s6_max{n in NURSES}: tOver[n]  >= (nA0[n] + sum{d in DAYS} w[n,d]) - maxA[n];

# S7: maximo de fins de semana trabalhados
s.t. s7_sab{n in NURSES, wk in 0 .. W-1}: ww[n,wk] >= w[n,7*wk+5];
s.t. s7_dom{n in NURSES, wk in 0 .. W-1}: ww[n,wk] >= w[n,7*wk+6];
s.t. s7_max{n in NURSES}: wExc[n] >= nWE0[n] + sum{wk in 0 .. W-1} ww[n,wk] - maxWE[n];
