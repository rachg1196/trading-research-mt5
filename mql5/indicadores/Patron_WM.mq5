//+------------------------------------------------------------------+
//|                                                  Patron_WM.mq5   |
//|  Proyecto W y M - Raul                                           |
//|  Dibuja patrones W (doble/triple piso) y M (doble/triple techo)  |
//|  y avisa (ventana + sonido + celular) cuando se rompe el cuello. |
//|  v2: ESCANER multi-mercado / multi-temporalidad (opcional).      |
//|                                                                  |
//|  NOTA: herramienta VISUAL. En las pruebas (Fase 3) el patron no  |
//|  mostro ventaja despues de costes. No es una senal para operar   |
//|  a ciegas.                                                       |
//+------------------------------------------------------------------+
#property copyright   "Proyecto W y M - Raul"
#property version     "2.00"
#property description "Dibuja W y M (doble/triple piso y techo) y avisa al romper el cuello."
#property description "Escaner opcional: mercados en filas, temporalidades en columnas."
#property description "Herramienta visual: el patron no mostro ventaja en las pruebas."
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

input group "Deteccion (mismos valores que la Fase 2)"
input int    InpATR          = 14;     // Periodo ATR
input double InpKATR         = 1.5;    // Tamano minimo de tramo (en ATR)
input double InpTolATR       = 0.5;    // Tolerancia de zona "igual" (en ATR)
input double InpMaxBarrida   = 0.5;    // Max. perforacion del 2do piso (fraccion del rebote)
input double InpMinCaida     = 1.0;    // Caida previa minima (veces el rebote)
input int    InpMinVelas     = 3;      // Velas minimas por tramo
input double InpMinRebATR    = 2.5;    // Rebote minimo (en ATR)
input double InpEsperaFact   = 1.0;    // Tiempo max. para romper cuello (x duracion)
input int    InpEsperaMin    = 5;      // Tiempo min. de espera (velas)
input bool   InpTriples      = true;   // Detectar triples
input int    InpBarras       = 3000;   // Velas a analizar en el grafico

input group "Escaner"
input bool   InpEscaner      = true;                                   // Activar escaner
input string InpSimbolos     = "BreakX 600,TrendX 600,SwitchX 600";    // Mercados (separados por coma)
input string InpTFs          = "M1,M2,M3,M4,M5,M6,M10,M15,M20,M30,H1"; // Temporalidades (o TODAS)
input int    InpBarrasEsc    = 1500;   // Velas a analizar por celda
input int    InpVigencia     = 3;      // Velas que la celda queda resaltada
input bool   InpClicCambia   = true;   // Clic en celda = cambiar el grafico a ese mercado/TF
input int    InpPanelX       = 10;     // Posicion X del panel
input int    InpPanelY       = 25;     // Posicion Y del panel
input int    InpAnchoCelda   = 46;     // Ancho de celda
input int    InpAltoCelda    = 20;     // Alto de celda

input group "Alertas"
input bool   InpAlerta       = true;        // Ventana de alerta con sonido
input bool   InpSonido       = true;        // Sonido (si la ventana esta apagada)
input string InpArchivoSonido= "alert.wav"; // Archivo de sonido (carpeta Sounds de MT5)
input bool   InpCelular      = true;        // Notificacion al celular (MetaQuotes ID)

input group "Dibujo"
input color  InpColorW       = clrDodgerBlue; // Color W (compra)
input color  InpColorM       = clrRed;        // Color M (venta)
input color  InpColorLinea   = clrYellow;     // Lineas del patron
input int    InpGrosor       = 2;             // Grosor de lineas
input bool   InpNumeros      = true;          // Numerar pisos/techos

struct Piv { int t; int i; double p; int c; };
struct Pat { int tipo; int toques; int variante; int idx[6]; double pr[6]; double cuello; int sig; };
struct Celda { string sym; ENUM_TIMEFRAMES tf; datetime ultBarra; bool primera; bool valido; int tipo; int edad; };

string   PFX  = "WMp_";     // objetos de patrones en el grafico
string   PFXS = "WMs_";     // objetos del escaner
datetime g_ultimaVela   = 0;
datetime g_ultimaAlerta = 0;
bool     g_primera      = true;

string          g_sims[];
ENUM_TIMEFRAMES g_tfs[];
string          g_tfn[];
Celda           g_cel[];
int             g_nS = 0, g_nT = 0;

//+------------------------------------------------------------------+
//| Utilidades de temporalidades                                     |
//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
int OnInit()
{
   string id = IntegerToString(ChartID() % 100000);
   PFX  = "WMp_" + id + "_";
   PFXS = "WMs_" + id + "_";
   g_primera = true;
   g_ultimaVela = 0;
   if(InpEscaner)
   {
      PrepararEscaner();
      PanelCrear();
      EventSetTimer(2);
   }
   return(INIT_SUCCEEDED);
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   ObjectsDeleteAll(0, PFX);
   ObjectsDeleteAll(0, PFXS);
   ChartRedraw();
}

