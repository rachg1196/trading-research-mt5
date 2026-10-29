//+------------------------------------------------------------------+
//| FTS_Ruptura_Demo.mq5                                             |
//| Regla validada (analizador de indicadores, FTS Spike, BreakX 600)|
//|  - M5. Lineas con las 2 ultimas flechas FTS que ya tienen 11 velas|
//|  - Linea de arriba BAJISTA (rojas) tocada  -> COMPRA (ruptura)    |
//|  - Linea de abajo ALCISTA (azules) tocada  -> VENTA  (ruptura)    |
//|  - Cada linea se usa una vez. SL 11.000 / TP 5.000 pts. Max 48 h. |
//| SEGURIDAD: NO OPERA EN CUENTA REAL (se bloquea solo).            |
//+------------------------------------------------------------------+
#property copyright "Analizador de indicadores - Raul"
#property version   "1.10"
#include <Trade/Trade.mqh>

input double InpLote      = 0.10;   // Lote
input int    InpSL        = 11000;  // Stop loss (puntos)
input int    InpTP        = 5000;   // Take profit (puntos)
input int    InpMaxHoras  = 48;     // Cerrar a mercado tras N horas
input bool   InpOperar    = true;   // Ejecutar operaciones (false = solo avisos)
input bool   InpAlerta    = true;   // Ventana y sonido
input bool   InpPush      = true;   // Notificacion al celular (MT5 movil)
input long   InpMagic     = 600511; // Numero magico
enum ModoPerdidas { SEGUIDAS=0,      // Perdidas seguidas (se reinicia cada dia)
                    DEL_DIA=1,       // Perdidas totales del dia (se reinicia cada dia)
                    DESDE_INICIO=2   // Perdidas totales desde que arranco el EA
                  };
input int          InpMaxPerdidas = 0;        // Limite de perdidas (0 = sin limite)
input ModoPerdidas InpModoPerdidas = SEGUIDAS; // Como contar las perdidas

string IND="FTS SPIKE";
int    h=INVALID_HANDLE;
CTrade trade;
datetime lastBar=0;
struct Arrow { datetime t; double p; int c; };
Arrow arr[]; 
datetime usedUp=0, usedDn=0;      // segunda flecha de la ultima linea usada
int flog=INVALID_HANDLE;
datetime inicioEA=0; bool detenido=false; int diaDetenido=-1;
int DiaHoy(){ MqlDateTime d; TimeToStruct(TimeCurrent(),d); return d.year*1000+d.day_of_year; }
// cuenta perdidas de este EA segun el modo elegido
int ContarPerdidas()
{
   MqlDateTime d; TimeToStruct(TimeCurrent(),d); d.hour=0; d.min=0; d.sec=0; datetime hoy=StructToTime(d);
   datetime desde=(InpModoPerdidas==DESDE_INICIO)?inicioEA:MathMax(hoy,inicioEA);
   if(!HistorySelect(desde,TimeCurrent()+60)) return 0;
   int total=0, seguidas=0;
   for(int i=0;i<HistoryDealsTotal();i++)
   {
      ulong t=HistoryDealGetTicket(i);
      if(HistoryDealGetInteger(t,DEAL_MAGIC)!=InpMagic || HistoryDealGetString(t,DEAL_SYMBOL)!=_Symbol) continue;
      long e=HistoryDealGetInteger(t,DEAL_ENTRY); if(e!=DEAL_ENTRY_OUT && e!=DEAL_ENTRY_OUT_BY) continue;
      double r=HistoryDealGetDouble(t,DEAL_PROFIT)+HistoryDealGetDouble(t,DEAL_SWAP)+HistoryDealGetDouble(t,DEAL_COMMISSION);
      if(r<0){ total++; seguidas++; } else seguidas=0;
   }
   return (InpModoPerdidas==SEGUIDAS)?seguidas:total;
}
void RevisarLimite()
{
   if(InpMaxPerdidas<=0) return;
   if(detenido && InpModoPerdidas!=DESDE_INICIO && DiaHoy()!=diaDetenido){ detenido=false; Aviso("FTS_Ruptura_Demo: nuevo dia, vuelve a operar"); }
   if(!detenido)
   {
      int n=ContarPerdidas();
      if(n>=InpMaxPerdidas){ detenido=true; diaDetenido=DiaHoy();
         Aviso("FTS_Ruptura_Demo DETENIDO: "+(string)n+" perdidas ("+EnumToString(InpModoPerdidas)+"). No abre mas operaciones"+(InpModoPerdidas==DESDE_INICIO?".":" hasta manana.")); }
   }
}
void OnTrade(){ RevisarLimite(); }

