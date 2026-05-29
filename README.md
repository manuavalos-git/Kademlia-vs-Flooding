# TP Final SOR2 - Simulación P2P: Kademlia vs Flooding

Simulación y análisis comparativo de redes P2P estructuradas (Kademlia/DHT) vs no estructuradas (Flooding tipo Gnutella) en Python.

## Pregunta de Investigación

¿En qué medida los mensajes por búsqueda de una simulación flooding en Python (N=100 a 1000, K=10) se aproximan a la predicción O(N), y cómo se compara con los O(log N) saltos de Kademlia bajo churn de 5%, 10% y 20%?

## Estructura del Proyecto

```
Kademlia-vs-Flooding/
├── README.md              # Este archivo
├── requirements.txt       # Dependencias Python
├── src/                   # Código fuente
│   ├── flooding.py        # Red P2P no estructurada
│   ├── kademlia.py        # DHT Kademlia
│   ├── node.py            # Clase base Node
│   ├── network.py         # Topología de red
│   ├── simulation.py      # Orquestador de simulaciones
│   └── metrics.py         # Métricas e instrumentación
├── data/                  # Resultados de experimentos (CSV)
│   ├── flooding/
│   ├── kademlia/
│   └── churn/
├── analysis/              # Análisis y visualización
│   ├── plot_results.py
│   ├── statistical_analysis.py
│   └── validate_theory.ipynb
├── configs/               # Configuración de simulaciones
│   └── simulation_config.yaml
├── tests/                 # Tests unitarios
└── informe/               # Informe final PDF
```

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
python -m src.simulation --mode churn --architecture <flooding|kademlia> --churn-rate <tasa> --nodes <N> --runs 100
```

Parámetros:
- `--architecture`: `flooding` o `kademlia`
- `--churn-rate`: Porcentaje de nodos que abandonan/unen por paso (0.05 = 5%)

## Reproducir Experimentos

Los siguientes comandos reproducen exactamente los experimentos del informe.

### Flooding — comparación principal (K=10)

```bash
python -m src.simulation --mode flooding --nodes 10  --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 50  --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 100 --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 500 --neighbors 10 --runs 100
python -m src.simulation --mode flooding --nodes 1000 --neighbors 10 --runs 100
```

### Flooding — sensibilidad al parámetro K

```bash
# K=5
python -m src.simulation --mode flooding --nodes 10  --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 50  --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 100 --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 500 --neighbors 5 --runs 100
python -m src.simulation --mode flooding --nodes 1000 --neighbors 5 --runs 100

# K=20
python -m src.simulation --mode flooding --nodes 50  --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 100 --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 500 --neighbors 20 --runs 100
python -m src.simulation --mode flooding --nodes 1000 --neighbors 20 --runs 100
```

### Kademlia — comparación principal (B=8)

```bash
python -m src.simulation --mode kademlia --nodes 10  --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 50  --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 100 --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 500 --bits 8 --runs 100
python -m src.simulation --mode kademlia --nodes 1000 --bits 8 --runs 100
```

### Kademlia — sensibilidad al parámetro B

```bash
# B=16
python -m src.simulation --mode kademlia --nodes 10  --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 50  --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 100 --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 500 --bits 16 --runs 100
python -m src.simulation --mode kademlia --nodes 1000 --bits 16 --runs 100
```

### Churn — robustez bajo fallas

```bash
# Flooding
python -m src.simulation --mode churn --architecture flooding --churn-rate 0.05 --nodes 1000 --runs 100
python -m src.simulation --mode churn --architecture flooding --churn-rate 0.10 --nodes 1000 --runs 100
python -m src.simulation --mode churn --architecture flooding --churn-rate 0.20 --nodes 1000 --runs 100

# Kademlia
python -m src.simulation --mode churn --architecture kademlia --churn-rate 0.05 --nodes 1000 --runs 100
python -m src.simulation --mode churn --architecture kademlia --churn-rate 0.10 --nodes 1000 --runs 100
python -m src.simulation --mode churn --architecture kademlia --churn-rate 0.20 --nodes 1000 --runs 100
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

## Configuración

Editar `configs/simulation_config.yaml` para cambiar parámetros por defecto:
- Tamaños de red (N values)
- Parámetros de flooding (K)
- Parámetros de Kademlia (B)
- Tasas de churn
- Número de repeticiones

## Tests

```bash
# Ejecutar todos los tests
pytest

# Con cobertura
pytest --cov=src tests/
```

## Resultados

Los resultados de las simulaciones se guardan en formato CSV en el directorio `data/`:
- `data/flooding/results_N{n}_K{k}.csv` - Resultados flooding
- `data/kademlia/results_N{n}_B{b}.csv` - Resultados Kademlia
- `data/churn/results_{arch}_churn{rate}.csv` - Resultados con churn

Cada CSV contiene:
- `run_id`: Número de corrida
- `messages`: Mensajes intercambiados
- `hops`: Saltos hasta encontrar recurso
- `success`: Búsqueda exitosa (True/False)
- `nodes_reached`: Nodos que recibieron la query

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
