from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd
import joblib
import requests
from typing import Dict, Any, List

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

model = joblib.load("models/rule_based_anomaly_model.pkl")
feature_names = joblib.load("models/feature_names.pkl")

API_URL = "http://localhost:8082/ReservationView/reservations/"

@app.get("/detect_anomalies/{id_entite}")
def detect_anomalies(id_entite: int) -> Dict[str, Any]:
    # Modifier l'URL pour récupérer les réservations par ID_ENTITE
    response = requests.get(f"{API_URL}{id_entite}")
    if response.status_code != 200:
        raise HTTPException(status_code=500, detail="Erreur lors de la récupération des données")
    data = response.json()
    df = pd.DataFrame(data)

    if df.empty:
        return {
            "message": "Aucune réservation trouvée pour cette entité",
            "anomalous_users": [],
            "user_df": [],
            "df": []
        }

    # Pré-traitement des dates
    df['DT_RESA'] = pd.to_datetime(df['DT_RESA'], errors='coerce')
    df['DT_CHECK_IN'] = pd.to_datetime(df['DT_CHECK_IN'], errors='coerce')
    df['DT_CHECK_OUT'] = pd.to_datetime(df['DT_CHECK_OUT'], errors='coerce')

    # Calculs dérivés
    df['booking_to_checkin'] = (df['DT_CHECK_IN'] - df['DT_RESA']).dt.days
    df['stay_duration'] = (df['DT_CHECK_OUT'] - df['DT_CHECK_IN']).dt.days

    # Mapping des colonnes catégorielles
    df['IS_REFUNDABLE'] = df['IS_REFUNDABLE'].map({'N': 0, 'O': 1})
    df['IS_MANUAL'] = df['IS_MANUAL'].map({'N': 0, 'O': 1})

    # Remplissage des NaN par le mode
    df['IS_REFUNDABLE'] = df.groupby('ID_SOURCE')['IS_REFUNDABLE'].transform(
        lambda x: x.fillna(x.mode().iloc[0]) if not x.mode().empty else 0)
    df['IS_MANUAL'] = df.groupby('ID_SOURCE')['IS_MANUAL'].transform(
        lambda x: x.fillna(x.mode().iloc[0]) if not x.mode().empty else 0)

    # Agrégation par utilisateur (ID_SOURCE)
    user_df = df.groupby('ID_SOURCE').agg({
        'ID_RESA': 'count',
        'MNT_FINAL_RESA': ['mean', 'max', 'sum'],
        'booking_to_checkin': ['mean', 'min', 'max'],
        'stay_duration': 'mean',
        'HOTEL_NAME': pd.Series.nunique,
        'SUPPLIER_NAME': pd.Series.nunique,
        'DT_RESA': ['min', 'max'],
        'IS_REFUNDABLE': 'mean',
        'IS_MANUAL': 'mean'
    })

    user_df.columns = ['_'.join(col).strip() for col in user_df.columns.values]
    user_df.reset_index(inplace=True)

    user_df['booking_span_days'] = (user_df['DT_RESA_max'] - user_df['DT_RESA_min']).dt.days + 1
    user_df['booking_freq_per_day'] = user_df['ID_RESA_count'] / user_df['booking_span_days']

    top_hotels = df['HOTEL_NAME'].value_counts().nlargest(10).index.tolist()
    top_suppliers = df['SUPPLIER_NAME'].value_counts().nlargest(10).index.tolist()

    df['HOTEL_TOP10'] = df['HOTEL_NAME'].apply(lambda x: x if x in top_hotels else 'OTHER')
    df['SUPPLIER_TOP10'] = df['SUPPLIER_NAME'].apply(lambda x: x if x in top_suppliers else 'OTHER')

    hotel_counts = df.groupby(['ID_SOURCE', 'HOTEL_TOP10']).size().unstack(fill_value=0)
    supplier_counts = df.groupby(['ID_SOURCE', 'SUPPLIER_TOP10']).size().unstack(fill_value=0)

    user_df = user_df.merge(hotel_counts, on='ID_SOURCE', how='left')
    user_df = user_df.merge(supplier_counts, on='ID_SOURCE', how='left')

    user_df.drop(columns=['DT_RESA_min', 'DT_RESA_max'], inplace=True, errors='ignore')
    user_df.fillna(0, inplace=True)

    X_final = user_df.reindex(columns=feature_names, fill_value=0)
    X_final_filled = X_final.fillna(0)
    user_df['prediction'] = model.predict(X_final_filled)

    # Règles d'anomalie
    rule1 = user_df['MNT_FINAL_RESA_max'] > user_df['MNT_FINAL_RESA_max'].quantile(0.95)
    rule2 = user_df['booking_freq_per_day'] > user_df['booking_freq_per_day'].quantile(0.95)
    rule3 = (user_df['HOTEL_NAME_nunique'] <= 1) & (user_df['ID_RESA_count'] > 10)
    rule4 = (user_df['booking_to_checkin_mean'] < 1) | (user_df['booking_to_checkin_mean'] > 100)

    user_df['rule_1'] = rule1.astype(int)
    user_df['rule_2'] = rule2.astype(int)
    user_df['rule_3'] = rule3.astype(int)
    user_df['rule_4'] = rule4.astype(int)
    user_df['anomaly_rules'] = (user_df[['rule_1', 'rule_2', 'rule_3', 'rule_4']].sum(axis=1) >= 2).astype(int)

    def explain_rules(row):
        triggered = []
        if row['rule_1']:
            triggered.append("💰 High Reservation Amount")
        if row['rule_2']:
            triggered.append("📈 High Booking Frequency")
        if row['rule_3']:
            triggered.append("🏨 Low Hotel Diversity")
        if row['rule_4']:
            triggered.append("⏱️ Suspicious Lead Time")
        return ", ".join(triggered) if triggered else "—"

    user_df['anomaly_reason'] = user_df.apply(explain_rules, axis=1)

    total = len(user_df)
    anomalies = user_df['prediction'].sum()
    percent = anomalies / total * 100 if total > 0 else 0

    anomalous_users = user_df[user_df['prediction'] == 1]
    anomalous_details = anomalous_users[[
        'ID_SOURCE',
        'MNT_FINAL_RESA_max',
        'booking_freq_per_day',
        'HOTEL_NAME_nunique',
        'booking_to_checkin_mean',
        'anomaly_reason'
    ]].to_dict(orient='records')

    # Fonction pour convertir les types si nécessaire
    def convert_types(obj):
        if isinstance(obj, dict):
            return {k: convert_types(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [convert_types(i) for i in obj]
        elif hasattr(obj, 'item'):
            return obj.item()
        else:
            return obj

    anomalous = convert_types(anomalous_details)

    # Création d'une liste de listes pour les réservations des utilisateurs
    user_reservations_list = []
    if anomalous:
        for user in anomalous:
            user_id = user['ID_SOURCE']
            user_reservations_df = df[df["ID_SOURCE"] == user_id]
            user_reservations = user_reservations_df.to_dict(orient='records')
            user_reservations_list.append(user_reservations)

    return {
        "id_entite": int(id_entite),
        "total_users": int(total),
        "anomaly_count": int(anomalies),
        "anomaly_percent": round(float(percent), 2),
        "anomalous_users": anomalous,
        "user_df": user_reservations_list,
    }