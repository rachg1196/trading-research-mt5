//+------------------------------------------------------------------+
//|                                              SMC_Ruptura_EA.mq5  |
//|  Proyecto oro bitcoin - Raul                                     |
//|  Opera la RUPTURA DE ESTRUCTURA INTERNA (BOS/CHoCH, pivotes de 5 |
//|  velas, logica LuxAlgo = SMC_EA_LuxAlgo) en la direccion de la   |
//|  ruptura, a la apertura de la vela siguiente.                    |
//|  SL = TP = ATR(14) x 2.                                          |
//|                                                                  |
//|  OJO: con velas M1 parecia ganar en BreakX 600, pero con TICKS   |
//|  reales PIERDE (los saltos cruzan el SL). Ver docs/LECCIONES.md. |
//|  Se conserva solo como ejemplo de codigo. NO usar.               |
//|  SEGURIDAD: por defecto NO opera en cuenta REAL.                 |
//+------------------------------------------------------------------+
#property copyright   "Proyecto oro bitcoin - Raul"
#property version     "1.00"
#property description "Ruptura de estructura interna SMC (LuxAlgo, pivotes de 5). SL = TP = 2 x ATR(14)."
#property description "Ejemplo: con ticks reales NO tiene ventaja. Por defecto NO opera en cuenta real."
#include <Trade\Trade.mqh>

input group "SEGURIDAD"
input bool    InpPermitirReal = false;            // Permitir operar en cuenta REAL

input group "Mercados"
input string  InpSimbolos  = "BreakX 600";        // Mercados (separados por coma)
input ENUM_TIMEFRAMES InpTF = PERIOD_M1;          // Temporalidad (probada: M1)

input group "Senal (igual que la prueba)"
input int     InpPivote    = 5;                   // Velas del pivote interno (LuxAlgo = 5)
input int     InpVelas     = 1000;                // Velas a analizar
input bool    InpCompras   = true;                // Operar compras
input bool    InpVentas    = true;                // Operar ventas

input group "Gestion"
input double  InpLote      = 0;                   // Lote (0 = minimo del mercado)
input double  InpMultATR   = 2.0;                 // SL = TP = ATR(14) x este numero
input int     InpMaxVelas  = 500;                 // Cerrar si sigue abierta tras N velas
input long    InpMagic     = 282810;              // Numero magico

input group "Avisos"
input bool    InpCelular   = false;               // Notificacion al celular en cada operacion

CTrade   g_trade;
string   g_sims[];
datetime g_ult[];
int      g_hATR[];
bool     g_puede = true;
string   g_motivo = "";
int      g_ops[], g_gan[];

//+------------------------------------------------------------------+
int OnInit()
{
   if(AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL && !InpPermitirReal)
   {
      g_puede = false;
      g_motivo = "CUENTA REAL y 'Permitir operar en cuenta REAL' = false: NO se abren operaciones.";
      Alert("SMC_Ruptura_EA: ", g_motivo);
   }
   g_trade.SetExpertMagicNumber(InpMagic);
   g_trade.SetDeviationInPoints(100);
   string p[];
   int n = StringSplit(InpSimbolos, ',', p);
   ArrayResize(g_sims, 0);
   for(int i = 0; i < n; i++)
   {
      string s = p[i]; StringTrimLeft(s); StringTrimRight(s);
      if(s == "") continue;
      if(!SymbolSelect(s, true)) { Print("SMC_Ruptura_EA: no existe el mercado ", s); continue; }
      int k = ArraySize(g_sims); ArrayResize(g_sims, k + 1); g_sims[k] = s;
   }
   int ns = ArraySize(g_sims);
   ArrayResize(g_ult, ns); ArrayResize(g_hATR, ns); ArrayResize(g_ops, ns); ArrayResize(g_gan, ns);
   for(int i = 0; i < ns; i++)
   {
      g_ult[i] = iTime(g_sims[i], InpTF, 0);       // no operar la vela que ya estaba abierta al iniciar
      g_hATR[i] = iATR(g_sims[i], InpTF, 14);
      g_ops[i] = 0; g_gan[i] = 0;
   }
   EventSetTimer(1);
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int r)
{
   EventKillTimer();
   for(int i = 0; i < ArraySize(g_hATR); i++) IndicatorRelease(g_hATR[i]);
   Comment("");
}

