from fastapi import FastAPI, Request
import requests
import os
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# 🔐 ENV VARIABLES (set these in Render later)
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")


# 🔁 Get Zoho Access Token
def get_access_token():
    url = "https://accounts.zoho.com/oauth/v2/token"

    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, params=params)
    return response.json().get("access_token")


# 🧠 Score Logic
def calculate_score(data):
    score = 0

    if data.get("product") == "A":
        score += 10
    elif data.get("product") == "B":
        score += 5

    try:
        if int(data.get("budget", 0)) > 10000:
            score += 20
    except:
        pass

    try:
        if int(data.get("team_size", 0)) > 5:
            score += 10
    except:
        pass

    return score


# 🔍 Get current score from Zoho
def get_existing_score(phone, access_token):
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }

    url = f"https://www.zohoapis.com/crm/v2/Leads/search?phone={phone}"
    res = requests.get(url, headers=headers).json()

    if "data" in res:
        lead = res["data"][0]
        lead_id = lead["id"]
        current_score = lead.get("Santulit_score1", 0) or 0
        return lead_id, int(current_score)

    return None, 0


# 🔄 Update Zoho
def update_zoho(lead_id, new_score, access_token):
    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }

    url = "https://www.zohoapis.com/crm/v2/Leads"

    payload = {
        "data": [
            {
                "id": lead_id,
                "Santulit_score1": new_score
            }
        ]
    }

    requests.put(url, json=payload, headers=headers)


# 🚀 MAIN WEBHOOK
@app.post("/webhook")
async def webhook(req: Request):
    data = await req.json()

    phone = data.get("phone")

    if not phone:
        return {"error": "phone is required"}

    access_token = get_access_token()

    # Step 1: get existing score
    lead_id, existing_score = get_existing_score(phone, access_token)

    if not lead_id:
        return {"error": "Lead not found in Zoho"}

    # Step 2: calculate new score
    new_points = calculate_score(data)
    final_score = existing_score + new_points

    # Step 3: update Zoho
    update_zoho(lead_id, final_score, access_token)

    return {
        "status": "success",
        "added_score": new_points,
        "total_score": final_score
    }
