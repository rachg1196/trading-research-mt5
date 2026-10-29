//+------------------------------------------------------------------+
//|                                                   Patron123.mq5  |
//|  Proyecto oro bitcoin - Raul                                     |
//|  Lineas de tendencia tipo Joel Montes (toque 1-2, validacion,    |
//|  toque 3, 4...) a favor de "la pierna" (temporalidad mayor).     |
//|  Dibuja las lineas, marca los toques y avisa (ventana + sonido + |
//|  celular). Escaner: mercados en filas, temporalidades en columnas|
//|                                                                  |
//|  NOTA: herramienta VISUAL. En las pruebas (26-10-2026) la regla  |
//|  no mostro ventaja despues de costes. No opera: solo dibuja y    |
//|  avisa.                                                          |
//+------------------------------------------------------------------+
#property copyright   "Proyecto oro bitcoin - Raul"
#property version     "1.02"
#property description "Patron 123: lineas de tendencia tipo Joel (toque 3) a favor de la pierna."
#property description "Escaner: mercados en filas, temporalidades en columnas. Solo dibuja y avisa."
#property description "Herramienta visual: la regla no mostro ventaja en las pruebas."
#property indicator_chart_window
#property indicator_buffers 0
#property indicator_plots   0

enum ENUM_CONF
{
   CONF_TOCAR   = 0, // Al tocar la linea (sin esperar el cierre)
   CONF_RECHAZO = 1  // Vela de rechazo (al cierre de la vela)
};

input group "Linea (mismos valores que en las pruebas)"
input int       InpATR        = 14;           // Periodo ATR
input int       InpK          = 2;            // Velas a cada lado del punto de reaccion
input double    InpProfATR    = 1.0;          // Retroceso minimo entre punto 1 y 2 (en ATR)
input double    InpTolATR     = 0.1;          // Margen para contar un toque (en ATR)
input int       InpVida       = 60;           // Velas que la linea sigue viva tras validarse
input int       InpToqueMin   = 3;            // Avisar desde el toque...
input int       InpToqueMax   = 4;            // ...hasta el toque
input ENUM_CONF InpConf       = CONF_RECHAZO; // Confirmacion del toque
input int       InpBarras     = 1500;         // Velas a analizar en el grafico
input int       InpMaxLineas  = 12;           // Max. lineas dibujadas en el grafico

input group "Pierna (direccion del mercado)"
input bool      InpFiltroPierna = true;       // Solo avisar a favor de la pierna
input string    InpTFPierna     = "AUTO";     // AUTO (H1 hasta M15, H4 hasta H1, D1 mayores) o p.ej. H4

enum ENUM_LISTA
{
   LISTA_ESCRITA  = 0, // Input_Symbols (los que escribo abajo)
   LISTA_MERCADO  = 1, // MarketWatch_Symbols (Observacion del mercado)
   LISTA_TODOS    = 2  // All_General_List_Symbols (todos los del broker)
};

input group "Escaner"
input bool      InpEscaner    = true;                                          // Activar escaner
input ENUM_LISTA InpLista     = LISTA_ESCRITA;                                 // Which Symbol List (que mercados escanear)
input int       InpMaxMercados = 30;                                           // Max. mercados en el panel (listas automaticas)
input string    InpSimbolos   = "BTCUSD,ETHUSD,LTCUSD,XAUUSD_i,XAGUSD_i,SPXUSD"; // Mercados (separados por coma)
input string    InpTFs        = "M2,M3,M5,M6,M10,M15,M20,M30,H1";              // Temporalidades (o TODAS)
input int       InpBarrasEsc  = 800;          // Velas a analizar por celda
input int       InpVigencia   = 3;            // Velas que la celda queda resaltada
input bool      InpClicCambia = true;         // Clic en celda = cambiar el grafico a ese mercado/TF
input int       InpPanelX     = 10;           // Posicion X del panel
input int       InpPanelY     = 25;           // Posicion Y del panel
input int       InpAnchoCelda = 46;           // Ancho de celda
input int       InpAltoCelda  = 20;           // Alto de celda