//+------------------------------------------------------------------+
//| Deteccion                                                        |
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

// ZigZag por ATR: un giro se confirma cuando el precio se aleja k*ATR del extremo
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

// Busca W sobre precios dados (para M se pasan precios invertidos)
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
         int j1 = jj - 2 * (toques - 1);       // piso 1
         if(j1 - 2 < 0) continue;
         Piv H0 = pv[j1 - 1];
         Piv L1 = pv[j1];
         Piv L0 = pv[j1 - 2];
         Piv Lu = pv[jj];
         if(!(L1.p < L0.p)) continue;          // contexto: venia bajando
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
         int variante = (MathAbs(dd) <= tol) ? 1 : (dd > 0 ? 0 : 2);   // 0 corto, 1 igual, 2 barrida
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

// Detecta W y M en el rango [from, last]. Arrays en orden normal (0 = vela mas antigua).
void Detectar(const double &high[], const double &low[], const double &close[],
              int total, int from, int last, Pat &res[])
{
   ArrayResize(res, 0);
   if(last - from < 30) return;
   double a[], hm[], lm[], cm[];
   ArrayResize(a, total);
   ArrayResize(hm, total);
   ArrayResize(lm, total);
   ArrayResize(cm, total);
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
//| Dibujo en el grafico                                             |
//+------------------------------------------------------------------+
string NombreVariante(int v)
{
   if(v == 0) return "2do extremo corto";
   if(v == 1) return "2do extremo igual";
   return "2do extremo barre al 1ro";
}

void Linea(string nm, datetime t1, double p1, datetime t2, double p2, color col, int ancho, int estilo)
{
   ObjectCreate(0, nm, OBJ_TREND, 0, t1, p1, t2, p2);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, ancho);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, estilo);
   ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}

void Texto(string nm, datetime t, double p, string txt, color col, ENUM_ANCHOR_POINT anc, int tam)
{
   ObjectCreate(0, nm, OBJ_TEXT, 0, t, p);
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, tam);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, anc);
   ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
}

void Dibujar(const Pat &P, const datetime &time[], int rates_total)
{
   bool   esW  = (P.tipo == 1);
   string base = PFX + (esW ? "W_" : "M_") + IntegerToString((long)time[P.sig]);
   int    n    = (P.toques == 3) ? 6 : 4;
   for(int q = 0; q < n - 1; q++)
      Linea(base + "_z" + IntegerToString(q), time[P.idx[q]], P.pr[q], time[P.idx[q+1]], P.pr[q+1],
            InpColorLinea, InpGrosor, STYLE_SOLID);
   int    fin = MathMin(P.sig + 10, rates_total - 1);
   Linea(base + "_cuello", time[P.idx[1]], P.cuello, time[fin], P.cuello, InpColorLinea, 1, STYLE_DASH);

   string na = base + "_flecha";
   ObjectCreate(0, na, esW ? OBJ_ARROW_BUY : OBJ_ARROW_SELL, 0, time[P.sig], P.cuello);
   ObjectSetInteger(0, na, OBJPROP_COLOR, esW ? InpColorW : InpColorM);
   ObjectSetInteger(0, na, OBJPROP_WIDTH, 3);
   ObjectSetInteger(0, na, OBJPROP_SELECTABLE, false);
   ObjectSetInteger(0, na, OBJPROP_HIDDEN, true);

   Texto(base + "_nombre", time[P.sig], P.cuello,
         (esW ? " W" : " M") + (P.toques == 3 ? " triple" : ""),
         esW ? InpColorW : InpColorM, esW ? ANCHOR_LEFT_UPPER : ANCHOR_LEFT_LOWER, 10);

   if(InpNumeros)
   {
      int num = 1;
      for(int q = 1; q < n; q += 2)
      {
         Texto(base + "_n" + IntegerToString(num), time[P.idx[q]], P.pr[q], IntegerToString(num),
               InpColorLinea, esW ? ANCHOR_UPPER : ANCHOR_LOWER, 10);
         num++;
      }
   }
}

