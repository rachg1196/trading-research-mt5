//+------------------------------------------------------------------+
//|                                               Patron_WM_EA.mq5   |
//|  Proyecto W y M - Raul                                           |
//|  Asesor experto v2.1 (panel sin parpadeo + estado guardado):                                              |
//|   - Detecta W/M igual que el indicador Patron_WM.                |
//|   - Confirma continuidad (precio mas alla del cuello y avanzando |
//|     a favor en los ultimos X segundos) antes de entrar.          |
//|   - Si el precio va en contra, espera; si vuelve a cruzar, entra.|
//|   - Descarta la senal tras K velas o si rompe el extremo.        |
//|   - Cierra cada operacion despues de N velas de su temporalidad. |
//|                                                                  |
//|  AVISO: en las pruebas con datos esta forma de operar NO mostro  |
//|  ventaja despues del spread. Probar primero en el Probador de    |
//|  Estrategias y en cuenta DEMO.                                   |
//|  Por seguridad NO opera en cuenta REAL salvo que se active       |
//|  "Permitir cuenta REAL".                                         |
//+------------------------------------------------------------------+
#property copyright   "Proyecto W y M - Raul"
#property version     "2.10"
#property description "Entra con cada senal W (compra) / M (venta) confirmada y cierra despues de N velas."
#property description "Por seguridad solo opera en DEMO salvo que se permita la cuenta REAL."

#include <Trade\Trade.mqh>

input group "Operacion"
input double InpLote          = 0.10;                                  // Lote
input int    InpVelasSalida   = 2;                                     // Cerrar despues de N velas
input string InpSimbolos      = "BreakX 600,TrendX 600,SwitchX 600";   // Mercados (separados por coma)
input string InpTFs           = "M1,M2,M3";                            // Temporalidades (separadas por coma o TODAS)
input bool   InpOperarW       = true;      // Operar W (compras)
input bool   InpOperarM       = true;      // Operar M (ventas)
input int    InpMaxPorMercado = 3;         // Max. operaciones abiertas en el MISMO mercado (0 = sin limite)
input bool   InpUnaPorCelda   = true;      // Max. 1 operacion abierta por mercado+temporalidad
input int    InpMaxPosiciones = 5;         // Max. operaciones abiertas en total (0 = sin limite)
input double InpSLEmergencia  = 0;         // SL de emergencia en puntos (0 = sin SL)
input bool   InpPermitirReal  = false;     // Permitir operar en cuenta REAL
input long   InpMagic         = 260520;    // Numero magico base

input group "Confirmacion de continuidad"
input int    InpConfirmSeg    = 30;        // Segundos de continuidad a favor (0 = entrar directo)
input int    InpExpiraVelas   = 10;        // Descartar la senal si no entra en K velas

input group "Reglas diarias (0 = desactivado; horas = hora de tu PC)"
input double InpMetaDiaria    = 0;         // Meta diaria en $ (al llegar, se detiene hasta manana)
input double InpPerdidaMax    = 0;         // Perdida maxima diaria en $ (al llegar, se detiene)
input int    InpMaxOpsDia     = 0;         // Max. operaciones por dia
input string InpHoraInicio    = "00:00";   // Hora de inicio
input string InpHoraFin       = "23:59";   // Hora de fin

input group "Avisos"
input bool   InpAvisoCelular  = true;      // Avisar al celular al abrir/cerrar
input bool   InpAvisoVentana  = false;     // Ventana de alerta al abrir/cerrar

enum ESQUINA_PANEL
{
   SUP_IZQ = 0,   // Superior izquierda
   SUP_DER = 1,   // Superior derecha
   INF_IZQ = 2,   // Inferior izquierda
   INF_DER = 3    // Inferior derecha
};

input group "Panel de informacion"
input bool          InpPanel        = true;      // Mostrar panel
input ESQUINA_PANEL InpPanelEsquina = INF_IZQ;   // Esquina del panel
input int           InpPanelMargenX = 10;        // Margen horizontal (pixeles)
input int           InpPanelMargenY = 10;        // Margen vertical (pixeles)
input int           InpPanelAncho   = 560;       // Ancho del panel
input int           InpPanelLetra   = 9;         // Tamano de letra

input group "Deteccion (mismos valores que el indicador)"
input int    InpATR           = 14;
input double InpKATR          = 1.5;
input double InpTolATR        = 0.5;
input double InpMaxBarrida    = 0.5;
input double InpMinCaida      = 1.0;
input int    InpMinVelas      = 3;
input double InpMinRebATR     = 2.5;
input double InpEsperaFact    = 1.0;
input int    InpEsperaMin     = 5;
input bool   InpTriples       = true;
input int    InpBarrasEsc     = 1500;

#define BUF 300   // segundos de precios guardados por mercado

struct Piv   { int t; int i; double p; int c; };
struct Pat   { int tipo; int toques; int variante; int idx[6]; double pr[6]; double cuello; int sig; };
struct Celda { string sym; int si; int tfi; datetime ultBarra; bool primera; };
struct Pend  { int si; int tfi; int tipo; double cuello; double extremo; datetime expira; string motivo; };