//+------------------------------------------------------------------+
//| Ruptura interna en la ultima vela cerrada (logica LuxAlgo)       |
//| Devuelve +1 (ruptura alcista), -1 (bajista) o 0.                 |
//+------------------------------------------------------------------+
int Ruptura(const MqlRates &r[], int n)
{
   int last = n - 2;                       // ultima vela cerrada
   int leg = -1;
   double nivH = 0, nivL = 0; bool hayH = false, hayL = false, cruH = true, cruL = true;
   int res = 0;
   for(int i = InpPivote; i <= last; i++)
   {
      int p = i - InpPivote;
      double mx = r[p + 1].high, mn = r[p + 1].low;
      for(int j = p + 1; j <= i; j++) { if(r[j].high > mx) mx = r[j].high; if(r[j].low < mn) mn = r[j].low; }
      int nl = -1;
      if(r[p].high > mx) nl = 0;
      else if(r[p].low < mn) nl = 1;
      if(nl != -1 && leg != -1 && nl != leg)
      {
         if(nl == 1) { nivL = r[p].low;  hayL = true; cruL = false; }
         else        { nivH = r[p].high; hayH = true; cruH = false; }
      }
      if(nl != -1) leg = nl;
      if(i > 0)
      {
         int rr = 0;
         if(hayH && !cruH && r[i-1].close <= nivH && r[i].close > nivH) { cruH = true; rr = 1; }
         if(hayL && !cruL && r[i-1].close >= nivL && r[i].close < nivL) { cruL = true; rr = -1; }
         if(i == last) res = rr;
      }
   }
   return res;
}

int Abiertas(string sym, int dir)
{
   int n = 0;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      if(PositionGetTicket(i) == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic || PositionGetString(POSITION_SYMBOL) != sym) continue;
      long t = PositionGetInteger(POSITION_TYPE);
      if((dir == 1 && t == POSITION_TYPE_BUY) || (dir == -1 && t == POSITION_TYPE_SELL)) n++;
   }
   return n;
}

void CerrarViejas(string sym)
{
   int seg = PeriodSeconds(InpTF) * InpMaxVelas;
   for(int i = PositionsTotal() - 1; i >= 0; i--)
   {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetInteger(POSITION_MAGIC) != InpMagic || PositionGetString(POSITION_SYMBOL) != sym) continue;
      if(TimeCurrent() - (datetime)PositionGetInteger(POSITION_TIME) > seg) g_trade.PositionClose(tk);
   }
}

void Abrir(int s, int dir)
{
   string sym = g_sims[s];
   if(!g_puede) return;
   if(!TerminalInfoInteger(TERMINAL_TRADE_ALLOWED) || !MQLInfoInteger(MQL_TRADE_ALLOWED)) { Print("SMC_Ruptura_EA: Algo Trading apagado"); return; }
   if((dir == 1 && !InpCompras) || (dir == -1 && !InpVentas)) return;
   if(Abiertas(sym, dir) > 0) return;                       // una a la vez por direccion (igual que la prueba)
   double a[];
   if(CopyBuffer(g_hATR[s], 0, 1, 1, a) < 1) return;        // ATR(14) de la vela de la ruptura
   double dist = a[0] * InpMultATR;
   int dig = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double pt = SymbolInfoDouble(sym, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * pt;
   if(dist < minStop) dist = minStop;
   double vmin = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN), vstep = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   double lote = (InpLote <= 0) ? vmin : MathMax(vmin, MathFloor(InpLote / vstep) * vstep);
   g_trade.SetTypeFillingBySymbol(sym);
   bool ok;
   if(dir == 1)
   {
      double pr = SymbolInfoDouble(sym, SYMBOL_ASK);
      ok = g_trade.Buy(lote, sym, 0, NormalizeDouble(pr - dist, dig), NormalizeDouble(pr + dist, dig), "SMC rupt");
   }
   else
   {
      double pr = SymbolInfoDouble(sym, SYMBOL_BID);
      ok = g_trade.Sell(lote, sym, 0, NormalizeDouble(pr + dist, dig), NormalizeDouble(pr - dist, dig), "SMC rupt");
   }
   string msg = StringFormat("SMC Ruptura: %s %s | lote %.2f | SL/TP %s | %s", dir == 1 ? "COMPRA" : "VENTA", sym, lote,
                             DoubleToString(dist, dig), ok ? "abierta" : "ERROR " + g_trade.ResultRetcodeDescription());
   Print(msg);
   if(InpCelular) SendNotification(msg);
}

void OnTimer()
{
   for(int s = 0; s < ArraySize(g_sims); s++)
   {
      string sym = g_sims[s];
      CerrarViejas(sym);
      datetime t0 = iTime(sym, InpTF, 0);
      if(t0 == 0 || t0 == g_ult[s]) continue;
      MqlRates r[];
      int n = CopyRates(sym, InpTF, 0, InpVelas, r);
      if(n < 100) continue;
      g_ult[s] = t0;
      int d = Ruptura(r, n);
      if(d != 0) Abrir(s, d);
   }
   // resumen
   string txt = "SMC RUPTURA EA | " + (g_puede ? "OPERANDO (" + (AccountInfoInteger(ACCOUNT_TRADE_MODE) == ACCOUNT_TRADE_MODE_REAL ? "REAL" : "DEMO") + ")" : g_motivo) +
                "\nTF " + EnumToString(InpTF) + " | SL = TP = ATR(14) x " + DoubleToString(InpMultATR, 1) + "\n";
   for(int s = 0; s < ArraySize(g_sims); s++)
      txt += g_sims[s] + ": compras abiertas " + IntegerToString(Abiertas(g_sims[s], 1)) +
             ", ventas abiertas " + IntegerToString(Abiertas(g_sims[s], -1)) + "\n";
   Comment(txt);
}

void OnTick() { }
//+------------------------------------------------------------------+
