"""Detector SRS (compra) / RSR (venta) según docs/DETECTOR_SPEC.md Rev. 1. Sin MT5 ni órdenes (D-015)."""
from .detector import BUY, SELL, Candle, Detector, Discard, Params, Signal, detect

__all__ = ["BUY", "SELL", "Candle", "Detector", "Discard", "Params", "Signal", "detect"]
