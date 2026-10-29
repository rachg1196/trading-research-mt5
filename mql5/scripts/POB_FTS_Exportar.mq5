//+------------------------------------------------------------------+
//| POB_FTS_Exportar.mq5 - SOLO LECTURA (proyecto oro bitcoin)       |
//| Carga FTS SPIKE (Period 9, Otstup 30) con iCustom en M5 en las 6 |
//| criptos operables y el oro, y guarda TODAS sus flechas.          |
//| No abre, modifica ni cierra ordenes.                             |
//+------------------------------------------------------------------+
#property script_show_inputs
input string InpIndicador = "FTS SPIKE";
input string InpSimbolos  = "BTCUSD,ETHUSD,LTCUSD,BCHUSD,DASHUSD,XRPUSDT,XAUUSD_i";
input string InpTFs       = "M5,M1,M15";
ENUM_TIMEFRAMES TF(string s){ if(s=="M1")return PERIOD_M1; if(s=="M15")return PERIOD_M15; return PERIOD_M5; }
void OnStart()
{
   string sims[]; int ns=StringSplit(InpSimbolos,',',sims);
   string tfs[];  int nt=StringSplit(InpTFs,',',tfs);
   int lg=FileOpen("ProyectoOroBitcoin\\fts_log.txt",FILE_WRITE|FILE_TXT|FILE_ANSI);
   for(int t=0;t<nt;t++) for(int s=0;s<ns;s++)
   {
      string sym=sims[s]; ENUM_TIMEFRAMES tf=TF(tfs[t]);
      SymbolSelect(sym,true);
      int nb=0; for(int k=0;k<60 && nb<=0;k++){ nb=Bars(sym,tf); Sleep(500); }
      int h=iCustom(sym,tf,InpIndicador,0,30,9);
      if(h==INVALID_HANDLE){ FileWriteString(lg,sym+" "+tfs[t]+": ERROR iCustom "+(string)GetLastError()+"\r\n"); continue; }
      int calc=-1; for(int k=0;k<1200;k++){ calc=BarsCalculated(h); if(calc>0) break; Sleep(250); }
      double v0[],v1[],v2[],v3[]; datetime tm[];
      int n=CopyBuffer(h,0,0,calc,v0); CopyBuffer(h,1,0,calc,v1);
      int n2=CopyBuffer(h,2,0,calc,v2); int n3=CopyBuffer(h,3,0,calc,v3); CopyTime(sym,tf,0,calc,tm);
      int f=FileOpen("ProyectoOroBitcoin\\fts_"+sym+"_"+tfs[t]+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI);
      FileWriteString(f,"time,b0,b1,b2,b3\r\n");
      int c=0;
      for(int i=0;i<n;i++)
      {
         bool a=(v0[i]!=EMPTY_VALUE && v0[i]!=0);
         bool b=(n2==n && v2[i]!=EMPTY_VALUE && v2[i]!=0);
         if(!a && !b) continue;
         FileWriteString(f,(string)(long)tm[i]+","+DoubleToString(v0[i],8)+","+DoubleToString(v1[i],2)+","+
                          DoubleToString(n2==n?v2[i]:0,8)+","+DoubleToString(n3==n?v3[i]:0,8)+"\r\n");
         c++;
      }
      FileClose(f); IndicatorRelease(h);
      string line=StringFormat("%s %s: velas=%d calculadas=%d flechas=%d desde=%s",sym,tfs[t],nb,calc,c,(n>0?TimeToString(tm[0]):"-"));
      Print(line); FileWriteString(lg,line+"\r\n");
   }
   FileWriteString(lg,"FIN\r\n"); FileClose(lg);
   Print("=== FIN exportacion FTS SPIKE ===");
}
