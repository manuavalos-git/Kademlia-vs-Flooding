# TP Final SOR2 - Simulación P2P: Kademlia vs Flooding

Simulación y análisis comparativo de redes P2P estructuradas (Kademlia/DHT) vs no estructuradas (Flooding tipo Gnutella) en Python.

## Pregunta de Investigación

¿En qué medida los mensajes por búsqueda de una simulación flooding en Python (N=10 a 15.000, K=10) se aproximan a la predicción O(N), y cómo se compara con los O(log N) saltos de Kademlia (B=16) bajo churn de 5%, 10% y 20%?

## Estructura del Proyecto

```
Kademlia-vs-Flooding/
├── README.md                      ← instrucciones de instalación y ejecución
├── requirements.txt               ← dependencias Python
├── configs/
│   └── simulation_config.yaml     ← parámetros por defecto de todas las simulaciones
├── src/
│   ├── node.py                    ← clase Node con hash, igualdad y recursos
│   ├── network.py                 ← topología aleatoria y distribución de recursos
│   ├── flooding.py                ← FloodingNetwork: búsqueda BFS con TTL
│   ├── kademlia.py                ← KademliaNetwork: k-buckets y lookup iterativo
│   ├── simulation.py              ← CLI argparse: --mode, --nodes, --bits, --runs
│   └── metrics.py                 ← SearchMetrics, MetricsCollector, export CSV
├── data/
│   ├── flooding/                  ← results_N{n}_K{k}.csv (100 repeticiones c/u)
│   ├── kademlia/                  ← results_N{n}_B{b}.csv
│   └── churn/                     ← flooding_N{n}_K{k}_churn{r}.csv,
│                                     kademlia_N{n}_B{b}_churn{r}.csv
├── analysis/
│   ├── plot_results.py            ← genera todas las figuras en informe/figures/
│   ├── statistical_analysis.py    ← regresiones, IC 95%, tablas comparativas
│   └── validate_theory.ipynb      ← notebook interactivo de validación
└── informe/
    ├── TPFinal_SOR2_2026_1s_AvalosLautaro.pdf   ← informe
    └── figures/                   ← gráficos generados por plot_results.py
```

## Reproducir todos los resultados del informe

Los siguientes pasos permiten clonar el repositorio y reproducir exactamente todos los resultados, figuras y análisis estadísticos del informe, comenzando desde cero.

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd Kademlia-vs-Flooding

# 2. Crear entorno virtual e instalar dependencias
python -m venv venv
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # Linux / Mac
pip install -r requirements.txt

# 3. Verificar que los tests pasan
python -m pytest tests/ -v

# 4. Correr simulaciones de flooding y Kademlia (Tareas 1 y 2)
#    Genera ~55 CSVs en data/flooding/ y data/kademlia/
python analysis/run_all_simulations.py

# 5. Correr experimentos de churn con 30 repeticiones (Tarea 4)
#    Genera 18 CSVs en data/churn/*_reps30.csv  (~3-4 hs, ver nota abajo)
python analysis/run_churn_reps.py --reps 30

# 6. Generar todos los gráficos
python analysis/plot_results.py --input data/ --output informe/figures/

# 7. Generar análisis estadístico (regresiones, Mann-Whitney, tablas)
python analysis/statistical_analysis.py --input data/
```

> **Nota de tiempo**: el paso 5 con `--reps 30` tarda ~3-4 horas en una máquina de escritorio convencional porque N=15000 requiere ~8 min por configuración × 30 reps. Para una prueba rápida usá `--reps 5` (~25 minutos, resultados comparables).

> **Semilla fija**: todos los comandos usan `--seed 42` por defecto, garantizando reproducibilidad exacta en cualquier plataforma con la misma versión de Python.

## Requisitos

- Python 3.10 o superior
- Dependencias listadas en `requirements.txt`

## Instalación

```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (Git Bash):
source venv/Scripts/activate
# Linux/Mac:
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

## Uso

### Ejecutar Simulación Flooding

```bash
python -m src.simulation --mode flooding --nodes <N> --neighbors <K> --runs 100
```

Parámetros:
- `--nodes`: Número de nodos en la red (N)
- `--neighbors`: Vecinos por nodo (K)
- `--runs`: Repeticiones para estadística

### Ejecutar Simulación Kademlia

```bash
python -m src.simulation --mode kademlia --nodes <N> --bits <B> --runs 100
```

Parámetros:
- `--nodes`: Número de nodos en la red (N)
- `--bits`: Bits del ID de nodo (B)
- `--runs`: Repeticiones para estadística

