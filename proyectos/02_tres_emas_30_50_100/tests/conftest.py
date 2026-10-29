import sys
from pathlib import Path

# Permite importar "emas" (raíz del proyecto) y "candles" (esta carpeta).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))
