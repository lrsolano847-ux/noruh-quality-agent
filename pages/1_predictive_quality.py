"""Page 1 — Predictive Quality Classifier.

Shows model health, feature importance, risk trend, and live prediction.
Requires: python ml/train.py  (needs data/noruh_quality.db to exist).
"""

import sys
from pathlib import Path

import joblib
import pandas as pd
import streamlit as st

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

MODEL_PATH = ROOT / "ml" / "quality_model.joblib"

st.set_page_config(
    page_title="Predictive Quality | Noruh",
    page_icon="🔮",
    layout="wide",
)

# ── Load artifact ────────────────────────────────────────────────────────────

@st.cache_resource(show_spinner="Loading model …")
def load_artifact():
    if not MODEL_PATH.exists():
        return None
    return joblib.load(MODEL_PATH)


artifact = load_artifact()

# ── Header ───────────────────────────────────────────────────────────────────

st.title("🔮 Predictive Quality Classifier")
st.caption(
    "Random Forest trained on 5 years of CNC telemetry + lab testing outcomes. "
    "Target: any defect (CNC rejection or visual inspection failure)."
)

if artifact is None:
    st.warning(
        "**Model not found.**\n\n"
        "Train the classifier first:\n"
        "```\n"
        "python pipeline.py          # generate database (~80 s)\n"
        "python ml/train.py          # train model (~2-4 min)\n"
        "```",
        icon="⚠️",
    )
    st.stop()

metrics = artifact["metrics"]
trained_at = artifact["trained_at"][:10]
sample_note = (
    f" · {artifact['sample_frac']:.0%} sample"
    if artifact["sample_frac"] < 1.0
    else ""
)

st.caption(
    f"Trained {trained_at}{sample_note} · "
    f"{metrics['n_train']:,} train / {metrics['n_test']:,} test · "
    f"Base defect rate: {metrics['defect_rate_train']:.1%}"
)

# ── Model health metrics ──────────────────────────────────────────────────────

st.subheader("Model Health")
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Accuracy", f"{metrics['accuracy']:.1%}")
c2.metric("Precision", f"{metrics['precision']:.1%}")
c3.metric("Recall", f"{metrics['recall']:.1%}")
c4.metric("F1 Score", f"{metrics['f1']:.1%}")
c5.metric("ROC-AUC", f"{metrics['roc_auc']:.3f}")

st.divider()

# ── Feature importance + Risk trend ──────────────────────────────────────────

left, right = st.columns([2, 3])

with left:
    st.subheader("Feature Importance")
    fi = artifact["feature_importances"].copy()

    try:
        import altair as alt

        chart = (
            alt.Chart(fi.sort_values("importance"))
            .mark_bar(cornerRadiusEnd=3)
            .encode(
                x=alt.X(
                    "importance:Q",
                    title="Mean Decrease in Impurity",
                    axis=alt.Axis(format=".3f"),
                ),
                y=alt.Y("display_name:N", sort="-x", title=""),
                color=alt.Color(
                    "importance:Q",
                    scale=alt.Scale(scheme="blues"),
                    legend=None,
                ),
                tooltip=[
                    alt.Tooltip("display_name:N", title="Feature"),
                    alt.Tooltip("importance:Q", title="Importance", format=".4f"),
                ],
            )
            .properties(height=240)
        )
        st.altair_chart(chart, use_container_width=True)
    except ImportError:
        st.bar_chart(fi.set_index("display_name")["importance"])

with right:
    st.subheader("Monthly Defect Risk Trend")
    risk_trend = artifact["risk_trend"].copy()
    risk_trend["month"] = pd.to_datetime(risk_trend["month"])

    try:
        import altair as alt

        melted = risk_trend.melt(
            id_vars="month",
            value_vars=["actual_defect_rate", "predicted_defect_rate"],
            var_name="series",
            value_name="rate",
        )
        melted["series"] = melted["series"].map(
            {
                "actual_defect_rate": "Actual",
                "predicted_defect_rate": "Predicted",
            }
        )

        # Anomaly reference bands
        anomalies = pd.DataFrame(
            [
                {"start": "2022-04-01", "end": "2022-06-30", "label": "ANOM-01"},
                {"start": "2023-06-01", "end": "2023-08-31", "label": "ANOM-02"},
                {"start": "2024-10-01", "end": "2024-10-31", "label": "ANOM-03"},
            ]
        )
        anomalies["start"] = pd.to_datetime(anomalies["start"])
        anomalies["end"] = pd.to_datetime(anomalies["end"])

        bands = (
            alt.Chart(anomalies)
            .mark_rect(opacity=0.12, color="#e53e3e")
            .encode(x="start:T", x2="end:T")
        )

        band_labels = (
            alt.Chart(anomalies)
            .mark_text(angle=270, fontSize=9, color="#e53e3e", dy=-4)
            .encode(x="start:T", text="label:N")
        )

        lines = (
            alt.Chart(melted)
            .mark_line(strokeWidth=2)
            .encode(
                x=alt.X("month:T", title="Month"),
                y=alt.Y(
                    "rate:Q",
                    title="Defect Rate",
                    axis=alt.Axis(format=".1%"),
                ),
                color=alt.Color(
                    "series:N",
                    scale=alt.Scale(
                        domain=["Actual", "Predicted"],
                        range=["#e53e3e", "#3182ce"],
                    ),
                    legend=alt.Legend(orient="bottom", title=None),
                ),
                tooltip=[
                    alt.Tooltip("month:T", title="Month"),
                    alt.Tooltip("series:N", title="Series"),
                    alt.Tooltip("rate:Q", title="Rate", format=".2%"),
                ],
            )
            .properties(height=240)
        )

        st.altair_chart(bands + band_labels + lines, use_container_width=True)
        st.caption(
            "Red bands mark known anomaly windows: "
            "ANOM-01 (Machine B calibration drift), "
            "ANOM-02 (cheap tooling campaign), "
            "ANOM-03 (OP-007 gouge events)."
        )
    except ImportError:
        st.line_chart(
            risk_trend.set_index("month")[
                ["actual_defect_rate", "predicted_defect_rate"]
            ]
        )

