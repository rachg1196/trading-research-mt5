//+------------------------------------------------------------------+
//|                                                 EMAs_Escaner.mq5 |
//|  Patrón de 3 EMAs (30/50/100) con las reglas aprobadas (Rev. 5)  |
//|  - Dibuja las EMAs y marca los patrones en el gráfico.           |
//|  - Escáner: filas = mercados, columnas = temporalidades.         |
//|  - Alertas en pantalla, sonido y celular (push de MT5).          |
//|  SOLO AVISA. No abre, cierra ni modifica operaciones.            |
//+------------------------------------------------------------------+
#property copyright   "Proyecto EMAs (Raul)"
#property version     "1.01"
#property description "EMAs 30/50/100, marcas del patrón y escáner de mercados y temporalidades."
#property description "Alertas en pantalla, sonido y celular. Solo avisa: no opera."
#property indicator_chart_window
#property indicator_buffers 3
#property indicator_plots   3
#property indicator_label1  "EMA 30"
#property indicator_type1   DRAW_LINE
#property indicator_color1  clrWhite
#property indicator_width1  1
#property indicator_label2  "EMA 50"
#property indicator_type2   DRAW_LINE
#property indicator_color2  clrGold
#property indicator_width2  1
#property indicator_label3  "EMA 100"
#property indicator_type3   DRAW_LINE
#property indicator_color3  clrBlack
#property indicator_width3  1

//--- El primer parámetro va SIN grupo: así se puede abrir otro gráfico con el escáner apagado.
input bool   InpMostrarEscaner   = true;   // Mostrar escáner y enviar alertas (ponlo en UN solo gráfico)

input group "Patrón (valores aprobados en el backtest)"
input double InpSeparacion       = 0.25;   // Separación mínima entre EMAs (en velas medias)
input int    InpVelasSinCruce    = 10;     // Velas sin cruce de EMAs (en la confirmación)
input int    InpMaxMaximoToque   = 20;     // Velas máx. del máximo al toque de la EMA 30
input int    InpMaxToqueRuptura  = 20;     // Velas máx. del toque a la ruptura de la zona
input int    InpMaxRupturaConf   = 10;     // Velas máx. de la ruptura a la confirmación

input group "Escáner"
input string InpSimbolos         = "";     // Mercados separados por comas (vacío = todos los de Observación de mercado)
input string InpTemporalidades   = "M1,M2,M3,M4,M5,M6,M10,M12,M15,M20,M30,H1,H2,H3,H4,H6,H8,H12,D1,W1,MN1"; // Temporalidades
input int    InpVelasAnalisis    = 1500;   // Velas que se analizan por mercado y temporalidad
input int    InpParesPorSegundo  = 60;     // Combinaciones que se revisan por segundo

input group "Alertas"
input bool   InpAlertaPantalla   = true;   // Ventana de alerta en MT5
input bool   InpAlertaSonido     = true;   // Sonido
input string InpSonido           = "alert.wav"; // Archivo de sonido (carpeta Sounds de MT5)
input bool   InpAlertaCelular    = true;   // Enviar al celular (push, requiere MetaQuotes ID)
input bool   InpAlertaEmail      = false;  // Enviar e-mail (requiere configurarlo en MT5)
input bool   InpAlertarTardias   = true;   // Avisar también señales de 1 a 3 velas atrás (regla 5)

input group "Gráfico"
input bool   InpDibujarEMAs      = true;   // Dibujar las 3 EMAs
input bool   InpMarcarPatrones   = true;   // Marcar en el gráfico los patrones encontrados
input int    InpVelasMarcar      = 3000;   // Velas del gráfico donde se buscan patrones
input color  InpColor30          = clrWhite;     // Color EMA 30
input color  InpColor50          = clrGold;      // Color EMA 50
input color  InpColor100         = clrBlack;     // Color EMA 100
input color  InpColorZona        = clrSteelBlue; // Color de la zona

#define PFX            "EMASC|"
#define MK             "EMAMK|"
#define CALENTAMIENTO  500
#define VM_VELAS       20

double B30[], B50[], B100[];

struct Senal
  {
   int      m;      // vela del máximo (mínimo en venta)
   int      t;      // toque a la EMA 30
   int      b;      // ruptura de la zona
   int      c;      // vela de confirmación
   int      dir;    // 1 compra, -1 venta
   double   techo;  // borde exterior de la zona
   double   suelo;  // borde del cuerpo
  };

struct Par
  {
   int      s;
   int      k;
   datetime ultBarra;
   int      dir;
   int      quedan;
   datetime tConf;
   bool     sinDatos;
  };

string          TODOS_NOM[21] = {"M1","M2","M3","M4","M5","M6","M10","M12","M15","M20","M30",
                                 "H1","H2","H3","H4","H6","H8","H12","D1","W1","MN1"};
