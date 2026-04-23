# SignalForge MLOps

## Overview

A production-style batch ML pipeline focused on reproducibility, observability, and deployment readiness. The system processes OHLCV data to compute rolling statistics on the close column, generates binary trading signals, and outputs structured metrics with comprehensive logging. The pipeline is Dockerized for one-command execution.

## Key Features

- Config-driven execution using YAML
- Deterministic runs via fixed seed
- Robust input and config validation
- Rolling mean computation and signal generation
- Structured metrics output (JSON)
- Detailed logging for observability
- Graceful error handling with consistent outputs
- Dockerized execution for portability

## Project Structure

```
signalforge-mlops/
├── run.py              # Main pipeline script
├── config.yaml         # Pipeline configuration
├── data.csv            # Input data (provided at runtime)
├── requirements.txt    # Python dependencies
├── Dockerfile          # Container build definition
├── README.md           # Project documentation
├── metrics.json        # Generated metrics output
└── run.log             # Generated log file
```

## Requirements

- Python 3.9+
- Docker (optional for containerized execution)

## Local Setup

```bash
pip install -r requirements.txt
```

## Usage

```bash
python run.py --input data.csv --config config.yaml --output metrics.json --log-file run.log
```

Arguments:
- `--input`: Path to input CSV file (must contain `close` column)
- `--config`: Path to YAML configuration file
- `--output`: Path to output metrics JSON file
- `--log-file`: Path to log file

## Docker Instructions

Build:
```bash
docker build -t mlops-task .
```

Run:
```bash
docker run --rm mlops-task
```

The container prints metrics JSON to stdout and writes `metrics.json` and `run.log` inside the container.

## Output Format

Success:
```json
{
  "version": "v1",
  "rows_processed": 10000,
  "metric": "signal_rate",
  "value": 0.4990,
  "latency_ms": 127,
  "seed": 42,
  "status": "success"
}
```

Error:
```json
{
  "version": "v1",
  "status": "error",
  "error_message": "Description of what went wrong"
}
```

## Processing Details

- Only the `close` column is used for computation
- Rolling mean is computed using the window parameter from config
- The first `window - 1` rows produce NaN values in rolling mean
- Rows with NaN rolling mean are excluded from signal calculation
- `rows_processed` reflects the full dataset size including NaN rows
- Signal definition: `1` if `close > rolling_mean`, otherwise `0`

## Observability

`run.log` contains structured execution logs including:
- Job lifecycle events (start, end, status)
- Config validation with seed, window, and version values
- Deterministic seed confirmation
- Data loading with row counts and column info
- Rolling mean computation step
- Signal generation completion
- Metrics summary
- Full exception traceback on failures

## Determinism

Numpy random seed is set from config to ensure reproducible results. Given identical input data and configuration, the pipeline produces identical metrics output.

## Error Handling

- All failures produce a structured `metrics.json` with error details
- Clear, actionable error messages describe the failure cause
- Non-zero exit codes indicate failure
- Exceptions are caught exclusively in `main()` with full traceback logging

## Design Philosophy

Simple, robust, production-style design prioritizing reproducibility and reliability. The codebase avoids unnecessary dependencies, maintains clear separation of concerns through modular functions, and uses type hints for clarity. Configuration is externalized, validation is strict, and outputs are machine-readable for downstream orchestration.