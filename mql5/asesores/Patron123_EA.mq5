//+------------------------------------------------------------------+
//|                                                Patron123_EA.mq5  |
//|  Proyecto oro bitcoin - Raul                                     |
//|  Asesor experto con la logica del indicador Patron 123:          |
//|  lineas tipo Joel, toque 3-4 (vela de rechazo) a favor de la     |
//|  pierna H1. SL = TP = ATR(14) x 2, sin decimales.                |
//|                                                                  |
//|  SEGURIDAD: por defecto NO opera en cuenta REAL                  |
//|  ("Permitir operar en cuenta REAL" = false). Usar en DEMO.       |
//|  La regla no mostro ventaja en las pruebas.                      |
//+------------------------------------------------------------------+
#property copyright   "Proyecto oro bitcoin - Raul"
#property version     "1.00"
#property description "Patron 123 EA: entra en la senal del Patron 123 (toque 3-4) a favor de la pierna H1."
#property description "SL = TP = ATR(14) x 2 sin decimales. Por defecto NO opera en cuenta real."
#include <Trade\Trade.mqh>

enum ENUM_CONF
{
   CONF_TOCAR   = 0, // Al tocar la linea (sin esperar el cierre)
   CONF_RECHAZO = 1  // Vela de rechazo (al cierre de la vela)
};
enum ENUM_LISTA
{
   LISTA_ESCRITA  = 0, // Input_Symbols (los que escribo abajo)
   LISTA_MERCADO  = 1, // MarketWatch_Symbols (Observacion del mercado)
   LISTA_TODOS    = 2  // All_General_List_Symbols (todos los del broker)
};

input group "SEGURIDAD"
input bool      InpPermitirReal = false;      // Permitir operar en cuenta REAL

input group "Mercados y temporalidades"
input ENUM_LISTA InpLista      = LISTA_ESCRITA;                      // Which Symbol List
input string    InpSimbolos    = "TrendX 600,SwitchX 600,BreakX 600"; // Mercados (separados por coma)
input int       InpMaxMercados = 30;                                 // Max. mercados (listas automaticas)
input string    InpTFs         = "M1,M2,M3,M5,M6";                   // Temporalidades (o TODAS)

input group "Linea (igual que el indicador)"
input int       InpATR        = 14;           // Periodo ATR (lineas)
input int       InpK          = 2;            // Velas a cada lado del punto de reaccion
input double    InpProfATR    = 1.0;          // Retroceso minimo entre punto 1 y 2 (en ATR)
input double    InpTolATR     = 0.1;          // Margen para contar un toque (en ATR)
input int       InpVida       = 60;           // Velas que la linea sigue viva tras validarse
input int       InpToqueMin   = 3;            // Operar desde el toque...
input int       InpToqueMax   = 4;            // ...hasta el toque
input ENUM_CONF InpConf       = CONF_RECHAZO; // Confirmacion del toque
input int       InpBarrasEsc  = 800;          // Velas a analizar por mercado/TF

input group "Pierna"
input bool      InpFiltroPierna = true;       // Solo operar a favor de la pierna
input string    InpTFPierna     = "H1";       // Temporalidad de la pierna (H1 manda)

input group "Gestion"
input double    InpLote         = 0;          // Lote (0 = lote minimo del mercado)
input double    InpMultATR      = 2.0;        // SL y TP = ATR(14) x este numero
input bool      InpSinDecimales = true;       // Quitar decimales al SL/TP (12,04 -> 12)
input int       InpMaxPorMercado= 5;          // Max. operaciones abiertas por mercado
input bool      InpUnaPorTF     = true;       // Solo 1 operacion abierta por mercado y temporalidad
input long      InpMagic        = 123123;     // Numero magico

input group "Avisos"
input bool      InpAlerta       = false;      // Ventana de alerta al abrir
input bool      InpCelular      = true;       // Notificacion al celular al abrir

struct Lin
{
   int    dir;        // -1 venta (linea bajista), +1 compra (linea alcista)
   int    a, b, val;  // punto 1, punto 2, vela de validacion
   double ya, m;      // precio en a y pendiente (en precios de trabajo)
   int    nt;         // toques registrados
   int    ti[4];      // vela de cada toque (3,4,5,6)
   int    tn[4];      // numero del toque
   bool   tr[4];      // hubo vela de rechazo
   int    fin;        // ultima vela de vida de la linea
   bool   viva;       // sigue viva en la ultima vela cerrada
   bool   lista;      // esperando el siguiente toque (hay piso/techo desde el ultimo)
   int    prox;       // numero del proximo toque
};

