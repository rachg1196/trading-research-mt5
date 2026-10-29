//+------------------------------------------------------------------+
//| AI_Inspector.mq5  - Fase 0 (generico) Analizador de indicadores     |
//| SOLO LECTURA: no envia, modifica ni cierra ordenes.              |
//| Carga Quantum con iCustom, lista sus buffers y los objetos que   |
//| dibuja en el grafico. No descompila nada.                        |
//+------------------------------------------------------------------+
#property script_show_inputs

input string InpIndicator = "FTS SPIKE";
input int    InpBars      = 5000;   // velas a revisar
input bool   InpAttach    = true;   // anadir al grafico para ver objetos/flechas
input string InpTag       = "ftsspike";

struct BufData { double v[]; };
int g_f = INVALID_HANDLE;
void L(string s){ Print(s); if(g_f!=INVALID_HANDLE) FileWriteString(g_f,s+"\r\n"); }

void OnStart()
{
   string tf  = StringSubstr(EnumToString(_Period),7);
   string sym = _Symbol; StringReplace(sym," ","_");
   string base= "AnalizadorIndicadores\\"+InpTag+"_fase0_"+sym+"_"+tf;
   g_f = FileOpen(base+".txt",FILE_WRITE|FILE_TXT|FILE_ANSI);

   L("=== FASE 0 - Inspeccion de "+InpIndicator+" ===");
   L("Simbolo: "+_Symbol+"  TF: "+tf+"  Fecha: "+TimeToString(TimeCurrent()));
   L("Cuenta: "+(AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL?"REAL":"DEMO")+
     "  Servidor: "+AccountInfoString(ACCOUNT_SERVER)+"  Conectado: "+(string)TerminalInfoInteger(TERMINAL_CONNECTED));
   L("Velas disponibles: "+(string)Bars(_Symbol,_Period)+"  Punto: "+DoubleToString(_Point,_Digits)+
     "  Spread actual (pts): "+(string)SymbolInfoInteger(_Symbol,SYMBOL_SPREAD));

   ResetLastError();
   int h = iCustom(_Symbol,_Period,InpIndicator);
   if(h==INVALID_HANDLE){ L("ERROR iCustom: "+(string)GetLastError()); FileClose(g_f); return; }

   int calc=-1;
   for(int i=0;i<200;i++){ calc=BarsCalculated(h); if(calc>0) break; Sleep(100); }
   L("BarsCalculated: "+(string)calc);

   MqlParam prm[]; ENUM_INDICATOR it;
   int np = IndicatorParameters(h,it,prm);
   L("Parametros devueltos por la API: "+(string)np);
   for(int i=0;i<np;i++)
      L("  p"+(string)i+" tipo="+EnumToString(prm[i].type)+" int="+(string)prm[i].integer_value+
        " dbl="+DoubleToString(prm[i].double_value,5)+" str="+prm[i].string_value);

   int n = MathMin(InpBars,calc);
   datetime tm[]; double o[],hi[],lo[],cl[];
   CopyTime(_Symbol,_Period,0,n,tm); CopyOpen(_Symbol,_Period,0,n,o);
   CopyHigh(_Symbol,_Period,0,n,hi); CopyLow(_Symbol,_Period,0,n,lo); CopyClose(_Symbol,_Period,0,n,cl);

   // ---- buffers
   BufData buf[64];  int nb=0;
   for(int b=0;b<64;b++)
   {
      double v[]; ResetLastError();
      int got=CopyBuffer(h,b,0,n,v);
      if(got<=0){ L("Buffer "+(string)b+": no disponible (err "+(string)GetLastError()+") -> fin"); break; }
      ArrayCopy(buf[b].v,v); nb=b+1;
      int cnt=0; double mn=DBL_MAX,mx=-DBL_MAX; string last="";
      int distinct=0; double seen[]; 
      for(int k=0;k<got;k++)
      {
         double x=v[k];
         if(x==EMPTY_VALUE || x==0.0) continue;
         cnt++; mn=MathMin(mn,x); mx=MathMax(mx,x);
         bool f=false; for(int s=0;s<ArraySize(seen);s++) if(seen[s]==x){f=true;break;}
         if(!f && ArraySize(seen)<20){ ArrayResize(seen,ArraySize(seen)+1); seen[ArraySize(seen)-1]=x; }
      }
      int shown=0;
      for(int k=got-1;k>=0 && shown<5;k--)
         if(v[k]!=EMPTY_VALUE && v[k]!=0.0){ last+=TimeToString(tm[k])+"="+DoubleToString(v[k],_Digits)+"  "; shown++; }
      L(StringFormat("Buffer %d: velas con valor=%d de %d (%.1f%%)  min=%s max=%s  valores distintos(<=20)=%d",
         b,cnt,got,100.0*cnt/got,(cnt>0?DoubleToString(mn,_Digits):"-"),(cnt>0?DoubleToString(mx,_Digits):"-"),ArraySize(seen)));
      L("   ultimos: "+last);
   }

   // ---- CSV con todos los buffers
   int c=FileOpen(base+"_buffers.csv",FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(c!=INVALID_HANDLE)
   {
      string hd="time,open,high,low,close"; for(int b=0;b<nb;b++) hd+=",b"+(string)b;
      FileWriteString(c,hd+"\r\n");
      for(int k=0;k<n;k++)
      {
         string r=TimeToString(tm[k],TIME_DATE|TIME_SECONDS)+","+DoubleToString(o[k],_Digits)+","+DoubleToString(hi[k],_Digits)+","+
                  DoubleToString(lo[k],_Digits)+","+DoubleToString(cl[k],_Digits);
         for(int b=0;b<nb;b++){ double x=(k<ArraySize(buf[b].v)?buf[b].v[k]:EMPTY_VALUE); r+=","+(x==EMPTY_VALUE?"":DoubleToString(x,_Digits)); }
         FileWriteString(c,r+"\r\n");
      }
      FileClose(c);
   }

   // ---- objetos dibujados en el grafico
   if(InpAttach)
   {
      int before=ObjectsTotal(0);
      string prev[]; ArrayResize(prev,before); for(int i=0;i<before;i++) prev[i]=ObjectName(0,i);
      bool ok=ChartIndicatorAdd(0,0,h);
      L("ChartIndicatorAdd: "+(string)ok+" (err "+(string)GetLastError()+")");
      Sleep(8000); ChartRedraw(0);
      int sw=(int)ChartGetInteger(0,CHART_WINDOWS_TOTAL);
      for(int w=0;w<sw;w++) for(int i=0;i<ChartIndicatorsTotal(0,w);i++) L("Indicador en ventana "+(string)w+": "+ChartIndicatorName(0,w,i));
      int tot=ObjectsTotal(0);
      L("Objetos en grafico antes="+(string)before+" despues="+(string)tot);
      int shown=0;
      for(int i=0;i<tot && shown<150;i++)
      {
         string nm=ObjectName(0,i);
         bool old=false; for(int j=0;j<before;j++) if(prev[j]==nm){old=true;break;}
         if(old) continue;
         ENUM_OBJECT ty=(ENUM_OBJECT)ObjectGetInteger(0,nm,OBJPROP_TYPE);
         L(StringFormat("  obj '%s' tipo=%s t=%s p=%s color=%s codigo=%d texto='%s'",nm,EnumToString(ty),
           TimeToString((datetime)ObjectGetInteger(0,nm,OBJPROP_TIME,0)),DoubleToString(ObjectGetDouble(0,nm,OBJPROP_PRICE,0),_Digits),
           ColorToString((color)ObjectGetInteger(0,nm,OBJPROP_COLOR),true),(int)ObjectGetInteger(0,nm,OBJPROP_ARROWCODE),
           ObjectGetString(0,nm,OBJPROP_TEXT)));
         shown++;
      }
   }
   L("=== FIN ===");
   FileClose(g_f);
}
