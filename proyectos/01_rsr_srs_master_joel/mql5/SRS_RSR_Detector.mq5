//+------------------------------------------------------------------+
//|                                            SRS_RSR_Detector.mq5  |
//|  Detector del patrón SRS (compra) / RSR (venta) de Master Joel.  |
//|  Traducción fiel de rsr_srs/detector.py del proyecto             |
//|  "proyecto videos" (estructura R-49, S-8, S-9, S-10, D-017).     |
//|                                                                  |
//|  - Solo trabaja con velas CERRADAS: no repinta.                  |
//|  - Dibuja la zona, la flecha en la vela de confirmación (vela 0) |
//|    y la ventana de 4 velas hasta la salida.                      |
//|  - Alertas: ventana de MT5, sonido, celular (push) y email.      |
//|  - NO envía órdenes.                                             |
//|                                                                  |
//|  AVISO: en el backtest (D-022) estas señales no superaron al     |
//|  azar después de costes en los sintéticos de Weltrade. Úsalo     |
//|  como ayuda visual, no como sistema automático de ganancias.     |
//+------------------------------------------------------------------+
#property copyright   "Proyecto RSR/SRS - Raul"
#property version     "1.00"
#property description "Detector SRS (compra) / RSR (venta). Solo velas cerradas, no repinta, no opera."
#property description "Valores por defecto = parámetros de la validación (D-017); no son reglas de Master Joel."
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2
#property indicator_label1  "SRS compra"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrLime
#property indicator_width1  2
#property indicator_label2  "RSR venta"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrRed
#property indicator_width2  2

#include <Arrays\ArrayObj.mqh>
#include <Arrays\ArrayLong.mqh>

//--- opciones
enum ENUM_P6_WICK
  {
   P6_A_DESCALIFICA    = 0, // (a) La mecha que sobresale descalifica
   P6_B_NO_DESCALIFICA = 1, // (b) No descalifica
   P6_C_ELEVA_NIVEL    = 2  // (c) No descalifica, pero eleva el nivel de entrada
  };
enum ENUM_P8_ZONE
  {
   P8_TODAS_LAS_QUE_QUEPAN = 0, // (a) Todas las velas que quepan
   P8_GRUPO_MAS_CORTO      = 1  // (b) Grupo más corto (2 velas)
  };
enum ENUM_P9_SINGLE
  {
   P9_VELA_DENTRO = 0, // (a) Al menos una vela que cierre dentro antes de la ruptura
   P9_SOLO_VELA0  = 1  // (b) Solo se descarta si la vela 0 cruza los dos niveles
  };

//--- parámetros
input group "=== Patrón (valores de la validación D-017) ==="
input double         InpMaxWidth  = 2.0;                     // P-2 Anchura máxima de la zona (en velas medias)
input int            InpMaxFake   = 5;                       // P-4 Velas máximas de engaño
input int            InpMaxTotal  = 24;                      // P-5 Duración máxima del patrón (velas)
input int            InpAvgN      = 50;                      // P-7 Velas para calcular la "vela media"
input ENUM_P8_ZONE   InpZonePick  = P8_TODAS_LAS_QUE_QUEPAN; // P-8 Qué velas forman la zona
input bool           InpExact2    = false;                   // P-1 Zona de exactamente 2 velas
input bool           InpDistinct  = true;                    // P-3 Permitir niveles de velas distintas
input ENUM_P9_SINGLE InpSingle    = P9_VELA_DENTRO;          // P-9 Una sola vela que cruza los dos niveles
input ENUM_P6_WICK   InpWick      = P6_B_NO_DESCALIFICA;     // P-6 Mecha que sobresale de la zona

input group "=== Filtros opcionales (0 = desactivado) ==="
input double         InpF3MaxDist = 0.0;  // F-3 Distancia máx. del cierre al nivel (velas medias). Ej: 1.0
input double         InpF4MaxRej  = 0.0;  // F-4 Rechazo máx. de la vela 0 (0 a 1). Ej: 0.4

input group "=== Dibujo ==="
input int            InpHistoryBars = 3000;           // Velas de historial a analizar
input bool           InpDrawZones   = true;           // Dibujar la zona del patrón
input bool           InpDrawExit    = true;           // Dibujar la ventana de 4 velas hasta la salida
input color          InpBuyColor    = clrMediumSeaGreen; // Color SRS (compra)
input color          InpSellColor   = clrIndianRed;      // Color RSR (venta)