bool EsReal(){ return AccountInfoInteger(ACCOUNT_TRADE_MODE)==ACCOUNT_TRADE_MODE_REAL; }

void Aviso(string s)
{
   Print(s);
   if(InpAlerta){ Alert(s); }
   if(InpPush) SendNotification(s);
}

void AddArrow(datetime t,double p,int c)
{
   for(int i=ArraySize(arr)-1;i>=0 && i>=ArraySize(arr)-20;i--) if(arr[i].t==t && arr[i].c==c) return;
   int n=ArraySize(arr); ArrayResize(arr,n+1); arr[n].t=t; arr[n].p=p; arr[n].c=c;
   if(n>400){ ArrayRemove(arr,0,100); }
}

void ReadArrowAt(int sh)
{
   double v[1],c[1];
   if(CopyBuffer(h,0,sh,1,v)<1 || CopyBuffer(h,1,sh,1,c)<1) return;
   if(v[0]==EMPTY_VALUE || v[0]==0) return;
   AddArrow(iTime(_Symbol,PERIOD_M5,sh),v[0],(int)MathRound(c[0]));
}

// linea con las 2 ultimas flechas del color c: devuelve false si no hay
bool Linea(int c,datetime &t2,double &valorAhora,double &pendiente)
{
   int i2=-1,i1=-1;
   for(int i=ArraySize(arr)-1;i>=0;i--) if(arr[i].c==c){ if(i2<0) i2=i; else { i1=i; break; } }
   if(i1<0) return false;
   int s1=iBarShift(_Symbol,PERIOD_M5,arr[i1].t), s2=iBarShift(_Symbol,PERIOD_M5,arr[i2].t);
   if(s1<=s2) return false;
   pendiente=(arr[i2].p-arr[i1].p)/(double)(s1-s2);          // precio por vela hacia adelante
   valorAhora=arr[i2].p+pendiente*(double)s2;                 // valor en la vela actual (shift 0)
   t2=arr[i2].t;
   return true;
}

void Dibujar(string nm,datetime t1,double p1,double v0,color col)
{
   if(ObjectFind(0,nm)<0) ObjectCreate(0,nm,OBJ_TREND,0,t1,p1,iTime(_Symbol,PERIOD_M5,0),v0);
   ObjectSetInteger(0,nm,OBJPROP_TIME,0,t1); ObjectSetDouble(0,nm,OBJPROP_PRICE,0,p1);
   ObjectSetInteger(0,nm,OBJPROP_TIME,1,iTime(_Symbol,PERIOD_M5,0)); ObjectSetDouble(0,nm,OBJPROP_PRICE,1,v0);
   ObjectSetInteger(0,nm,OBJPROP_COLOR,col); ObjectSetInteger(0,nm,OBJPROP_RAY_RIGHT,true); ObjectSetInteger(0,nm,OBJPROP_WIDTH,2);
}

int OnInit()
{
   if(_Period!=PERIOD_M5){ Alert("FTS_Ruptura_Demo: ponlo en un grafico M5"); return INIT_FAILED; }
   if(_Symbol!="BreakX 600"){ Alert("FTS_Ruptura_Demo: la regla solo esta validada en BreakX 600"); return INIT_FAILED; }
   if(EsReal()){ Alert("FTS_Ruptura_Demo BLOQUEADO: la cuenta es REAL. Solo funciona en DEMO."); return INIT_FAILED; }
   h=iCustom(_Symbol,PERIOD_M5,IND,0,30,9);
   if(h==INVALID_HANDLE){ Alert("No se pudo cargar FTS SPIKE"); return INIT_FAILED; }
   trade.SetExpertMagicNumber(InpMagic);
   for(int k=0;k<100 && BarsCalculated(h)<=0;k++) Sleep(50);
   for(int sh=600;sh>=11;sh--) ReadArrowAt(sh);              // historial: flechas ya confirmadas
   flog=FileOpen("AnalizadorIndicadores\\fts_ruptura_demo_log.csv",FILE_READ|FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_SHARE_READ);
   if(flog!=INVALID_HANDLE){ FileSeek(flog,0,SEEK_END); if(FileTell(flog)==0) FileWriteString(flog,"hora,evento,tipo,precio,linea,lote,ticket\r\n"); }
   lastBar=iTime(_Symbol,PERIOD_M5,0); inicioEA=TimeCurrent();
   Aviso("FTS_Ruptura_Demo iniciado en "+_Symbol+" (cuenta DEMO "+(string)AccountInfoInteger(ACCOUNT_LOGIN)+")");
   return INIT_SUCCEEDED;
}

