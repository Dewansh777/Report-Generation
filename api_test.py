import requests
import json
import base64
import random

def generate_random_json_data():
    """Generates random JSON data for testing."""
    # ... (Same random data generation logic as in the previous JavaScript example)
    names = ["Alice", "Bob", "Charlie", "David", "Eve", "Frank", "Grace", "Henry", "Ivy", "Jack"]
    uhids = [str(random.randint(100000, 999999)) for _ in range(10)]
    ages = [random.randint(1, 90) for _ in range(10)]
    sexes = ["M", "F"]
    complaints = ["Headache", "Cough", "Fever", "Fatigue", "Sneezing", "Runny nose", "Sore throat"]
    med_names = ["Medicine A", "Medicine B", "Medicine C", "Medicine D"]
    dosages = ["1 tablet", "2 capsules", "1 ml", "1 spray"]
    details = ["Take with food", "Take at night", "Use as directed"]
    reports = ["Consultation on 2024-01-10: Normal", "Report from 2024-02-15: Improved"]

    patient_data = {
        "name": random.choice(names),
        "uhid": random.choice(uhids),
        "age_sex": f"{random.choice(ages)}/{random.choice(sexes)}",
        "chief_complaints": ", ".join(random.sample(complaints, random.randint(1, 3))),
        "aggravating_factor": random.choice(["Weather", "Stress", "Food", "Exercise"]),
        "present_illness": random.choice(["Mild", "Moderate", "Severe"]),
        "family_history": random.choice(["Positive", "Negative"]),
        "surgical_history": random.choice(["Yes", "No"]),
        "examination": random.choice(["Normal", "Abnormal"]),
        "clinical_impression": random.choice(["Healthy", "Unhealthy"]),
    }

    hospital_data = {
        "name": "Random Hospital",
        "address": "Random City",
        "phone": "+1-123-456-7890",
        "email": "info@random.com",
        "website": "www.random.com",
        "emergency": "+1-987-654-3210",
        "footer": {
            "name": "Random Hospital Footer",
            "address": "Footer Address",
            "email": "footer@random.com",
            "phone": "+1-111-222-3333"
        }
    }

    doctor_data = {
        "name": "Dr. Random Doctor",
        "degree": "MD",
        "speciality": "General Physician",
        "mobile": "+1-555-123-4567",
        "email": "doctor@random.com",
        "pmc": "PMC12345"
    }

    advice_data = [
        {
            "name": random.choice(med_names),
            "dosage": random.choice(dosages),
            "details": random.choice(details),
        } for _ in range(random.randint(1, 3))
    ]

    previous_reports = random.sample(reports, random.randint(0, 2))


    json_data = {
        "patient_data": patient_data,
        "hospital_data": hospital_data,
        "doctor_data": doctor_data,
        "advice_data": advice_data,
        "previous_reports": previous_reports,
    }

    return json_data


json_data = generate_random_json_data()  # Generate random JSON

url = "http://127.0.0.1:8000/generate_report"  # Or your actual URL
headers = {"Content-Type": "application/json"}

response = requests.post(url, data=json.dumps(json_data), headers=headers)

if response.status_code == 200:
    data = response.json()
    pdf_base64 = data["pdf_data"]

    pdf_bytes = base64.b64decode(pdf_base64)
    with open("patient_report.pdf", "wb") as f:
        f.write(pdf_bytes)

    print("PDF downloaded successfully!")
else:
    print(f"Error: {response.status_code}")
    print(response.text)