#define SIN_DATOS 99
string          TFN_ALL[] = {"M1","M2","M3","M4","M5","M6","M10","M12","M15","M20","M30",
                             "H1","H2","H3","H4","H6","H8","H12","D1","W1","MN1"};
ENUM_TIMEFRAMES TFV_ALL[] = {PERIOD_M1,PERIOD_M2,PERIOD_M3,PERIOD_M4,PERIOD_M5,PERIOD_M6,
                             PERIOD_M10,PERIOD_M12,PERIOD_M15,PERIOD_M20,PERIOD_M30,
                             PERIOD_H1,PERIOD_H2,PERIOD_H3,PERIOD_H4,PERIOD_H6,PERIOD_H8,
                             PERIOD_H12,PERIOD_D1,PERIOD_W1,PERIOD_MN1};

int BuscarTF(string s)
{
   StringToUpper(s);
   for(int i = 0; i < ArraySize(TFN_ALL); i++)
      if(TFN_ALL[i] == s) return i;
   return -1;
}

string NombreTFde(ENUM_TIMEFRAMES tf)
{
   for(int i = 0; i < ArraySize(TFV_ALL); i++)
      if(TFV_ALL[i] == tf) return TFN_ALL[i];
   return "?";
}
// ATR de la vela ANTERIOR (sin mirar la vela actual)
void ATRprev(const double &h[], const double &l[], const double &c[], int n, double &ap[])
{
   ArrayResize(ap, n);
   double a = h[0] - l[0];
   ap[0] = a;
   for(int i = 1; i < n; i++)
   {
      ap[i] = a;
      double tr = MathMax(h[i] - l[i], MathMax(MathAbs(h[i] - c[i-1]), MathAbs(l[i] - c[i-1])));
      a = a + (tr - a) / InpATR;
   }
}

// puntos de reaccion confirmados hasta 'last' (un punto en i se conoce en i+K)
void Pivotes(const double &h[], const double &l[], int n, int last, bool &ph[], bool &pl[])
{
   ArrayResize(ph, n); ArrayResize(pl, n);
   for(int i = 0; i < n; i++) { ph[i] = false; pl[i] = false; }
   for(int i = InpK; i <= last - InpK; i++)
   {
      bool okh = true, okl = true;
      for(int j = i - InpK; j < i; j++) { if(h[j] >= h[i]) okh = false; if(l[j] <= l[i]) okl = false; }
      for(int j = i + 1; j <= i + InpK; j++) { if(h[j] > h[i]) okh = false; if(l[j] < l[i]) okl = false; }
      ph[i] = okh; pl[i] = okl;
   }
}

bool Rechazo(double o, double h, double c, double L)
{
   // para venta (en precios de trabajo): cierra por debajo de la linea y es bajista o deja mecha superior >= cuerpo
   if(c >= L) return false;
   double cuerpo = MathAbs(c - o);
   double mecha  = h - MathMax(o, c);
   return (c < o) || (mecha >= cuerpo);
}