st.divider()

# ── Live prediction tool ──────────────────────────────────────────────────────

st.subheader("Live Risk Predictor")
st.caption("Dial in CNC telemetry parameters to get an instant defect-probability estimate.")

machine_classes = artifact["machine_classes"]
operator_classes = artifact["operator_classes"]
ranges = artifact.get("feature_ranges", {})

def _range(col, default_min, default_max):
    lo, hi = ranges.get(col, (default_min, default_max))
    return float(lo), float(hi)


p1, p2, p3 = st.columns(3)

with p1:
    machine_id = st.selectbox("Machine", machine_classes)
    operator_id = st.selectbox("Operator", operator_classes)

with p2:
    rpm_lo, rpm_hi = _range("spindle_speed_rpm", 8_000, 14_000)
    spindle_speed_rpm = st.slider(
        "Spindle Speed (RPM)",
        min_value=int(rpm_lo),
        max_value=int(rpm_hi),
        value=int((rpm_lo + rpm_hi) / 2),
        step=50,
    )

    feed_lo, feed_hi = _range("feed_rate_mm_min", 1_000, 1_800)
    feed_rate_mm_min = st.slider(
        "Feed Rate (mm/min)",
        min_value=int(feed_lo),
        max_value=int(feed_hi),
        value=int((feed_lo + feed_hi) / 2),
        step=10,
    )

with p3:
    vib_lo, vib_hi = _range("vibration_amplitude_g", 0.10, 4.00)
    vibration_amplitude_g = st.slider(
        "Vibration Amplitude (g)",
        min_value=round(vib_lo, 2),
        max_value=round(vib_hi, 2),
        value=0.50,
        step=0.05,
        format="%.2f",
        help="Parts are auto-rejected at the CNC stage when vibration exceeds 3.5 g (ANOM-04).",
    )

    age_lo, age_hi = _range("tool_age_part_count", 1, 400)
    tool_age_part_count = st.slider(
        "Tool Age (parts since last change)",
        min_value=int(age_lo),
        max_value=int(age_hi),
        value=100,
        step=1,
    )

input_df = pd.DataFrame(
    [
        {
            "spindle_speed_rpm": float(spindle_speed_rpm),
            "feed_rate_mm_min": float(feed_rate_mm_min),
            "vibration_amplitude_g": vibration_amplitude_g,
            "tool_age_part_count": float(tool_age_part_count),
            "machine_id": machine_id,
            "operator_id": operator_id,
        }
    ]
)

pipeline = artifact["pipeline"]
prob = float(pipeline.predict_proba(input_df)[0, 1])

if prob < 0.15:
    risk_level, risk_color, risk_icon = "Low", "green", "✅"
elif prob < 0.40:
    risk_level, risk_color, risk_icon = "Medium", "orange", "⚠️"
else:
    risk_level, risk_color, risk_icon = "High", "red", "🔴"

r1, r2, r3 = st.columns([1, 1, 2])
r1.metric("Defect Probability", f"{prob:.1%}")
r2.metric("Risk Band", f"{risk_icon} {risk_level}")
with r3:
    st.progress(
        min(prob, 1.0),
        text=f"{risk_icon} {risk_level} risk — {prob:.1%} predicted defect probability",
    )

# Contextual note for extreme vibration
if vibration_amplitude_g > 3.5:
    st.error(
        "Vibration exceeds 3.5 g — this part would be **auto-rejected** at the CNC "
        "stage before reaching lab testing (ANOM-04).",
        icon="🚨",
    )
elif vibration_amplitude_g > 2.5:
    st.warning(
        "Vibration above 2.5 g raises FAIL_CRACK risk in lab visual inspection.",
        icon="⚠️",
    )