string          TFN_ALL[] = {"M1","M2","M3","M4","M5","M6","M10","M12","M15","M20","M30",
                             "H1","H2","H3","H4","H6","H8","H12","D1","W1","MN1"};
ENUM_TIMEFRAMES TFV_ALL[] = {PERIOD_M1,PERIOD_M2,PERIOD_M3,PERIOD_M4,PERIOD_M5,PERIOD_M6,
                             PERIOD_M10,PERIOD_M12,PERIOD_M15,PERIOD_M20,PERIOD_M30,
                             PERIOD_H1,PERIOD_H2,PERIOD_H3,PERIOD_H4,PERIOD_H6,PERIOD_H8,
                             PERIOD_H12,PERIOD_D1,PERIOD_W1,PERIOD_MN1};

CTrade  trade;
Celda   g_cel[];
Pend    g_pend[];
string  g_sims[];
int     g_tfi[];
double  g_px[];        // precios por segundo: g_px[si*BUF + pos]
int     g_pxPos[];
int     g_pxCnt[];
string  g_ultimo = "-";
bool    g_bloqueoReal = false;
string  PFXE = "WMea_";
bool    g_cambio = false;      // hay algo nuevo que guardar
string  ARCH_ESTADO = "";

//+------------------------------------------------------------------+
int BuscarTF(string s)
{
   StringToUpper(s);
   for(int i = 0; i < ArraySize(TFN_ALL); i++)
      if(TFN_ALL[i] == s) return i;
   return -1;
}

int MinutosDe(string hhmm)
{
   string p[];
   if(StringSplit(hhmm, ':', p) != 2) return -1;
   return (int)StringToInteger(p[0]) * 60 + (int)StringToInteger(p[1]);
}

void Avisar(string msg)
{
   Print("Patron_WM_EA: ", msg);
   if(InpAvisoVentana) Alert(msg);
   if(InpAvisoCelular) SendNotification(msg);
}

//+------------------------------------------------------------------+
int OnInit()
{
   string partes[];
   int ns = StringSplit(InpSimbolos, ',', partes);
   ArrayResize(g_sims, 0);
   for(int i = 0; i < ns; i++)
   {
      string s = partes[i];
      StringTrimLeft(s); StringTrimRight(s);
      if(StringLen(s) == 0) continue;
      if(!SymbolSelect(s, true)) { Print("Patron_WM_EA: mercado no encontrado: ", s); continue; }
      int n = ArraySize(g_sims); ArrayResize(g_sims, n + 1); g_sims[n] = s;
   }
   ArrayResize(g_tfi, 0);
   string t = InpTFs;
   StringToUpper(t); StringTrimLeft(t); StringTrimRight(t);
   if(t == "TODAS")
   {
      ArrayResize(g_tfi, ArraySize(TFN_ALL));
      for(int i = 0; i < ArraySize(TFN_ALL); i++) g_tfi[i] = i;
   }
   else
   {
      string pt[];
      int nt = StringSplit(t, ',', pt);
      for(int i = 0; i < nt; i++)
      {
         string s = pt[i];
         StringTrimLeft(s); StringTrimRight(s);
         int k = BuscarTF(s);
         if(k < 0) { Print("Patron_WM_EA: temporalidad no reconocida: ", s); continue; }
         int n = ArraySize(g_tfi); ArrayResize(g_tfi, n + 1); g_tfi[n] = k;
      }
   }
   if(ArraySize(g_sims) == 0 || ArraySize(g_tfi) == 0)
   {
      Print("Patron_WM_EA: no hay mercados o temporalidades validos.");
      return(INIT_PARAMETERS_INCORRECT);
   }
   if(InpVelasSalida < 1) { Print("Patron_WM_EA: N velas debe ser 1 o mas."); return(INIT_PARAMETERS_INCORRECT); }
   if(InpConfirmSeg < 0 || InpConfirmSeg > BUF - 10) { Print("Patron_WM_EA: segundos de confirmacion entre 0 y ", BUF - 10); return(INIT_PARAMETERS_INCORRECT); }

   int nS = ArraySize(g_sims), nT = ArraySize(g_tfi);
   ArrayResize(g_cel, nS * nT);
   for(int s = 0; s < nS; s++)
      for(int k = 0; k < nT; k++)
      {
         int c = s * nT + k;
         g_cel[c].sym = g_sims[s]; g_cel[c].si = s; g_cel[c].tfi = g_tfi[k];
         g_cel[c].ultBarra = 0; g_cel[c].primera = true;
      }
   ArrayResize(g_px, nS * BUF);
   ArrayResize(g_pxPos, nS);
   ArrayResize(g_pxCnt, nS);
   ArrayInitialize(g_px, 0.0);
   ArrayInitialize(g_pxPos, 0);
   ArrayInitialize(g_pxCnt, 0);
   ArrayResize(g_pend, 0);

   g_bloqueoReal = (AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL && !InpPermitirReal);
   if(g_bloqueoReal)
      Print("Patron_WM_EA: CUENTA REAL detectada. No se abriran operaciones (activa 'Permitir cuenta REAL' si lo decides).");

   PFXE = "WMea_" + IntegerToString(ChartID() % 100000) + "_";
   ARCH_ESTADO = "Patron_WM_EA_" + IntegerToString(AccountInfoInteger(ACCOUNT_LOGIN)) + "_" + IntegerToString(InpMagic) + ".txt";
   CargarEstado();
   EventSetTimer(1);
   Estado();
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   GuardarEstado();
   ObjectsDeleteAll(0, PFXE);
   ChartRedraw();
}