// Busca lineas bajistas en precios de trabajo (para compras se pasan espejados)
void Buscar(const double &o[], const double &h[], const double &l[], const double &c[], const double &ap[],
            int n, int from, int last, int dir, Lin &res[])
{
   bool ph[], pl[];
   Pivotes(h, l, n, last, ph, pl);
   int idx[]; ArrayResize(idx, 0);
   for(int i = from; i <= last; i++)
      if(ph[i]) { int q = ArraySize(idx); ArrayResize(idx, q + 1); idx[q] = i; }
   for(int q = 0; q + 1 < ArraySize(idx); q++)
   {
      int a = idx[q], b = idx[q+1];
      if(b - a < 3 || !(h[b] < h[a])) continue;
      double piso = l[a];
      for(int j = a; j <= b; j++) if(l[j] < piso) piso = l[j];
      if(h[b] - piso < InpProfATR * ap[b] || h[a] - piso < 1.5 * InpProfATR * ap[b]) continue;
      double m = (h[b] - h[a]) / (b - a);
      int start = b + InpK, val = -1;
      for(int i = start; i <= MathMin(start + 199, last); i++)
      {
         double L = h[a] + m * (i - a);
         if(c[i] > L + InpTolATR * ap[i] || h[i] > h[a]) break;
         if(c[i] < piso) { val = i; break; }
      }
      if(val < 0) continue;
      Lin X;
      X.dir = dir; X.a = a; X.b = b; X.val = val; X.ya = h[a]; X.m = m; X.nt = 0;
      X.viva = false; X.lista = false; X.prox = 3; X.fin = val;
      for(int z = 0; z < 4; z++) { X.ti[z] = -1; X.tn[z] = 0; X.tr[z] = false; }
      int num = 3; bool hayPiso = true; int ult = val; bool corto = false;
      int fin = MathMin(val + InpVida - 1, last);
      for(int i = val + 1; i <= fin; i++)
      {
         double L = h[a] + m * (i - a);
         if(i - InpK > ult && pl[i - InpK]) hayPiso = true;
         if(h[i] >= L - InpTolATR * ap[i] && hayPiso)
         {
            if(X.nt < 4) { X.ti[X.nt] = i; X.tn[X.nt] = num; X.tr[X.nt] = Rechazo(o[i], h[i], c[i], L); X.nt++; }
            ult = i; hayPiso = false; num++;
            if(num > 6) { X.fin = i; corto = true; break; }
         }
         X.fin = i;
         if(c[i] > L + InpTolATR * ap[i]) { corto = true; break; }
      }
      if(X.nt == 0) X.fin = MathMax(X.fin, val);
      // sigue viva en la ultima vela cerrada?
      X.viva  = (!corto && val + InpVida - 1 > last);
      // ultima vela cerrada: puede haberse formado un piso que habilita el siguiente toque
      if(X.viva && last - InpK > ult && last - InpK >= 0 && pl[last - InpK]) hayPiso = true;
      X.lista = X.viva && hayPiso && num <= InpToqueMax;
      X.prox  = num;
      int r = ArraySize(res); ArrayResize(res, r + 1); res[r] = X;
   }
}

// Detecta lineas de venta y de compra. Arrays en orden normal (0 = vela mas antigua).
void Detectar(const double &open[], const double &high[], const double &low[], const double &close[],
              int n, int from, int last, Lin &res[])
{
   ArrayResize(res, 0);
   if(last - from < 30) return;
   double ap[];
   ATRprev(high, low, close, n, ap);
   Buscar(open, high, low, close, ap, n, from, last, -1, res);
   double om[], hm[], lm[], cm[];
   ArrayResize(om, n); ArrayResize(hm, n); ArrayResize(lm, n); ArrayResize(cm, n);
   for(int i = 0; i < n; i++) { om[i] = -open[i]; hm[i] = -low[i]; lm[i] = -high[i]; cm[i] = -close[i]; }
   Buscar(om, hm, lm, cm, ap, n, from, last, 1, res);
}

// precio real de la linea en la vela i
double PrecioLinea(const Lin &X, double i)
{
   double p = X.ya + X.m * (i - X.a);
   return (X.dir == -1) ? p : -p;
}

// nivel de toque (real) en la vela i: la linea menos/mas el margen
double NivelToque(const Lin &X, int i, const double &ap[])
{
   double p = X.ya + X.m * (i - X.a) - InpTolATR * ap[MathMax(i - 1, 0)];
   return (X.dir == -1) ? p : -p;
}

// Pierna: +1 alcista, -1 bajista, 0 sin definir (estado a la ultima vela cerrada)
int Pierna(string sym, ENUM_TIMEFRAMES tf)
{
   MqlRates r[];
   int n = CopyRates(sym, tf, 0, 400, r);
   if(n < 50) return SIN_DATOS;
   double h[], l[], c[];
   ArrayResize(h, n); ArrayResize(l, n); ArrayResize(c, n);
   for(int i = 0; i < n; i++) { h[i] = r[i].high; l[i] = r[i].low; c[i] = r[i].close; }
   int last = n - 2;
   bool ph[], pl[];
   Pivotes(h, l, n, last, ph, pl);
   double uh = EMPTY_VALUE, ul = EMPTY_VALUE; int s = 0;
   for(int i = 0; i <= last; i++)
   {
      if(i - InpK >= 0)
      {
         if(ph[i - InpK]) uh = h[i - InpK];
         if(pl[i - InpK]) ul = l[i - InpK];
      }
      if(uh != EMPTY_VALUE && c[i] > uh)      { s = 1;  uh = EMPTY_VALUE; }
      else if(ul != EMPTY_VALUE && c[i] < ul) { s = -1; ul = EMPTY_VALUE; }
   }
   return s;
}