ENUM_TIMEFRAMES TODOS_TF[21]  = {PERIOD_M1,PERIOD_M2,PERIOD_M3,PERIOD_M4,PERIOD_M5,PERIOD_M6,
                                 PERIOD_M10,PERIOD_M12,PERIOD_M15,PERIOD_M20,PERIOD_M30,
                                 PERIOD_H1,PERIOD_H2,PERIOD_H3,PERIOD_H4,PERIOD_H6,PERIOD_H8,
                                 PERIOD_H12,PERIOD_D1,PERIOD_W1,PERIOD_MN1};

string          g_sym[];
string          g_tfNom[];
ENUM_TIMEFRAMES g_tf[];
Par             g_par[];
string          g_ultimas[];
string          g_cola[];
int             g_cursor = 0;
int             g_top = 0;
int             g_filasVis = 0;
int             g_filasDibujadas = 0;
bool            g_redibujar = true;
datetime        g_ultPush = 0;
datetime        g_barraGrafico = 0;
bool            g_avisoPush = false;
string          ARRIBA = "";
string          ABAJO = "";

//+------------------------------------------------------------------+
//| Utilidades                                                       |
//+------------------------------------------------------------------+
int Separar(string texto, string &out[])
  {
   ArrayResize(out, 0);
   string partes[];
   int n = StringSplit(texto, ',', partes);
   for(int i = 0; i < n; i++)
     {
      string p = partes[i];
      StringTrimLeft(p);
      StringTrimRight(p);
      if(p == "")
         continue;
      int z = ArraySize(out);
      ArrayResize(out, z + 1);
      out[z] = p;
     }
   return ArraySize(out);
  }

int Signo(double x)
  {
   if(x > 0)
      return 1;
   if(x < 0)
      return -1;
   return 0;
  }

void CalcEMA(const double &src[], int n, int periodo, double &dst[])
  {
   ArrayResize(dst, n);
   if(n <= 0)
      return;
   double a = 2.0 / (periodo + 1.0);
   dst[0] = src[0];
   for(int i = 1; i < n; i++)
      dst[i] = a * src[i] + (1.0 - a) * dst[i - 1];
  }

void AgregarSenal(Senal &out[], int m, int t, int b, int c, int dir, double techo, double suelo)
  {
   int z = ArraySize(out);
   ArrayResize(out, z + 1);
   out[z].m = m;
   out[z].t = t;
   out[z].b = b;
   out[z].c = c;
   out[z].dir = dir;
   out[z].techo = (dir > 0 ? techo : -techo);
   out[z].suelo = (dir > 0 ? suelo : -suelo);
  }

