"""Train and compare candidate classifiers without replacing the production model."""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path

from sklearn.ensemble import GradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score, precision_score, recall_score, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier


TRAINING_DIR = Path(__file__).resolve().parent
PROJECT_DIR = TRAINING_DIR.parent
DATA_PATH = TRAINING_DIR / "final_data.csv"
RESULTS_PATH = PROJECT_DIR / "model_comparison.json"
TABLE_PATH = PROJECT_DIR / "model_comparison.csv"
FEATURES = ["temp", "max_temp", "wind_speed", "cloudcover", "precip", "humidity"]
TARGET = "class"
TEST_SIZE = 0.2
RANDOM_STATE = 42


def load_dataset():
    rows = []
    with DATA_PATH.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        missing = [column for column in FEATURES + [TARGET] if column not in (reader.fieldnames or [])]
        if missing:
            raise ValueError("Training data is missing required columns: " + ", ".join(missing))

        for line_number, row in enumerate(reader, start=2):
            try:
                features = [float(row[column]) for column in FEATURES]
                label = int(row[TARGET])
            except (TypeError, ValueError) as exc:
                raise ValueError("Invalid training value on CSV line {}.".format(line_number)) from exc
            if label not in (0, 1):
                raise ValueError("Expected binary class labels 0 and 1; found {} on line {}.".format(label, line_number))
            rows.append((features, label))

    if not rows:
        raise ValueError("Training data contains no rows.")
    return [row[0] for row in rows], [row[1] for row in rows]


def build_models():
    return [
        ("Logistic Regression", make_pipeline(StandardScaler(), LogisticRegression(max_iter=1000, random_state=RANDOM_STATE))),
        ("Decision Tree", DecisionTreeClassifier(random_state=RANDOM_STATE)),
        ("Random Forest", RandomForestClassifier(n_estimators=100, random_state=RANDOM_STATE, n_jobs=-1)),
        ("Gradient Boosting", GradientBoostingClassifier(random_state=RANDOM_STATE)),
        ("Support Vector Machine", make_pipeline(StandardScaler(), SVC(probability=True, random_state=RANDOM_STATE))),
        ("K-Nearest Neighbors", make_pipeline(StandardScaler(), KNeighborsClassifier(n_neighbors=5))),
    ]


def main():
    features, labels = load_dataset()
    x_train, x_test, y_train, y_test = train_test_split(
        features,
        labels,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=labels,
    )

    results = []
    for name, model in build_models():
        model.fit(x_train, y_train)
        predictions = model.predict(x_test)
        probabilities = model.predict_proba(x_test)[:, 1]
        metrics = {
            "accuracy": round(accuracy_score(y_test, predictions) * 100, 2),
            "precision": round(precision_score(y_test, predictions, zero_division=0) * 100, 2),
            "recall": round(recall_score(y_test, predictions, zero_division=0) * 100, 2),
            "f1_score": round(f1_score(y_test, predictions, zero_division=0) * 100, 2),
            "roc_auc": round(roc_auc_score(y_test, probabilities) * 100, 2),
        }
        results.append({"name": name, "metrics": metrics})
        print("{}: accuracy {:.2f}%".format(name, metrics["accuracy"]))

    results.sort(key=lambda result: result["metrics"]["accuracy"], reverse=True)
    report = {
        "status": "ok",
        "generated_at": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "data_file": "training/final_data.csv",
        "sample_count": len(features),
        "class_counts": {
            "0": labels.count(0),
            "1": labels.count(1),
        },
        "features": FEATURES,
        "target": TARGET,
        "split": {
            "strategy": "stratified train/test split",
            "test_size_percent": round(TEST_SIZE * 100, 2),
            "random_state": RANDOM_STATE,
            "training_samples": len(x_train),
            "test_samples": len(x_test),
        },
        "models": results,
    }
    RESULTS_PATH.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    with TABLE_PATH.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Model", "Accuracy (%)", "Precision (%)", "Recall (%)", "F1 Score (%)", "ROC AUC (%)"])
        for result in results:
            metrics = result["metrics"]
            writer.writerow([
                result["name"],
                metrics["accuracy"],
                metrics["precision"],
                metrics["recall"],
                metrics["f1_score"],
                metrics["roc_auc"],
            ])
    print("Saved comparison results to {}".format(RESULTS_PATH))
    print("Saved comparison table to {}".format(TABLE_PATH))


if __name__ == "__main__":
    main()
