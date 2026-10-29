# Fase 2 – Reproducción de EMACEAV5.1 (informe)

Periodo: desarrollo, 1-ene-2025 a 30-abr-2026. La reserva (may-oct 2026) no se tocó.
Simulación: M5, indicadores calculados como MT5 (EMA, iADX, iCCI), señal en vela cerrada, entrada en la apertura de la vela siguiente. SL/TP revisados en M1 (si ambos se tocan en el mismo minuto, cuenta SL). Compras entran al ask y salen al bid. Lote 0,1 (1.000 puntos = $1).

## ¿El backtest reproduce al EA real? Sí
- 25-ago a 8-sep-2025: de 111 operaciones reales del EA, 83 aparecen idénticas en el backtest (misma vela y dirección); 96% con el mismo resultado.
- El backtest abre además 86 operaciones que en la realidad no se tomaron (EA o PC apagados).
  - Operaciones que sí se tomaron: +70.000 pts.
  - Las que no se tomaron: −125.000 pts.
  - Si el EA hubiera estado encendido todo el tiempo, esas 2 semanas habrían terminado en −55.000 pts (−$55).

## Resultado completo (spread 130)
| Métrica | Valor |
|---|---|
| Operaciones | 5.283 (10,9 por día) |
| Acierto | 65,7% (necesario para empatar: 66,7%) |
| Resultado | −735.000 pts = −$735 a lote 0,1 |
| Promedio por operación | −139 pts |
| Meses positivos | 5 de 16 |
| Peor caída (drawdown) | −875.000 pts = −$875 |
| Mejor tramo de 14 días | +205.000 pts (+$205), mayo 2025 |

Con spread 65: −445.000 pts (−$445). El spread empeora el resultado, pero no es la causa.

## Comparación con el azar
| Prueba | Promedio por operación |
|---|---|
| Estrategia | −139 pts |
| Mismas horas, dirección al azar (2.000 simulaciones) | −124 pts (el 57% de las simulaciones iguala o supera a la estrategia) |
| Horas y dirección al azar | −175 pts (36%) |
| Mismas horas, dirección CONTRARIA | −111 pts |

Conclusión: la estrategia original no supera al azar después de costes. Sus señales de dirección no aportan información. La racha de 2 semanas fue suerte de cuándo estuvo encendido el EA, más el aumento de lote.
