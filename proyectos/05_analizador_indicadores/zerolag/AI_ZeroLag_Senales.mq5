//+------------------------------------------------------------------+
//| AI_ZeroLag_Senales.mq5 - Fase 2 (ZeroLag) - SOLO LECTURA          |
//| Carga Zero Lag MA Trend Levels (Market) con iCustom, alertas OFF, |
//| en todas las temporalidades, y guarda lineas, tendencia y flechas.|
//+------------------------------------------------------------------+
#property script_show_inputs
input int      InpLength = 10;            // 10 = config de Raul, 15 = defecto
input datetime InpDesde  = D'2025.01.01';
string IND="Market\\Zero Lag MA Trend Levels MT5 with Scanner";
ENUM_TIMEFRAMES TFS[]={PERIOD_M1,PERIOD_M2,PERIOD_M3,PERIOD_M4,PERIOD_M5,PERIOD_M6,PERIOD_M10,PERIOD_M12,PERIOD_M15,PERIOD_M20,PERIOD_M30,
                       PERIOD_H1,PERIOD_H2,PERIOD_H3,PERIOD_H4,PERIOD_H6,PERIOD_H8,PERIOD_H12,PERIOD_D1,PERIOD_W1,PERIOD_MN1};
int Load(ENUM_TIMEFRAMES tf)
{
   return iCustom(_Symbol,tf,IND,
      0,InpLength,200,1,                                   // barras(0=todas), longitud, ATR, precio cierre
      "",70.0,true,60.0,true,233,clrGreen,234,clrRed,clrBlack,10,   // grupo estilo
      "",false,false,false,false,false,false,"request.wav",        // grupo alertas: TODO APAGADO
      "",false,"M5",0,1,_Symbol,false,0,100,22,false,20,20,0.5,clrWhite,clrWhite,clrBlack,clrGreen,clrRed,"Calibri",10,0); // escaner apagado
}
void OnStart()
{
   string dir="AnalizadorIndicadores\\zerolag_fase2_L"+(string)InpLength+"\\";
   int lg=FileOpen(dir+"log.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   for(int t=0;t<ArraySize(TFS);t++)
   {
      ENUM_TIMEFRAMES tf=TFS[t]; string tn=StringSubstr(EnumToString(tf),7);
      ResetLastError();
      int h=Load(tf);
      if(h==INVALID_HANDLE){ FileWriteString(lg,tn+": ERROR iCustom "+(string)GetLastError()+"\r\n"); continue; }
      int calc=-1; for(int k=0;k<600;k++){ calc=BarsCalculated(h); if(calc>0) break; Sleep(100); }
      int n=MathMax(calc,0);
      double zl[],ema[],col[],sv[],bv[],up[],dn[]; datetime tm[];
      int a=CopyBuffer(h,2,0,n,zl); CopyBuffer(h,4,0,n,ema); CopyBuffer(h,3,0,n,col);
      CopyBuffer(h,0,0,n,sv); CopyBuffer(h,1,0,n,bv); CopyBuffer(h,14,0,n,up); CopyBuffer(h,15,0,n,dn); CopyTime(_Symbol,tf,0,n,tm);
      int f=FileOpen(dir+"zl_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI);
      FileWriteString(f,"time,zl,ema,color,flecha_venta,flecha_compra,tend_alcista,tend_bajista\r\n");
      int c1=0,c2=0,c3=0,c4=0;
      for(int i=0;i<a;i++)
      {
         if(tm[i]<InpDesde) continue;
         string s0=(sv[i]==EMPTY_VALUE||sv[i]==0)?"":"1"; string s1=(bv[i]==EMPTY_VALUE||bv[i]==0)?"":"1";
         string s2=(up[i]==1)?"1":""; string s3=(dn[i]==1)?"1":"";
         if(s0!="")c1++; if(s1!="")c2++; if(s2!="")c3++; if(s3!="")c4++;
         FileWriteString(f,TimeToString(tm[i],TIME_DATE|TIME_SECONDS)+","+DoubleToString(zl[i],_Digits)+","+DoubleToString(ema[i],_Digits)+","+
            DoubleToString(col[i],0)+","+s0+","+s1+","+s2+","+s3+"\r\n");
      }
      FileClose(f); IndicatorRelease(h);
      string line=StringFormat("%s: calculadas=%d flechas_venta=%d flechas_compra=%d tend_alcista=%d tend_bajista=%d",tn,n,c1,c2,c3,c4);
      Print(line); FileWriteString(lg,line+"\r\n");
   }
   FileClose(lg); Print("=== FIN ZeroLag Fase 2 L",InpLength," ===");
}
