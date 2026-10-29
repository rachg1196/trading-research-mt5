//+------------------------------------------------------------------+
//| ExportarEMAs.mq5 — script de SOLO LECTURA (proyecto emas, D-016)  |
//|                                                                  |
//| Qué hace: en el gráfico donde lo sueltas, lee las velas cerradas  |
//| entre dos fechas y los valores del indicador Moving Average       |
//| exponencial de 30, 50 y 100 sobre el cierre, y los guarda en un   |
//| archivo CSV en la carpeta MQL5\Files del terminal.               |
//|                                                                  |
//| Qué NO hace: no abre, cierra ni modifica órdenes o posiciones; no |
//| usa ninguna función de trading; no cambia el gráfico ni ajustes.  |
//+------------------------------------------------------------------+
#property script_show_inputs
#property strict

input datetime InpDesde = D'2025.01.01 00:00';  // Desde (hora del servidor)
input datetime InpHasta = D'2025.01.02 00:00';  // Hasta (hora del servidor)

void OnStart()
  {
   int periodos[3] = {30, 50, 100};
   int handles[3];
   for(int k = 0; k < 3; k++)
     {
      handles[k] = iMA(_Symbol, _Period, periodos[k], 0, MODE_EMA, PRICE_CLOSE);
      if(handles[k] == INVALID_HANDLE)
        {
         Print("No se pudo crear la EMA ", periodos[k], ". Error ", GetLastError());
         return;
        }
     }

   // Espera (máx. 30 s) a que las tres EMAs estén calculadas sobre todo el historial.
   int total = Bars(_Symbol, _Period);
   for(int intento = 0; intento < 300; intento++)
     {
      if(BarsCalculated(handles[0]) >= total && BarsCalculated(handles[1]) >= total &&
         BarsCalculated(handles[2]) >= total)
         break;
      Sleep(100);
     }

   MqlRates velas[];
   int n = CopyRates(_Symbol, _Period, InpDesde, InpHasta, velas);
   if(n <= 0)
     {
      Print("No hay velas en ese rango. Error ", GetLastError());
      return;
     }

   double e30[], e50[], e100[];
   if(CopyBuffer(handles[0], 0, InpDesde, InpHasta, e30) != n ||
      CopyBuffer(handles[1], 0, InpDesde, InpHasta, e50) != n ||
      CopyBuffer(handles[2], 0, InpDesde, InpHasta, e100) != n)
     {
      Print("Las EMAs no tienen el mismo número de velas que el gráfico. Error ", GetLastError());
      return;
     }

   // La vela que aún está abierta no se exporta (solo velas cerradas).
   datetime abierta = iTime(_Symbol, _Period, 0);

   string simbolo = _Symbol;
   StringReplace(simbolo, " ", "");
   string nombre = "emas_" + simbolo + "_" + StringSubstr(EnumToString((ENUM_TIMEFRAMES)_Period), 7) + ".csv";
   int f = FileOpen(nombre, FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(f == INVALID_HANDLE)
     {
      Print("No se pudo crear el archivo ", nombre, ". Error ", GetLastError());
      return;
     }
   FileWrite(f, "time", "open", "high", "low", "close", "ema30", "ema50", "ema100");
   int escritas = 0;
   for(int i = 0; i < n; i++)
     {
      if(velas[i].time >= abierta)
         continue;
      FileWrite(f, TimeToString(velas[i].time, TIME_DATE | TIME_MINUTES),
                DoubleToString(velas[i].open, _Digits), DoubleToString(velas[i].high, _Digits),
                DoubleToString(velas[i].low, _Digits), DoubleToString(velas[i].close, _Digits),
                DoubleToString(e30[i], 8), DoubleToString(e50[i], 8), DoubleToString(e100[i], 8));
      escritas++;
     }
   FileClose(f);
   for(int k = 0; k < 3; k++)
      IndicatorRelease(handles[k]);
   Print("Guardadas ", escritas, " velas en MQL5\\Files\\", nombre);
  }
//+------------------------------------------------------------------+
