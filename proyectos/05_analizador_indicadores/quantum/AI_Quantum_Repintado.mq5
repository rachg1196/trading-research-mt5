//+------------------------------------------------------------------+
//| AI_Quantum_Repintado.mq5 - Fase 3 Analizador de indicadores      |
//| EA SOLO LECTURA para el Probador: NO abre ni cierra operaciones. |
//| Anota, tick a tick, lo que Quantum mostraba en cada vela.        |
//+------------------------------------------------------------------+
input string InpIndicator = "QUANTUM Todo Gratis en BOTGRATIS12 Youtube y Telegram";

int h=INVALID_HANDLE, f=INVALID_HANDLE;
datetime curBar=0;
// estado de la vela en formacion
bool  buyAppeared, sellAppeared; int firstBuySec, firstSellSec, flips, lastState, ticks;
double lastG0, lastR0;

int Diff(int shift){ double g[1],r[1];
   if(CopyBuffer(h,0,shift,1,g)<1||CopyBuffer(h,1,shift,1,r)<1) return -999;
   return (int)MathRound(g[0]-r[0]); }

int OnInit()
{
   h=iCustom(_Symbol,_Period,InpIndicator);
   if(h==INVALID_HANDLE) return INIT_FAILED;
   string tn=StringSubstr(EnumToString(_Period),7);
   f=FileOpen("AnalizadorIndicadores\\fase3_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   FileWriteString(f,"vela,ticks,verde_final_envivo,diff_final_envivo,diff_prev,senal_cierre_envivo,"
                     "compra_intravela,seg_1a_compra,venta_intravela,seg_1a_venta,cambios_estado\r\n");
   return INIT_SUCCEEDED;
}

void Reset(){ buyAppeared=false; sellAppeared=false; firstBuySec=-1; firstSellSec=-1; flips=0; lastState=0; ticks=0; }

void FlushBar(datetime bar)
{
   // la vela 'bar' acaba de cerrar: ahora es shift 1
   int d1=Diff(1), d2=Diff(2);
   string sig="";
   if(d1>0 && d2<=0) sig="COMPRA";
   if(d1<0 && d2>=0) sig="VENTA";
   double g[1]; CopyBuffer(h,0,1,1,g);
   FileWriteString(f,TimeToString(bar,TIME_DATE|TIME_SECONDS)+","+(string)ticks+","+DoubleToString(g[0],0)+","+(string)d1+","+(string)d2+","+sig+","+
      (string)(int)buyAppeared+","+(string)firstBuySec+","+(string)(int)sellAppeared+","+(string)firstSellSec+","+(string)flips+"\r\n");
}

void OnTick()
{
   datetime b=iTime(_Symbol,_Period,0);
   if(b!=curBar)
   {
      if(curBar!=0) FlushBar(curBar);
      curBar=b; Reset();
   }
   ticks++;
   int d0=Diff(0), d1=Diff(1);
   if(d0==-999||d1==-999) return;
   int st=0;
   if(d0>0 && d1<=0) st=1;      // cruce de compra visible en vivo
   if(d0<0 && d1>=0) st=-1;     // cruce de venta visible en vivo
   int sec=(int)(TimeCurrent()-curBar);
   if(st==1 && !buyAppeared){ buyAppeared=true; firstBuySec=sec; }
   if(st==-1 && !sellAppeared){ sellAppeared=true; firstSellSec=sec; }
   if(st!=lastState){ if(ticks>1) flips++; lastState=st; }
}

void OnDeinit(const int r){ if(f!=INVALID_HANDLE) FileClose(f); IndicatorRelease(h); }
