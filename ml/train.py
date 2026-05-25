"""Train Random Forest quality classifier on cnc_telemetry + lab_testing.

Usage:
    python ml/train.py             # full dataset (~2-4 min)
    python ml/train.py --sample 0.1  # 10% sample for quick testing
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd
import joblib
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    f1_score,
    precision_score,
    recall_score,
    roc_auc_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OrdinalEncoder

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "noruh_quality.db"
MODEL_PATH = Path(__file__).parent / "quality_model.joblib"

NUMERIC_FEATURES = [
    "spindle_speed_rpm",
    "feed_rate_mm_min",
    "vibration_amplitude_g",
    "tool_age_part_count",
]
CATEGORICAL_FEATURES = ["machine_id", "operator_id"]
ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

DISPLAY_NAMES = {
    "spindle_speed_rpm": "Spindle Speed (RPM)",
    "feed_rate_mm_min": "Feed Rate (mm/min)",
    "vibration_amplitude_g": "Vibration (g)",
    "tool_age_part_count": "Tool Age (parts)",
    "machine_id": "Machine",
    "operator_id": "Operator",
}

# Binary defect label: CNC rejection OR any visual inspection failure
TRAINING_QUERY = """
SELECT
    c.timestamp,
    c.spindle_speed_rpm,
    c.feed_rate_mm_min,
    c.vibration_amplitude_g,
    c.tool_age_part_count,
    c.machine_id,
    c.operator_id,
    CASE
        WHEN c.part_status = 'COMPLETED_REJECTED' THEN 1
        WHEN l.visual_inspection IN ('FAIL_CRACK', 'FAIL_SCRATCH', 'FAIL_GOUGE') THEN 1
        ELSE 0
    END AS is_defect
FROM cnc_telemetry c
LEFT JOIN lab_testing l ON c.part_serial_number = l.part_serial_number
"""


def load_data(sample_frac: float = 1.0) -> pd.DataFrame:
    if not DB_PATH.exists():
        raise FileNotFoundError(
            f"Database not found at {DB_PATH}. Run `python pipeline.py` first."
        )
    con = duckdb.connect(str(DB_PATH), read_only=True)
    df = con.execute(TRAINING_QUERY).df()
    con.close()
    if sample_frac < 1.0:
        df = df.sample(frac=sample_frac, random_state=42).reset_index(drop=True)
    return df


def build_risk_trend(df: pd.DataFrame, pipeline: Pipeline) -> pd.DataFrame:
    """Monthly actual vs predicted defect rate across the full dataset."""
    tmp = df.copy()
    tmp["month"] = pd.to_datetime(tmp["timestamp"]).dt.to_period("M").dt.to_timestamp()
    tmp["pred_prob"] = pipeline.predict_proba(tmp[ALL_FEATURES])[:, 1]
    monthly = (
        tmp.groupby("month")
        .agg(
            actual_defect_rate=("is_defect", "mean"),
            predicted_defect_rate=("pred_prob", "mean"),
            n_parts=("is_defect", "count"),
        )
        .reset_index()
    )
    return monthly


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Noruh quality classifier")
    parser.add_argument(
        "--sample",
        type=float,
        default=1.0,
        metavar="FRAC",
        help="Fraction of data to use for training (0 < FRAC ≤ 1, default: 1.0)",
    )
    args = parser.parse_args()

    if not 0 < args.sample <= 1.0:
        sys.exit("--sample must be between 0 and 1")

    print(f"Loading data from {DB_PATH} ...")
    df = load_data(sample_frac=args.sample)
    n_total = len(df)
    defect_rate = df["is_defect"].mean()
    print(f"  {n_total:,} rows  |  defect rate: {defect_rate:.2%}")

    X = df[ALL_FEATURES]
    y = df["is_defect"]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )
    print(f"  train: {len(X_train):,}  |  test: {len(X_test):,}")

    preprocessor = ColumnTransformer(
        [
            ("num", "passthrough", NUMERIC_FEATURES),
            (
                "cat",
                OrdinalEncoder(
                    handle_unknown="use_encoded_value", unknown_value=-1
                ),
                CATEGORICAL_FEATURES,
            ),
        ]
    )

    clf = RandomForestClassifier(
        n_estimators=100,
        max_depth=14,
        class_weight="balanced",
        n_jobs=-1,
        random_state=42,
    )

    pipeline = Pipeline([("pre", preprocessor), ("clf", clf)])

    print("Training Random Forest (n_estimators=100) ...")
    pipeline.fit(X_train, y_train)

    y_pred = pipeline.predict(X_test)
    y_prob = pipeline.predict_proba(X_test)[:, 1]

    metrics = {
        "accuracy": float(accuracy_score(y_test, y_pred)),
        "precision": float(precision_score(y_test, y_pred, zero_division=0)),
        "recall": float(recall_score(y_test, y_pred, zero_division=0)),
        "f1": float(f1_score(y_test, y_pred, zero_division=0)),
        "roc_auc": float(roc_auc_score(y_test, y_prob)),
        "n_train": int(len(X_train)),
        "n_test": int(len(X_test)),
        "defect_rate_train": float(y_train.mean()),
    }

    print("\nTest metrics:")
    for k, v in metrics.items():
        print(f"  {k:<22} {v:.4f}" if isinstance(v, float) else f"  {k:<22} {v:,}")

    print(f"\n{classification_report(y_test, y_pred, target_names=['Pass', 'Defect'])}")

    # Feature importances (column order matches ColumnTransformer: numeric then categorical)
    fi = pd.DataFrame(
        {
            "feature": ALL_FEATURES,
            "display_name": [DISPLAY_NAMES[f] for f in ALL_FEATURES],
            "importance": pipeline.named_steps["clf"].feature_importances_,
        }
    ).sort_values("importance", ascending=False, ignore_index=True)

    print("Feature importances:")
    for _, row in fi.iterrows():
        bar = "█" * int(row["importance"] * 40)
        print(f"  {row['display_name']:<25} {row['importance']:.4f}  {bar}")

    print("\nComputing monthly risk trend ...")
    risk_trend = build_risk_trend(df, pipeline)

    MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
    artifact = {
        "pipeline": pipeline,
        "feature_names": ALL_FEATURES,
        "display_names": DISPLAY_NAMES,
        "feature_importances": fi,
        "metrics": metrics,
        "risk_trend": risk_trend,
        "machine_classes": sorted(df["machine_id"].unique().tolist()),
        "operator_classes": sorted(df["operator_id"].unique().tolist()),
        "feature_ranges": {
            col: (float(df[col].min()), float(df[col].max()))
            for col in NUMERIC_FEATURES
        },
        "trained_at": datetime.utcnow().isoformat(),
        "sample_frac": args.sample,
    }
    joblib.dump(artifact, MODEL_PATH)
    print(f"\nSaved → {MODEL_PATH}")


if __name__ == "__main__":
    main()