input group "=== Alertas (solo señales nuevas, al cerrar la vela) ==="
input bool           InpAlertPopup = true;        // Ventana de alerta en MT5
input bool           InpAlertSound = true;        // Sonido
input string         InpSoundFile  = "alert.wav"; // Archivo de sonido
input bool           InpAlertPush  = true;        // Notificación al celular (MetaQuotes ID)
input bool           InpAlertEmail = false;       // Email

//--- buffers
double BuyBuf[];
double SellBuf[];

//--- prefijo de objetos
#define PREFIX "SRSRSR_"

//+------------------------------------------------------------------+
//| Candidato: zona que espera engaño, vuelta y ruptura              |
//+------------------------------------------------------------------+
class CCand : public CObject
  {
public:
   int               dir;            // +1 SRS (compra), -1 RSR (venta)
   int               start;
   int               zend;
   int               fakeStart;
   double            hi, lo, avg, entry;
   bool              sameLevels;
   int               fakeCount;
   bool              insideSinceFake;
   int               insideTotal;
   bool              silent;         // zona alternativa más corta, se sigue sin registrar nada (D-017)
   bool              retry;          // descartada por duración total: probar la zona más corta
   CArrayObj         shadows;        // zonas más cortas (de la más larga a la más corta)

                     CCand(void)
     {
      shadows.FreeMode(false);
      fakeCount = 0;
      insideSinceFake = false;
      insideTotal = 0;
      silent = false;
      retry = false;
     }
  };

//--- estado global
CArrayObj  g_active;          // candidatos vivos
CArrayLong g_used;            // zonas ya usadas (una zona da como máximo una señal)
int        g_lastBar   = -1;  // última vela procesada
int        g_alertBar  = -1;  // vela en la que se permiten alertas (señal nueva en vivo)
int        g_lastSig[2];      // última vela 0 con señal por dirección (S-10)
int        g_synced    = 0;
int        g_signals   = 0;
string     g_lastText  = "";

double     g_o[], g_h[], g_l[], g_c[];
datetime   g_t[];

//+------------------------------------------------------------------+
string TfName(void)
  {
   return StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period), 7);
  }

//+------------------------------------------------------------------+
long ZoneKey(const int dir, const int start, const int zend)
  {
   return (((long)(dir > 0 ? 1 : 2)) << 60) | (((long)start) << 30) | (long)zend;
  }

bool IsUsed(const int dir, const int start, const int zend)
  {
   return g_used.Search(ZoneKey(dir, start, zend)) >= 0;
  }

void AddUsed(const int dir, const int start, const int zend)
  {
   long key = ZoneKey(dir, start, zend);
   if(g_used.Search(key) < 0)
      g_used.InsertSort(key);
  }

//+------------------------------------------------------------------+
void DeleteCand(CCand *c)
  {
   if(c == NULL)
      return;
   for(int i = 0; i < c.shadows.Total(); i++)
     {
      CCand *s = (CCand *)c.shadows.At(i);
      if(s != NULL)
         delete s;
     }
   c.shadows.Clear();
   delete c;
  }

void ClearActive(void)
  {
   for(int i = 0; i < g_active.Total(); i++)
      DeleteCand((CCand *)g_active.At(i));
   g_active.Clear();
  }

//+------------------------------------------------------------------+
//| "Vela media": tamaño medio de las N velas cerradas anteriores    |
//+------------------------------------------------------------------+
double AvgCandle(const int k)
  {
   int n = InpAvgN;
   if(k < n)
      return 0.0;
   double s = 0.0;
   for(int i = k - n; i < k; i++)
      s += g_h[i] - g_l[i];
   return s / n;
  }

//+------------------------------------------------------------------+
//| S-8: niveles "de las mismas velas" si máximo y mínimo salen de   |
//| la misma vela o de velas contiguas                               |
//+------------------------------------------------------------------+
bool SameLevels(const int start, const int zend, const double hi, const double lo)
  {
   int best = INT_MAX;
   for(int a = start; a <= zend; a++)
     {
      if(g_h[a] != hi)
         continue;
      for(int b = start; b <= zend; b++)
        {
         if(g_l[b] != lo)
            continue;
         int d = MathAbs(a - b);
         if(d < best)
            best = d;
        }
     }
   return best <= 1;
  }

