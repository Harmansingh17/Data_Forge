# ==============================
# app1.py
# Secure AutoML System
# No Database Version
# ==============================

from flask import Flask, render_template, request, redirect, session
import pandas as pd
import numpy as np
import os
import time

# ML Libraries
from sklearn.preprocessing import LabelEncoder
from sklearn.preprocessing import StandardScaler

from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier

import matplotlib.pyplot as plt
import seaborn as sns

# Import Storage Utility
from storage import *

# ==============================
# FLASK APP
# ==============================

app = Flask(__name__)

app.secret_key = os.urandom(24)

# ==============================
# HOME PAGE
# ==============================

@app.route("/")
def home():

    return render_template("page.html")


# ==============================
# UPLOAD DATASET
# ==============================

@app.route("/upload", methods=["GET", "POST"])
def upload():

    if request.method == "GET":

        return render_template("upload.html")

    file = request.files["file"]

    if file.filename == "":

        return "No file selected"

    try:

        df = pd.read_csv(file)

        # Save dataset in session memory
        DataStore.save(
            "dataset",
            df.to_dict(orient="records")
        )

        # Save headers
        DataStore.save(
            "headers",
            df.columns.tolist()
        )

        return redirect("/data")

    except Exception as e:

        return f"Error: {e}"


# ==============================
# SHOW DATASET
# ==============================

@app.route("/data")
def show_data():

    rows = DataStore.load("dataset")

    if not rows:

        return "No dataset uploaded"

    df = pd.DataFrame(rows)

    return df.head(20).to_html()


# ==============================
# PREPROCESSING
# ==============================

@app.route("/pre_processing")
def pre_processing():

    rows = DataStore.load("dataset")

    if not rows:

        return "Upload dataset first"

    df = pd.DataFrame(rows)

    # Remove duplicates
    df.drop_duplicates(inplace=True)

    # Fill numeric missing values
    df.fillna(
        df.mean(numeric_only=True),
        inplace=True
    )

    # Fill categorical missing values
    for col in df.select_dtypes(include='object'):

        df[col].fillna(
            df[col].mode()[0],
            inplace=True
        )

    # Encoding
    for col in df.select_dtypes(include='object'):

        if df[col].nunique() == 2:

            le = LabelEncoder()

            df[col] = le.fit_transform(df[col])

        else:

            df = pd.get_dummies(
                df,
                columns=[col]
            )

    # Save processed data
    DataStore.save(
        "processed",
        df.to_dict(orient="records")
    )

    return df.head(20).to_html()


# ==============================
# STANDARD SCALER
# ==============================

@app.route("/standscaler")
def standscaler():

    rows = DataStore.load("processed")

    if not rows:

        return redirect("/pre_processing")

    df = pd.DataFrame(rows)

    scaler = StandardScaler()

    numeric_cols = df.select_dtypes(
        include='number'
    ).columns

    df[numeric_cols] = scaler.fit_transform(
        df[numeric_cols]
    )

    # Save scaled data
    DataStore.save(
        "scaled",
        df.to_dict(orient="records")
    )

    return df.head(20).to_html()


# ==============================
# DATASET ANALYSIS
# ==============================

@app.route("/analysis")
def analysis():

    rows = DataStore.load("dataset")

    if not rows:

        return "Upload dataset first"

    df = pd.DataFrame(rows)

    info = {

        "Rows": df.shape[0],
        "Columns": df.shape[1],
        "Missing Values": count_missing(df),
        "Column Types": detect_types(df)

    }

    return f"""
    <h2>Dataset Analysis</h2>

    <pre>{info}</pre>
    """


# ==============================
# VISUALIZATION
# ==============================

@app.route("/graph")
def graph():

    rows = DataStore.load("processed")

    if not rows:

        return redirect("/pre_processing")

    df = pd.DataFrame(rows)

    if not os.path.exists("static"):

        os.makedirs("static")

    numeric_df = df.select_dtypes(include=np.number)

    if numeric_df.shape[1] < 2:

        return "Not enough numeric columns"

    # Heatmap
    plt.figure(figsize=(10, 8))

    sns.heatmap(
        numeric_df.corr(),
        annot=True
    )

    plt.savefig("static/heatmap.png")

    plt.close()

    # Distribution Plot
    plt.figure()

    col = numeric_df.columns[0]

    sns.histplot(
        numeric_df[col],
        kde=True
    )

    plt.savefig("static/dist.png")

    plt.close()

    return render_template(
        "visulization.html",
        t=time.time()
    )


# ==============================
# TRAIN MODELS
# ==============================

@app.route("/train")
def train_models():

    rows = DataStore.load("scaled")

    if not rows:

        return redirect("/standscaler")

    df = pd.DataFrame(rows)

    target = df.columns[-1]

    X = df.drop(target, axis=1)

    y = df[target]

    X_train, X_test, y_train, y_test = train_test_split(
        X,
        y,
        test_size=0.2,
        random_state=42
    )

    models = {

        "LogisticRegression":
            LogisticRegression(max_iter=1000),

        "DecisionTree":
            DecisionTreeClassifier(),

        "RandomForest":
            RandomForestClassifier(),

        "KNN":
            KNeighborsClassifier()

    }

    results = {}

    best_model = None

    best_accuracy = 0

    for name, model in models.items():

        try:

            model.fit(X_train, y_train)

            score = model.score(X_test, y_test)

            accuracy = round(score * 100, 2)

            results[name] = accuracy

            if score > best_accuracy:

                best_accuracy = score

                best_model = name

        except Exception as e:

            results[name] = str(e)

    # Save Results
    DataStore.save("results", results)

    DataStore.save("best_model", best_model)

    return render_template(
        "result.html",
        results=results,
        best_model=best_model,
        best_accuracy=round(best_accuracy * 100, 2)
    )


# ==============================
# DOWNLOAD DATASET CSV
# ==============================

@app.route("/download_csv")
def download_dataset():

    rows = DataStore.load("dataset")

    headers = DataStore.load("headers")

    if not rows:

        return "No dataset"

    return download_csv(
        "dataset.csv",
        headers,
        rows
    )


# ==============================
# DOWNLOAD JSON
# ==============================

@app.route("/download_json")
def download_dataset_json():

    rows = DataStore.load("dataset")

    if not rows:

        return "No dataset"

    return download_json(
        "dataset.json",
        rows
    )


# ==============================
# CLEAR MEMORY
# ==============================

@app.route("/clear")
def clear():

    DataStore.clear_all()

    return """
    <h2>Dataset Cleared Successfully</h2>

    <p>
    Your dataset has been securely deleted from memory.
    No data stored permanently.
    </p>
    """


# ==============================
# RUN APP
# ==============================

if __name__ == "__main__":

    app.run(debug=True)