string TextoPierna(int s) { return s == 1 ? "ALCISTA" : (s == -1 ? "BAJISTA" : "sin definir"); }
bool ToqueEsSenal(const Lin &X, int z)
{
   if(X.tn[z] < InpToqueMin || X.tn[z] > InpToqueMax) return false;
   if(InpConf == CONF_RECHAZO && !X.tr[z]) return false;
   return true;
}

struct Celda { string sym; ENUM_TIMEFRAMES tf; datetime ultBarra; bool primera; int hATR;
               bool espera; int espDir; int espNum; double nivel; datetime velaToque; };

CTrade          g_trade;
string          g_sims[];
ENUM_TIMEFRAMES g_tfs[];
string          g_tfn[];
Celda           g_cel[];
int             g_nS = 0, g_nT = 0;
bool            g_puedeOperar = false;
string          g_motivo = "";

ENUM_TIMEFRAMES TFPierna(ENUM_TIMEFRAMES tf)
{
   string t = InpTFPierna; StringToUpper(t); StringTrimLeft(t); StringTrimRight(t);
   int k = BuscarTF(t);
   return (k >= 0) ? TFV_ALL[k] : PERIOD_H1;
}

//+------------------------------------------------------------------+
int OnInit()
{
   // --- seguridad: cuenta real
   long modo = AccountInfoInteger(ACCOUNT_TRADE_MODE);
   g_puedeOperar = true;
   if(modo == ACCOUNT_TRADE_MODE_REAL && !InpPermitirReal)
   {
      g_puedeOperar = false;
      g_motivo = "CUENTA REAL detectada y 'Permitir operar en cuenta REAL' = false: el EA NO abre operaciones.";
      Print("Patron123_EA: ", g_motivo);
      Alert("Patron123_EA: ", g_motivo);
   }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(50);

   // --- mercados
   ArrayResize(g_sims, 0);
   if(InpLista == LISTA_ESCRITA)
   {
      string partes[];
      int ns = StringSplit(InpSimbolos, ',', partes);
      for(int i = 0; i < ns; i++)
      {
         string s = partes[i]; StringTrimLeft(s); StringTrimRight(s);
         if(StringLen(s) == 0) continue;
         if(!SymbolSelect(s, true)) { Print("Patron123_EA: mercado no encontrado: ", s); continue; }
         int n = ArraySize(g_sims); ArrayResize(g_sims, n + 1); g_sims[n] = s;
      }
   }
   else
   {
      bool soloMercado = (InpLista == LISTA_MERCADO);
      int tot = SymbolsTotal(soloMercado);
      for(int i = 0; i < tot && ArraySize(g_sims) < InpMaxMercados; i++)
      {
         string s = SymbolName(i, soloMercado);
         if((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(s, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL) continue;
         if(!soloMercado) SymbolSelect(s, true);
         int n = ArraySize(g_sims); ArrayResize(g_sims, n + 1); g_sims[n] = s;
      }
   }
   g_nS = ArraySize(g_sims);

   // --- temporalidades
   ArrayResize(g_tfs, 0); ArrayResize(g_tfn, 0);
   string t = InpTFs; StringToUpper(t); StringTrimLeft(t); StringTrimRight(t);
   if(t == "TODAS")
   {
      ArrayResize(g_tfs, ArraySize(TFV_ALL)); ArrayResize(g_tfn, ArraySize(TFN_ALL));
      for(int i = 0; i < ArraySize(TFV_ALL); i++) { g_tfs[i] = TFV_ALL[i]; g_tfn[i] = TFN_ALL[i]; }
   }
   else
   {
      string pt[];
      int nt = StringSplit(t, ',', pt);
      for(int i = 0; i < nt; i++)
      {
         string s = pt[i]; StringTrimLeft(s); StringTrimRight(s);
         int k = BuscarTF(s);
         if(k < 0) { Print("Patron123_EA: temporalidad no reconocida: ", s); continue; }
         int n = ArraySize(g_tfs); ArrayResize(g_tfs, n + 1); ArrayResize(g_tfn, n + 1);
         g_tfs[n] = TFV_ALL[k]; g_tfn[n] = TFN_ALL[k];
      }
   }
   g_nT = ArraySize(g_tfs);

   ArrayResize(g_cel, g_nS * g_nT);
   for(int s = 0; s < g_nS; s++)
      for(int k = 0; k < g_nT; k++)
      {
         int c = s * g_nT + k;
         g_cel[c].sym = g_sims[s]; g_cel[c].tf = g_tfs[k];
         g_cel[c].ultBarra = 0; g_cel[c].primera = true; g_cel[c].espera = false;
         g_cel[c].espDir = 0; g_cel[c].espNum = 0; g_cel[c].nivel = 0; g_cel[c].velaToque = 0;
         g_cel[c].hATR = iATR(g_sims[s], g_tfs[k], 14);     // el mismo ATR(14) que ves en MT5
      }
   EventSetTimer(2);
   Print("Patron123_EA iniciado: ", g_nS, " mercados x ", g_nT, " temporalidades. Operar: ", g_puedeOperar);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   for(int c = 0; c < ArraySize(g_cel); c++) if(g_cel[c].hATR != INVALID_HANDLE) IndicatorRelease(g_cel[c].hATR);
   Comment("");
}

//+------------------------------------------------------------------+
//| Posiciones                                                       |
//+------------------------------------------------------------------+
string ComentarioTF(ENUM_TIMEFRAMES tf) { return "P123 " + NombreTFde(tf); }

int ContarPos(string sym, string coment)
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic) continue;
      if(PositionGetString(POSITION_SYMBOL) != sym) continue;
      if(coment != "" && PositionGetString(POSITION_COMMENT) != coment) continue;
      n++;
   }
   return n;
}