//+------------------------------------------------------------------+
//| Descarte: la zona queda usada (salvo zonas alternativas)         |
//+------------------------------------------------------------------+
bool Discard(CCand *c)
  {
   if(c.silent)
      return false;
   AddUsed(c.dir, c.start, c.zend);
   return false;
  }

//+------------------------------------------------------------------+
//| Avisos                                                           |
//+------------------------------------------------------------------+
void SendAlerts(const string msg)
  {
   if(InpAlertPopup)
      Alert(msg);                  // la ventana de alerta ya suena
   else
      if(InpAlertSound)
         PlaySound(InpSoundFile);
   if(InpAlertPush)
      SendNotification(StringSubstr(msg, 0, 250));
   if(InpAlertEmail)
      SendMail("Señal " + _Symbol + " " + TfName(), msg);
  }

//+------------------------------------------------------------------+
//| Señal confirmada en la vela k                                     |
//+------------------------------------------------------------------+
void EmitSignal(CCand *c, const int k)
  {
   bool     buy   = (c.dir > 0);
   int      per   = PeriodSeconds();
   datetime tEnt  = g_t[k] + per;          // apertura de la vela siguiente
   datetime tExit = g_t[k] + 5 * per;      // cierre de la 4.ª vela posterior
   color    col   = buy ? InpBuyColor : InpSellColor;
   string   id    = PREFIX + (buy ? "B_" : "S_") + IntegerToString((long)g_t[k]);

   if(buy)
      BuyBuf[k] = g_l[k] - 0.3 * c.avg;
   else
      SellBuf[k] = g_h[k] + 0.3 * c.avg;

   if(InpDrawZones)
     {
      string r = id + "_zona";
      ObjectCreate(0, r, OBJ_RECTANGLE, 0, g_t[c.start], c.hi, g_t[k], c.lo);
      ObjectSetInteger(0, r, OBJPROP_COLOR, col);
      ObjectSetInteger(0, r, OBJPROP_FILL, true);
      ObjectSetInteger(0, r, OBJPROP_BACK, true);
      ObjectSetInteger(0, r, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, r, OBJPROP_TOOLTIP, (buy ? "SRS (compra)" : "RSR (venta)") +
                      "\nZona: " + DoubleToString(c.lo, _Digits) + " - " + DoubleToString(c.hi, _Digits) +
                      "\nVelas de engaño: " + IntegerToString(c.fakeCount));

      string tx = id + "_txt";
      double py = buy ? g_l[k] - 0.9 * c.avg : g_h[k] + 0.9 * c.avg;
      ObjectCreate(0, tx, OBJ_TEXT, 0, g_t[k], py);
      ObjectSetString(0, tx, OBJPROP_TEXT, buy ? "SRS" : "RSR");
      ObjectSetInteger(0, tx, OBJPROP_COLOR, col);
      ObjectSetInteger(0, tx, OBJPROP_FONTSIZE, 8);
      ObjectSetInteger(0, tx, OBJPROP_ANCHOR, ANCHOR_CENTER);
      ObjectSetInteger(0, tx, OBJPROP_SELECTABLE, false);
     }

   if(InpDrawExit)
     {
      string w = id + "_salida";
      ObjectCreate(0, w, OBJ_TREND, 0, tEnt, g_c[k], tExit, g_c[k]);
      ObjectSetInteger(0, w, OBJPROP_COLOR, col);
      ObjectSetInteger(0, w, OBJPROP_STYLE, STYLE_DOT);
      ObjectSetInteger(0, w, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, w, OBJPROP_SELECTABLE, false);
      ObjectSetString(0, w, OBJPROP_TOOLTIP, "Ventana de 4 velas: salida al cierre de la 4.ª vela (" +
                      TimeToString(tExit, TIME_DATE | TIME_MINUTES) + ")");
     }

   g_signals++;
   string msg = StringFormat("%s | %s %s | Confirmada al cierre de %s | Entrada: apertura de la vela siguiente | Salida: cierre de la 4.ª vela (%s)",
                             buy ? "SRS COMPRA" : "RSR VENTA", _Symbol, TfName(),
                             TimeToString(tEnt, TIME_DATE | TIME_MINUTES),
                             TimeToString(tExit, TIME_MINUTES));
   g_lastText = msg;
   if(k == g_alertBar)
      SendAlerts(msg);
  }