//+------------------------------------------------------------------+
//| Alertas                                                          |
//+------------------------------------------------------------------+
void Avisar(const Pat &P, string sym, ENUM_TIMEFRAMES tf, int digitos)
{
   bool esW = (P.tipo == 1);
   string msg = StringFormat("SENAL %s en %s %s | %s | %s | cuello %s",
                             esW ? "W (compra)" : "M (venta)", sym, NombreTFde(tf),
                             P.toques == 3 ? "triple" : "doble", NombreVariante(P.variante),
                             DoubleToString(P.cuello, digitos));
   if(InpAlerta)       Alert(msg);
   else if(InpSonido)  PlaySound(InpArchivoSonido);
   if(InpCelular)
   {
      if(!SendNotification(msg))
         Print("Patron_WM: no se pudo enviar al celular (revisa Herramientas > Opciones > Notificaciones). Error ",
               GetLastError());
   }
   Print("Patron_WM: ", msg);
}

//+------------------------------------------------------------------+
//| Grafico actual                                                   |
//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[], const double &high[],
                const double &low[], const double &close[], const long &tick_volume[],
                const long &volume[], const int &spread[])
{
   if(rates_total < 100) return(rates_total);
   ArraySetAsSeries(time, false);
   ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);
   ArraySetAsSeries(close, false);

   datetime vela = time[rates_total - 1];
   if(vela == g_ultimaVela && prev_calculated > 0) return(rates_total);
   g_ultimaVela = vela;

   int last = rates_total - 2;                 // ultima vela cerrada
   int from = MathMax(0, rates_total - InpBarras);

   Pat res[];
   Detectar(high, low, close, rates_total, from, last, res);

   ObjectsDeleteAll(0, PFX);
   for(int k = 0; k < ArraySize(res); k++)
      Dibujar(res[k], time, rates_total);

   // alertas del grafico (si el escaner esta activo, el escaner avisa por todos)
   if(!InpEscaner && !g_primera && time[last] > g_ultimaAlerta)
   {
      bool hubo = false;
      for(int k = 0; k < ArraySize(res); k++)
         if(res[k].sig == last) { Avisar(res[k], _Symbol, (ENUM_TIMEFRAMES)Period(), _Digits); hubo = true; }
      if(hubo) g_ultimaAlerta = time[last];
   }
   g_primera = false;

   ChartRedraw();
   return(rates_total);
}

//+------------------------------------------------------------------+
//| ESCANER                                                          |
//+------------------------------------------------------------------+
void PrepararEscaner()
{
   string partes[];
   int ns = StringSplit(InpSimbolos, ',', partes);
   ArrayResize(g_sims, 0);
   for(int i = 0; i < ns; i++)
   {
      string s = partes[i];
      StringTrimLeft(s); StringTrimRight(s);
      if(StringLen(s) == 0) continue;
      int n = ArraySize(g_sims); ArrayResize(g_sims, n + 1); g_sims[n] = s;
      SymbolSelect(s, true);
   }
   g_nS = ArraySize(g_sims);

   ArrayResize(g_tfs, 0); ArrayResize(g_tfn, 0);
   string t = InpTFs;
   StringToUpper(t);
   StringTrimLeft(t); StringTrimRight(t);
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
         string s = pt[i];
         StringTrimLeft(s); StringTrimRight(s);
         int k = BuscarTF(s);
         if(k < 0) { Print("Patron_WM: temporalidad no reconocida: ", s); continue; }
         int n = ArraySize(g_tfs);
         ArrayResize(g_tfs, n + 1); ArrayResize(g_tfn, n + 1);
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
         g_cel[c].ultBarra = 0; g_cel[c].primera = true; g_cel[c].valido = false;
         g_cel[c].tipo = 0; g_cel[c].edad = -1;
      }
}

void Caja(string nm, int x, int y, int w, int h, string txt, color bg, color fg, bool clic)
{
   if(ObjectFind(0, nm) < 0)
   {
      ObjectCreate(0, nm, clic ? OBJ_BUTTON : OBJ_EDIT, 0, 0, 0);
      ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
      ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, y);
      ObjectSetInteger(0, nm, OBJPROP_XSIZE, w);
      ObjectSetInteger(0, nm, OBJPROP_YSIZE, h);
      ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, 8);
      ObjectSetString(0, nm, OBJPROP_FONT, "Arial");
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, nm, OBJPROP_ZORDER, 10);
      if(!clic)
      {
         ObjectSetInteger(0, nm, OBJPROP_READONLY, true);
         ObjectSetInteger(0, nm, OBJPROP_ALIGN, ALIGN_CENTER);
      }
   }
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_BGCOLOR, bg);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, fg);
   ObjectSetInteger(0, nm, OBJPROP_BORDER_COLOR, C'70,70,70');
   if(clic) ObjectSetInteger(0, nm, OBJPROP_STATE, false);
}