//+------------------------------------------------------------------+
//| Detector (COMPRA). La VENTA usa los precios reflejados.          |
//| Arrays en orden cronológico (0 = vela más antigua), solo velas    |
//| cerradas.                                                         |
//+------------------------------------------------------------------+
void DetectarDir(const double &O[], const double &H[], const double &L[], const double &C[],
                 int n, int dir, Senal &out[])
  {
   if(n <= CALENTAMIENTO + 2)
      return;

   double e30[], e50[], e100[], vm[];
   CalcEMA(C, n, 30, e30);
   CalcEMA(C, n, 50, e50);
   CalcEMA(C, n, 100, e100);

   ArrayResize(vm, n);
   for(int i = 0; i < n; i++)
     {
      int desde = (i - VM_VELAS + 1 > 0 ? i - VM_VELAS + 1 : 0);
      double suma = 0;
      for(int j = desde; j <= i; j++)
         suma += H[j] - L[j];
      vm[i] = suma / (i - desde + 1);
     }

   bool alin[];
   bool cruce[];
   int  ultCruce[];
   ArrayResize(alin, n);
   ArrayResize(cruce, n);
   ArrayResize(ultCruce, n);
   int uc = 0;
   for(int i = 0; i < n; i++)
     {
      bool orden = (e100[i] < e50[i] && e50[i] < e30[i]);
      double sep = InpSeparacion * vm[i];
      alin[i] = (orden && (e30[i] - e50[i]) >= sep && (e50[i] - e100[i]) >= sep);
      cruce[i] = false;
      if(i > 0)
        {
         if(Signo(e30[i] - e50[i]) != Signo(e30[i - 1] - e50[i - 1]) ||
            Signo(e50[i] - e100[i]) != Signo(e50[i - 1] - e100[i - 1]) ||
            Signo(e30[i] - e100[i]) != Signo(e30[i - 1] - e100[i - 1]))
            cruce[i] = true;
        }
      if(cruce[i])
         uc = i;
      ultCruce[i] = uc;
     }

   // Estados: 0 espera cruce, 1 busca toque, 2 retroceso (espera ruptura), 3 roto (espera confirmación)
   int estado = 0, origen = -1, m = -1, t = -1, b = -1;
   double techo = 0, suelo = 0;

   for(int i = (CALENTAMIENTO > 1 ? CALENTAMIENTO : 1); i < n; i++)
     {
      if(cruce[i] && (estado == 0 || estado == 1))
        {
         estado = 1;
         origen = i;
         continue;   // la vela del cruce no cuenta como toque
        }
      if(estado == 0)
         continue;

      if(estado == 1)
        {
         // Primer retroceso: toque a la EMA 30 con las EMAs ordenadas y separadas
         if(!alin[i] || !(L[i] <= e30[i]))
            continue;
         m = origen;
         for(int k = origen; k < i; k++)
            if(H[k] >= H[m])
               m = k;   // máximo más alto desde el cruce (en empate, el más reciente)
         t = i;
         techo = H[m];
         suelo = MathMax(O[m], C[m]);
         bool ok = true;
         if(t - m > InpMaxMaximoToque)
            ok = false;
         else
            if(!(techo - suelo > 0))
               ok = false;            // sin mecha no hay zona
            else
              {
               for(int k = m; k <= t; k++)
                  if(!alin[k])
                    {
                     ok = false;
                     break;
                    }
              }
         if(ok && L[i] <= e100[i])
            ok = false;               // tocó la EMA 100
         estado = (ok ? 2 : 0);
         continue;
        }

      if(estado == 2)
        {
         if(!alin[i] || L[i] <= e100[i] || i - t > InpMaxToqueRuptura)
           {
            estado = 0;
            continue;
           }
         if(C[i] > techo)
           {
            b = i;
            estado = 3;               // la confirmación será una vela posterior
           }
         continue;
        }

      if(estado == 3)
        {
         if(!alin[i] || L[i] <= e30[i] || i - b > InpMaxRupturaConf)
           {
            estado = 0;               // perdió armonía, tocó la EMA 30 o se acabó el tiempo
            continue;
           }
         if(L[i] <= techo)            // la vela toca la zona
           {
            if(C[i] < suelo || i - ultCruce[i] < InpVelasSinCruce)
              {
               estado = 0;            // cerró bajo la zona o EMAs recién cruzadas
               continue;
              }
            AgregarSenal(out, m, t, b, i, dir, techo, suelo);
            estado = 0;
           }
        }
     }
  }

void DetectarAmbos(const double &o[], const double &h[], const double &l[], const double &c[],
                   int n, Senal &out[])
  {
   ArrayResize(out, 0);
   DetectarDir(o, h, l, c, n, 1, out);
   double O2[], H2[], L2[], C2[];
   ArrayResize(O2, n);
   ArrayResize(H2, n);
   ArrayResize(L2, n);
   ArrayResize(C2, n);
   for(int i = 0; i < n; i++)
     {
      O2[i] = -o[i];
      H2[i] = -l[i];
      L2[i] = -h[i];
      C2[i] = -c[i];
     }
   DetectarDir(O2, H2, L2, C2, n, -1, out);
  }

//+------------------------------------------------------------------+
//| Objetos del panel                                                |
//+------------------------------------------------------------------+
void Boton(string nombre, int x, int y, int w, int h, string texto, color fondo, color letra, int tam = 8)
  {
   if(ObjectFind(0, nombre) < 0)
     {
      ObjectCreate(0, nombre, OBJ_BUTTON, 0, 0, 0);
      ObjectSetInteger(0, nombre, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, nombre, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nombre, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, nombre, OBJPROP_BACK, false);
      ObjectSetInteger(0, nombre, OBJPROP_ZORDER, 10);
      ObjectSetString(0, nombre, OBJPROP_FONT, "Arial");
     }
   ObjectSetInteger(0, nombre, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nombre, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, nombre, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, nombre, OBJPROP_YSIZE, h);
   ObjectSetString(0, nombre, OBJPROP_TEXT, texto);
   ObjectSetInteger(0, nombre, OBJPROP_BGCOLOR, fondo);
   ObjectSetInteger(0, nombre, OBJPROP_COLOR, letra);
   ObjectSetInteger(0, nombre, OBJPROP_BORDER_COLOR, C'20,20,20');
   ObjectSetInteger(0, nombre, OBJPROP_FONTSIZE, tam);
   ObjectSetInteger(0, nombre, OBJPROP_STATE, false);
  }

void Etiqueta(string nombre, int x, int y, string texto, color letra, int tam = 8)
  {
   if(ObjectFind(0, nombre) < 0)
     {
      ObjectCreate(0, nombre, OBJ_LABEL, 0, 0, 0);
      ObjectSetInteger(0, nombre, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, nombre, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nombre, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, nombre, OBJPROP_ZORDER, 11);
      ObjectSetString(0, nombre, OBJPROP_FONT, "Arial");
     }
   ObjectSetInteger(0, nombre, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nombre, OBJPROP_YDISTANCE, y);
   ObjectSetString(0, nombre, OBJPROP_TEXT, texto);
   ObjectSetInteger(0, nombre, OBJPROP_COLOR, letra);
   ObjectSetInteger(0, nombre, OBJPROP_FONTSIZE, tam);
  }