### Ejecutar Simulación con Churn

```bash
python -m src.simulation --mode churn --architecture <flooding|kademlia> \
    --nodes <N> --churn-rate <tasa> --rounds <rondas> --runs <busquedas_por_ronda> \
    [--churn-reps <repeticiones>]
```

Parámetros:
- `--architecture`: `flooding` o `kademlia`
- `--churn-rate`: Fracción de nodos que abandonan/unen por ronda (0.05 = 5%)
- `--rounds`: Número de rondas de churn (default 20)
- `--runs`: Búsquedas por ronda (default 50)
- `--churn-reps`: Repeticiones independientes (default 1). Con `--churn-reps 30` corre el experimento 30 veces con distintas semillas y guarda un CSV con media ± desvío estándar por ronda en `data/churn/*_reps30.csv`.

Para reproducir los resultados de la Tabla 7 del informe (con desvío estándar) de manera automática para las 18 configuraciones:

```bash
python analysis/run_churn_reps.py --reps 30
```

## Reproducir Experimentos

Los siguientes comandos reproducen exactamente los experimentos del informe.

**Serie de N elegida**: {10, 50, 100, 500, 1000, 5000, 15000}
**Justificación de límite superior**: N=15000 tarda ~19s/100 runs; N=50000 (~2.4 min/100 runs) se descartó. B=16 sigue siendo válido para todo el rango (2^16=65536 >> 15000).
**Justificación K=10**: K ≥ ln(N) garantiza conectividad (umbral Erdős–Rényi); ln(15000)≈9.6, por lo que K=10 es el mínimo teórico redondeado.
**Justificación B=16**: requiere B ≥ log2(N); log2(15000)≈13.9, B=16 da margen suficiente para todo el rango sin colisiones de ID.

---

### Tarea 1 — Flooding, comparación principal (K=10)

```bash
python -m src.simulation --mode flooding --nodes 10    --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 50    --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 100   --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 500   --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 1000  --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 5000  --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 15000 --neighbors 10 --runs 100
```

### Tarea 1 — Flooding, sensibilidad al parámetro K

Permite justificar K=10 frente a valores menores y mayores. N=10 con K=20 no aplica (no hay 20 vecinos posibles).

```bash
# K=5
python -m src.simulation --mode flooding --nodes 10    --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 50    --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 100   --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 500   --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 1000  --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 5000  --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 15000 --neighbors 5 --runs 100

# K=20
python -m src.simulation --mode flooding --nodes 50    --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 100   --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 500   --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 1000  --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 5000  --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 15000 --neighbors 20 --runs 100
```

### Tarea 2 — Kademlia, comparación principal (B=16)

B=16 garantiza 2^16=65536 IDs disponibles para todo el rango de N, evitando colisiones de identificadores.

```bash
python -m src.simulation --mode kademlia --nodes 10    --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 50    --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 100   --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 500   --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 1000  --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 5000  --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 15000 --bits 16 --runs 100
```

### Tarea 2 — Kademlia, caso de estudio: saturación de espacio de IDs (B=8)

Con B=8 el espacio tiene solo 2^8=256 posiciones. Para N>256 múltiples nodos comparten el mismo ID,
lo que destruye el routing antes que cualquier otro factor. Se usa como caso de estudio en el informe
para ilustrar la interdependencia entre B y N.

```bash
python -m src.simulation --mode kademlia --nodes 10    --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 50    --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 100   --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 500   --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 1000  --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 5000  --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 15000 --bits 8 --runs 100
```

### Tarea 3 — Validación teórica y gráficos

No requiere correr simulaciones adicionales. Usar los CSVs generados en Tareas 1 y 2:

```bash
python analysis/plot_results.py --input data/ --output informe/figures/
python analysis/statistical_analysis.py --input data/
jupyter notebook analysis/validate_theory.ipynb
```

### Tarea 4 — Churn, robustez bajo fallas

Cada corrida ejecuta 20 rondas de churn con 50 búsquedas por ronda (1000 búsquedas totales).
**Serie de N para churn**: {1000, 5000, 15000} — N pequeños (10–500) no son significativos para churn
porque con 5% de churn sobre N=10 se reemplaza menos de 1 nodo por ronda.

