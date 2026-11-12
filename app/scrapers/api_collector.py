import requests
from app.db.database import SessionLocal, Reading

def collect_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {"latitude": 26.85, "longitude": 80.95,  # Lucknow
              "hourly": "temperature_2m", "forecast_days": 1}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()["hourly"]

    db = SessionLocal()
    for t, v in zip(data["time"], data["temperature_2m"]):
        db.add(Reading(source="open-meteo", label=t, value=v))
    db.commit()
    db.close()
    print("Saved", len(data["time"]), "rows")

if __name__ == "__main__":
    collect_weather()