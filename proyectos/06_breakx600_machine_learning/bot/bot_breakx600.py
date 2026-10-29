"""
===============================================================================
PROYECTO BREAKX 600 — ASESOR EXPERTO / BOT EN PYTHON PARA METATRADER 5 (ETAPA 5)
===============================================================================
Lógica cuantitativa auditada en Etapa 4:
  - Timeframe principal: M5
  - Filtro tendencial de fondo: EMA20 en H1
  - Impulso (Spike): Rango >= 3500 pts, cuerpo >= 60%
  - Retroceso controlado: 800 pts <= Retroceso <= 3500 pts (en máx 8 velas M5)
  - Confirmación: Vela M5 a favor con cuerpo >= 500 pts
  - Take Profit: +5000 pts (+50.00 en precio)
  - Stop Loss: -3000 pts (-30.00 en precio)
  - Ratio R:R: 1.67 : 1 (Umbral mínimo rentabilidad: 37.5%)
  - Ejecución en vivo: Solo en cuentas DEMO (seguridad absoluta)

REGLAS MATEMÁTICAS ESTRICTAS:
  - POINT = 0.01 (sin divisiones distorsionadas)
  - 1000 pts = 10.00 en precio = $1.00 USD (a 0.10 lotes)
  - 5000 pts = 50.00 en precio = $5.00 USD (a 0.10 lotes)
  - Precios directos con 2 decimales sin comas de miles (ej. 97162.90)
===============================================================================
"""

import os
import sys
import json
import time
import datetime
import logging
from pathlib import Path
import numpy as np
import pandas as pd
import MetaTrader5 as mt5

# ─────────────────────────────────────────────────────────────
# CONFIGURACIÓN Y RUTAS
# ─────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = BASE_DIR / "config.json"
LOG_PATH = BASE_DIR / "bot.log"
TRADES_CSV = BASE_DIR / "registro_operaciones.csv"

# Configurar Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
        logging.StreamHandler(sys.stdout)
    ]
)
log = logging.getLogger("BreakX600_Bot")

POINT = 0.01  # Constante del símbolo BreakX 600

def cargar_config() -> dict:
    """Carga y valida el archivo de configuración externo config.json."""
    if not CONFIG_PATH.exists():
        log.error(f"Archivo de configuración no encontrado: {CONFIG_PATH}")
        sys.exit(1)
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
    return cfg

# ─────────────────────────────────────────────────────────────
# GESTOR DE CONEXIÓN A METATRADER 5
# ─────────────────────────────────────────────────────────────
def inicializar_mt5(cfg: dict) -> bool:
    """Inicializa la API de MT5 y verifica la cuenta."""
    log.info("Inicializando conexión con MetaTrader 5...")
    
    login = int(cfg.get("ACCOUNT_LOGIN", 0))
    password = str(cfg.get("ACCOUNT_PASSWORD", ""))
    server = str(cfg.get("ACCOUNT_SERVER", ""))
    
    # Intentar inicializar
    if login > 0 and password and server:
        initialized = mt5.initialize(login=login, password=password, server=server)
    else:
        # Se conecta a la terminal abierta actualmente
        initialized = mt5.initialize()
        
    if not initialized:
        log.error(f"Error al inicializar MT5. Código: {mt5.last_error()}")
        return False
        
    account_info = mt5.account_info()
    if account_info is None:
        log.error(f"No se pudo obtener información de la cuenta: {mt5.last_error()}")
        return False
        
    log.info("=" * 65)
    log.info(f"CONECTADO A MT5 EXITOSAMENTE")
    log.info(f"  Servidor     : {account_info.server}")
    log.info(f"  Balance      : {account_info.balance:.2f} {account_info.currency}")
    log.info(f"  Equidad      : {account_info.equity:.2f} {account_info.currency}")
    log.info(f"  Tipo Cuenta  : {cfg.get('ACCOUNT_TYPE', 'DEMO').upper()}")
    log.info("=" * 65)
    
    # Control de seguridad: Si no es DEMO, abortar ejecución automática
    acc_type = cfg.get("ACCOUNT_TYPE", "DEMO").upper()
    if acc_type != "DEMO":
        log.critical("SEGURIDAD: ACCOUNT_TYPE no está configurado como DEMO.")
        log.critical("Por protección de capital, el bot solo ejecuta operaciones automáticas en cuentas DEMO.")
        log.critical("Para operar en demo, asegúrate de que config.json tenga 'ACCOUNT_TYPE': 'DEMO'.")
        mt5.shutdown()
        sys.exit(1)
    # Segundo control: el tipo REAL de la cuenta según MT5 (no solo lo que dice config.json)
    if account_info.trade_mode != mt5.ACCOUNT_TRADE_MODE_DEMO:
        log.critical("SEGURIDAD: la cuenta conectada NO es DEMO según MT5. El bot no opera.")
        mt5.shutdown()
        sys.exit(1)
        
    # Verificar símbolo
    symbol = cfg.get("SYMBOL", "BreakX 600")
    if not mt5.symbol_select(symbol, True):
        log.error(f"No se pudo seleccionar el símbolo '{symbol}' en el MarketWatch de MT5.")
        return False
        
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        log.error(f"Símbolo '{symbol}' no encontrado en el broker.")
        return False
        
    log.info(f"Símbolo activo : {symbol_info.name} (Dígitos: {symbol_info.digits}, Point: {symbol_info.point})")
    return True

