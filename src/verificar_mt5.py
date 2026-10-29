# -*- coding: utf-8 -*-
"""
FASE 0 - Verificacion de MT5 en SOLO LECTURA.

Este script NO envia, NO modifica y NO cierra ordenes. Solo usa funciones de lectura:
initialize, account_info, terminal_info, symbols_get, symbol_info, symbol_info_tick,
copy_rates_range y order_calc_margin (este ultimo solo CALCULA el margen, no abre nada).

Guarda:
  resultados/fase0_verificacion.txt   (resumen legible)
  resultados/fase0_verificacion.json  (datos completos para Claude)
"""
import json
import os
import sys
import traceback
from datetime import datetime, timezone

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RES = os.path.join(BASE, "resultados")
os.makedirs(RES, exist_ok=True)

lineas = []
datos = {"generado_utc": datetime.now(timezone.utc).isoformat()}


def out(txt=""):
    print(txt)
    lineas.append(str(txt))


def guardar():
    with open(os.path.join(RES, "fase0_verificacion.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lineas) + "\n")
    with open(os.path.join(RES, "fase0_verificacion.json"), "w", encoding="utf-8") as f:
        json.dump(datos, f, ensure_ascii=False, indent=2, default=str)


try:
    import MetaTrader5 as mt5
except ImportError:
    out("ERROR: falta el paquete MetaTrader5 de Python.")
    datos["error"] = "MetaTrader5 no instalado"
    guardar()
    sys.exit(1)

TFS = ["M1", "M2", "M3", "M4", "M5", "M6", "M10", "M12", "M15", "M20", "M30",
       "H1", "H2", "H3", "H4", "H6", "H8", "H12", "D1"]

out("=== FASE 0: verificacion de MT5 (solo lectura) ===")
out("Conectando con MT5 abierto...")
if not mt5.initialize():
    out(f"ERROR: no se pudo conectar con MT5: {mt5.last_error()}")
    out("Revisa que MT5 este ABIERTO y con la sesion de Weltrade iniciada.")
    datos["error"] = f"initialize: {mt5.last_error()}"
    guardar()
    sys.exit(1)

try:
    # ---------- Terminal y cuenta ----------
    ti = mt5.terminal_info()
    ai = mt5.account_info()
    modos = {0: "DEMO", 1: "CONCURSO", 2: "REAL"}
    datos["terminal"] = {
        "nombre": ti.name, "empresa": ti.company, "ruta": ti.path,
        "conectado": ti.connected, "max_barras_grafico": ti.maxbars,
        "trading_algoritmico_permitido": ti.trade_allowed,
    }
    datos["cuenta"] = {
        "tipo": modos.get(ai.trade_mode, ai.trade_mode), "servidor": ai.server,
        "empresa": ai.company, "moneda": ai.currency, "apalancamiento": ai.leverage,
        "balance": ai.balance, "equity": ai.equity,
    }
    out("")
    out("--- CUENTA ---")
    out(f"Empresa: {ai.company}")
    out(f"Servidor: {ai.server}")
    out(f"Tipo de cuenta: {modos.get(ai.trade_mode, ai.trade_mode)}")
    out(f"Moneda: {ai.currency}   Apalancamiento: 1:{ai.leverage}   Balance: {ai.balance}")
    out(f"Max. barras en grafico (ajuste de MT5): {ti.maxbars}")
    if "weltrade" not in (ai.company or "").lower() and "weltrade" not in (ai.server or "").lower():
        out("AVISO: la cuenta conectada NO parece ser de Weltrade.")

    # ---------- Simbolos ----------
    todos = mt5.symbols_get() or []
    cand = {"oro": [], "bitcoin": []}
    for s in todos:
        n = s.name.upper()
        if "XAU" in n or "GOLD" in n:
            cand["oro"].append(s.name)
        if "BTC" in n or "BITCOIN" in n:
            cand["bitcoin"].append(s.name)
    datos["candidatos"] = cand
    out("")
    out("--- SIMBOLOS ENCONTRADOS ---")
    out(f"Oro: {cand['oro']}")
    out(f"Bitcoin: {cand['bitcoin']}")

    def elegir(lista, preferido):
        for x in lista:
            if x.upper() == preferido:
                return x
        for x in lista:
            if x.upper().startswith(preferido):
                return x
        return lista[0] if lista else None

    simbolos = {"oro": elegir(cand["oro"], "XAUUSD"), "bitcoin": elegir(cand["bitcoin"], "BTCUSD")}
    datos["simbolos_elegidos"] = simbolos

    # ---------- Hora del servidor ----------
    ahora_utc = datetime.now(timezone.utc)
    offsets = {}
    for k, sym in simbolos.items():
        if not sym:
            continue
        mt5.symbol_select(sym, True)  # solo lo agrega a Observacion del mercado
        tk = mt5.symbol_info_tick(sym)
        if tk and tk.time:
            dif_h = round((tk.time - ahora_utc.timestamp()) / 3600)
            offsets[sym] = {"ultimo_tick_hora_servidor": datetime.fromtimestamp(tk.time, timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                            "segundos_desde_tick": round(ahora_utc.timestamp() - (tk.time - dif_h * 3600)),
                            "servidor_menos_utc_h": dif_h}
    datos["hora"] = {"utc_ahora": ahora_utc.isoformat(), "por_simbolo": offsets}
    out("")
    out("--- HORA DEL SERVIDOR ---")
    out(f"Hora UTC ahora: {ahora_utc:%Y-%m-%d %H:%M:%S}")
    for sym, o in offsets.items():
        out(f"{sym}: ultimo tick {o['ultimo_tick_hora_servidor']} (hora servidor) -> servidor = UTC{o['servidor_menos_utc_h']:+d}"
            f" = Ecuador {o['servidor_menos_utc_h'] + 5:+d} h  (tick de hace {o['segundos_desde_tick']} s)")
    out("(Si un mercado esta cerrado, su ultimo tick es viejo y esa diferencia NO sirve.)")

    # ---------- Especificaciones ----------
    campos = ["name", "description", "path", "currency_base", "currency_profit", "currency_margin",
              "digits", "point", "trade_contract_size", "trade_tick_size", "trade_tick_value",
              "trade_tick_value_profit", "trade_tick_value_loss",
              "volume_min", "volume_step", "volume_max", "spread", "spread_float",
              "trade_stops_level", "trade_freeze_level", "trade_mode", "trade_calc_mode",
              "trade_exemode", "filling_mode", "swap_mode", "swap_long", "swap_short",
              "swap_rollover3days", "margin_initial", "margin_maintenance", "margin_hedged",
              "bid", "ask"]
    datos["especificaciones"] = {}
    out("")
    out("--- ESPECIFICACIONES ---")
    swap_modos = {0: "desactivado", 1: "en puntos", 2: "en moneda base", 3: "en moneda de margen",
                  4: "en moneda de deposito", 5: "% anual sobre precio actual", 6: "% anual sobre precio de apertura",
                  7: "reapertura a precio actual", 8: "reapertura a bid"}
    dias = {0: "domingo", 1: "lunes", 2: "martes", 3: "miercoles", 4: "jueves", 5: "viernes", 6: "sabado"}
    for k, sym in simbolos.items():
        if not sym:
            out(f"{k}: NO encontrado")
            continue
        si = mt5.symbol_info(sym)
        d = {c: getattr(si, c, None) for c in campos}
        # margen para el lote minimo (solo calculo)
        try:
            d["margen_lote_min_compra"] = mt5.order_calc_margin(mt5.ORDER_TYPE_BUY, sym, si.volume_min, si.ask)
        except Exception as e:
            d["margen_lote_min_compra"] = f"error: {e}"
        try:
            d["ganancia_1_punto_lote_min"] = mt5.order_calc_profit(mt5.ORDER_TYPE_BUY, sym, si.volume_min, si.ask, si.ask + si.point)
        except Exception as e:
            d["ganancia_1_punto_lote_min"] = f"error: {e}"
        datos["especificaciones"][sym] = d
        out(f"[{sym}] {si.description}")
        out(f"  Precio: bid {si.bid}  ask {si.ask}  spread actual {si.spread} puntos (flotante: {si.spread_float})")
        out(f"  Digitos {si.digits}, punto {si.point}, contrato {si.trade_contract_size}")
        out(f"  Lote min {si.volume_min}, paso {si.volume_step}, max {si.volume_max}")
        out(f"  Valor de 1 tick ({si.trade_tick_size}) con 1 lote: {si.trade_tick_value} {ai.currency}")
        out(f"  Ganancia/perdida por 1 punto con lote minimo: {d['ganancia_1_punto_lote_min']}")
        out(f"  Margen para lote minimo: {d['margen_lote_min_compra']} {ai.currency}")
        out(f"  Swap {swap_modos.get(si.swap_mode, si.swap_mode)}: compra {si.swap_long}, venta {si.swap_short};"
            f" swap triple el {dias.get(si.swap_rollover3days, si.swap_rollover3days)}")
        out(f"  Nivel minimo de stops: {si.trade_stops_level} puntos")

    # ---------- Historial por temporalidad ----------
    out("")
    out("--- HISTORIAL DISPONIBLE POR TEMPORALIDAD ---")
    datos["historial"] = {}
    desde = datetime(2000, 1, 1, tzinfo=timezone.utc)
    hasta = datetime.now(timezone.utc)
    for k, sym in simbolos.items():
        if not sym:
            continue
        datos["historial"][sym] = {}
        out(f"[{sym}]")
        for tf in TFS:
            r = mt5.copy_rates_range(sym, getattr(mt5, "TIMEFRAME_" + tf), desde, hasta)
            if r is None or len(r) == 0:
                datos["historial"][sym][tf] = {"velas": 0, "error": str(mt5.last_error())}
                out(f"  {tf:>4}: sin datos ({mt5.last_error()})")
                continue
            ini = datetime.fromtimestamp(int(r["time"][0]), timezone.utc)
            fin = datetime.fromtimestamp(int(r["time"][-1]), timezone.utc)
            recortado = ti.maxbars and len(r) >= ti.maxbars
            datos["historial"][sym][tf] = {"velas": int(len(r)), "desde": ini.strftime("%Y-%m-%d %H:%M"),
                                           "hasta": fin.strftime("%Y-%m-%d %H:%M"),
                                           "anios": round((fin - ini).days / 365.25, 2),
                                           "posible_limite_max_barras": bool(recortado)}
            out(f"  {tf:>4}: {len(r):>9} velas  desde {ini:%Y-%m-%d}  hasta {fin:%Y-%m-%d}"
                f"  ({(fin - ini).days / 365.25:.1f} anios){'  <- tope de max barras' if recortado else ''}")

    # ---------- Horario observado (ultimas 4 semanas, M1) ----------
    out("")
    out("--- HORARIO OBSERVADO EN M1 (ultimas 4 semanas, hora del SERVIDOR) ---")
    datos["horario_observado"] = {}
    import numpy as np
    for k, sym in simbolos.items():
        if not sym:
            continue
        r = mt5.copy_rates_range(sym, mt5.TIMEFRAME_M1, datetime.fromtimestamp(hasta.timestamp() - 28 * 86400, timezone.utc), hasta)
        if r is None or len(r) == 0:
            continue
        t = r["time"].astype("int64")
        dow = ((t // 86400) + 4) % 7  # 0=domingo
        hora = (t % 86400) // 3600
        tabla = {}
        out(f"[{sym}] minutos con velas por dia y hora (promedio por semana):")
        for d_ in range(7):
            m = dow == d_
            if not m.any():
                tabla[dias[d_]] = "sin velas"
                out(f"  {dias[d_]:>9}: sin velas")
                continue
            horas = sorted(set(hora[m].tolist()))
            mins = (t[m] % 86400) // 60
            tabla[dias[d_]] = {"primera_vela": f"{mins.min() // 60:02d}:{mins.min() % 60:02d}",
                               "ultima_vela": f"{mins.max() // 60:02d}:{mins.max() % 60:02d}",
                               "horas_con_velas": horas,
                               "horas_sin_velas": [h for h in range(24) if h not in horas]}
            out(f"  {dias[d_]:>9}: de {tabla[dias[d_]]['primera_vela']} a {tabla[dias[d_]]['ultima_vela']};"
                f" horas sin velas: {tabla[dias[d_]]['horas_sin_velas'] or 'ninguna'}")
        datos["horario_observado"][sym] = tabla

    out("")
    out("Verificacion terminada. No se envio ni modifico ninguna orden.")
except Exception:
    out("ERROR inesperado:")
    out(traceback.format_exc())
    datos["error"] = traceback.format_exc()
finally:
    mt5.shutdown()
    guardar()