void Fondo(string nombre, int x, int y, int w, int h)
  {
   if(ObjectFind(0, nombre) < 0)
     {
      ObjectCreate(0, nombre, OBJ_RECTANGLE_LABEL, 0, 0, 0);
      ObjectSetInteger(0, nombre, OBJPROP_CORNER, CORNER_LEFT_UPPER);
      ObjectSetInteger(0, nombre, OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, nombre, OBJPROP_HIDDEN, true);
      ObjectSetInteger(0, nombre, OBJPROP_BACK, false);
      ObjectSetInteger(0, nombre, OBJPROP_ZORDER, 5);
      ObjectSetInteger(0, nombre, OBJPROP_BGCOLOR, C'25,25,25');
      ObjectSetInteger(0, nombre, OBJPROP_BORDER_TYPE, BORDER_FLAT);
      ObjectSetInteger(0, nombre, OBJPROP_COLOR, C'70,70,70');
     }
   ObjectSetInteger(0, nombre, OBJPROP_XDISTANCE, x);
   ObjectSetInteger(0, nombre, OBJPROP_YDISTANCE, y);
   ObjectSetInteger(0, nombre, OBJPROP_XSIZE, w);
   ObjectSetInteger(0, nombre, OBJPROP_YSIZE, h);
  }

int Analizados()
  {
   int n = 0;
   for(int i = 0; i < ArraySize(g_par); i++)
      if(g_par[i].ultBarra != 0)
         n++;
   return n;
  }

void DibujarPanel()
  {
   g_redibujar = false;
   int nS = ArraySize(g_sym);
   int nT = ArraySize(g_tf);
   if(nS == 0 || nT == 0)
      return;

   int x0 = 10, y0 = 24, wS = 120, wT = 36, hF = 18, hH = 20;
   int alto = (int)ChartGetInteger(0, CHART_HEIGHT_IN_PIXELS);
   int caben = (alto - y0 - 20 - hH - 52) / hF;
   if(caben < 3)
      caben = 3;
   g_filasVis = (caben < nS ? caben : nS);
   if(g_top > nS - g_filasVis)
      g_top = nS - g_filasVis;
   if(g_top < 0)
      g_top = 0;

   int ancho = wS + nT * wT;
   int altoPanel = 20 + hH + g_filasVis * hF + 50;
   Fondo(PFX + "fondo", x0 - 6, y0 - 6, ancho + 12, altoPanel + 12);
   Etiqueta(PFX + "titulo", x0, y0, "ESCÁNER EMAs 30/50/100   " + ARRIBA + " compra   " + ABAJO +
            " venta   número = velas que quedan   clic = abrir gráfico", clrWhite, 9);

   int yH = y0 + 20;
   Boton(PFX + "hm", x0, yH, wS, hH, "Mercado", C'20,60,110', clrWhite);
   for(int k = 0; k < nT; k++)
      Boton(PFX + "h|" + (string)k, x0 + wS + k * wT, yH, wT, hH, g_tfNom[k], C'20,60,110', clrWhite);

   for(int r = g_filasVis; r < g_filasDibujadas; r++)
     {
      ObjectDelete(0, PFX + "s|" + (string)r);
      for(int k = 0; k < nT; k++)
         ObjectDelete(0, PFX + "c|" + (string)r + "|" + (string)k);
     }
   g_filasDibujadas = g_filasVis;

   for(int r = 0; r < g_filasVis; r++)
     {
      int s = g_top + r;
      int y = yH + hH + r * hF;
      Boton(PFX + "s|" + (string)r, x0, y, wS, hF, g_sym[s], C'35,35,35', clrWhite);
      for(int k = 0; k < nT; k++)
        {
         int idx = s * nT + k;
         string txt = "·";
         color bg = C'45,45,45';
         color fg = C'110,110,110';
         if(g_par[idx].ultBarra == 0)
            txt = "…";
         else
            if(g_par[idx].sinDatos)
              {
               txt = "–";
               bg = C'32,32,32';
              }
            else
               if(g_par[idx].dir > 0)
                 {
                  txt = ARRIBA + (string)g_par[idx].quedan;
                  bg = clrForestGreen;
                  fg = clrWhite;
                 }
               else
                  if(g_par[idx].dir < 0)
                    {
                     txt = ABAJO + (string)g_par[idx].quedan;
                     bg = C'178,34,34';
                     fg = clrWhite;
                    }
         Boton(PFX + "c|" + (string)r + "|" + (string)k, x0 + wS + k * wT, y, wT, hF, txt, bg, fg);
        }
     }

   int yPie = yH + hH + g_filasVis * hF + 6;
   Etiqueta(PFX + "leyenda", x0, yPie,
            "–  pocas velas para analizar      …  cargando datos      Mercados " +
            (string)(g_top + 1) + "-" + (string)(g_top + g_filasVis) + " de " + (string)nS, C'170,170,170', 8);
   Etiqueta(PFX + "estado", x0, yPie + 18, "Analizados " + (string)Analizados() + " de " +
            (string)ArraySize(g_par) + "   ·   " + TimeToString(TimeCurrent(), TIME_SECONDS), C'170,170,170', 8);
   if(nS > g_filasVis)
     {
      Boton(PFX + "arriba", x0 + ancho - 70, yPie, 32, 18, ARRIBA, C'60,60,60', clrWhite);
      Boton(PFX + "abajo", x0 + ancho - 34, yPie, 32, 18, ABAJO, C'60,60,60', clrWhite);
     }
   else
     {
      ObjectDelete(0, PFX + "arriba");
      ObjectDelete(0, PFX + "abajo");
     }

   // Últimas señales, a la derecha de la tabla
   int xU = x0 + ancho + 14;
   Fondo(PFX + "fondoU", xU - 6, y0 - 6, 330, 20 + 16 * 15 + 12);
   Etiqueta(PFX + "tituloU", xU, y0, "ÚLTIMAS SEÑALES (hora del servidor)", clrWhite, 9);
   for(int i = 0; i < 15; i++)
     {
      string txt = (i < ArraySize(g_ultimas) ? g_ultimas[i] : " ");
      color col = C'170,170,170';
      if(StringFind(txt, "COMPRA") >= 0)
         col = clrLimeGreen;
      if(StringFind(txt, "VENTA") >= 0)
         col = clrTomato;
      Etiqueta(PFX + "u|" + (string)i, xU, y0 + 20 + i * 16, txt, col, 8);
     }
   ChartRedraw(0);
  }