void PanelCrear()
{
   int x0 = InpPanelX, y0 = InpPanelY, w = InpAnchoCelda, h = InpAltoCelda, wn = 90;
   color fondo = C'25,25,25', cab = C'45,45,45';
   Caja(PFXS + "titulo", x0, y0, wn + w * g_nT, h, "ESCANER W / M", cab, clrWhite, false);
   Caja(PFXS + "hm", x0, y0 + h, wn, h, "Mercado", cab, clrSilver, false);
   for(int k = 0; k < g_nT; k++)
      Caja(PFXS + "h_" + IntegerToString(k), x0 + wn + k * w, y0 + h, w, h, g_tfn[k], cab, clrSilver, false);
   for(int s = 0; s < g_nS; s++)
   {
      Caja(PFXS + "s_" + IntegerToString(s), x0, y0 + h * (s + 2), wn, h, g_sims[s], cab, clrWhite, false);
      for(int k = 0; k < g_nT; k++)
         Caja(PFXS + "c_" + IntegerToString(s) + "_" + IntegerToString(k),
              x0 + wn + k * w, y0 + h * (s + 2), w, h, "...", fondo, clrGray, true);
   }
   ChartRedraw();
}

void PanelCelda(int s, int k)
{
   int c = s * g_nT + k;
   string txt = "-";
   color  bg  = C'25,25,25', fg = clrGray;
   if(!g_cel[c].valido) { txt = "sin datos"; fg = C'90,90,90'; }
   else if(g_cel[c].edad >= 0)
   {
      txt = (g_cel[c].tipo == 1 ? "W " : "M ") + IntegerToString(g_cel[c].edad);
      if(g_cel[c].edad < InpVigencia)
      {
         bg = (g_cel[c].tipo == 1) ? InpColorW : InpColorM;
         fg = clrWhite;
      }
      else fg = (g_cel[c].tipo == 1) ? C'110,150,200' : C'200,110,110';
   }
   int x0 = InpPanelX, y0 = InpPanelY, w = InpAnchoCelda, h = InpAltoCelda, wn = 90;
   Caja(PFXS + "c_" + IntegerToString(s) + "_" + IntegerToString(k),
        x0 + wn + k * w, y0 + h * (s + 2), w, h, txt, bg, fg, true);
}

void EscanearCelda(int s, int k)
{
   int c = s * g_nT + k;
   string sym = g_cel[c].sym;
   ENUM_TIMEFRAMES tf = g_cel[c].tf;
   datetime t0 = iTime(sym, tf, 0);
   if(t0 == 0) { g_cel[c].valido = false; return; }
   if(t0 == g_cel[c].ultBarra) return;              // sin vela nueva: nada que hacer

   MqlRates r[];
   int n = CopyRates(sym, tf, 0, InpBarrasEsc, r);
   if(n < 100) { g_cel[c].valido = false; return; }  // datos aun cargando: se reintenta
   double hh[], ll[], cc[];
   ArrayResize(hh, n); ArrayResize(ll, n); ArrayResize(cc, n);
   for(int i = 0; i < n; i++) { hh[i] = r[i].high; ll[i] = r[i].low; cc[i] = r[i].close; }
   int last = n - 2;

   Pat res[];
   Detectar(hh, ll, cc, n, 0, last, res);

   // patron mas reciente (para mostrar en la celda)
   int mejor = -1;
   for(int q = 0; q < ArraySize(res); q++)
      if(mejor < 0 || res[q].sig > res[mejor].sig) mejor = q;
   g_cel[c].valido = true;
   g_cel[c].tipo = (mejor >= 0) ? res[mejor].tipo : 0;
   g_cel[c].edad = (mejor >= 0) ? last - res[mejor].sig : -1;

   // alertas: solo patrones nuevos en la vela recien cerrada
   if(!g_cel[c].primera)
      for(int q = 0; q < ArraySize(res); q++)
         if(res[q].sig == last)
            Avisar(res[q], sym, tf, (int)SymbolInfoInteger(sym, SYMBOL_DIGITS));

   g_cel[c].primera = false;
   g_cel[c].ultBarra = t0;
}

void OnTimer()
{
   if(!InpEscaner) return;
   for(int s = 0; s < g_nS; s++)
      for(int k = 0; k < g_nT; k++)
      {
         EscanearCelda(s, k);
         PanelCelda(s, k);
      }
   ChartRedraw();
}

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
{
   if(id != CHARTEVENT_OBJECT_CLICK) return;
   string pre = PFXS + "c_";
   if(StringFind(sparam, pre) != 0) return;
   ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
   if(!InpClicCambia) return;
   string resto = StringSubstr(sparam, StringLen(pre));
   string p[];
   if(StringSplit(resto, '_', p) != 2) return;
   int s = (int)StringToInteger(p[0]), k = (int)StringToInteger(p[1]);
   if(s < 0 || s >= g_nS || k < 0 || k >= g_nT) return;
   ChartSetSymbolPeriod(0, g_sims[s], g_tfs[k]);
}
//+------------------------------------------------------------------+