void OnTick() { }   // el trabajo se hace en OnTimer (multi-mercado)

//+------------------------------------------------------------------+
//| Deteccion (identica al indicador)                                |
//+------------------------------------------------------------------+
void CalcATR(const double &h[], const double &l[], const double &c[], int from, int to, int n, double &a[])
{
   for(int i = from; i <= to; i++)
   {
      double tr = h[i] - l[i];
      if(i > from)
         tr = MathMax(tr, MathMax(MathAbs(h[i] - c[i-1]), MathAbs(l[i] - c[i-1])));
      if(i == from) a[i] = tr;
      else          a[i] = a[i-1] + (tr - a[i-1]) / n;
   }
}

void AddPiv(Piv &pv[], int t, int i, double p, int c)
{
   int n = ArraySize(pv);
   ArrayResize(pv, n + 1);
   pv[n].t = t; pv[n].i = i; pv[n].p = p; pv[n].c = c;
}

void ZigZag(const double &h[], const double &l[], const double &a[], int from, int to, double k, Piv &pv[])
{
   ArrayResize(pv, 0);
   int    d = 0;
   int    ext_i = from;  double ext_p = h[from];
   int    lo_i  = from;  double lo_p  = l[from];
   int    hi_i  = from;  double hi_p  = h[from];
   for(int i = from + 1; i <= to; i++)
   {
      double th = k * a[i];
      if(d == 0)
      {
         if(h[i] > hi_p) { hi_i = i; hi_p = h[i]; }
         if(l[i] < lo_p) { lo_i = i; lo_p = l[i]; }
         if(hi_p - lo_p >= th)
         {
            if(hi_i > lo_i) { AddPiv(pv, -1, lo_i, lo_p, i); d = 1;  ext_i = hi_i; ext_p = hi_p; }
            else            { AddPiv(pv,  1, hi_i, hi_p, i); d = -1; ext_i = lo_i; ext_p = lo_p; }
         }
         continue;
      }
      if(d == 1)
      {
         if(h[i] > ext_p) { ext_i = i; ext_p = h[i]; }
         else if(ext_p - l[i] >= th) { AddPiv(pv, 1, ext_i, ext_p, i); d = -1; ext_i = i; ext_p = l[i]; }
      }
      else
      {
         if(l[i] < ext_p) { ext_i = i; ext_p = l[i]; }
         else if(h[i] - ext_p >= th) { AddPiv(pv, -1, ext_i, ext_p, i); d = 1; ext_i = i; ext_p = h[i]; }
      }
   }
}

void AddPat(Pat &res[], const Pat &P)
{
   int n = ArraySize(res);
   for(int k = 0; k < n; k++)
      if(res[k].tipo == P.tipo && res[k].sig == P.sig)
      {
         if(P.toques > res[k].toques) res[k] = P;
         return;
      }
   ArrayResize(res, n + 1);
   res[n] = P;
}

void BuscarW(const double &h[], const double &l[], const double &c[], const double &a[],
             const Piv &pv[], int last, int tipo, Pat &res[])
{
   int np = ArraySize(pv);
   for(int jj = 0; jj < np; jj++)
   {
      if(pv[jj].t != -1) continue;
      for(int toques = 2; toques <= 3; toques++)
      {
         if(toques == 3 && !InpTriples) continue;
         int j1 = jj - 2 * (toques - 1);
         if(j1 - 2 < 0) continue;
         Piv H0 = pv[j1 - 1];
         Piv L1 = pv[j1];
         Piv L0 = pv[j1 - 2];
         Piv Lu = pv[jj];
         if(!(L1.p < L0.p)) continue;
         double cuello = -DBL_MAX;
         for(int q = j1 + 1; q <= jj; q += 2) cuello = MathMax(cuello, pv[q].p);
         double rebote = cuello - L1.p;
         if(rebote <= 0) continue;
         if((H0.p - L1.p) < InpMinCaida * rebote) continue;
         if(rebote < InpMinRebATR * a[L1.i]) continue;
         bool ok = true;
         for(int q = j1 + 1; q <= jj; q++)
            if(pv[q].i - pv[q-1].i < InpMinVelas) { ok = false; break; }
         if(!ok) continue;
         double tol    = InpTolATR * a[Lu.i];
         double limite = L1.p - InpMaxBarrida * rebote;
         for(int q = j1 + 2; q <= jj; q += 2)
            if(pv[q].p < limite) { ok = false; break; }
         if(!ok) continue;
         if(toques == 3 && pv[j1 + 3].p > pv[j1 + 1].p + tol) continue;
         double dd = Lu.p - L1.p;
         int variante = (MathAbs(dd) <= tol) ? 1 : (dd > 0 ? 0 : 2);
         int inicio = Lu.c;
         int dur    = Lu.i - L1.i + 1;
         int fin    = MathMin(last, inicio + MathMax(InpEsperaMin, (int)(InpEsperaFact * dur)));
         double minp = DBL_MAX;
         for(int q = j1; q <= jj; q += 2) minp = MathMin(minp, pv[q].p);
         double invalido = minp - tol;
         int sig = -1;
         for(int i = inicio; i <= fin; i++)
         {
            if(l[i] < invalido) break;
            if(c[i] > cuello) { sig = i; break; }
         }
         if(sig < 0) continue;
         Pat P;
         P.tipo = tipo; P.toques = toques; P.variante = variante; P.cuello = cuello; P.sig = sig;
         for(int q = 0; q < 6; q++) { P.idx[q] = -1; P.pr[q] = 0.0; }
         int ns = jj - (j1 - 1) + 1;
         for(int q = 0; q < ns && q < 6; q++) { P.idx[q] = pv[j1 - 1 + q].i; P.pr[q] = pv[j1 - 1 + q].p; }
         AddPat(res, P);
      }
   }
}

