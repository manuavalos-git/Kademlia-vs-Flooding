# Simulación Comparativa: Kademlia vs Flooding en Redes P2P

Trabajo Final Individual — Sistemas Operativos y Redes 2 (SOR2)  
Universidad Nacional de General Sarmiento, primer semestre de 2026

---

## Descripción

Este proyecto implementa y compara experimentalmente dos arquitecturas de redes peer-to-peer para distribución de contenido:

- **Flooding** (estilo Gnutella): red no estructurada donde las búsquedas se propagan por inundación con TTL, con complejidad esperada O(N) en mensajes.
- **Kademlia** (DHT con métrica XOR): red estructurada basada en tablas de ruteo distribuidas (k-buckets), con complejidad esperada O(log N) en saltos.

La simulación valida experimentalmente las fórmulas teóricas de distribución P2P estudiadas en la materia (Tcs y Tp2p) y cuantifica el comportamiento de ambas arquitecturas bajo condiciones de churn (entrada y salida de nodos) del 5%, 10% y 20%.

**Pregunta de investigación:**  
¿En qué medida los mensajes por búsqueda de una simulación flooding (N=10 a 15.000, K=10) se aproximan a la predicción O(N), y cómo se compara con los O(log N) saltos de Kademlia (B=16) bajo churn de 5%, 10% y 20%?

---

## Pipeline del Proyecto

El proyecto sigue el siguiente flujo completo de simulación y análisis:

```
Configuración (configs/simulation_config.yaml)
        │
        ▼
Simulación (src/simulation.py)
  ├── FloodingNetwork  ──── BFS con TTL sobre grafo Erdős–Rényi
  └── KademliaNetwork  ──── lookup iterativo sobre k-buckets XOR
        │
        ▼
Instrumentación (src/metrics.py)
  Mensajes, saltos, tasa de éxito, nodos alcanzados → CSV
        │
        ▼
Almacenamiento (data/)
  ├── flooding/   results_N{n}_K{k}.csv
  ├── kademlia/   results_N{n}_B{b}.csv
  └── churn/      {arch}_N{n}_{params}_churn{r}.csv
        │
        ▼
Análisis y validación (analysis/)
  ├── plot_results.py         → figuras comparativas
  ├── statistical_analysis.py → regresiones, Mann-Whitney, IC 95%
  └── validate_theory.ipynb   → validación contra Tcs / Tp2p
        │
        ▼
Informe (informe/TPFinal_SOR2_2026_1s_AvalosLautaro.pdf)
```

Cada etapa es reproducible de forma independiente dado que los CSVs están versionados en el repositorio.

---

## Arquitecturas Evaluadas

### Flooding (red no estructurada)

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| Vecinos por nodo (K) | 10 | K ≥ ln(N); ln(15000) ≈ 9,6 — umbral de conectividad Erdős–Rényi |
| TTL | 20 | Suficiente para N=15000 sin saturar la red en redes pequeñas |
| Repeticiones | 100 | Garantiza IC 95% con varianza empírica observada |

La topología es un grafo aleatorio donde cada nodo elige K vecinos sin repetición. La búsqueda propaga la query a todos los vecinos conocidos hasta encontrar el recurso o agotar el TTL. Se instrumentan los mensajes totales, los saltos hasta el recurso y la tasa de éxito.

### Kademlia (DHT estructurada)

| Parámetro | Valor | Justificación |
|-----------|-------|---------------|
| Bits de ID (B) | 16 | B ≥ log₂(N); log₂(15000) ≈ 13,9 — B=16 evita colisiones para todo el rango |
| Tamaño de k-bucket (k) | 3 | Simplificación; el protocolo real usa k=20. Documentado como limitación |
| Búsquedas paralelas (α) | 3 | Estándar del paper original de Maymounkov & Mazières (2002) |
| Candidatos en shortlist | 9 (k×α) | Compensa el conocimiento parcial de la red sin modificar la semántica del lookup |

Cada nodo mantiene B=16 k-buckets con hasta k=3 entradas cada uno (máximo 48 peers conocidos). El lookup iterativo consulta los α nodos más cercanos al target por distancia XOR en cada ronda, acotando la búsqueda a O(log N) saltos.

**Caso de estudio adicional — saturación de espacio de IDs (B=8):**  
Con B=8, el espacio tiene solo 2^8=256 posiciones. Para N>256, múltiples nodos comparten el mismo ID y el routing colapsa antes que cualquier factor de churn. Los CSVs de B=8 se incluyen en `data/kademlia/` como caso de estudio del impacto de la elección de B.

---

## Requisitos de Hardware y Software

