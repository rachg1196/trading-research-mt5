//+------------------------------------------------------------------+
//| AI_BlackEagle_Registro.mq5 - Fase 3 - EA SOLO LECTURA (Probador)  |
//| NO abre ni cierra operaciones. Registra lo que se veia en vivo.  |
//+------------------------------------------------------------------+
string IND="Black Eagle  Botgratis12 V1";
int h=INVALID_HANDLE,f=INVALID_HANDLE; datetime cur=0; bool bAp,sAp; int bSec,sSec;
bool On(int b,int sh){ double x[1]; if(CopyBuffer(h,b,sh,1,x)<1) return false; return (x[0]!=EMPTY_VALUE && x[0]!=0); }
int OnInit()
{
   h=iCustom(_Symbol,_Period,IND,false,2,false,false);
   if(h==INVALID_HANDLE) return INIT_FAILED;
   string tn=StringSubstr(EnumToString(_Period),7);
   f=FileOpen("AnalizadorIndicadores\\be_tester_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   FileWriteString(f,"time,compra,venta,compra_intravela,seg_compra,venta_intravela,seg_venta,compra_hace1,venta_hace1,compra_hace3,venta_hace3\r\n");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   datetime b=iTime(_Symbol,_Period,0);
   if(b!=cur)
   {
      if(cur!=0)   // vela 'cur' acaba de cerrar (shift 1). Tambien registro lo que se ve ahora en velas mas antiguas
         FileWriteString(f,TimeToString(cur,TIME_DATE|TIME_SECONDS)+","+(string)(int)On(1,1)+","+(string)(int)On(0,1)+","+
            (string)(int)bAp+","+(string)bSec+","+(string)(int)sAp+","+(string)sSec+","+
            (string)(int)On(1,2)+","+(string)(int)On(0,2)+","+(string)(int)On(1,4)+","+(string)(int)On(0,4)+"\r\n");
      cur=b; bAp=sAp=false; bSec=sSec=-1;
   }
   int sec=(int)(TimeCurrent()-cur);
   if(!bAp && On(1,0)){ bAp=true; bSec=sec; }
   if(!sAp && On(0,0)){ sAp=true; sSec=sec; }
}
void OnDeinit(const int r){ if(f!=INVALID_HANDLE) FileClose(f); }
