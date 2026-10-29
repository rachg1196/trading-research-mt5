//+------------------------------------------------------------------+
//| AI_Quantum_Senales.mq5 - Fase 2 Analizador de indicadores        |
//| SOLO LECTURA. Carga Quantum con iCustom en todas las             |
//| temporalidades y guarda sus valores, cruces y las velas.         |
//+------------------------------------------------------------------+
#property script_show_inputs
input string   InpIndicator = "QUANTUM Todo Gratis en BOTGRATIS12 Youtube y Telegram";
input datetime InpDesde     = D'2025.01.01';

ENUM_TIMEFRAMES TFS[]={PERIOD_M1,PERIOD_M2,PERIOD_M3,PERIOD_M4,PERIOD_M5,PERIOD_M6,PERIOD_M10,PERIOD_M12,PERIOD_M15,PERIOD_M20,PERIOD_M30,
                       PERIOD_H1,PERIOD_H2,PERIOD_H3,PERIOD_H4,PERIOD_H6,PERIOD_H8,PERIOD_H12,PERIOD_D1,PERIOD_W1,PERIOD_MN1};

void OnStart()
{
   string dir="AnalizadorIndicadores\\fase2\\";
   int lg=FileOpen(dir+"log_fase2.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   FileWriteString(lg,"Simbolo: "+_Symbol+"  maxbars terminal: "+(string)TerminalInfoInteger(TERMINAL_MAXBARS)+"\r\n");
   for(int t=0;t<ArraySize(TFS);t++)
   {
      ENUM_TIMEFRAMES tf=TFS[t]; string tn=StringSubstr(EnumToString(tf),7);
      // ---- velas completas
      MqlRates r[]; int nr=CopyRates(_Symbol,tf,InpDesde,TimeCurrent(),r);
      for(int k=0;k<20 && nr<=0;k++){ Sleep(500); nr=CopyRates(_Symbol,tf,InpDesde,TimeCurrent(),r); }
      int fv=FileOpen(dir+"velas_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI);
      FileWriteString(fv,"time,open,high,low,close,spread\r\n");
      for(int i=0;i<nr;i++)
         FileWriteString(fv,TimeToString(r[i].time,TIME_DATE|TIME_SECONDS)+","+DoubleToString(r[i].open,_Digits)+","+DoubleToString(r[i].high,_Digits)+","+
            DoubleToString(r[i].low,_Digits)+","+DoubleToString(r[i].close,_Digits)+","+(string)r[i].spread+"\r\n");
      FileClose(fv);
      // ---- Quantum
      int h=iCustom(_Symbol,tf,InpIndicator);
      int calc=-1; for(int k=0;k<300;k++){ calc=BarsCalculated(h); if(calc>0) break; Sleep(100); }
      double g[],rd[],ma[]; datetime tm[];
      int n=MathMax(calc,0);
      int a=CopyBuffer(h,0,0,n,g), b=CopyBuffer(h,1,0,n,rd), c=CopyBuffer(h,2,0,n,ma), d=CopyTime(_Symbol,tf,0,n,tm);
      int m=MathMin(MathMin(a,b),MathMin(c,d));
      int fq=FileOpen(dir+"quantum_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI);
      FileWriteString(fq,"time,verde,roja,media,senal\r\n");
      int nb=0,ns=0;
      for(int i=0;i<m;i++)
      {
         string s="";
         if(i>0 && i<m-1)   // solo velas cerradas
         {
            double d0=g[i]-rd[i], d1=g[i-1]-rd[i-1];
            if(d0>0 && d1<=0){ s="COMPRA"; nb++; }
            if(d0<0 && d1>=0){ s="VENTA";  ns++; }
         }
         FileWriteString(fq,TimeToString(tm[i],TIME_DATE|TIME_SECONDS)+","+DoubleToString(g[i],0)+","+DoubleToString(rd[i],0)+","+
                            DoubleToString(ma[i],_Digits)+","+s+"\r\n");
      }
      FileClose(fq);
      IndicatorRelease(h);
      string line=StringFormat("%s: velas=%d  quantum_calculadas=%d  desde=%s  compras=%d ventas=%d",
                  tn,nr,m,(m>0?TimeToString(tm[0]):"-"),nb,ns);
      Print(line); FileWriteString(lg,line+"\r\n");
   }
   FileClose(lg);
   Print("=== FIN Fase 2 ===");
}
