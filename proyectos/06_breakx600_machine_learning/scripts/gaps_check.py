import polars as pl
import numpy as np

m5 = pl.read_parquet(str(__import__('pathlib').Path(__file__).resolve().parent.parent/'output'/'m5_limpio.parquet'))
print(f'Total filas: {len(m5):,}')
print(f'Primera vela: {m5["dt"].min()}')
print(f'Ultima vela:  {m5["dt"].max()}')
print(f'Duplicados de dt: {len(m5) - m5["dt"].n_unique()}')
print()

# Huecos temporales
diffs = m5.select(pl.col('dt').diff().dt.total_minutes().alias('d')).drop_nulls()
non5 = diffs.filter(pl.col('d') != 5)
print(f'Intervalos != 5 min: {len(non5):,}')

gap_dist = non5.group_by('d').agg(pl.len().alias('n')).sort('n', descending=True)
print('Distribucion de huecos:')
print(gap_dist.head(20))

# Huecos grandes con fecha
big = (
    m5.with_columns(pl.col('dt').diff().dt.total_minutes().alias('diff_min'))
    .filter(pl.col('diff_min') > 60)
    .select(['dt', 'diff_min'])
    .sort('diff_min', descending=True)
)
print(f'\nHuecos > 60 min: {len(big):,}')
print(big.head(30))

# Spreads
print('\nDistribucion de spread (puntos):')
sp = m5.group_by('spread').agg(pl.len().alias('n')).sort('spread')
print(sp)