// distancia de SL/TP en precio: ATR(14) de la ultima vela cerrada x multiplicador, sin decimales
double DistanciaSLTP(int c)
{
   double a[];
   if(CopyBuffer(g_cel[c].hATR, 0, 1, 1, a) < 1) return 0;
   double d = a[0] * InpMultATR;
   if(InpSinDecimales && MathFloor(d) >= 1.0) d = MathFloor(d);   // 12,04 -> 12 ; 12,8 -> 12
   return d;
}

void Abrir(int c, int dir, int toque, int pierna)
{
   string sym = g_cel[c].sym;
   ENUM_TIMEFRAMES tf = g_cel[c].tf;
   string coment = ComentarioTF(tf);
   if(!g_puedeOperar) { Print("Patron123_EA: senal ", sym, " ", NombreTFde(tf), " NO operada: ", g_motivo); return; }
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED))
   { Print("Patron123_EA: Algo Trading desactivado, no se abre ", sym); return; }
   if(InpUnaPorTF && ContarPos(sym, coment) > 0) { Print("Patron123_EA: ya hay operacion en ", sym, " ", NombreTFde(tf)); return; }
   if(ContarPos(sym, "") >= InpMaxPorMercado) { Print("Patron123_EA: maximo de operaciones en ", sym); return; }

   double dist = DistanciaSLTP(c);
   if(dist <= 0) { Print("Patron123_EA: sin ATR en ", sym); return; }
   int dig = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(dist < minStop) dist = minStop;

   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), vstep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double lote = (InpLote <= 0) ? vmin : MathMax(vmin, MathFloor(InpLote / vstep) * vstep);

   g_trade.SetTypeFillingBySymbol(sym);
   bool ok;
   double precio, sl, tp;
   if(dir == 1)
   {
      precio = SymbolInfoDouble(sym, SYMBOL_ASK);
      sl = NormalizeDouble(precio - dist, dig); tp = NormalizeDouble(precio + dist, dig);
      ok = g_trade.Buy(lote, sym, 0, sl, tp, coment);
   }
   else
   {
      precio = SymbolInfoDouble(sym, SYMBOL_BID);
      sl = NormalizeDouble(precio + dist, dig); tp = NormalizeDouble(precio - dist, dig);
      ok = g_trade.Sell(lote, sym, 0, sl, tp, coment);
   }
   string msg = StringFormat("PATRON 123 EA: %s %s %s | toque %d | pierna %s %s | lote %.2f | SL/TP %s (%d puntos) | %s",
                             dir == 1 ? "COMPRA" : "VENTA", sym, NombreTFde(tf), toque,
                             NombreTFde(TFPierna(tf)), pierna == 1 ? "ALCISTA" : (pierna == -1 ? "BAJISTA" : "-"),
                             lote, DoubleToString(dist, dig), (int)MathRound(dist / pt),
                             ok ? "ABIERTA" : ("ERROR " + IntegerToString(g_trade.ResultRetcode()) + " " + g_trade.ResultRetcodeDescription()));
   Print(msg);
   if(InpAlerta) Alert(msg);
   if(InpCelular) SendNotification(msg);
}