# ─────────────────────────────────────────────────────────────
# CÁLCULOS CUANTITATIVOS Y VELAS
# ─────────────────────────────────────────────────────────────
def obtener_tendencia_h1(symbol: str, ema_period: int = 20) -> int:
    """
    Calcula la EMA de H1 sobre velas cerradas y retorna:
      +1 si el cierre de H1 está por encima de la EMA
      -1 si está por debajo
       0 en caso de error
    """
    rates_h1 = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_H1, 1, ema_period + 20)
    if rates_h1 is None or len(rates_h1) < ema_period:
        return 0
    df_h1 = pd.DataFrame(rates_h1)
    df_h1["ema"] = df_h1["close"].ewm(span=ema_period, adjust=False).mean()
    last_close = df_h1["close"].iloc[-1]
    last_ema = df_h1["ema"].iloc[-1]
    return 1 if last_close > last_ema else -1

def obtener_ultimas_velas_m5(symbol: str, count: int = 20) -> pd.DataFrame:
    """Obtiene las últimas 'count' velas M5 cerradas (excluyendo la vela en formación [0])."""
    # pos 1 es la vela que acaba de cerrar
    rates = mt5.copy_rates_from_pos(symbol, mt5.TIMEFRAME_M5, 1, count)
    if rates is None or len(rates) == 0:
        return pd.DataFrame()
    df = pd.DataFrame(rates)
    df["dt"] = pd.to_datetime(df["time"], unit="s")
    df["rango_pts"] = ((df["high"] - df["low"]) / POINT).round(0).astype(int)
    df["cuerpo_pts"] = ((df["close"] - df["open"]).abs() / POINT).round(0).astype(int)
    df["dir"] = np.where(df["close"] > df["open"], 1, np.where(df["close"] < df["open"], -1, 0))
    return df

# ─────────────────────────────────────────────────────────────
# GESTIÓN Y ENVÍO DE ÓRDENES A METATRADER 5
# ─────────────────────────────────────────────────────────────
def detectar_filling_mode(symbol_info) -> int:
    """Detecta la política de ejecución (filling) soportada por el broker para el símbolo."""
    modes = symbol_info.filling_mode
    # En MT5 C++ / Python API:
    # Bit 0 (valor 1): SYMBOL_FILLING_FOK -> corresponde a ORDER_FILLING_FOK (0)
    # Bit 1 (valor 2): SYMBOL_FILLING_IOC -> corresponde a ORDER_FILLING_IOC (1)
    if modes & 1:
        return mt5.ORDER_FILLING_FOK
    elif modes & 2:
        return mt5.ORDER_FILLING_IOC
    else:
        return mt5.ORDER_FILLING_RETURN

def hay_posicion_abierta(symbol: str, magic: int) -> bool:
    """Comprueba si el bot ya tiene una posición abierta para evitar duplicados."""
    positions = mt5.positions_get(symbol=symbol)
    if positions is None or len(positions) == 0:
        return False
    for pos in positions:
        if pos.magic == magic:
            return True
    return False

