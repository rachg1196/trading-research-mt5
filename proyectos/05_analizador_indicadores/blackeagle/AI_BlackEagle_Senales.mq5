//+------------------------------------------------------------------+
//| AI_BlackEagle_Senales.mq5 - Fase 2 - SOLO LECTURA                |
//| Black Eagle en todas las temporalidades (alertas apagadas).      |
//+------------------------------------------------------------------+
#property script_show_inputs
input datetime InpDesde = D'2025.01.01';
string IND="Black Eagle  Botgratis12 V1";
ENUM_TIMEFRAMES TFS[]={PERIOD_M1,PERIOD_M2,PERIOD_M3,PERIOD_M4,PERIOD_M5,PERIOD_M6,PERIOD_M10,PERIOD_M12,PERIOD_M15,PERIOD_M20,PERIOD_M30,
                       PERIOD_H1,PERIOD_H2,PERIOD_H3,PERIOD_H4,PERIOD_H6,PERIOD_H8,PERIOD_H12,PERIOD_D1,PERIOD_W1,PERIOD_MN1};
void OnStart()
{
   string dir="AnalizadorIndicadores\\blackeagle_fase2\\";
   int lg=FileOpen(dir+"log.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   for(int t=0;t<ArraySize(TFS);t++)
   {
      ENUM_TIMEFRAMES tf=TFS[t]; string tn=StringSubstr(EnumToString(tf),7);
      int h=iCustom(_Symbol,tf,IND,false,2,false,false);
      if(h==INVALID_HANDLE){ FileWriteString(lg,tn+": ERROR "+(string)GetLastError()+"\r\n"); continue; }
      int calc=-1; for(int k=0;k<1800;k++){ calc=BarsCalculated(h); if(calc>0) break; Sleep(100); }
      double v[],c[]; datetime tm[]; int n=MathMax(calc,0);
      int a=CopyBuffer(h,0,0,n,v); CopyBuffer(h,1,0,n,c); CopyTime(_Symbol,tf,0,n,tm);
      int f=FileOpen(dir+"be_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI);
      FileWriteString(f,"time,senal\r\n"); int nv=0,nc=0;
      for(int i=0;i<a-1;i++)   // sin la vela abierta
      {
         if(tm[i]<InpDesde) continue;
         bool sv=(v[i]!=EMPTY_VALUE&&v[i]!=0), sc=(c[i]!=EMPTY_VALUE&&c[i]!=0);
         if(sv){ FileWriteString(f,TimeToString(tm[i],TIME_DATE|TIME_SECONDS)+",VENTA\r\n"); nv++; }
         if(sc){ FileWriteString(f,TimeToString(tm[i],TIME_DATE|TIME_SECONDS)+",COMPRA\r\n"); nc++; }
      }
      FileClose(f); IndicatorRelease(h);
      string line=StringFormat("%s: calculadas=%d compras=%d ventas=%d",tn,n,nc,nv); Print(line); FileWriteString(lg,line+"\r\n");
   }
   FileClose(lg); Print("=== FIN Black Eagle Fase 2 ===");
}