void ActualizarEstado()
  {
   if(ObjectFind(0, PFX + "estado") < 0)
      return;
   ObjectSetString(0, PFX + "estado", OBJPROP_TEXT, "Analizados " + (string)Analizados() + " de " +
                   (string)ArraySize(g_par) + "   ·   " + TimeToString(TimeCurrent(), TIME_SECONDS));
  }

//+------------------------------------------------------------------+
//| Alertas                                                          |
//+------------------------------------------------------------------+
void Avisar(int idx, int sc)
  {
   string sym = g_sym[g_par[idx].s];
   string tfn = g_tfNom[g_par[idx].k];
   string lado = (g_par[idx].dir > 0 ? "COMPRA" : "VENTA");
   int quedan = 5 - sc;

   // No repetir la misma señal aunque se reinicie el indicador
   string clave = "EMAsA_" + sym + "_" + tfn + "_" + (string)g_par[idx].dir;
   if(StringLen(clave) > 63)
      clave = StringSubstr(clave, 0, 63);
   if(GlobalVariableCheck(clave) && (datetime)(long)GlobalVariableGet(clave) == g_par[idx].tConf)
      return;
   GlobalVariableSet(clave, (double)(long)g_par[idx].tConf);

   string cuando = (sc == 1 ? "entrar ahora" : "señal tardía");
   string msg = StringFormat("EMAs 30/50/100: %s en %s %s - %s - quedan %d velas (salida al cierre de la 4.ª vela)",
                             lado, sym, tfn, cuando, quedan);

   string linea = TimeToString(TimeCurrent(), TIME_DATE | TIME_MINUTES) + "  " + lado + "  " + sym + "  " +
                  tfn + "  (quedan " + (string)quedan + ")";
   int n = ArraySize(g_ultimas);
   int nuevo = (n < 15 ? n + 1 : 15);
   ArrayResize(g_ultimas, nuevo);
   for(int i = nuevo - 1; i > 0; i--)
      g_ultimas[i] = g_ultimas[i - 1];
   g_ultimas[0] = linea;

   if(InpAlertaPantalla)
      Alert(msg);
   else
      if(InpAlertaSonido)
         PlaySound(InpSonido);
   if(InpAlertaPantalla && InpAlertaSonido && InpSonido != "alert.wav")
      PlaySound(InpSonido);

   if(InpAlertaCelular)
     {
      int z = ArraySize(g_cola);
      ArrayResize(g_cola, z + 1);
      g_cola[z] = lado + " " + sym + " " + tfn + " (quedan " + (string)quedan + ")";
     }
   if(InpAlertaEmail)
      SendMail("Señal EMAs: " + lado + " " + sym + " " + tfn, msg);
   Print(msg);
   g_redibujar = true;
  }