### Hardware mínimo

| Recurso | Mínimo | Utilizado en este trabajo |
|---------|--------|--------------------------|
| CPU | 2 núcleos | Intel Core i5 / AMD Ryzen 5 |
| RAM | 4 GB | 8 GB |
| Almacenamiento | 500 MB libres | ~200 MB (CSVs + figuras) |
| SO | Windows 10 / Ubuntu 20.04 / macOS 11 | Windows 11 Pro |

### Tiempos de ejecución de referencia

| Configuración | Tiempo por 100 runs | Total (serie completa) |
|---------------|---------------------|-----------------------|
| N=1.000 (flooding o Kademlia) | ~2 s | — |
| N=5.000 | ~4,5 s | — |
| N=15.000 | ~19 s | — |
| Serie completa N={10..15000}, todas las tareas | — | ~15-20 min |
| Churn con 30 repeticiones | — | ~3-4 horas |

> Los experimentos de churn con `--reps 30` son costosos. Para una verificación rápida usá `--reps 5` (~25 minutos, resultados estadísticamente comparables).

### Software

- **Python 3.10 o superior** (probado con Python 3.10, 3.11 y 3.13)
- Ver `requirements.txt` para las dependencias exactas

---

## Instalación

```bash
# 1. Clonar el repositorio
git clone <url-del-repo>
cd Kademlia-vs-Flooding

# 2. Crear entorno virtual
python -m venv venv

# 3. Activar entorno virtual
# Windows (PowerShell):
venv\Scripts\Activate.ps1
# Windows (Git Bash):
source venv/Scripts/activate
# Linux / macOS:
source venv/bin/activate

# 4. Instalar dependencias
pip install -r requirements.txt

# 5. Verificar instalación ejecutando los tests
python -m pytest tests/ -v
```

Los 26 tests deben pasar sin errores antes de correr cualquier simulación.

---

## Comandos de Ejecución

### Simulación individual

```bash
# Flooding
python -m src.simulation --mode flooding --nodes <N> --neighbors <K> --runs 100

# Kademlia
python -m src.simulation --mode kademlia --nodes <N> --bits <B> --runs 100

# Churn (corrida única)
python -m src.simulation --mode churn --architecture <flooding|kademlia> \
    --nodes <N> --churn-rate <tasa> --rounds 20 --runs 50

# Churn con múltiples repeticiones (para desvío estándar)
python -m src.simulation --mode churn --architecture flooding \
    --nodes 1000 --neighbors 10 --churn-rate 0.05 --rounds 20 --runs 50 --churn-reps 30
```

### Reproducir todos los resultados del informe

El siguiente script ejecuta en secuencia todas las simulaciones de las Tareas 1 y 2:

```bash
python analysis/run_all_simulations.py
```

Para los experimentos de churn con desvío estándar (Tabla 7 del informe):

```bash
python analysis/run_churn_reps.py --reps 30   # ~3-4 horas
# Para verificación rápida:
python analysis/run_churn_reps.py --reps 5    # ~25 minutos
```

### Generar gráficos y análisis estadístico

```bash
# Generar las 11 figuras del informe
python analysis/plot_results.py --input data/ --output informe/figures/

# Regresiones, prueba Mann-Whitney, tablas comparativas
python analysis/statistical_analysis.py --input data/

# Notebook interactivo con validación teórica
jupyter notebook analysis/validate_theory.ipynb
```

### Limpiar datos generados

```bash
# Linux / macOS / Git Bash
rm -f data/flooding/*.csv data/kademlia/*.csv data/churn/*.csv
rm -f data/analysis_*.csv informe/figures/*.png

# Windows (PowerShell)
Remove-Item data\flooding\*.csv, data\kademlia\*.csv, data\churn\*.csv -ErrorAction SilentlyContinue
Remove-Item data\analysis_*.csv, informe\figures\*.png -ErrorAction SilentlyContinue
```

---

## Descripción de los Datasets

Todos los CSVs están versionados en `data/` y pueden regenerarse con los comandos de la sección anterior.

### Datos de escalabilidad (Tareas 1 y 2)

**Archivos:** `data/flooding/results_N{n}_K{k}.csv`, `data/kademlia/results_N{n}_B{b}.csv`

Una fila por búsqueda individual (100 filas por archivo):

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `messages` | int | Mensajes intercambiados en la búsqueda |
| `hops` | int | Saltos hasta encontrar el recurso |
| `success` | bool | True si el recurso fue encontrado |
| `nodes_reached` | int | Nodos que recibieron la query |