//+------------------------------------------------------------------+
//| Revision de cada mercado / temporalidad                          |
//+------------------------------------------------------------------+
void Revisar(int c)
{
   string sym = g_cel[c].sym;
   ENUM_TIMEFRAMES tf = g_cel[c].tf;
   ENUM_TIMEFRAMES tfp = TFPierna(tf);
   datetime t0 = iTime(sym, tf, 0);
   if(t0 == 0) return;

   if(t0 != g_cel[c].ultBarra)
   {
      MqlRates r[];
      int n = CopyRates(sym, tf, 0, InpBarrasEsc, r);
      if(n < 100) return;                               // datos aun cargando: se reintenta
      int pierna = Pierna(sym, tfp);
      if(pierna == SIN_DATOS) return;
      double oo[], hh[], ll[], cc[];
      ArrayResize(oo, n); ArrayResize(hh, n); ArrayResize(ll, n); ArrayResize(cc, n);
      for(int i = 0; i < n; i++) { oo[i] = r[i].open; hh[i] = r[i].high; ll[i] = r[i].low; cc[i] = r[i].close; }
      int last = n - 2;
      Lin res[];
      Detectar(oo, hh, ll, cc, n, 0, last, res);
      double ap[]; ATRprev(hh, ll, cc, n, ap);

      g_cel[c].espera = false;
      for(int q = 0; q < ArraySize(res); q++)
      {
         if(InpFiltroPierna && res[q].dir != pierna) continue;
         if(res[q].lista && res[q].prox >= InpToqueMin && res[q].prox <= InpToqueMax)
         {
            double nv = NivelToque(res[q], n - 1, ap);
            if(!g_cel[c].espera || MathAbs(nv - cc[last]) < MathAbs(g_cel[c].nivel - cc[last]))
            { g_cel[c].espera = true; g_cel[c].espDir = res[q].dir; g_cel[c].espNum = res[q].prox; g_cel[c].nivel = nv; }
         }
         if(!g_cel[c].primera && InpConf == CONF_RECHAZO)
            for(int z = 0; z < res[q].nt; z++)
               if(res[q].ti[z] == last && ToqueEsSenal(res[q], z))
                  Abrir(c, res[q].dir, res[q].tn[z], pierna);
      }
      g_cel[c].primera = false;
      g_cel[c].ultBarra = t0;
   }

   if(InpConf == CONF_TOCAR && g_cel[c].espera && g_cel[c].velaToque != t0)
   {
      double hi = iHigh(sym, tf, 0), lo = iLow(sym, tf, 0);
      bool toca = (g_cel[c].espDir == -1) ? (hi >= g_cel[c].nivel) : (lo <= g_cel[c].nivel);
      if(toca)
      {
         g_cel[c].velaToque = t0;
         int pp = Pierna(sym, tfp);
         if(!InpFiltroPierna || pp == g_cel[c].espDir) Abrir(c, g_cel[c].espDir, g_cel[c].espNum, pp);
      }
   }
}

void OnTimer()
{
   for(int c = 0; c < ArraySize(g_cel); c++) Revisar(c);
   // resumen en el grafico
   string txt = "PATRON 123 EA  |  " + (g_puedeOperar ? "OPERANDO (" + (AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL ? "REAL" : "DEMO") + ")" : "SIN OPERAR: " + g_motivo) + "\n";
   txt += "SL = TP = ATR(14) x " + DoubleToString(InpMultATR, 1) + (InpSinDecimales ? " sin decimales" : "") +
          "  |  max " + IntegerToString(InpMaxPorMercado) + " por mercado\n";
   for(int s = 0; s < g_nS; s++)
   {
      int p = Pierna(g_sims[s], TFPierna(PERIOD_M1));
      txt += g_sims[s] + ":  pierna " + InpTFPierna + " " + (p == 1 ? "ALZA" : (p == -1 ? "BAJA" : "-")) +
             "  |  abiertas " + IntegerToString(ContarPos(g_sims[s], "")) + "\n";
   }
   Comment(txt);
}

void OnTick() { }
//+------------------------------------------------------------------+