input group "Alertas"
input bool      InpAlerta       = true;        // Ventana de alerta con sonido
input bool      InpSonido       = true;        // Sonido (si la ventana esta apagada)
input string    InpArchivoSonido= "alert.wav"; // Archivo de sonido (carpeta Sounds de MT5)
input bool      InpCelular      = true;        // Notificacion al celular (MetaQuotes ID)

input group "Dibujo"
input color     InpColorCompra = clrDodgerBlue; // Color compra (linea alcista)
input color     InpColorVenta  = clrRed;        // Color venta (linea bajista)
input color     InpColorTexto  = clrYellow;     // Numeros de los toques
input int       InpGrosor      = 2;             // Grosor de lineas

//--- una linea detectada (en precios "normales" para ventas; espejados para compras)
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

struct Celda { string sym; ENUM_TIMEFRAMES tf; datetime ultBarra; bool primera; bool valido;
               int dir; int toque; int edad; bool espera; int espDir; int espNum;
               double nivel; datetime velaToque; };

string   PFX  = "P123p_";
string   PFXS = "P123s_";
datetime g_ultimaVela = 0;
datetime g_ultimaAlerta = 0;
datetime g_ultToqueVivo = 0;
#define SIN_DATOS 99
int      g_piernaGraf = 0;
int      g_p1[], g_p4[];
bool     g_primera = true;

string          g_sims[];
ENUM_TIMEFRAMES g_tfs[];
string          g_tfn[];
Celda           g_cel[];
int             g_nS = 0, g_nT = 0;

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

ENUM_TIMEFRAMES TFPierna(ENUM_TIMEFRAMES tf)
{
   string t = InpTFPierna; StringToUpper(t); StringTrimLeft(t); StringTrimRight(t);
   if(t != "AUTO")
   {
      int k = BuscarTF(t);
      if(k >= 0) return TFV_ALL[k];
   }
   int seg = PeriodSeconds(tf);
   if(seg <= 15 * 60)   return PERIOD_H1;
   if(seg <= 60 * 60)   return PERIOD_H4;
   return PERIOD_D1;
}