**Configuraciones:**
- Flooding: N ∈ {10, 50, 100, 500, 1000, 5000, 15000} × K ∈ {5, 10, 20}
- Kademlia: N ∈ {10, 50, 100, 500, 1000, 5000, 15000} × B ∈ {8, 16}

### Datos de churn (Tarea 4)

**Archivos:** `data/churn/{arch}_N{n}_{params}_churn{r}.csv`, `data/churn/*_reps30.csv`

Una fila por ronda de churn (20 rondas por experimento):

| Columna | Tipo | Descripción |
|---------|------|-------------|
| `round` | int | Número de ronda (0 = baseline sin churn) |
| `nodes_in_network` | int | Nodos activos al final de la ronda |
| `nodes_churned` | int | Nodos removidos/incorporados en esa ronda |
| `resources_lost` | int | Recursos perdidos (nodos que abandonaron sin redistribución) |
| `success_rate` | float | Fracción de búsquedas exitosas en esa ronda |
| `avg_messages` | float | Mensajes promedio por búsqueda en esa ronda |
| `avg_hops` | float | Saltos promedio por búsqueda en esa ronda |

Los archivos `*_reps30.csv` contienen columnas adicionales `success_rate_std`, `avg_messages_std`, `avg_hops_std` con el desvío estándar sobre 30 repeticiones independientes.

---

## Metodología

### Diseño experimental

Se adoptó un diseño de experimentos con factor único variable (N) y parámetros fijos (K=10, B=16), con análisis de sensibilidad adicional para K ∈ {5, 20} y B=8. Cada configuración se repite 100 veces con semilla fija (`--seed 42`) para garantizar reproducibilidad exacta y calcular intervalos de confianza del 95%.

### Modelo de simulación

**Topología:** grafo aleatorio con distribución de vecinos uniforme. Cada nodo en flooding elige K vecinos sin reemplazo; en Kademlia los vecinos se organizan en k-buckets por distancia XOR.

**Distribución de recursos:** cada nodo almacena un subconjunto de N recursos posibles. La asignación es aleatoria (uniforme) al inicio de cada corrida.

**Modelo de churn:** reemplazo instantáneo por rondas — en cada ronda, una fracción `churn_rate` de nodos abandona (sus recursos se pierden permanentemente) y se incorpora la misma cantidad de nodos nuevos (sin recursos). Este modelo produce una cota inferior de robustez real de Kademlia, dado que en producción cada clave se replica en los k nodos XOR más cercanos.

### Validación teórica

Se calcularon Tcs y Tp2p según las fórmulas del programa para los parámetros indicados en `configs/simulation_config.yaml` (F=1 Gb, Us=100 Mbps, dmin=10 Mbps, Ui_avg=5 Mbps) y se compararon contra los resultados de la simulación. La comparación es de clase de complejidad, no de magnitud: Tcs escala O(N) al igual que flooding; Tp2p escala sub-linealmente al igual que Kademlia.

### Análisis estadístico

- **Regresión lineal** en escala log-log para flooding: estimar la pendiente de O(N).
- **Regresión lineal** hops vs log₂(N) para Kademlia: estimar la pendiente de O(log N).
- **Prueba de Mann-Whitney** (no paramétrica) para comparar distribuciones flooding vs Kademlia por cada N.
- **Intervalos de confianza** del 95% por bootstrap sobre las 100 repeticiones.

---

## Resultados Principales

Los resultados detallados se encuentran en el informe `informe/TPFinal_SOR2_2026_1s_AvalosLautaro.pdf`. A continuación se presenta un resumen de los hallazgos clave.

### Escalabilidad (sin churn)

| N | Flooding — mensajes (media) | Kademlia — saltos (media) | p-valor Mann-Whitney |
|---|------------------------------|---------------------------|----------------------|
| 10 | ~15 | ~2 | < 0,001 |
| 100 | ~155 | ~4 | < 0,001 |
| 1.000 | ~1.550 | ~6 | < 0,001 |
| 5.000 | ~7.700 | ~8 | < 0,001 |
| 15.000 | ~23.000 | ~9 | < 0,001 |

- **Flooding:** pendiente log-log ≈ 1,01 (confirma O(N)).
- **Kademlia:** pendiente hops vs log₂(N) ≈ 0,47 (mejor que la cota O(log N) del paper original porque k=3 entradas por bucket permiten saltos multi-bit, R²=0,99).
- La prueba Mann-Whitney arroja p < 0,001 para todo N ≥ 100, confirmando que la diferencia es estadísticamente significativa.

### Robustez bajo churn

