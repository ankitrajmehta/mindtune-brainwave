import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report, accuracy_score, f1_score

import joblib

# Plotting is optional (comment out if you don't have these installed)
import matplotlib.pyplot as plt
import seaborn as sns

# Importing more models
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    AdaBoostClassifier,
)
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.svm import LinearSVC
from sklearn.neural_network import MLPClassifier
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis

# Optional boosters (install if missing):
#   python3 -m pip install xgboost lightgbm
try:
    from xgboost import XGBClassifier
except Exception:
    XGBClassifier = None

try:
    from lightgbm import LGBMClassifier
except Exception:
    LGBMClassifier = None

# Load the featured dataset
df = pd.read_csv("featured_mindtune.csv")
df = df.drop_duplicates(subset=['session_id', 'timestamp_ms'], keep='first')
# Define features and target
drop_cols = ["session_id", "participant_id", "timestamp_ms", "label_3class", "label_encoded"]
X = df.drop(columns=drop_cols)
y = df["label_encoded"]

# Split the data
X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.2, random_state=42, stratify=y
)

# Scaling features (Required for many models like KNN, SVM, MLP, LogReg)
scaler = StandardScaler()
X_train_scaled = scaler.fit_transform(X_train)
X_test_scaled = scaler.transform(X_test)

models = {
    "Random Forest": RandomForestClassifier(n_estimators=300, random_state=42, n_jobs=-1),
    "Extra Trees": ExtraTreesClassifier(n_estimators=600, random_state=42, n_jobs=-1),
    "Decision Tree": DecisionTreeClassifier(random_state=42),
    "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=25),
    "Gradient Boosting": GradientBoostingClassifier(n_estimators=200, random_state=42),
    "AdaBoost": AdaBoostClassifier(n_estimators=200, random_state=42),
    "MLP (Neural Net)": MLPClassifier(max_iter=800, random_state=42),
    "Linear SVC": LinearSVC(max_iter=8000, random_state=42),
    "Logistic Regression": LogisticRegression(max_iter=5000, solver="lbfgs", random_state=42),
    "Ridge Classifier": RidgeClassifier(random_state=42),
    "LDA": LinearDiscriminantAnalysis(),
    "QDA": QuadraticDiscriminantAnalysis(),
    "Gaussian Naive Bayes": GaussianNB(),
    "SGD Classifier": SGDClassifier(random_state=42),
}

if XGBClassifier is not None:
    models["XGBoost"] = XGBClassifier(
        n_estimators=600,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.9,
        colsample_bytree=0.9,
        reg_lambda=1.0,
        objective="multi:softprob",
        eval_metric="mlogloss",
        random_state=42,
        n_jobs=-1,
    )

if LGBMClassifier is not None:
    models["LightGBM"] = LGBMClassifier(
        n_estimators=800,
        learning_rate=0.05,
        num_leaves=63,
        subsample=0.9,
        colsample_bytree=0.9,
        random_state=42,
        n_jobs=-1,
    )

results = []
trained_models = {}

needs_scaling = {
    "K-Nearest Neighbors",
    "Linear SVC",
    "Logistic Regression",
    "Ridge Classifier",
    "MLP (Neural Net)",
    "SGD Classifier",
    "LDA",
    "QDA",
}

for name, model in models.items():
    X_train_to_use = X_train_scaled if name in needs_scaling else X_train
    X_test_to_use = X_test_scaled if name in needs_scaling else X_test

    try:
        model.fit(X_train_to_use, y_train)
        y_pred = model.predict(X_test_to_use)

        acc = accuracy_score(y_test, y_pred)
        f1 = f1_score(y_test, y_pred, average="weighted")
        results.append({"Model": name, "Accuracy": acc, "F1-Score": f1})
        trained_models[name] = model
    except Exception as e:
        print(f"Error training {name}: {e}")

results_df = pd.DataFrame(results).sort_values(by="F1-Score", ascending=False)
print(results_df)

best_model_name = results_df.iloc[0]["Model"]
best_model = trained_models[best_model_name]
X_test_best = X_test_scaled if best_model_name in needs_scaling else X_test
y_pred_best = best_model.predict(X_test_best)

print(f"\nTop Performer: {best_model_name}")
print(classification_report(y_test, y_pred_best, target_names=["calm", "neutral", "stressed"]))


joblib.dump(best_model, 'extra_trees_model.pkl')
joblib.dump(scaler, 'scaler.pkl')