//+------------------------------------------------------------------+
int OnInit()
{
   string id = IntegerToString(ChartID() % 100000);
   PFX  = "P123p_" + id + "_";
   PFXS = "P123s_" + id + "_";
   g_primera = true; g_ultimaVela = 0;
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
//| Calculos                                                         |
//+------------------------------------------------------------------+
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

//+------------------------------------------------------------------+
//| Dibujo                                                           |
//+------------------------------------------------------------------+
//--- objetos vigentes en este calculo (los demas se borran al final): asi no parpadean
string g_vivos[];
void Reg(string nm) { int n = ArraySize(g_vivos); ArrayResize(g_vivos, n + 1); g_vivos[n] = nm; }

void BorrarNoVigentes()
{
   for(int i = ObjectsTotal(0, -1, -1) - 1; i >= 0; i--)
   {
      string nm = ObjectName(0, i, -1, -1);
      if(StringFind(nm, PFX) != 0) continue;
      bool vigente = false;
      for(int k = 0; k < ArraySize(g_vivos); k++) if(g_vivos[k] == nm) { vigente = true; break; }
      if(!vigente) ObjectDelete(0, nm);
   }
}

void Linea(string nm, datetime t1, double p1, datetime t2, double p2, color col, int ancho, int estilo)
{
   if(ObjectFind(0, nm) < 0)
   {
      ObjectCreate(0, nm, OBJ_TREND, 0, t1, p1, t2, p2);
      ObjectSetInteger(0, nm, OBJPROP_RAY_RIGHT, false);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
   else { ObjectMove(0, nm, 0, t1, p1); ObjectMove(0, nm, 1, t2, p2); }
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, ancho);
   ObjectSetInteger(0, nm, OBJPROP_STYLE, estilo);
   Reg(nm);
}

void Texto(string nm, datetime t, double p, string txt, color col, ENUM_ANCHOR_POINT anc, int tam)
{
   if(ObjectFind(0, nm) < 0)
   {
      ObjectCreate(0, nm, OBJ_TEXT, 0, t, p);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
   else ObjectMove(0, nm, 0, t, p);
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, tam);
   ObjectSetInteger(0, nm, OBJPROP_ANCHOR, anc);
   Reg(nm);
}

void Flecha(string nm, bool venta, datetime t, double p, color col)
{
   if(ObjectFind(0, nm) < 0)
   {
      ObjectCreate(0, nm, venta ? OBJ_ARROW_SELL : OBJ_ARROW_BUY, 0, t, p);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
   else ObjectMove(0, nm, 0, t, p);
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_WIDTH, 3);
   Reg(nm);
}

void Etiqueta(string nm, int x, int y, string txt, color col, int tam)
{
   if(ObjectFind(0, nm) < 0)
   {
      ObjectCreate(0, nm, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, nm, OBJPROP_CORNER, CORNER_RIGHT_UPPER);
      ObjectSetInteger(0, nm, OBJPROP_ANCHOR, ANCHOR_RIGHT_UPPER);
      ObjectSetInteger(0, nm, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nm, OBJPROP_HIDDEN, true);
   }
   ObjectSetInteger(0, nm, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nm, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, nm, OBJPROP_TEXT, txt);
   ObjectSetString(0, nm, OBJPROP_FONT, "Arial Bold");
   ObjectSetInteger(0, nm, OBJPROP_COLOR, col);
   ObjectSetInteger(0, nm, OBJPROP_FONTSIZE, tam);
   Reg(nm);
}

bool ToqueEsSenal(const Lin &X, int z)
{
   if(X.tn[z] < InpToqueMin || X.tn[z] > InpToqueMax) return false;
   if(InpConf == CONF_RECHAZO && !X.tr[z]) return false;
   return true;
}

void Dibujar(const Lin &X, int k, const datetime &time[], const double &high[], const double &low[], int n)
{
   bool   venta = (X.dir == -1);
   color  col   = venta ? InpColorVenta : InpColorCompra;
   string base  = PFX + (venta ? "V" : "C") + IntegerToString((long)time[X.a]) + "_" + IntegerToString((long)time[X.b]) + "_";   // nombre fijo por linea
   int    fin   = MathMin(X.fin + (X.viva ? 3 : 1), n - 1);
   Linea(base + "l", time[X.a], PrecioLinea(X, X.a), time[fin], PrecioLinea(X, fin), col, InpGrosor,
         X.viva ? STYLE_SOLID : STYLE_DOT);
   ENUM_ANCHOR_POINT anc = venta ? ANCHOR_LOWER : ANCHOR_UPPER;
   Texto(base + "p1", time[X.a], venta ? high[X.a] : low[X.a], "1", InpColorTexto, anc, 10);
   Texto(base + "p2", time[X.b], venta ? high[X.b] : low[X.b], "2", InpColorTexto, anc, 10);
   for(int z = 0; z < X.nt; z++)
   {
      int i = X.ti[z];
      bool sen = ToqueEsSenal(X, z);
      string txt = IntegerToString(X.tn[z]) + (X.tr[z] ? "R" : "");
      Texto(base + "t" + IntegerToString(z), time[i], venta ? high[i] : low[i], txt,
            sen ? col : clrGray, anc, sen ? 11 : 9);
      if(sen)
      {
         Flecha(base + "f" + IntegerToString(z), venta, time[i], PrecioLinea(X, i), col);
      }
   }
}

//+------------------------------------------------------------------+
//| Alertas                                                          |
//+------------------------------------------------------------------+
void Avisar(string sym, ENUM_TIMEFRAMES tf, int dir, int toque, bool rechazo, bool enCurso, double nivel,
            int pierna, ENUM_TIMEFRAMES tfp, int digitos)
{
   string msg = StringFormat("PATRON 123: %s %s %s | toque %d%s | pierna %s %s | linea %s",
                             dir == -1 ? "VENTA" : "COMPRA", sym, NombreTFde(tf), toque,
                             enCurso ? " (tocando ahora)" : (rechazo ? " con vela de rechazo" : ""),
                             NombreTFde(tfp), TextoPierna(pierna), DoubleToString(nivel, digitos));
   if(InpAlerta)      Alert(msg);
   else if(InpSonido) PlaySound(InpArchivoSonido);
   if(InpCelular)
   {
      if(!SendNotification(msg))
         Print("Patron123: no se pudo enviar al celular (Herramientas > Opciones > Notificaciones). Error ",
               GetLastError());
   }
   Print(msg);
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
   ArraySetAsSeries(open, false);
   ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);
   ArraySetAsSeries(close, false);

   datetime vela = time[rates_total - 1];
   if(vela == g_ultimaVela && prev_calculated > 0) return(rates_total);
   g_ultimaVela = vela;

   int last = rates_total - 2;
   int from = MathMax(0, rates_total - InpBarras);
   Lin res[];
   Detectar(open, high, low, close, rates_total, from, last, res);

   ENUM_TIMEFRAMES tfp = TFPierna((ENUM_TIMEFRAMES)Period());
   int pn = Pierna(_Symbol, tfp);
   if(pn != SIN_DATOS) g_piernaGraf = pn;          // si los datos aun cargan, se mantiene la anterior
   int pierna = g_piernaGraf;

   // dibujar solo las lineas mas recientes que tienen toques o siguen vivas (sin borrar todo: no parpadea)
   ArrayResize(g_vivos, 0);
   int dibujadas = 0;
   for(int k = ArraySize(res) - 1; k >= 0 && dibujadas < InpMaxLineas; k--)
   {
      // las compras van despues de las ventas en res: recorrer por fecha de validacion
      int mejor = -1;
      for(int q = 0; q < ArraySize(res); q++)
         if(res[q].val >= 0 && (res[q].nt > 0 || res[q].viva) && (mejor < 0 || res[q].fin > res[mejor].fin)) mejor = q;
      if(mejor < 0) break;
      if(!InpFiltroPierna || pierna == 0 || res[mejor].dir == pierna)
      { Dibujar(res[mejor], dibujadas, time, high, low, rates_total); dibujadas++; }
      res[mejor].val = -1;   // marcar como usada
   }
   Etiqueta(PFX + "pierna", 10, 20, "Pierna " + NombreTFde(tfp) + ": " + TextoPierna(pierna) +
            (pierna == 1 ? "  (solo compras)" : (pierna == -1 ? "  (solo ventas)" : "")),
            pierna == 1 ? InpColorCompra : (pierna == -1 ? InpColorVenta : clrGray), 11);
   BorrarNoVigentes();

   // alertas del grafico (si el escaner esta activo, el escaner avisa por todos)
   if(!InpEscaner && !g_primera && time[last] > g_ultimaAlerta)
   {
      Lin r2[];
      Detectar(open, high, low, close, rates_total, from, last, r2);
      for(int k = 0; k < ArraySize(r2); k++)
         for(int z = 0; z < r2[k].nt; z++)
            if(r2[k].ti[z] == last && ToqueEsSenal(r2[k], z) && InpConf == CONF_RECHAZO &&
               (!InpFiltroPierna || r2[k].dir == pierna))
               Avisar(_Symbol, (ENUM_TIMEFRAMES)Period(), r2[k].dir, r2[k].tn[z], true, false,
                      PrecioLinea(r2[k], last), pierna, tfp, _Digits);
      g_ultimaAlerta = time[last];
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
   ArrayResize(g_sims, 0);
   if(InpLista == LISTA_ESCRITA)
   {
      string partes[];
      int ns = StringSplit(InpSimbolos, ',', partes);
      for(int i = 0; i < ns; i++)
      {
         string s = partes[i];
         StringTrimLeft(s); StringTrimRight(s);
         if(StringLen(s) == 0) continue;
         int n = ArraySize(g_sims); ArrayResize(g_sims, n + 1); g_sims[n] = s;
         SymbolSelect(s, true);
      }
   }
   else
   {
      bool soloMercado = (InpLista == LISTA_MERCADO);
      int tot = SymbolsTotal(soloMercado);
      for(int i = 0; i < tot && ArraySize(g_sims) < InpMaxMercados; i++)
      {
         string s = SymbolName(i, soloMercado);
         if(StringLen(s) == 0) continue;
         // solo mercados que se pueden operar (los de "solo cierre" o deshabilitados no sirven)
         if((ENUM_SYMBOL_TRADE_MODE)SymbolInfoInteger(s, SYMBOL_TRADE_MODE) != SYMBOL_TRADE_MODE_FULL) continue;
         int n = ArraySize(g_sims); ArrayResize(g_sims, n + 1); g_sims[n] = s;
         if(!soloMercado) SymbolSelect(s, true);
      }
      if(tot > InpMaxMercados)
         Print("Patron123: la lista tiene ", tot, " mercados; se muestran hasta ", InpMaxMercados,
               " (cambia 'Max. mercados en el panel').");
   }
   g_nS = ArraySize(g_sims);
   ArrayResize(g_p1, g_nS); ArrayResize(g_p4, g_nS);
   for(int i = 0; i < g_nS; i++) { g_p1[i] = 0; g_p4[i] = 0; }

   ArrayResize(g_tfs, 0); ArrayResize(g_tfn, 0);
   string t = InpTFs;
   StringToUpper(t); StringTrimLeft(t); StringTrimRight(t);
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
         if(k < 0) { Print("Patron123: temporalidad no reconocida: ", s); continue; }
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
         g_cel[c].dir = 0; g_cel[c].toque = 0; g_cel[c].edad = -1;
         g_cel[c].espera = false; g_cel[c].espDir = 0; g_cel[c].espNum = 0; g_cel[c].nivel = 0;
         g_cel[c].velaToque = 0;
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

int WN() { return 90; }
int WP() { return 58; }

void PanelCrear()
{
   int x0 = InpPanelX, y0 = InpPanelY, w = InpAnchoCelda, h = InpAltoCelda, wn = WN(), wp = WP();
   color cab = C'45,45,45', fondo = C'25,25,25';
   Caja(PFXS + "titulo", x0, y0, wn + 2 * wp + w * g_nT, h,
        "PATRON 123   (V = venta, C = compra, numero = toque, R = rechazo, ? = esperando toque)", cab, clrWhite, false);
   Caja(PFXS + "hm", x0, y0 + h, wn, h, "Mercado", cab, clrSilver, false);
   Caja(PFXS + "hp1", x0 + wn, y0 + h, wp, h, "Pierna H1", cab, clrSilver, false);
   Caja(PFXS + "hp4", x0 + wn + wp, y0 + h, wp, h, "Pierna H4", cab, clrSilver, false);
   for(int k = 0; k < g_nT; k++)
      Caja(PFXS + "h_" + IntegerToString(k), x0 + wn + 2 * wp + k * w, y0 + h, w, h, g_tfn[k], cab, clrSilver, false);
   for(int s = 0; s < g_nS; s++)
   {
      Caja(PFXS + "s_" + IntegerToString(s), x0, y0 + h * (s + 2), wn, h, g_sims[s], cab, clrWhite, false);
      Caja(PFXS + "p1_" + IntegerToString(s), x0 + wn, y0 + h * (s + 2), wp, h, "...", fondo, clrGray, false);
      Caja(PFXS + "p4_" + IntegerToString(s), x0 + wn + wp, y0 + h * (s + 2), wp, h, "...", fondo, clrGray, false);
      for(int k = 0; k < g_nT; k++)
         Caja(PFXS + "c_" + IntegerToString(s) + "_" + IntegerToString(k),
              x0 + wn + 2 * wp + k * w, y0 + h * (s + 2), w, h, "...", fondo, clrGray, true);
   }
   ChartRedraw();
}

void PanelPierna(int s)
{
   int x0 = InpPanelX, y0 = InpPanelY, h = InpAltoCelda, wn = WN(), wp = WP();
   int a1 = Pierna(g_sims[s], PERIOD_H1), a4 = Pierna(g_sims[s], PERIOD_H4);
   if(a1 != SIN_DATOS) g_p1[s] = a1;
   if(a4 != SIN_DATOS) g_p4[s] = a4;
   int p1 = g_p1[s], p4 = g_p4[s];
   Caja(PFXS + "p1_" + IntegerToString(s), x0 + wn, y0 + h * (s + 2), wp, h,
        p1 == 1 ? "ALZA" : (p1 == -1 ? "BAJA" : "-"),
        p1 == 1 ? C'20,60,110' : (p1 == -1 ? C'110,25,25' : C'25,25,25'), clrWhite, false);
   Caja(PFXS + "p4_" + IntegerToString(s), x0 + wn + wp, y0 + h * (s + 2), wp, h,
        p4 == 1 ? "ALZA" : (p4 == -1 ? "BAJA" : "-"),
        p4 == 1 ? C'20,60,110' : (p4 == -1 ? C'110,25,25' : C'25,25,25'), clrWhite, false);
}

void PanelCelda(int s, int k)
{
   int c = s * g_nT + k;
   string txt = "-";
   color  bg = C'25,25,25', fg = clrGray;
   if(!g_cel[c].valido) { txt = "sin datos"; fg = C'90,90,90'; }
   else if(g_cel[c].edad >= 0 && g_cel[c].edad < InpVigencia)
   {
      txt = (g_cel[c].dir == -1 ? "V" : "C") + IntegerToString(g_cel[c].toque) + " " + IntegerToString(g_cel[c].edad);
      bg = (g_cel[c].dir == -1) ? InpColorVenta : InpColorCompra; fg = clrWhite;
   }
   else if(g_cel[c].espera)
   {
      txt = (g_cel[c].espDir == -1 ? "V" : "C") + IntegerToString(g_cel[c].espNum) + "?";
      fg = (g_cel[c].espDir == -1) ? C'230,120,120' : C'120,170,230';
      bg = C'45,45,30';
   }
   else if(g_cel[c].edad >= 0)
   {
      txt = (g_cel[c].dir == -1 ? "V" : "C") + IntegerToString(g_cel[c].toque) + " " + IntegerToString(g_cel[c].edad);
      fg = (g_cel[c].dir == -1) ? C'200,110,110' : C'110,150,200';
   }
   int x0 = InpPanelX, y0 = InpPanelY, w = InpAnchoCelda, h = InpAltoCelda, wn = WN(), wp = WP();
   Caja(PFXS + "c_" + IntegerToString(s) + "_" + IntegerToString(k),
        x0 + wn + 2 * wp + k * w, y0 + h * (s + 2), w, h, txt, bg, fg, true);
}

void EscanearCelda(int s, int k)
{
   int c = s * g_nT + k;
   string sym = g_cel[c].sym;
   ENUM_TIMEFRAMES tf = g_cel[c].tf;
   ENUM_TIMEFRAMES tfp = TFPierna(tf);
   datetime t0 = iTime(sym, tf, 0);
   if(t0 == 0) { g_cel[c].valido = false; return; }
   int digitos = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);

   // 1) vela nueva: recalcular lineas y avisar toques confirmados en la vela recien cerrada
   if(t0 != g_cel[c].ultBarra)
   {
      MqlRates r[];
      int n = CopyRates(sym, tf, 0, InpBarrasEsc, r);
      if(n < 100) { g_cel[c].valido = false; return; }
      double oo[], hh[], ll[], cc[];
      ArrayResize(oo, n); ArrayResize(hh, n); ArrayResize(ll, n); ArrayResize(cc, n);
      for(int i = 0; i < n; i++) { oo[i] = r[i].open; hh[i] = r[i].high; ll[i] = r[i].low; cc[i] = r[i].close; }
      int last = n - 2;
      Lin res[];
      Detectar(oo, hh, ll, cc, n, 0, last, res);
      int pierna = Pierna(sym, tfp);
      if(pierna == SIN_DATOS) return;              // datos de la pierna aun cargando: se reintenta en 2 s
      double ap[]; ATRprev(hh, ll, cc, n, ap);

      g_cel[c].valido = true;
      g_cel[c].edad = -1; g_cel[c].espera = false;
      int mejorI = -1;
      for(int q = 0; q < ArraySize(res); q++)
      {
         if(InpFiltroPierna && res[q].dir != pierna) continue;
         for(int z = 0; z < res[q].nt; z++)
            if(ToqueEsSenal(res[q], z) && res[q].ti[z] > mejorI)
            { mejorI = res[q].ti[z]; g_cel[c].dir = res[q].dir; g_cel[c].toque = res[q].tn[z]; g_cel[c].edad = last - mejorI; }
         // linea esperando su proximo toque (la mas cercana al precio)
         if(res[q].lista && res[q].prox >= InpToqueMin && res[q].prox <= InpToqueMax)
         {
            double nv = NivelToque(res[q], n - 1, ap);
            if(!g_cel[c].espera || MathAbs(nv - cc[last]) < MathAbs(g_cel[c].nivel - cc[last]))
            { g_cel[c].espera = true; g_cel[c].espDir = res[q].dir; g_cel[c].espNum = res[q].prox; g_cel[c].nivel = nv; }
         }
      }
      if(!g_cel[c].primera && InpConf == CONF_RECHAZO)
         for(int q = 0; q < ArraySize(res); q++)
         {
            if(InpFiltroPierna && res[q].dir != pierna) continue;
            for(int z = 0; z < res[q].nt; z++)
               if(res[q].ti[z] == last && ToqueEsSenal(res[q], z))
                  Avisar(sym, tf, res[q].dir, res[q].tn[z], true, false, PrecioLinea(res[q], last),
                         pierna, tfp, digitos);
         }
      g_cel[c].primera = false;
      g_cel[c].ultBarra = t0;
   }

   // 2) modo "al tocar": avisar en cuanto el precio llega a la linea que espera su toque (una vez por vela)
   if(InpConf == CONF_TOCAR && g_cel[c].espera && g_cel[c].velaToque != t0)
   {
      double hi = iHigh(sym, tf, 0), lo = iLow(sym, tf, 0);
      bool toca = (g_cel[c].espDir == -1) ? (hi >= g_cel[c].nivel) : (lo <= g_cel[c].nivel);
      if(toca)
      {
         g_cel[c].velaToque = t0;
         int pp = Pierna(sym, tfp);
         Avisar(sym, tf, g_cel[c].espDir, g_cel[c].espNum, false, true, g_cel[c].nivel,
                pp == SIN_DATOS ? 0 : pp, tfp, digitos);
         g_cel[c].dir = g_cel[c].espDir; g_cel[c].toque = g_cel[c].espNum; g_cel[c].edad = 0;
      }
   }
}

void OnTimer()
{
   if(!InpEscaner) return;
   for(int s = 0; s < g_nS; s++)
   {
      PanelPierna(s);
      for(int k = 0; k < g_nT; k++)
      {
         EscanearCelda(s, k);
         PanelCelda(s, k);
      }
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