Ambas arquitecturas muestran degradación comparable de la tasa de éxito, lo que aparentemente contradice la literatura. La causa es la ausencia de replicación en el modelo: cuando un nodo abandona, sus recursos se pierden permanentemente independientemente del protocolo. Con churn_rate=5%/ronda, tras la ronda 5 se perdió ≈23% del contenido (1−0,95⁵). Esta simplificación constituye la principal limitación documentada del modelo.

### Validación teórica

Las simulaciones confirman la misma clase de complejidad que predice la teoría: flooding crece O(N) al igual que Tcs; Kademlia crece O(log N) al igual que Tp2p (sub-lineal). La comparación entre fases (búsqueda vs transferencia) se analiza en detalle en la sección 5 del informe.

---

## Limitaciones

1. **Sin replicación de contenido:** en Kademlia real cada clave se replica en los k=20 nodos XOR más cercanos. La ausencia de replicación hace que la comparación de robustez bajo churn subestime la ventaja real de Kademlia.
2. **k=3 en lugar de k=20:** el tamaño de k-bucket simplificado reduce las alternativas de routing y aumenta la probabilidad de fallo de lookup (2⁻³ = 12,5% vs 2⁻²⁰ ≈ 10⁻⁶ en producción).
3. **Entrega instantánea de mensajes:** no se modela latencia, pérdida de paquetes ni ancho de banda por enlace.
4. **Churn sincrónico:** todos los cambios de membresía ocurren al inicio de cada ronda, no de forma continua.
5. **Sin mantenimiento activo de k-buckets:** en Kademlia real los nodos lanzan periódicamente `FIND_NODE` para refrescar los buckets; el modelo no implementa este mecanismo.

---

## Estructura del Repositorio

```
Kademlia-vs-Flooding/
├── README.md                                       ← este archivo
├── requirements.txt                                ← dependencias Python
├── configs/
│   └── simulation_config.yaml                      ← parámetros de todas las simulaciones
├── src/
│   ├── node.py                                     ← clase Node (hash, igualdad, recursos)
│   ├── network.py                                  ← topología aleatoria y distribución de recursos
│   ├── flooding.py                                 ← FloodingNetwork: BFS con TTL
│   ├── kademlia.py                                 ← KademliaNetwork: k-buckets y lookup iterativo
│   ├── simulation.py                               ← CLI argparse: --mode, --nodes, --bits, --runs
│   └── metrics.py                                  ← SearchMetrics, MetricsCollector, export CSV
├── tests/
│   ├── test_node.py       (6 tests)
│   ├── test_network.py    (6 tests)
│   ├── test_kademlia.py   (7 tests)
│   └── test_flooding.py   (7 tests)
├── data/
│   ├── flooding/                                   ← results_N{n}_K{k}.csv
│   ├── kademlia/                                   ← results_N{n}_B{b}.csv
│   └── churn/                                      ← {arch}_N{n}_{params}_churn{r}.csv
├── analysis/
│   ├── plot_results.py                             ← genera informe/figures/
│   ├── statistical_analysis.py                     ← regresiones, Mann-Whitney, tablas
│   ├── run_all_simulations.py                      ← reproduce Tareas 1 y 2 completas
│   ├── run_churn_reps.py                           ← reproduce Tarea 4 con N repeticiones
│   └── validate_theory.ipynb                       ← validación interactiva Tcs / Tp2p
└── informe/
    ├── TPFinal_SOR2_2026_1s_AvalosLautaro.pdf
    └── figures/                                    ← 11 figuras generadas por plot_results.py
```

---

## Tests

```bash
# Activar entorno virtual primero
source venv/Scripts/activate   # Windows Git Bash
# source venv/bin/activate     # Linux / macOS

# Ejecutar suite completa (26 tests)
python -m pytest tests/ -v

# Con reporte de cobertura
python -m pytest tests/ -v --cov=src --cov-report=term-missing
```

---

## Autores y Contexto Académico

**Lautaro Manuel Avalos**  
Autor principal y desarrollador  
Estudiante de Licenciatura en Sistemas — Universidad Nacional de General Sarmiento  
lautaromanuelavalos@gmail.com

**Benjamín Chuquimango**  
Coautor y director académico  
Universidad Nacional de General Sarmiento

---

**Institución:** Universidad Nacional de General Sarmiento (UNGS)  
**Materia:** Sistemas Operativos y Redes 2 (SOR2)  
**Tipo de trabajo:** Trabajo Final Individual  
**Período:** Primer semestre de 2026  
**Tema:** D1 — Simulación comparativa de redes P2P estructuradas vs no estructuradas

---

## Cita Provisional

Citación: pendiente de definición después de la revisión académica y de la decisión sobre publicación del repositorio.