// MT5 permite pocas notificaciones por minuto: se agrupan y se envían cada 7 segundos.
void EnviarCola()
  {
   int n = ArraySize(g_cola);
   if(n == 0)
      return;
   if(TimeLocal() - g_ultPush < 7)
      return;
   string texto = "EMAs: ";
   int usados = 0;
   for(int i = 0; i < n; i++)
     {
      string sep = (usados == 0 ? "" : " | ");
      if(StringLen(texto) + StringLen(sep) + StringLen(g_cola[i]) > 250)
         break;
      texto += sep + g_cola[i];
      usados++;
     }
   if(usados == 0)
     {
      texto = StringSubstr(g_cola[0], 0, 250);
      usados = 1;
     }
   if(!SendNotification(texto) && !g_avisoPush)
     {
      Print("No se pudo enviar al celular. Configura el MetaQuotes ID en Herramientas > Opciones > Notificaciones. Error ",
            GetLastError());
      g_avisoPush = true;
     }
   g_ultPush = TimeLocal();
   int resto = n - usados;
   for(int i = 0; i < resto; i++)
      g_cola[i] = g_cola[i + usados];
   ArrayResize(g_cola, resto);
  }

//+------------------------------------------------------------------+
//| Escáner                                                          |
//+------------------------------------------------------------------+
void PrepararListas()
  {
   ArrayResize(g_sym, 0);
   string lista[];
   if(Separar(InpSimbolos, lista) > 0)
     {
      for(int i = 0; i < ArraySize(lista); i++)
        {
         if(!SymbolSelect(lista[i], true))
           {
            Print("Mercado no encontrado en este broker: ", lista[i]);
            continue;
           }
         int z = ArraySize(g_sym);
         ArrayResize(g_sym, z + 1);
         g_sym[z] = lista[i];
        }
     }
   else
     {
      int total = SymbolsTotal(true);
      ArrayResize(g_sym, total);
      for(int i = 0; i < total; i++)
         g_sym[i] = SymbolName(i, true);
     }

   ArrayResize(g_tf, 0);
   ArrayResize(g_tfNom, 0);
   string tfs[];
   Separar(InpTemporalidades, tfs);
   for(int i = 0; i < ArraySize(tfs); i++)
     {
      string nombre = tfs[i];
      StringToUpper(nombre);
      for(int k = 0; k < 21; k++)
         if(TODOS_NOM[k] == nombre)
           {
            int z = ArraySize(g_tf);
            ArrayResize(g_tf, z + 1);
            ArrayResize(g_tfNom, z + 1);
            g_tf[z] = TODOS_TF[k];
            g_tfNom[z] = TODOS_NOM[k];
           }
     }
   if(ArraySize(g_tf) == 0)
     {
      ArrayResize(g_tf, 21);
      ArrayResize(g_tfNom, 21);
      for(int k = 0; k < 21; k++)
        {
         g_tf[k] = TODOS_TF[k];
         g_tfNom[k] = TODOS_NOM[k];
        }
     }

   int nS = ArraySize(g_sym), nT = ArraySize(g_tf);
   ArrayResize(g_par, nS * nT);
   for(int s = 0; s < nS; s++)
      for(int k = 0; k < nT; k++)
        {
         int idx = s * nT + k;
         g_par[idx].s = s;
         g_par[idx].k = k;
         g_par[idx].ultBarra = 0;
         g_par[idx].dir = 0;
         g_par[idx].quedan = 0;
         g_par[idx].tConf = 0;
         g_par[idx].sinDatos = false;
        }
  }

void ProcesarPar(int idx, datetime t0)
  {
   string sym = g_sym[g_par[idx].s];
   ENUM_TIMEFRAMES tf = g_tf[g_par[idx].k];
   MqlRates r[];
   int got = CopyRates(sym, tf, 1, InpVelasAnalisis, r);   // desde la última vela CERRADA
   if(got <= 0)
      return;                                              // sin datos aún: se reintenta
   g_par[idx].ultBarra = t0;
   if(got < CALENTAMIENTO + 60)
     {
      if(!g_par[idx].sinDatos || g_par[idx].dir != 0)
         g_redibujar = true;
      g_par[idx].sinDatos = true;
      g_par[idx].dir = 0;
      return;
     }
   if(g_par[idx].sinDatos)
      g_redibujar = true;
   g_par[idx].sinDatos = false;

   double o[], h[], l[], c[];
   ArrayResize(o, got);
   ArrayResize(h, got);
   ArrayResize(l, got);
   ArrayResize(c, got);
   for(int i = 0; i < got; i++)
     {
      o[i] = r[i].open;
      h[i] = r[i].high;
      l[i] = r[i].low;
      c[i] = r[i].close;
     }
   Senal s[];
   DetectarAmbos(o, h, l, c, got, s);

   int mejor = -1;
   for(int i = 0; i < ArraySize(s); i++)
      if(mejor < 0 || s[i].c > s[mejor].c)
         mejor = i;

   int dirAnt = g_par[idx].dir, quedAnt = g_par[idx].quedan;
   g_par[idx].dir = 0;
   g_par[idx].quedan = 0;
   if(mejor >= 0)
     {
      int sc = got - s[mejor].c;   // 1 = la confirmación es la última vela cerrada
      if(sc >= 1 && sc <= 4)
        {
         g_par[idx].dir = s[mejor].dir;
         g_par[idx].quedan = 5 - sc;
         g_par[idx].tConf = r[s[mejor].c].time;
         if(sc == 1 || InpAlertarTardias)
            Avisar(idx, sc);
        }
     }
   if(dirAnt != g_par[idx].dir || quedAnt != g_par[idx].quedan)
      g_redibujar = true;
  }