```bash
# Flooding K=10
python -m src.simulation --mode churn --architecture flooding --nodes 1000  --neighbors 10 --churn-rate 0.05 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 1000  --neighbors 10 --churn-rate 0.10 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 1000  --neighbors 10 --churn-rate 0.20 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 5000  --neighbors 10 --churn-rate 0.05 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 5000  --neighbors 10 --churn-rate 0.10 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 5000  --neighbors 10 --churn-rate 0.20 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 15000 --neighbors 10 --churn-rate 0.05 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 15000 --neighbors 10 --churn-rate 0.10 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture flooding --nodes 15000 --neighbors 10 --churn-rate 0.20 --rounds 20 --runs 50

# Kademlia B=16 — comparación principal con flooding (2^16=65536 >> N=15000, sin colisiones de ID)
python -m src.simulation --mode churn --architecture kademlia --nodes 1000  --bits 16 --churn-rate 0.05 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 1000  --bits 16 --churn-rate 0.10 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 1000  --bits 16 --churn-rate 0.20 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 5000  --bits 16 --churn-rate 0.05 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 5000  --bits 16 --churn-rate 0.10 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 5000  --bits 16 --churn-rate 0.20 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 15000 --bits 16 --churn-rate 0.05 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 15000 --bits 16 --churn-rate 0.10 --rounds 20 --runs 50
python -m src.simulation --mode churn --architecture kademlia --nodes 15000 --bits 16 --churn-rate 0.20 --rounds 20 --runs 50
```

### Generar Gráficos y Análisis

```bash
# Generar gráficos de resultados
python analysis/plot_results.py --input data/ --output informe/figures/

# Análisis estadístico
python analysis/statistical_analysis.py --input data/

# Análisis interactivo con Jupyter
jupyter notebook analysis/validate_theory.ipynb
```

## Limpiar Datos Generados

Para borrar todos los CSVs de experimentos y figuras y volver a empezar desde cero:

```bash
# Linux/Mac/Git Bash
rm -f data/flooding/*.csv data/kademlia/*.csv data/churn/*.csv
rm -f data/analysis_*.csv
rm -f informe/figures/*.png

# Windows (PowerShell)
Remove-Item data\flooding\*.csv, data\kademlia\*.csv, data\churn\*.csv -ErrorAction SilentlyContinue
Remove-Item data\analysis_*.csv -ErrorAction SilentlyContinue
Remove-Item informe\figures\*.png -ErrorAction SilentlyContinue
```

Los archivos `.gitkeep` dentro de cada carpeta no se eliminan, preservando la estructura de directorios.

## Configuración

Editar `configs/simulation_config.yaml` para cambiar parámetros por defecto:
- Tamaños de red (N values)
- Parámetros de flooding (K)
- Parámetros de Kademlia (B)
- Tasas de churn
- Número de repeticiones

## Tests

```bash
# Activar el entorno virtual primero
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # Linux / Mac

# Ejecutar todos los tests
python -m pytest tests/ -v
```

## Resultados

Los resultados de las simulaciones se guardan en formato CSV en el directorio `data/`:
- `data/flooding/results_N{n}_K{k}.csv` — búsquedas individuales (flooding)
- `data/kademlia/results_N{n}_B{b}.csv` — búsquedas individuales (Kademlia)
- `data/churn/flooding_N{n}_K{k}_churn{pct}.csv` — métricas por ronda bajo churn, corrida única
- `data/churn/kademlia_N{n}_B{b}_churn{pct}.csv` — ídem para Kademlia
- `data/churn/*_reps30.csv` — media ± desvío estándar por ronda sobre 30 repeticiones independientes

CSVs de flooding/kademlia (una fila por búsqueda):
- `messages`: Mensajes intercambiados
- `hops`: Saltos hasta encontrar recurso
- `success`: Búsqueda exitosa (True/False)
- `nodes_reached`: Nodos que recibieron la query

CSVs de churn (una fila por ronda):
- `round`: Número de ronda
- `nodes_in_network`: Nodos activos al final de la ronda
- `nodes_churned`: Nodos removidos/agregados en esa ronda
- `resources_lost`: Recursos perdidos por nodos que abandonaron
- `success_rate`: Tasa de éxito de búsquedas en esa ronda
- `avg_messages`, `avg_hops`: Métricas promedio de la ronda

## Validación Teórica

El proyecto valida experimentalmente las fórmulas:
- **Tcs** = max(NF/Us, F/dmin) - Tiempo distribución cliente-servidor
- **Tp2p** = max(F/Us, F/dmin, NF/(Us + ΣUi)) - Tiempo distribución P2P
- **Flooding**: O(N) mensajes esperados
- **Kademlia**: O(log N) saltos esperados

## Autor

Lautaro Avalos - TP Final SOR2 2026

## Licencia

MIT License
