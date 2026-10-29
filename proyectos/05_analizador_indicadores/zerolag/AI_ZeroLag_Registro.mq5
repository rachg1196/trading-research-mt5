//+------------------------------------------------------------------+
//| AI_ZeroLag_Registro.mq5 - Fases 2 y 3 (ZeroLag)                  |
//| EA SOLO LECTURA para el Probador: NO abre ni cierra operaciones. |
//| En cada vela cerrada guarda lo que mostraba ZeroLag, y anota si  |
//| aparecieron flechas durante la vela que luego desaparecieron.    |
//+------------------------------------------------------------------+
input int InpLength = 10;   // 10 = config de Raul, 15 = defecto
string IND="Market\\Zero Lag MA Trend Levels MT5 with Scanner";
int h=INVALID_HANDLE,f=INVALID_HANDLE; datetime cur=0;
bool sAp,bAp,uAp,dAp; int sSec,bSec;
double V(int b,int sh){ double x[1]; if(CopyBuffer(h,b,sh,1,x)<1) return EMPTY_VALUE; return x[0]; }
bool On(int b,int sh){ double x=V(b,sh); return (x!=EMPTY_VALUE && x!=0); }
int OnInit()
{
   h=iCustom(_Symbol,_Period,IND,
      5000,InpLength,200,1,
      "",70.0,true,60.0,true,233,clrGreen,234,clrRed,clrBlack,10,
      "",false,false,false,false,false,false,"request.wav",
      "",false,"M5",0,1,_Symbol,false,0,100,22,false,20,20,0.5,clrWhite,clrWhite,clrBlack,clrGreen,clrRed,"Calibri",10,0);
   if(h==INVALID_HANDLE){ Print("iCustom error ",GetLastError()); return INIT_FAILED; }
   string tn=StringSubstr(EnumToString(_Period),7);
   f=FileOpen("AnalizadorIndicadores\\zl_tester_L"+(string)InpLength+"_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   FileWriteString(f,"time,zl,ema,compra,venta,tend_alcista,tend_bajista,compra_intravela,seg_compra,venta_intravela,seg_venta,alza_intravela,baja_intravela\r\n");
   return INIT_SUCCEEDED;
}
void Flush(datetime bar)
{
   FileWriteString(f,TimeToString(bar,TIME_DATE|TIME_SECONDS)+","+DoubleToString(V(2,1),_Digits)+","+DoubleToString(V(4,1),_Digits)+","+
      (string)(int)On(0,1)+","+(string)(int)On(1,1)+","+(string)(int)(V(14,1)==1)+","+(string)(int)(V(15,1)==1)+","+
      (string)(int)bAp+","+(string)bSec+","+(string)(int)sAp+","+(string)sSec+","+(string)(int)uAp+","+(string)(int)dAp+"\r\n");
}
void OnTick()
{
   datetime b=iTime(_Symbol,_Period,0);
   if(b!=cur){ if(cur!=0) Flush(cur); cur=b; sAp=bAp=uAp=dAp=false; sSec=bSec=-1; }
   int sec=(int)(TimeCurrent()-cur);
   if(!bAp && On(0,0)){ bAp=true; bSec=sec; }
   if(!sAp && On(1,0)){ sAp=true; sSec=sec; }
   if(V(14,0)==1) uAp=true;
   if(V(15,0)==1) dAp=true;
}
void OnDeinit(const int r){ if(f!=INVALID_HANDLE) FileClose(f); }