def enviar_orden(direccion: int, precio_entrada: float, motivo: str) -> bool:
    """
    Envía una orden al mercado con el lotaje estricto configurado y TP/SL exactos.
    """
    cfg = cargar_config()  # Leer configuración fresca en cada orden
    symbol = cfg.get("SYMBOL", "BreakX 600")
    lot_size = float(cfg.get("LOT_SIZE", 0.10))
    tp_points = int(cfg.get("TP_POINTS", 5000))
    sl_points = int(cfg.get("SL_POINTS", 3000))
    magic = int(cfg.get("MAGIC_NUMBER", 600001))
    
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        log.error(f"Error obteniendo info de {symbol}")
        return False
        
    tick = mt5.symbol_info_tick(symbol)
    if tick is None:
        log.error(f"Error obteniendo tick actual de {symbol}")
        return False
        
    filling = detectar_filling_mode(symbol_info)
    
    # Cálculo estricto de TP y SL con POINT = 0.01
    tp_distance = tp_points * POINT
    sl_distance = sl_points * POINT
    
    if direccion == 1:  # BUY
        order_type = mt5.ORDER_TYPE_BUY
        price = tick.ask
        sl = round(price - sl_distance, 2)
        tp = round(price + tp_distance, 2)
        dir_txt = "BUY (COMPRA)"
    else:  # SELL
        order_type = mt5.ORDER_TYPE_SELL
        price = tick.bid
        sl = round(price + sl_distance, 2)
        tp = round(price - tp_distance, 2)
        dir_txt = "SELL (VENTA)"
        
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": order_type,
        "price": price,
        "sl": sl,
        "tp": tp,
        "deviation": 25,
        "magic": magic,
        "comment": f"BX600 {motivo[:18]}",
        "type_time": mt5.ORDER_TIME_GTC,
        "type_filling": filling,
    }
    
    log.info("-" * 65)
    log.info(f"DISPARANDO ORDEN: {dir_txt}")
    log.info(f"  Volumen / Lotes : {lot_size:.2f} (Estrictamente manual según config.json)")
    log.info(f"  Precio Entrada  : {price:.2f}")
    log.info(f"  Stop Loss (SL)  : {sl:.2f} (-{sl_points} pts)")
    log.info(f"  Take Profit (TP): {tp:.2f} (+{tp_points} pts)")
    log.info(f"  Motivo          : {motivo}")
    
    result = mt5.order_send(request)
    
    # Reintento inteligente con modos de filling alternativos si el broker rechaza con 10030
    if result is not None and result.retcode == 10030:
        log.warning("Broker rechazó filling inicial (10030). Probando modos de filling alternativos...")
        modos_alternativos = [mt5.ORDER_FILLING_FOK, mt5.ORDER_FILLING_RETURN, mt5.ORDER_FILLING_IOC]
        for alt_fill in modos_alternativos:
            if alt_fill == filling:
                continue
            request["type_filling"] = alt_fill
            result = mt5.order_send(request)
            if result is not None and result.retcode == mt5.TRADE_RETCODE_DONE:
                log.info(f"  ✓ Orden aceptada con éxito usando filling alternativo {alt_fill}!")
                break
    
    if result is None:
        log.error(f"Fallo al enviar orden: {mt5.last_error()}")
        return False
        
    if result.retcode != mt5.TRADE_RETCODE_DONE:
        log.error(f"Orden rechazada por el broker. Retcode: {result.retcode} | {result.comment}")
        return False
        
    log.info(f"ORDEN EJECUTADA EXITOSAMENTE en MT5!")
    log.info(f"  Ticket de posición : {result.order}")
    log.info(f"  Precio ejecutado   : {result.price:.2f}")
    log.info("-" * 65)
    
    # Registrar en CSV para auditoría
    registrar_operacion_csv({
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ticket": result.order,
        "symbol": symbol,
        "tipo": "BUY" if direccion == 1 else "SELL",
        "lotes": lot_size,
        "precio": result.price,
        "sl": sl,
        "tp": tp,
        "motivo": motivo
    })
    return True