void Detectar(const double &high[], const double &low[], const double &close[],
              int total, int from, int last, Pat &res[])
{
   ArrayResize(res, 0);
   if(last - from < 30) return;
   double a[], hm[], lm[], cm[];
   ArrayResize(a, total); ArrayResize(hm, total); ArrayResize(lm, total); ArrayResize(cm, total);
   CalcATR(high, low, close, from, last, InpATR, a);
   for(int i = from; i <= last; i++) { hm[i] = -low[i]; lm[i] = -high[i]; cm[i] = -close[i]; }
   Piv pv[];
   ZigZag(high, low, a, from, last, InpKATR, pv);
   BuscarW(high, low, close, a, pv, last, 1, res);
   int nW = ArraySize(res);
   Piv pvm[];
   ZigZag(hm, lm, a, from, last, InpKATR, pvm);
   BuscarW(hm, lm, cm, a, pvm, last, -1, res);
   for(int k = nW; k < ArraySize(res); k++)
   {
      res[k].cuello = -res[k].cuello;
      for(int q = 0; q < 6; q++) res[k].pr[q] = -res[k].pr[q];
   }
}

//+------------------------------------------------------------------+
//| Precios por segundo (para confirmar continuidad)                 |
//+------------------------------------------------------------------+
void Muestrear()
{
   for(int si = 0; si < ArraySize(g_sims); si++)
   {
      double bid = SymbolInfoDouble(g_sims[si], SYMBOL_BID);
      if(bid <= 0) continue;
      g_px[si * BUF + g_pxPos[si]] = bid;
      g_pxPos[si] = (g_pxPos[si] + 1) % BUF;
      if(g_pxCnt[si] < BUF) g_pxCnt[si]++;
   }
}

// precio de hace k segundos (k = 0: el ultimo)
double Precio(int si, int k)
{
   int idx = (g_pxPos[si] - 1 - k + 2 * BUF) % BUF;
   return g_px[si * BUF + idx];
}

// M: precio debajo del cuello y bajando sin rebotes en los ultimos X seg. W: al reves.
bool Confirmado(int si, int tipo, double cuello)
{
   if(g_pxCnt[si] < 1) return false;
   double ahora = Precio(si, 0);
   if(tipo == -1 && !(ahora < cuello)) return false;
   if(tipo ==  1 && !(ahora > cuello)) return false;
   if(InpConfirmSeg <= 0) return true;
   if(g_pxCnt[si] <= InpConfirmSeg) return false;
   double ini = Precio(si, InpConfirmSeg);
   double tolp = 10 * SymbolInfoDouble(g_sims[si], SYMBOL_POINT);
   for(int k = 0; k <= InpConfirmSeg; k++)
   {
      double v = Precio(si, k);
      if(tipo == -1 && v > ini + tolp) return false;    // hubo subida en contra
      if(tipo ==  1 && v < ini - tolp) return false;    // hubo bajada en contra
   }
   return (tipo == -1) ? (ahora < ini) : (ahora > ini);
}

//+------------------------------------------------------------------+
//| Reglas y limites                                                 |
//+------------------------------------------------------------------+
bool EsNuestro(long magic) { return (magic >= InpMagic && magic < InpMagic + ArraySize(TFN_ALL)); }

void ResumenHoy(double &pl, int &ops)
{
   pl = 0; ops = 0;
   datetime local    = TimeLocal();
   datetime iniLocal = (datetime)((long)local - ((long)local % 86400));
   long     desfase  = (long)TimeCurrent() - (long)local;
   datetime iniServ  = (datetime)((long)iniLocal + desfase);
   if(!HistorySelect(iniServ, TimeCurrent() + 60)) return;
   int n = HistoryDealsTotal();
   for(int i = 0; i < n; i++)
   {
      ulong tk = HistoryDealGetTicket(i);
      if(tk == 0) continue;
      if(!EsNuestro(HistoryDealGetInteger(tk, DEAL_MAGIC))) continue;
      if(HistoryDealGetInteger(tk, DEAL_ENTRY) == DEAL_ENTRY_IN) ops++;
      pl += HistoryDealGetDouble(tk, DEAL_PROFIT) + HistoryDealGetDouble(tk, DEAL_SWAP)
          + HistoryDealGetDouble(tk, DEAL_COMMISSION);
   }
}

