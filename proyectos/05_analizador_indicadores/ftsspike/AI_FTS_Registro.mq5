//+------------------------------------------------------------------+
//| AI_FTS_Registro.mq5 - EA SOLO LECTURA para el Probador           |
//| NO abre ni cierra operaciones. Al cerrar cada vela anota todas   |
//| las flechas que FTS SPIKE muestra en las ultimas 30 velas, para  |
//| saber cuando aparece cada flecha y si luego desaparece.          |
//+------------------------------------------------------------------+
string IND="FTS SPIKE";
int h=INVALID_HANDLE,f=INVALID_HANDLE; datetime cur=0;
int OnInit()
{
   h=iCustom(_Symbol,_Period,IND,0,30,9);
   if(h==INVALID_HANDLE) return INIT_FAILED;
   string tn=StringSubstr(EnumToString(_Period),7);
   f=FileOpen("AnalizadorIndicadores\\fts_tester_"+tn+".csv",FILE_WRITE|FILE_TXT|FILE_ANSI|FILE_COMMON);
   FileWriteString(f,"visto_al_cerrar,vela_flecha,shift,precio,color,b2,b3\r\n");
   return INIT_SUCCEEDED;
}
void OnTick()
{
   datetime b=iTime(_Symbol,_Period,0);
   if(b==cur) return;
   if(cur!=0)
   {
      double v0[],v1[],v2[],v3[]; datetime tm[];
      int n=CopyBuffer(h,0,1,30,v0); CopyBuffer(h,1,1,30,v1); 
      if(CopyBuffer(h,2,1,30,v2)<30) ArrayInitialize(v2,0); if(CopyBuffer(h,3,1,30,v3)<30) ArrayInitialize(v3,0);
      CopyTime(_Symbol,_Period,1,30,tm);
      for(int i=0;i<n;i++)
      {
         bool a=(v0[i]!=EMPTY_VALUE && v0[i]!=0); bool c=(ArraySize(v2)==30 && v2[i]!=EMPTY_VALUE && v2[i]!=0);
         if(a||c)
            FileWriteString(f,TimeToString(cur,TIME_DATE|TIME_SECONDS)+","+TimeToString(tm[i],TIME_DATE|TIME_SECONDS)+","+(string)(n-i)+","+
               DoubleToString(v0[i],_Digits)+","+DoubleToString(v1[i],0)+","+DoubleToString(ArraySize(v2)==30?v2[i]:0,_Digits)+","+DoubleToString(ArraySize(v3)==30?v3[i]:0,_Digits)+"\r\n");
      }
   }
   cur=b;
}
void OnDeinit(const int r){ if(f!=INVALID_HANDLE) FileClose(f); }
