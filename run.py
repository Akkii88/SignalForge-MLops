import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd
import yaml


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="MLOps batch job for signal generation."
    )
    parser.add_argument("--input", required=True, help="Path to input CSV file")
    parser.add_argument("--config", required=True, help="Path to config YAML file")
    parser.add_argument(
        "--output", required=True, help="Path to output metrics JSON file"
    )
    parser.add_argument("--log-file", required=True, help="Path to log file")
    return parser.parse_args()


def setup_logger(log_file: Path) -> logging.Logger:
    logger = logging.getLogger("mlops_task")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    handler = logging.FileHandler(log_file)
    handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(handler)
    return logger


def load_config(config_path: Path) -> Dict[str, Any]:
    if not config_path.exists():
        raise FileNotFoundError(f"Config file not found: {config_path}")
    with open(config_path, "r") as f:
        try:
            config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML: {e}")
    if not isinstance(config, dict):
        raise ValueError("Config must be a dictionary")
    required_keys = {"seed", "window", "version"}
    if missing := required_keys - set(config.keys()):
        raise ValueError(f"Missing config keys: {missing}")
    seed, window, version = config["seed"], config["window"], config["version"]
    if not isinstance(seed, int):
        raise TypeError(f"seed must be int, got {type(seed).__name__}")
    if not isinstance(window, int) or window <= 0:
        raise ValueError(f"window must be positive int, got {window}")
    if not isinstance(version, str):
        raise TypeError(f"version must be str, got {type(version).__name__}")
    return config


def load_data(input_path: Path) -> pd.DataFrame:
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    try:
        df = pd.read_csv(input_path)
    except Exception as e:
        raise ValueError(f"Failed to read CSV: {e}")
    if df.empty:
        raise ValueError("Input CSV is empty")
    if "close" not in df.columns:
        raise ValueError("Required column 'close' not found")
    return df


def compute_signals(df: pd.DataFrame, window: int) -> pd.DataFrame:
    df = df.copy()
    df["rolling_mean"] = df["close"].rolling(window=window).mean()
    valid_mask = df["rolling_mean"].notna()
    df["signal"] = np.nan
    df.loc[valid_mask, "signal"] = (
        df.loc[valid_mask, "close"] > df.loc[valid_mask, "rolling_mean"]
    ).astype(int)
    return df


def build_success_metrics(
    version: str, rows_processed: int, signal_rate: float, latency_ms: int, seed: int
) -> Dict[str, Any]:
    return {
        "version": version,
        "rows_processed": rows_processed,
        "metric": "signal_rate",
        "value": round(signal_rate, 4),
        "latency_ms": latency_ms,
        "seed": seed,
        "status": "success",
    }


def build_error_metrics(version: str, error_message: str) -> Dict[str, Any]:
    return {"version": version, "status": "error", "error_message": error_message}


def write_json(data: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(data, f, indent=2)


def main() -> None:
    start_time = time.time()
    args = parse_args()
    logger = setup_logger(Path(args.log_file))
    logger.info("Job started")

    version = "v1"
    try:
        config = load_config(Path(args.config))
        version = config["version"]
        logger.info(
            f"Config validated: seed={config['seed']}, window={config['window']}, version={config['version']}"
        )

        np.random.seed(config["seed"])
        logger.info(f"Set deterministic seed: {config['seed']}")

        df = load_data(Path(args.input))
        logger.info(f"Loaded {len(df)} rows, columns: {list(df.columns)}")

        df = compute_signals(df, config["window"])
        valid_signals = df["signal"].notna().sum()
        logger.info(
            f"Rolling mean (window={config['window']}) computed, {valid_signals} valid signal rows"
        )
        logger.info("Signal generation completed")
        logger.info(f"Signal distribution: {df['signal'].value_counts().to_dict()}")

        rows_processed = len(df)
        signal_series = df["signal"].dropna()
        signal_rate = round(signal_series.mean(), 4) if not signal_series.empty else 0.0
        latency_ms = int((time.time() - start_time) * 1000)

        metrics = build_success_metrics(
            version, rows_processed, signal_rate, latency_ms, config["seed"]
        )
        write_json(metrics, Path(args.output))
        logger.info(
            f"Metrics: rows_processed={rows_processed}, signal_rate={signal_rate:.4f}, latency_ms={latency_ms}"
        )
        logger.info("Job completed successfully")

        print(json.dumps(metrics, indent=2))
        sys.exit(0)

    except Exception as e:
        try:
            config = load_config(Path(args.config))
            version = config.get("version", version)
        except:
            pass
        metrics = build_error_metrics(version, str(e))
        try:
            write_json(metrics, Path(args.output))
        except:
            pass
        logger.exception("Job failed")
        print(json.dumps(metrics, indent=2))
        sys.exit(1)


if __name__ == "__main__":
    main()