bool EnHorario()
{
   int ini = MinutosDe(InpHoraInicio), fin = MinutosDe(InpHoraFin);
   if(ini < 0 || fin < 0) return true;
   MqlDateTime dt; TimeToStruct(TimeLocal(), dt);
   int ahora = dt.hour * 60 + dt.min;
   if(ini <= fin) return (ahora >= ini && ahora <= fin);
   return (ahora >= ini || ahora <= fin);
}

int ContarPosiciones(string sym, long magic)   // sym "" = todos; magic -1 = cualquiera nuestro
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      long mg = PositionGetInteger(POSITION_MAGIC);
      if(!EsNuestro(mg)) continue;
      if(sym != "" && PositionGetString(POSITION_SYMBOL) != sym) continue;
      if(magic >= 0 && mg != magic) continue;
      n++;
   }
   return n;
}

bool HayCualquierPosicion(string sym)
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk != 0 && PositionGetString(POSITION_SYMBOL) == sym) return true;
   }
   return false;
}

// motivos generales (todo el robot)
string MotivoGeneral()
{
   if(g_bloqueoReal) return "cuenta REAL bloqueada";
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
      return "trading algoritmico desactivado en MT5";
   if(!EnHorario()) return "fuera de horario";
   double pl; int ops;
   ResumenHoy(pl, ops);
   if(InpMetaDiaria > 0 && pl >= InpMetaDiaria) return "meta diaria alcanzada";
   if(InpPerdidaMax > 0 && pl <= -InpPerdidaMax) return "perdida maxima diaria alcanzada";
   if(InpMaxOpsDia > 0 && ops >= InpMaxOpsDia) return "maximo de operaciones del dia";
   if(InpMaxPosiciones > 0 && ContarPosiciones("", -1) >= InpMaxPosiciones) return "maximo de posiciones abiertas";
   return "";
}

// motivos de un mercado/temporalidad concretos
string MotivoCelda(string sym, int tfi)
{
   if(InpMaxPorMercado > 0 && ContarPosiciones(sym, -1) >= InpMaxPorMercado) return "maximo por mercado";
   if(InpUnaPorCelda && ContarPosiciones(sym, InpMagic + tfi) > 0) return "ya hay una abierta en esa temporalidad";
   bool netting = (AccountInfoInteger(ACCOUNT_MARGIN_MODE) != ACCOUNT_MARGIN_MODE_RETAIL_HEDGING);
   if(netting && HayCualquierPosicion(sym)) return "cuenta netting con posicion abierta";
   return "";
}

//+------------------------------------------------------------------+
//| Ordenes                                                          |
//+------------------------------------------------------------------+
double LoteValido(string sym)
{
   double mn = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double st = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double v = InpLote;
   if(st > 0) v = MathFloor(v / st + 1e-9) * st;
   v = MathMax(mn, MathMin(mx, v));
   return NormalizeDouble(v, 2);
}

bool Abrir(string sym, int tfi, int tipo)
{
   string nombre = (tipo == 1 ? "W compra " : "M venta ") + sym + " " + TFN_ALL[tfi];
   long magic = InpMagic + tfi;
   trade.SetExpertMagicNumber(magic);
   trade.SetTypeFillingBySymbol(sym);
   trade.SetDeviationInPoints(1000);
   double lote = LoteValido(sym);
   double pt   = SymbolInfoDouble(sym, SYMBOL_POINT);
   int    dg   = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double sl   = 0;
   string cm   = "WM " + TFN_ALL[tfi] + (tipo == 1 ? " W" : " M") + " N" + IntegerToString(InpVelasSalida);
   bool ok;
   if(tipo == 1)
   {
      if(InpSLEmergencia > 0) sl = NormalizeDouble(SymbolInfoDouble(sym, SYMBOL_ASK) - InpSLEmergencia * pt, dg);
      ok = trade.Buy(lote, sym, 0, sl, 0, cm);
   }
   else
   {
      if(InpSLEmergencia > 0) sl = NormalizeDouble(SymbolInfoDouble(sym, SYMBOL_BID) + InpSLEmergencia * pt, dg);
      ok = trade.Sell(lote, sym, 0, sl, 0, cm);
   }
   if(ok && (trade.ResultRetcode() == TRADE_RETCODE_DONE || trade.ResultRetcode() == TRADE_RETCODE_PLACED))
   {
      g_ultimo = nombre + " @ " + DoubleToString(trade.ResultPrice(), dg) + "  " + TimeToString(TimeCurrent(), TIME_MINUTES);
      g_cambio = true;
      Avisar("ABIERTA " + nombre + " lote " + DoubleToString(lote, 2) + " | cierra en " +
             IntegerToString(InpVelasSalida) + " velas");
      return true;
   }
   Print("Patron_WM_EA: error al abrir ", nombre, ": ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   return false;
}

void CerrarVencidas()
{
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      long magic = PositionGetInteger(POSITION_MAGIC);
      if(!EsNuestro(magic)) continue;
      int tfi = (int)(magic - InpMagic);
      long per = PeriodSeconds(TFV_ALL[tfi]);
      datetime t0 = (datetime)PositionGetInteger(POSITION_TIME);
      datetime salida = (datetime)((long)t0 + (long)InpVelasSalida * per);   // N velas desde la entrada
      if(TimeCurrent() < salida) continue;
      string sym = PositionGetString(POSITION_SYMBOL);
      double pl  = PositionGetDouble(POSITION_PROFIT) + PositionGetDouble(POSITION_SWAP);
      trade.SetExpertMagicNumber(magic);
      trade.SetTypeFillingBySymbol(sym);
      if(trade.PositionClose(tk))
         Avisar("CERRADA " + sym + " " + TFN_ALL[tfi] + " tras " + IntegerToString(InpVelasSalida) +
                " velas | resultado aprox. " + DoubleToString(pl, 2) + " $");
      else
         Print("Patron_WM_EA: error al cerrar ", tk, ": ", trade.ResultRetcode(), " ", trade.ResultRetcodeDescription());
   }
}