void AbrirGrafico(string sym, ENUM_TIMEFRAMES tf)
  {
   SymbolSelect(sym, true);
   long id = ChartOpen(sym, tf);
   if(id <= 0)
     {
      Print("No se pudo abrir el gráfico de ", sym);
      return;
     }
   // Mismo indicador en el gráfico nuevo, con el escáner apagado (sin alertas repetidas)
   int handle = iCustom(sym, tf, "EMAs_Escaner", false);
   if(handle != INVALID_HANDLE)
      ChartIndicatorAdd(id, 0, handle);
  }

//+------------------------------------------------------------------+
//| Marcas en el gráfico actual                                      |
//+------------------------------------------------------------------+
void MarcarGrafico(int total, const datetime &time[], const double &open[], const double &high[],
                   const double &low[], const double &close[])
  {
   ObjectsDeleteAll(0, MK);
   int n = total - 1;                 // sin la vela que aún se está formando
   if(n > InpVelasMarcar)
      n = InpVelasMarcar;
   if(n <= CALENTAMIENTO + 2)
      return;
   int ini = total - 1 - n;
   double o[], h[], l[], c[];
   ArrayResize(o, n);
   ArrayResize(h, n);
   ArrayResize(l, n);
   ArrayResize(c, n);
   for(int j = 0; j < n; j++)
     {
      o[j] = open[ini + j];
      h[j] = high[ini + j];
      l[j] = low[ini + j];
      c[j] = close[ini + j];
     }
   Senal s[];
   DetectarAmbos(o, h, l, c, n, s);

   for(int i = 0; i < ArraySize(s); i++)
     {
      int im = ini + s[i].m;
      int ic = ini + s[i].c;
      int fin = ic + 4;
      if(fin > total - 1)
         fin = total - 1;
      string id = MK + (string)i + "|";

      ObjectCreate(0, id + "zona", OBJ_RECTANGLE, 0, time[im], s[i].suelo, time[fin], s[i].techo);
      ObjectSetInteger(0, id + "zona", OBJPROP_COLOR, InpColorZona);
      ObjectSetInteger(0, id + "zona", OBJPROP_FILL, true);
      ObjectSetInteger(0, id + "zona", OBJPROP_BACK, true);
      ObjectSetInteger(0, id + "zona", OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, id + "zona", OBJPROP_HIDDEN, true);

      bool compra = (s[i].dir > 0);
      ObjectCreate(0, id + "flecha", OBJ_ARROW, 0, time[ic], compra ? low[ic] : high[ic]);
      ObjectSetInteger(0, id + "flecha", OBJPROP_ARROWCODE, compra ? 233 : 234);
      ObjectSetInteger(0, id + "flecha", OBJPROP_ANCHOR, compra ? ANCHOR_TOP : ANCHOR_BOTTOM);
      ObjectSetInteger(0, id + "flecha", OBJPROP_COLOR, compra ? clrLime : clrRed);
      ObjectSetInteger(0, id + "flecha", OBJPROP_WIDTH, 2);
      ObjectSetInteger(0, id + "flecha", OBJPROP_SELECTABLE, false);
      ObjectSetInteger(0, id + "flecha", OBJPROP_HIDDEN, true);

      if(ic + 4 <= total - 1)
        {
         ObjectCreate(0, id + "salida", OBJ_TEXT, 0, time[ic + 4], close[ic + 4]);
         ObjectSetString(0, id + "salida", OBJPROP_TEXT, "Salida");
         ObjectSetInteger(0, id + "salida", OBJPROP_COLOR, clrYellow);
         ObjectSetInteger(0, id + "salida", OBJPROP_FONTSIZE, 7);
         ObjectSetInteger(0, id + "salida", OBJPROP_ANCHOR, compra ? ANCHOR_LOWER : ANCHOR_UPPER);
         ObjectSetInteger(0, id + "salida", OBJPROP_SELECTABLE, false);
         ObjectSetInteger(0, id + "salida", OBJPROP_HIDDEN, true);
        }
     }
   ChartRedraw(0);
  }