void Log(string ev,string tipo,double precio,double linea,ulong ticket)
{
   if(flog==INVALID_HANDLE) return;
   FileWriteString(flog,TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS)+","+ev+","+tipo+","+DoubleToString(precio,_Digits)+","+
      DoubleToString(linea,_Digits)+","+DoubleToString(InpLote,2)+","+(string)ticket+"\r\n");
   FileFlush(flog);
}

void CerrarViejas()
{
   for(int i=PositionsTotal()-1;i>=0;i--)
   {
      ulong tk=PositionGetTicket(i);
      if(!PositionSelectByTicket(tk)) continue;
      if(PositionGetInteger(POSITION_MAGIC)!=InpMagic || PositionGetString(POSITION_SYMBOL)!=_Symbol) continue;
      if(TimeCurrent()-(datetime)PositionGetInteger(POSITION_TIME) >= InpMaxHoras*3600)
         if(trade.PositionClose(tk)) Log("CIERRE_TIEMPO","",PositionGetDouble(POSITION_PRICE_CURRENT),0,tk);
   }
}

void Entrar(int dir,double linea)
{
   string tipo=(dir>0?"COMPRA":"VENTA");
   if(detenido){ Log("SENAL_IGNORADA_LIMITE",tipo,0,linea,0); return; }
   Aviso("FTS ruptura: "+tipo+" "+_Symbol+" en linea "+DoubleToString(linea,_Digits));
   if(!InpOperar || EsReal()){ Log("SENAL",tipo,dir>0?SymbolInfoDouble(_Symbol,SYMBOL_ASK):SymbolInfoDouble(_Symbol,SYMBOL_BID),linea,0); return; }
   double pt=_Point; bool ok;
   if(dir>0){ double a=SymbolInfoDouble(_Symbol,SYMBOL_ASK); ok=trade.Buy(InpLote,_Symbol,0,a-InpSL*pt,a+InpTP*pt,"FTS ruptura"); }
   else     { double b=SymbolInfoDouble(_Symbol,SYMBOL_BID); ok=trade.Sell(InpLote,_Symbol,0,b+InpSL*pt,b-InpTP*pt,"FTS ruptura"); }
   Log(ok?"ENTRADA":"ERROR_"+(string)trade.ResultRetcode(),tipo,trade.ResultPrice(),linea,trade.ResultOrder());
}

void OnTick()
{
   if(EsReal()){ ExpertRemove(); return; }
   datetime b=iTime(_Symbol,PERIOD_M5,0);
   if(b!=lastBar){ lastBar=b; ReadArrowAt(11); CerrarViejas(); RevisarLimite(); }
   double bid=SymbolInfoDouble(_Symbol,SYMBOL_BID), op=iOpen(_Symbol,PERIOD_M5,0);
   datetime t2; double v,m;
   // linea de arriba (rojas, color 1) bajista -> compra al tocarla
   if(Linea(1,t2,v,m))
   {
      Dibujar("FTS_sup",t2,v-m*iBarShift(_Symbol,PERIOD_M5,t2),v,m<0?clrOrange:clrDimGray);
      if(m<0 && t2!=usedUp && op<v && bid>=v){ usedUp=t2; Entrar(+1,v); }
   }
   // linea de abajo (azules, color 0) alcista -> venta al tocarla
   if(Linea(0,t2,v,m))
   {
      Dibujar("FTS_inf",t2,v-m*iBarShift(_Symbol,PERIOD_M5,t2),v,m>0?clrOrange:clrDimGray);
      if(m>0 && t2!=usedDn && op>v && bid<=v){ usedDn=t2; Entrar(-1,v); }
   }
}

void OnDeinit(const int r){ if(flog!=INVALID_HANDLE) FileClose(flog); IndicatorRelease(h); ObjectDelete(0,"FTS_sup"); ObjectDelete(0,"FTS_inf"); }