//+------------------------------------------------------------------+
//| Senales pendientes                                               |
//+------------------------------------------------------------------+
void QuitarPend(int k)
{
   int n = ArraySize(g_pend);
   for(int i = k; i < n - 1; i++) g_pend[i] = g_pend[i + 1];
   ArrayResize(g_pend, n - 1);
   g_cambio = true;
}

void AgregarPend(int si, int tfi, const Pat &P, datetime t0)
{
   if(P.tipo == 1 && !InpOperarW) return;
   if(P.tipo == -1 && !InpOperarM) return;
   int nT = (P.toques == 3) ? 6 : 4;
   double ext = (P.tipo == 1) ? DBL_MAX : -DBL_MAX;
   for(int q = 1; q < nT; q += 2)                     // pisos (W) o techos (M)
      ext = (P.tipo == 1) ? MathMin(ext, P.pr[q]) : MathMax(ext, P.pr[q]);
   int n = ArraySize(g_pend);
   ArrayResize(g_pend, n + 1);
   g_pend[n].si = si; g_pend[n].tfi = tfi; g_pend[n].tipo = P.tipo;
   g_pend[n].cuello = P.cuello; g_pend[n].extremo = ext;
   g_pend[n].expira = (datetime)((long)t0 + (long)InpExpiraVelas * PeriodSeconds(TFV_ALL[tfi]));
   g_pend[n].motivo = "";
   g_cambio = true;
   Print("Patron_WM_EA: senal ", (P.tipo == 1 ? "W " : "M "), g_sims[si], " ", TFN_ALL[tfi],
         " | cuello ", DoubleToString(P.cuello, (int)SymbolInfoInteger(g_sims[si], SYMBOL_DIGITS)),
         " | esperando confirmacion");
}

void RevisarPendientes()
{
   string general = MotivoGeneral();
   for(int k = ArraySize(g_pend) - 1; k >= 0; k--)
   {
      int si = g_pend[k].si;
      string sym = g_sims[si];
      string nombre = (g_pend[k].tipo == 1 ? "W " : "M ") + sym + " " + TFN_ALL[g_pend[k].tfi];
      double bid = SymbolInfoDouble(sym, SYMBOL_BID);
      if(TimeCurrent() > g_pend[k].expira)
      { Print("Patron_WM_EA: senal ", nombre, " descartada: paso el tiempo sin confirmar"); QuitarPend(k); continue; }
      if((g_pend[k].tipo == -1 && bid > g_pend[k].extremo) || (g_pend[k].tipo == 1 && bid < g_pend[k].extremo))
      { Print("Patron_WM_EA: senal ", nombre, " descartada: rompio el ", (g_pend[k].tipo == -1 ? "techo" : "piso")); QuitarPend(k); continue; }
      if(!Confirmado(si, g_pend[k].tipo, g_pend[k].cuello)) continue;
      string motivo = (general != "") ? general : MotivoCelda(sym, g_pend[k].tfi);
      if(motivo != "")
      {
         if(motivo != g_pend[k].motivo) Print("Patron_WM_EA: senal ", nombre, " confirmada pero en espera: ", motivo);
         g_pend[k].motivo = motivo;
         continue;
      }
      if(Abrir(sym, g_pend[k].tfi, g_pend[k].tipo)) QuitarPend(k);   // una sola entrada por senal
   }
}