def registrar_operacion_csv(datos: dict):
    """Guarda un registro permanente de cada operación ejecutada en CSV."""
    df_new = pd.DataFrame([datos])
    if not TRADES_CSV.exists():
        df_new.to_csv(TRADES_CSV, index=False, encoding="utf-8")
    else:
        df_new.to_csv(TRADES_CSV, mode="a", header=False, index=False, encoding="utf-8")

# ─────────────────────────────────────────────────────────────
# MOTOR PRINCIPAL DE TRADING EN TIEMPO REAL
# ─────────────────────────────────────────────────────────────
class BotBreakX600:
    def __init__(self):
        self.cfg = cargar_config()
        self.symbol = self.cfg.get("SYMBOL", "BreakX 600")
        self.magic = int(self.cfg.get("MAGIC_NUMBER", 600001))
        self.last_candle_time = None
        
        # Estado del rastreador de spikes y retrocesos
        self.active_spike = None
        
    def reset_spike(self):
        self.active_spike = None

    def procesar_vela_cerrada(self, df_m5: pd.DataFrame):
        """
        Analiza la vela M5 recién cerrada aplicando la estrategia cuantitativa de 4 pasos.
        """
        if len(df_m5) < 10:
            return
            
        vela_actual = df_m5.iloc[-1]
        t_actual = vela_actual["dt"]
        
        log.info(f"[NUEVA VELA M5 CERRADA] {t_actual.strftime('%Y-%m-%d %H:%M')} | "
                 f"Open={vela_actual['open']:.2f} Close={vela_actual['close']:.2f} "
                 f"Rango={vela_actual['rango_pts']} pts Cuerpo={vela_actual['cuerpo_pts']} pts")
                 
        # Tendencia de fondo H1
        trend_h1 = obtener_tendencia_h1(self.symbol, self.cfg.get("H1_EMA_PERIOD", 20))
        trend_h1_str = "ALCISTA (BUY)" if trend_h1 == 1 else "BAJISTA (SELL)" if trend_h1 == -1 else "NEUTRA"
        
        spike_min_pts = int(self.cfg.get("SPIKE_MIN_POINTS", 3500))
        retro_min_pts = int(self.cfg.get("RETRO_MIN_POINTS", 800))
        retro_max_pts = int(self.cfg.get("RETRO_MAX_POINTS", 3500))
        confirm_body_pts = int(self.cfg.get("CONFIRM_BODY_POINTS", 500))
        max_retro_bars = int(self.cfg.get("MAX_RETRO_BARS", 8))
        
        # 1. Comprobar si la vela actual es un nuevo Spike de impulso
        rango = vela_actual["rango_pts"]
        cuerpo = vela_actual["cuerpo_pts"]
        d = vela_actual["dir"]
        
        es_spike = (rango >= spike_min_pts) and (d != 0) and (cuerpo / rango >= 0.60)
        
        if es_spike:
            self.active_spike = {
                "dir": d,
                "close": vela_actual["close"],
                "extreme": vela_actual["high"] if d == 1 else vela_actual["low"],
                "time": t_actual,
                "bars_elapsed": 0,
                "max_retro_pts": 0.0,
            }
            log.info(f"  ⚡ SPIKE DETECTADO: Dirección={'BUY' if d==1 else 'SELL'} | Rango={rango} pts | Tendencia H1={trend_h1_str}")
            return
            
        # 2. Si hay un Spike activo en seguimiento, evaluar el retroceso
        if self.active_spike is not None:
            self.active_spike["bars_elapsed"] += 1
            sp_dir = self.active_spike["dir"]
            sp_close = self.active_spike["close"]
            bars_count = self.active_spike["bars_elapsed"]
            
            # Si transcurrieron más de las velas permitidas, descartar ciclo
            if bars_count > max_retro_bars:
                log.info(f"  [SPIKE ANULADO] Se excedió el límite de {max_retro_bars} velas sin confirmación.")
                self.reset_spike()
                return
                
            # Calcular retroceso adverso visto en esta vela
            if sp_dir == 1:  # Impulso alcista: retroceso es caída respecto al cierre del spike
                retro_pts = (sp_close - vela_actual["low"]) / POINT
            else:            # Impulso bajista: retroceso es subida respecto al cierre del spike
                retro_pts = (vela_actual["high"] - sp_close) / POINT
                
            if retro_pts > self.active_spike["max_retro_pts"]:
                self.active_spike["max_retro_pts"] = retro_pts
                
            max_retro = self.active_spike["max_retro_pts"]
            
            # Si el retroceso supera el límite cuantitativo (>3500 pts), anular por riesgo de cambio de tendencia
            if max_retro > retro_max_pts:
                log.info(f"  [SPIKE INVALIDADO] Retroceso ({max_retro:.0f} pts) superó el umbral seguro de {retro_max_pts} pts. Posible giro contrario.")
                self.reset_spike()
                return
                
            log.info(f"  -> Monitoreando Retroceso: {max_retro:.0f} pts acumulados (Vela {bars_count}/{max_retro_bars})")
            
            # 3. Comprobar si se produce la Confirmación de Giro (Reentrada)
            # - Retroceso acumulado dentro de la zona válida [800, 3500]
            # - La vela actual cierra a favor del spike
            # - Tiene cuerpo constructivo >= 500 pts
            # - Alineado con la tendencia de fondo de H1
            if (retro_min_pts <= max_retro <= retro_max_pts):
                if (d == sp_dir) and (cuerpo >= confirm_body_pts):
                    if d == trend_h1:
                        log.info(f"  🎯 CONDICIONES CUMPLIDAS: Reentrada en retroceso confirmada!")
                        
                        # Comprobar si ya existe posición abierta para evitar sobreoperar
                        if hay_posicion_abierta(self.symbol, self.magic):
                            log.warning("  Posición ya abierta en MT5 con este Magic Number. Se omite orden para no duplicar riesgo.")
                            self.reset_spike()
                            return
                            
                        motivo = f"Reentrada retro={max_retro:.0f}pts v={bars_count}"
                        enviar_orden(d, vela_actual["close"], motivo)
                        self.reset_spike()
                    else:
                        log.info(f"  [FILTRADO POR H1] Señal omitida porque no coincide con tendencia de fondo H1 ({trend_h1_str}).")
                        self.reset_spike()

    def run(self):
        """Bucle principal de monitoreo en tiempo real."""
        log.info(f"Iniciando bucle de escaneo para {self.symbol} (Timeframe M5)...")
        log.info(f"Intervalo de sondeo: {self.cfg.get('POLL_INTERVAL_SECONDS', 2)}s. Presione Ctrl+C para detener.")
        
        while True:
            try:
                # Comprobar conexión viva
                if not mt5.terminal_info():
                    log.warning("Pérdida de conexión con terminal MT5. Reintentando...")
                    mt5.initialize()
                    time.sleep(5)
                    continue
                    
                # Obtener la vela M5 cerrada más reciente
                rates = mt5.copy_rates_from_pos(self.symbol, mt5.TIMEFRAME_M5, 1, 1)
                if rates is not None and len(rates) > 0:
                    current_closed_time = rates[0]["time"]
                    
                    # Si detectamos que cerró una vela nueva
                    if self.last_candle_time is None:
                        self.last_candle_time = current_closed_time
                        log.info(f"Sincronizado con vela M5 actual: {datetime.datetime.fromtimestamp(current_closed_time)}")
                    elif current_closed_time > self.last_candle_time:
                        self.last_candle_time = current_closed_time
                        # Cargar historial suficiente de M5 y procesar
                        df_m5 = obtener_ultimas_velas_m5(self.symbol, count=25)
                        self.procesar_vela_cerrada(df_m5)
                        
                time.sleep(self.cfg.get("POLL_INTERVAL_SECONDS", 2))
                
            except KeyboardInterrupt:
                log.info("Detención manual solicitada por el usuario (Ctrl+C). Cerrando bot...")
                break
            except Exception as e:
                log.error(f"Excepción no controlada en el bucle: {e}", exc_info=True)
                time.sleep(5)
                
        mt5.shutdown()
        log.info("MetaTrader 5 desconectado. Bot finalizado correctamente.")

if __name__ == "__main__":
    cfg = cargar_config()
    if inicializar_mt5(cfg):
        bot = BotBreakX600()
        bot.run()
