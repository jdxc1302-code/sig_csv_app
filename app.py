from flask import Flask, render_template, request, redirect, url_for
import pandas as pd
import os

app = Flask(__name__)

# Ruta al CSV
CSV_PATH = os.path.join("data", "base_de_datos.csv")

# Cargar columnas del CSV
_df_init = pd.read_csv(CSV_PATH, dtype=str)
COLUMNS = list(_df_init.columns)
STATUSES = sorted(_df_init['Status importacion'].dropna().unique().tolist())

# Columnas tipo fecha (para datepicker)
DATE_COLUMNS = [
    "Fecha Solicitud al proveedor",
    "Fecha de Inicio Fabricacion",
    "ETD (Fecha de zarpe)",
    "ETA (Fecha de llegada material a Puerto)",
    "Fecha de llegada material"
]

# Colores por estado
COLOR_MAP = {
    "Cumplida": "#4CAF50",
    "Nacionalizacion": "#6f42c1",
    "Transito Maritimo": "#2196F3",
    "Zarpe": "#00ACC1",
    "Fabricacion": "#FF9800",
    "Sin Estado": "#BDBDBD"
}


def cargar_df():
    df = pd.read_csv(CSV_PATH, dtype=str).fillna("")
    for c in COLUMNS:
        if c not in df.columns:
            df[c] = ""
    df = df[COLUMNS]
    return df


def guardar_df(df):
    df.to_csv(CSV_PATH, index=False)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/consultar", methods=["GET", "POST"])
def consultar():
    resultados = []
    query = ""

    if request.method == "POST":
        query = request.form.get("q", "").strip()
        df = cargar_df()

        if query:
            mask = (
                df["No. Pedido de importacion"].str.contains(query, case=False, na=False) |
                df["No. Contrato"].str.contains(query, case=False, na=False)
            )
            resultados = df[mask].to_dict(orient="records")

    return render_template(
        "consultar.html",
        q=query,
        resultados=resultados,
        color_map=COLOR_MAP   # ← ★ IMPORTANTE ★
    )


@app.route("/add", methods=["GET", "POST"])
def add():
    if request.method == "POST":
        df = cargar_df()
        nuevo = {col: request.form.get(col, "") for col in COLUMNS}
        df = pd.concat([df, pd.DataFrame([nuevo])], ignore_index=True)
        guardar_df(df)
        return redirect(url_for("index"))

    return render_template("add.html", columns=COLUMNS, statuses=STATUSES, date_columns=DATE_COLUMNS)


@app.route("/detalle/<int:idx>")
def detalle(idx):
    df = cargar_df()
    if idx < 0 or idx >= len(df):
        return "Registro no encontrado", 404

    row = df.iloc[idx].to_dict()

    # --- MANEJO DE BANDERA ---
    procedencia = row.get("Procedencia", "").strip()
    flag_file = None

    if procedencia:
        flag_name = procedencia.lower().replace(" ", "_") + ".png"
        flag_path = os.path.join("static", "flags", flag_name)
        if os.path.exists(flag_path):
            flag_file = flag_name  # sólo el nombre del archivo

    return render_template(
        "detalle.html",
        row=row,
        flag_file=flag_file
    )


@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", color_map=COLOR_MAP)


@app.route("/dashboard-data")
def dashboard_data():
    df = cargar_df()

    status_counts = df["Status importacion"].replace("", "Sin Estado").value_counts().to_dict()

    if "ETA (Fecha de llegada material a Puerto)" in df.columns:
        s = pd.to_datetime(df["ETA (Fecha de llegada material a Puerto)"], errors='coerce')
        months = s.dt.to_period("M").astype(str).value_counts().sort_index().to_dict()
    else:
        months = {}

    top_prov = df["Proveedor"].replace("", "Sin Proveedor").value_counts().head(10).to_dict()
    procedencias = df["Procedencia"].replace("", "Desconocida").value_counts().head(10).to_dict()

    return {
        "status_counts": status_counts,
        "eta_months": months,
        "top_proveedores": top_prov,
        "procedencias": procedencias
    }


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