//+------------------------------------------------------------------+
//| Escaneo                                                          |
//+------------------------------------------------------------------+
void EscanearCelda(int c)
{
   string sym = g_cel[c].sym;
   ENUM_TIMEFRAMES tf = TFV_ALL[g_cel[c].tfi];
   datetime t0 = iTime(sym, tf, 0);
   if(t0 == 0 || t0 == g_cel[c].ultBarra) return;
   MqlRates r[];
   int n = CopyRates(sym, tf, 0, InpBarrasEsc, r);
   if(n < 100) return;
   double hh[], ll[], cc[];
   ArrayResize(hh, n); ArrayResize(ll, n); ArrayResize(cc, n);
   for(int i = 0; i < n; i++) { hh[i] = r[i].high; ll[i] = r[i].low; cc[i] = r[i].close; }
   int last = n - 2;
   Pat res[];
   Detectar(hh, ll, cc, n, 0, last, res);
   if(!g_cel[c].primera)
      for(int q = 0; q < ArraySize(res); q++)
         if(res[q].sig == last)
            AgregarPend(g_cel[c].si, g_cel[c].tfi, res[q], t0);
   g_cel[c].primera = false;
   g_cel[c].ultBarra = t0;
}

//+------------------------------------------------------------------+
//| Estado guardado en archivo (MQL5\Files): senales en espera y     |
//| ultima entrada. El resultado del dia y las operaciones abiertas  |
//| se leen siempre del historial de MT5, asi que tambien continuan. |
//+------------------------------------------------------------------+
void GuardarEstado()
{
   int h = FileOpen(ARCH_ESTADO, FILE_WRITE | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   FileWriteString(h, "ULTIMO|" + g_ultimo + "\n");
   for(int k = 0; k < ArraySize(g_pend); k++)
      FileWriteString(h, StringFormat("PEND|%s|%d|%d|%.5f|%.5f|%I64d\n", g_sims[g_pend[k].si], g_pend[k].tfi,
                      g_pend[k].tipo, g_pend[k].cuello, g_pend[k].extremo, (long)g_pend[k].expira));
   FileClose(h);
   g_cambio = false;
}

void CargarEstado()
{
   if(!FileIsExist(ARCH_ESTADO)) return;
   int h = FileOpen(ARCH_ESTADO, FILE_READ | FILE_TXT | FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   int recuperadas = 0;
   while(!FileIsEnding(h))
   {
      string lin = FileReadString(h);
      string p[];
      int n = StringSplit(lin, '|', p);
      if(n >= 2 && p[0] == "ULTIMO") { g_ultimo = p[1]; continue; }
      if(n != 7 || p[0] != "PEND") continue;
      int si = -1;
      for(int s = 0; s < ArraySize(g_sims); s++) if(g_sims[s] == p[1]) si = s;
      datetime exp = (datetime)StringToInteger(p[6]);
      if(si < 0 || exp <= TimeCurrent()) continue;            // mercado quitado o senal ya vencida
      int k = ArraySize(g_pend); ArrayResize(g_pend, k + 1);
      g_pend[k].si = si; g_pend[k].tfi = (int)StringToInteger(p[2]); g_pend[k].tipo = (int)StringToInteger(p[3]);
      g_pend[k].cuello = StringToDouble(p[4]); g_pend[k].extremo = StringToDouble(p[5]);
      g_pend[k].expira = exp; g_pend[k].motivo = "";
      recuperadas++;
   }
   FileClose(h);
   if(recuperadas > 0) Print("Patron_WM_EA: recuperadas ", recuperadas, " senales en espera del reinicio anterior");
}

//+------------------------------------------------------------------+
//| Panel propio (esquina a eleccion). Solo se redibuja lo que       |
//| cambia, para que no parpadee ni choque con otros indicadores.    |
//+------------------------------------------------------------------+
ENUM_BASE_CORNER EsquinaMT5()
{
   if(InpPanelEsquina == SUP_IZQ) return CORNER_LEFT_UPPER;
   if(InpPanelEsquina == SUP_DER) return CORNER_RIGHT_UPPER;
   if(InpPanelEsquina == INF_IZQ) return CORNER_LEFT_LOWER;
   return CORNER_RIGHT_LOWER;
}
bool EsDerecha() { return (InpPanelEsquina == SUP_DER || InpPanelEsquina == INF_DER); }
bool EsAbajo()   { return (InpPanelEsquina == INF_IZQ || InpPanelEsquina == INF_DER); }
int  AltoLinea() { return (int)MathRound(InpPanelLetra * 1.8); }

// ajusta una propiedad solo si cambio (evita redibujar y parpadear)
bool SetI(string nm, ENUM_OBJECT_PROPERTY_INTEGER pr, long v)
{
   if(ObjectGetInteger(0, nm, pr) == v) return false;
   ObjectSetInteger(0, nm, pr, v);
   return true;
}

bool PanelLinea(int i, int total, string txt, color col)
{
   string nm = PFXE + "l" + IntegerToString(i);
   int alto = AltoLinea(), hbox = total * alto + 10;
   if(ObjectFind(0, nm) < 0)
   {
      ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_LEFT_UPPER);
      ObjectSetString(0, nm, OBJPROP_FONT, "Consolas");
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
   // posicion del texto dentro del recuadro, segun la esquina elegida
   long x = EsDerecha() ? InpPanelMargenX + InpPanelAncho - 8 : InpPanelMargenX + 8;
   long y = EsAbajo()   ? InpPanelMargenY + hbox - 5 - i * alto : InpPanelMargenY + 5 + i * alto;
   bool cambio = false;
   if(SetI(nm, OBJPROP_CORNER, EsquinaMT5()))   cambio = true;
   if(SetI(nm, OBJPROP_FONTSIZE, InpPanelLetra)) cambio = true;
   if(SetI(nm, OBJPROP_XDISTANCE, x))           cambio = true;
   if(SetI(nm, OBJPROP_YDISTANCE, y))           cambio = true;
   if(SetI(nm, OBJPROP_COLOR, col))             cambio = true;
   if(ObjectGetString(0, nm, OBJPROP_TEXT) != txt) { ObjectSetString(0, nm, OBJPROP_TEXT, txt); cambio = true; }
   return cambio;
}

void Estado()
{
   double pl; int ops;
   ResumenHoy(pl, ops);
   string motivo = MotivoGeneral();
   bool real = (AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL);
   string tfs = "";
   for(int k = 0; k < ArraySize(g_tfi); k++) tfs += (k > 0 ? "," : "") + TFN_ALL[g_tfi[k]];

   string L[]; color C[];
   ArrayResize(L, 0); ArrayResize(C, 0);
   #define ADD(t, c) { int _n = ArraySize(L); ArrayResize(L, _n + 1); ArrayResize(C, _n + 1); L[_n] = t; C[_n] = c; }
   ADD("PATRON W/M  -  Asesor experto v2.1", clrWhite);
   ADD("Cuenta: " + (real ? "REAL  (opera con dinero real)" : "DEMO"), real ? clrOrangeRed : clrSilver);
   ADD("Estado: " + (motivo == "" ? "OPERANDO" : "EN PAUSA - " + motivo), motivo == "" ? clrLime : clrOrange);
   ADD("Temporalidades: " + tfs, clrSilver);
   ADD("Lote " + DoubleToString(InpLote, 2) + " | salida " + IntegerToString(InpVelasSalida) + " velas | confirmacion " +
       IntegerToString(InpConfirmSeg) + " s | max/mercado " + IntegerToString(InpMaxPorMercado), clrSilver);
   string metas = "";
   if(InpMetaDiaria > 0) metas += "  (meta " + DoubleToString(InpMetaDiaria, 0) + " $";
   if(InpPerdidaMax > 0) metas += (metas == "" ? "  (" : " / ") + "limite -" + DoubleToString(InpPerdidaMax, 0) + " $";
   if(metas != "") metas += ")";
   ADD("Hoy: " + IntegerToString(ops) + " operaciones | resultado cerrado " + DoubleToString(pl, 2) + " $" + metas,
       pl > 0 ? clrLime : (pl < 0 ? clrTomato : clrSilver));
   ADD("Abiertas ahora: " + IntegerToString(ContarPosiciones("", -1)), clrSilver);
   ADD("Ultima entrada: " + g_ultimo, clrSilver);
   ADD("Senales esperando confirmacion: " + IntegerToString(ArraySize(g_pend)), clrSilver);
   for(int k = 0; k < ArraySize(g_pend) && k < 5; k++)
      ADD("   " + (g_pend[k].tipo == 1 ? "W " : "M ") + g_sims[g_pend[k].si] + " " + TFN_ALL[g_pend[k].tfi], clrSilver);

   int n = ArraySize(L);
   bool cambio = false;
   if(!InpPanel) { ObjectsDeleteAll(0, PFXE); return; }
   // fondo
   string bg = PFXE + "bg";
   if(ObjectFind(0, bg) < 0)
   {
      ObjectCreate(0, bg, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, bg, OBJPROP_BGCOLOR, C'18,18,18');
      ObjectSetInteger(0, bg, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, bg, OBJPROP_COLOR, C'70,70,70');
      ObjectSetInteger(0, bg, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, bg, OBJPROP_HIDDEN, true);
      cambio = true;
   }
   long hbg = n * AltoLinea() + 10;
   long xbg = EsDerecha() ? InpPanelMargenX + InpPanelAncho : InpPanelMargenX;
   long ybg = EsAbajo()   ? InpPanelMargenY + hbg : InpPanelMargenY;
   if(SetI(bg, OBJPROP_CORNER, EsquinaMT5())) cambio = true;
   if(SetI(bg, OBJPROP_XDISTANCE, xbg))       cambio = true;
   if(SetI(bg, OBJPROP_YDISTANCE, ybg))       cambio = true;
   if(SetI(bg, OBJPROP_XSIZE, InpPanelAncho)) cambio = true;
   if(SetI(bg, OBJPROP_YSIZE, hbg))           cambio = true;
   for(int i = 0; i < n; i++)
      if(PanelLinea(i, n, L[i], C[i])) cambio = true;
   // borrar lineas sobrantes (cuando bajan las senales en espera)
   for(int i = n; i < n + 8; i++)
   {
      string nm = PFXE + "l" + IntegerToString(i);
      if(ObjectFind(0, nm) >= 0) { ObjectDelete(0, nm); cambio = true; }
   }
   if(cambio) ChartRedraw();
}

void OnTimer()
{
   Muestrear();
   CerrarVencidas();
   for(int c = 0; c < ArraySize(g_cel); c++)
      EscanearCelda(c);
   RevisarPendientes();
   if(g_cambio) GuardarEstado();
   Estado();
}
//+------------------------------------------------------------------+