//+------------------------------------------------------------------+
//| Confirmación (vela 0)                                            |
//+------------------------------------------------------------------+
bool Confirm(CCand *c, const int k)
  {
   if(c.silent)          // zona alternativa que confirma mientras la principal vive: no cuenta
      return false;
   bool buy = (c.dir > 0);
   if(InpF3MaxDist > 0.0)
     {
      double d = buy ? (g_c[k] - c.entry) / c.avg : (c.entry - g_c[k]) / c.avg;
      if(d > InpF3MaxDist)
         return Discard(c);
     }
   if(InpF4MaxRej > 0.0)
     {
      double rng = g_h[k] - g_l[k];
      double rej = 0.0;
      if(rng > 0.0)
         rej = buy ? (g_h[k] - MathMax(g_o[k], g_c[k])) / rng : (MathMin(g_o[k], g_c[k]) - g_l[k]) / rng;
      if(rej > InpF4MaxRej)
         return Discard(c);
     }
   AddUsed(c.dir, c.start, c.zend);
   int di = buy ? 0 : 1;
   if(g_lastSig[di] == k)   // S-10: misma vela 0 y dirección = una sola señal
      return false;
   g_lastSig[di] = k;
   EmitSignal(c, k);
   return false;
  }

//+------------------------------------------------------------------+
//| Aplica la vela k a un candidato. true = sigue vivo               |
//+------------------------------------------------------------------+
bool Step(CCand *c, const int k)
  {
   bool buy        = (c.dir > 0);
   int  total      = k - c.start + 1;
   bool beyondFake = buy ? (g_l[k] < c.lo) : (g_h[k] > c.hi);
   bool closesOut  = buy ? (g_c[k] > c.entry) : (g_c[k] < c.entry);

   if(total > InpMaxTotal)
     {
      c.retry = true;
      return Discard(c);
     }
   if(beyondFake && closesOut)                 // una sola vela cruza los dos niveles (R-28)
      return Discard(c);

   bool closesInside = buy ? (c.lo <= g_c[k] && g_c[k] <= c.entry) : (c.entry <= g_c[k] && g_c[k] <= c.hi);
   if(beyondFake && closesInside && k != c.fakeStart)
      beyondFake = false;                      // S-9: la vela que vuelve y cierra dentro no es engaño

   if(closesOut)
     {
      if(InpSingle == P9_VELA_DENTRO && !c.insideSinceFake)
         return Discard(c);
      return Confirm(c, k);
     }
   if(beyondFake)
     {
      c.fakeCount++;
      c.insideSinceFake = false;
      if(c.fakeCount > InpMaxFake)
         return Discard(c);
      return true;
     }
   if(closesInside)
     {
      c.insideSinceFake = true;
      c.insideTotal++;
     }
   bool wick = buy ? (g_h[k] > c.entry) : (g_l[k] < c.entry);   // mecha por el lado de entrada (P-6)
   if(wick)
     {
      if(InpWick == P6_A_DESCALIFICA)
         return Discard(c);
      if(InpWick == P6_C_ELEVA_NIVEL)
        {
         c.entry = buy ? g_h[k] : g_l[k];
         double base = buy ? c.lo : c.hi;
         if(MathAbs(c.entry - base) / c.avg > InpMaxWidth)
            return Discard(c);
        }
     }
   return true;
  }