//+------------------------------------------------------------------+
//| Eventos                                                          |
//+------------------------------------------------------------------+
int OnInit()
  {
   SetIndexBuffer(0, B30, INDICATOR_DATA);
   SetIndexBuffer(1, B50, INDICATOR_DATA);
   SetIndexBuffer(2, B100, INDICATOR_DATA);
   ArraySetAsSeries(B30, false);
   ArraySetAsSeries(B50, false);
   ArraySetAsSeries(B100, false);
   PlotIndexSetInteger(0, PLOT_LINE_COLOR, InpColor30);
   PlotIndexSetInteger(1, PLOT_LINE_COLOR, InpColor50);
   PlotIndexSetInteger(2, PLOT_LINE_COLOR, InpColor100);
   if(!InpDibujarEMAs)
      for(int p = 0; p < 3; p++)
         PlotIndexSetInteger(p, PLOT_DRAW_TYPE, DRAW_NONE);
   IndicatorSetString(INDICATOR_SHORTNAME, "EMAs 30/50/100");

   ARRIBA = ShortToString(0x25B2);
   ABAJO = ShortToString(0x25BC);

   if(InpMostrarEscaner)
     {
      PrepararListas();
      DibujarPanel();
      EventSetTimer(1);
     }
   return INIT_SUCCEEDED;
  }

void OnDeinit(const int reason)
  {
   EventKillTimer();
   ObjectsDeleteAll(0, PFX);
   ObjectsDeleteAll(0, MK);
   ChartRedraw(0);
  }

void OnTimer()
  {
   if(InpMostrarEscaner)
     {
      int total = ArraySize(g_par);
      int hechos = 0;
      for(int k = 0; k < total; k++)
        {
         int idx = (g_cursor + k) % total;
         datetime t0 = iTime(g_sym[g_par[idx].s], g_tf[g_par[idx].k], 0);
         if(t0 == 0 || t0 == g_par[idx].ultBarra)
            continue;
         if(hechos >= InpParesPorSegundo)
           {
            g_cursor = idx;
            break;
           }
         ProcesarPar(idx, t0);
         hechos++;
        }
      if(g_redibujar)
         DibujarPanel();
      else
        {
         ActualizarEstado();
         ChartRedraw(0);
        }
     }
   if(InpAlertaCelular)
      EnviarCola();
  }

void OnChartEvent(const int id, const long &lparam, const double &dparam, const string &sparam)
  {
   if(id == CHARTEVENT_OBJECT_CLICK && StringFind(sparam, PFX) == 0)
     {
      ObjectSetInteger(0, sparam, OBJPROP_STATE, false);
      string p[];
      int n = StringSplit(sparam, '|', p);
      if(n == 4 && p[1] == "c")
        {
         int s = g_top + (int)StringToInteger(p[2]);
         int k = (int)StringToInteger(p[3]);
         if(s >= 0 && s < ArraySize(g_sym) && k >= 0 && k < ArraySize(g_tf))
            AbrirGrafico(g_sym[s], g_tf[k]);
        }
      else
         if(n >= 2 && p[1] == "arriba")
           {
            g_top -= g_filasVis;
            DibujarPanel();
           }
         else
            if(n >= 2 && p[1] == "abajo")
              {
               g_top += g_filasVis;
               DibujarPanel();
              }
      ChartRedraw(0);
     }
   if(id == CHARTEVENT_CHART_CHANGE && InpMostrarEscaner)
      g_redibujar = true;
  }

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
   if(rates_total < 2)
      return 0;
   ArraySetAsSeries(time, false);
   ArraySetAsSeries(open, false);
   ArraySetAsSeries(high, false);
   ArraySetAsSeries(low, false);
   ArraySetAsSeries(close, false);

   int inicio = prev_calculated - 1;
   if(prev_calculated <= 0)
     {
      B30[0] = close[0];
      B50[0] = close[0];
      B100[0] = close[0];
      inicio = 1;
     }
   if(inicio < 1)
      inicio = 1;
   double a30 = 2.0 / 31.0, a50 = 2.0 / 51.0, a100 = 2.0 / 101.0;
   for(int i = inicio; i < rates_total; i++)
     {
      B30[i] = a30 * close[i] + (1.0 - a30) * B30[i - 1];
      B50[i] = a50 * close[i] + (1.0 - a50) * B50[i - 1];
      B100[i] = a100 * close[i] + (1.0 - a100) * B100[i - 1];
     }

   if(InpMarcarPatrones && (prev_calculated <= 0 || time[rates_total - 1] != g_barraGrafico))
     {
      g_barraGrafico = time[rates_total - 1];
      MarcarGrafico(rates_total, time, open, high, low, close);
     }
   return rates_total;
  }
//+------------------------------------------------------------------+