//+------------------------------------------------------------------+
//| Avanza un candidato y sus zonas alternativas (D-017)             |
//+------------------------------------------------------------------+
CCand *Advance(CCand *c, const int k)
  {
   if(Step(c, k))
     {
      CArrayObj keep;
      keep.FreeMode(false);
      for(int i = 0; i < c.shadows.Total(); i++)
        {
         CCand *s = (CCand *)c.shadows.At(i);
         if(Step(s, k))
            keep.Add(s);
         else
            delete s;
        }
      c.shadows.Clear();
      for(int i = 0; i < keep.Total(); i++)
         c.shadows.Add(keep.At(i));
      keep.Clear();
      return c;
     }
   if(!c.retry)
     {
      DeleteCand(c);
      return NULL;
     }
//--- descartada por duración total: se prueba la siguiente zona más corta con esta misma vela
   int n = c.shadows.Total();
   for(int i = 0; i < n; i++)
     {
      CCand *nx = (CCand *)c.shadows.At(i);
      nx.silent = false;
      if(Step(nx, k))
        {
         for(int j = i + 1; j < n; j++)
           {
            CCand *s = (CCand *)c.shadows.At(j);
            if(Step(s, k))
               nx.shadows.Add(s);
            else
               delete s;
           }
         c.shadows.Clear();
         delete c;
         return nx;
        }
      if(!nx.retry)
        {
         for(int j = i; j < n; j++)
           {
            CCand *s = (CCand *)c.shadows.At(j);
            delete s;
           }
         c.shadows.Clear();
         delete c;
         return NULL;
        }
      delete nx;
     }
   c.shadows.Clear();
   delete c;
   return NULL;
  }

//+------------------------------------------------------------------+
//| Crea un candidato si la vela k empieza un engaño                  |
//+------------------------------------------------------------------+
CCand *NewCand(const int dir, const int k, const double avg)
  {
   if(k < 2 || avg <= 0.0)
      return NULL;
   int reserve = InpMaxFake + (InpSingle == P9_VELA_DENTRO ? 2 : 1);   // D-017
   int maxLen  = (InpExact2 || InpZonePick == P8_GRUPO_MAS_CORTO) ? 2 : InpMaxTotal - reserve;
   int lim     = MathMin(maxLen, k);
   if(lim < 2)
      return NULL;

   int    lens[];
   double his[], los[];
   ArrayResize(lens, lim + 1);
   ArrayResize(his, lim + 1);
   ArrayResize(los, lim + 1);
   int    n  = 0;
   double hh = -DBL_MAX, ll = DBL_MAX;
   for(int len = 1; len <= lim; len++)
     {
      int i = k - len;
      hh = MathMax(hh, g_h[i]);
      ll = MathMin(ll, g_l[i]);
      if((hh - ll) / avg > InpMaxWidth)
         break;
      if(len >= 2)
        {
         lens[n] = len;
         his[n]  = hh;
         los[n]  = ll;
         n++;
        }
     }
   if(n == 0)
      return NULL;

   int    len0 = lens[n - 1];
   double hi   = his[n - 1];
   double lo   = los[n - 1];
   int    st   = k - len0;
   int    en   = k - 1;
   if(IsUsed(dir, st, en))
      return NULL;
   bool begins = (dir > 0) ? (g_l[k] < lo) : (g_h[k] > hi);
   if(!begins)
      return NULL;
   bool same = SameLevels(st, en, hi, lo);
   if(!same && !InpDistinct)
      return NULL;

   CCand *c = new CCand();
   c.dir = dir;
   c.start = st;
   c.zend = en;
   c.hi = hi;
   c.lo = lo;
   c.avg = avg;
   c.sameLevels = same;
   c.entry = (dir > 0) ? hi : lo;
   c.fakeStart = k;

   for(int j = n - 2; j >= 0; j--)
     {
      int s0 = k - lens[j];
      if(IsUsed(dir, s0, en))
         continue;
      bool sm = SameLevels(s0, en, his[j], los[j]);
      if(!sm && !InpDistinct)
         continue;
      CCand *s = new CCand();
      s.dir = dir;
      s.start = s0;
      s.zend = en;
      s.hi = his[j];
      s.lo = los[j];
      s.avg = avg;
      s.sameLevels = sm;
      s.entry = (dir > 0) ? his[j] : los[j];
      s.fakeStart = k;
      s.silent = true;
      c.shadows.Add(s);
     }
   return c;
  }

//+------------------------------------------------------------------+
//| Procesa una vela cerrada                                          |
//+------------------------------------------------------------------+
void ProcessBar(const int k)
  {
   CArrayObj still;
   still.FreeMode(false);
   for(int i = 0; i < g_active.Total(); i++)
     {
      CCand *r = Advance((CCand *)g_active.At(i), k);
      if(r != NULL)
         still.Add(r);
     }
   double avg = AvgCandle(k);
   for(int d = 0; d < 2; d++)
     {
      int dir = (d == 0) ? 1 : -1;      // primero SRS, luego RSR (igual que el detector Python)
      CCand *nc = NewCand(dir, k, avg);
      if(nc != NULL)
        {
         CCand *r = Advance(nc, k);
         if(r != NULL)
            still.Add(r);
        }
     }
   g_active.Clear();
   for(int i = 0; i < still.Total(); i++)
      g_active.Add(still.At(i));
   still.Clear();
  }

//+------------------------------------------------------------------+
void ResetState(void)
  {
   ClearActive();
   g_used.Shutdown();
   g_used.Sort();
   g_lastSig[0] = -1;
   g_lastSig[1] = -1;
   g_lastBar  = -1;
   g_alertBar = -1;
   g_synced   = 0;
   g_signals  = 0;
   g_lastText = "";
   ObjectsDeleteAll(0, PREFIX);
  }

//+------------------------------------------------------------------+
int OnInit(void)
  {
   if(InpMaxWidth <= 0.0 || InpMaxTotal < 4 || InpAvgN < 1 || InpMaxFake < 1)
     {
      Print("SRS_RSR_Detector: parámetros no válidos (anchura > 0, duración >= 4, vela media >= 1, engaño >= 1).");
      return INIT_PARAMETERS_INCORRECT;
     }
   SetIndexBuffer(0, BuyBuf, INDICATOR_DATA);
   SetIndexBuffer(1, SellBuf, INDICATOR_DATA);
   PlotIndexSetInteger(0, PLOT_ARROW, 233);
   PlotIndexSetInteger(1, PLOT_ARROW, 234);
   PlotIndexSetDouble(0, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1, PLOT_EMPTY_VALUE, EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME, "SRS/RSR Detector");
   g_active.FreeMode(false);
   ResetState();
   return INIT_SUCCEEDED;
  }

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   ClearActive();
   ObjectsDeleteAll(0, PREFIX);
   Comment("");
  }

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total,
                const int prev_calculated,
                const datetime &time[],
                const double &open[],
                const double &high[],
                const double &low[],
                const double &close[],
                const long &tick_volume[],
                const long &volume[],
                const int &spread[])
  {
   if(rates_total < InpAvgN + 5)
      return 0;

   bool reset = (prev_calculated == 0);
   if(reset)
     {
      ResetState();
      ArrayInitialize(BuyBuf, EMPTY_VALUE);
      ArrayInitialize(SellBuf, EMPTY_VALUE);
     }
   else
      for(int i = MathMax(prev_calculated - 1, 0); i < rates_total; i++)
        {
         if(i >= prev_calculated)
           {
            BuyBuf[i]  = EMPTY_VALUE;
            SellBuf[i] = EMPTY_VALUE;
           }
        }

//--- copia de precios (solo lo nuevo)
   int from = reset ? 0 : MathMax(0, g_synced);
   ArrayResize(g_o, rates_total);
   ArrayResize(g_h, rates_total);
   ArrayResize(g_l, rates_total);
   ArrayResize(g_c, rates_total);
   ArrayResize(g_t, rates_total);
   int cnt = rates_total - from;
   ArrayCopy(g_o, open,  from, from, cnt);
   ArrayCopy(g_h, high,  from, from, cnt);
   ArrayCopy(g_l, low,   from, from, cnt);
   ArrayCopy(g_c, close, from, from, cnt);
   ArrayCopy(g_t, time,  from, from, cnt);
   g_synced = rates_total - 1;   // la vela en formación se vuelve a copiar la próxima vez

//--- primera pasada: historial, sin alertas
   int lastClosed = rates_total - 2;
   if(reset)
      g_lastBar = MathMax(InpAvgN, rates_total - 1 - InpHistoryBars) - 1;

   for(int k = g_lastBar + 1; k <= lastClosed; k++)
     {
      g_alertBar = (!reset && k == lastClosed) ? k : -1;   // solo señales nuevas en vivo
      ProcessBar(k);
     }
   g_lastBar  = lastClosed;
   g_alertBar = -1;

   Comment("SRS/RSR Detector · ", _Symbol, " ", TfName(), " · señales en pantalla: ", g_signals,
           (g_lastText != "" ? "\nÚltima: " + g_lastText : ""));
   return rates_total;
  }
//+------------------------------------------------------------------+
