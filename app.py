from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import requests
from datetime import datetime
from dotenv import load_dotenv
import time

load_dotenv()
import os

app = FastAPI()

# 🔑 Your credentials
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REFRESH_TOKEN = os.getenv("REFRESH_TOKEN")

MODULE = "Event_Invites"  # or Contacts

# Global token cache
ACCESS_TOKEN = None
TOKEN_EXPIRY = None


# 🔄 Get fresh access token
def get_access_token():
    global ACCESS_TOKEN, TOKEN_EXPIRY

    # reuse token if still valid
    if ACCESS_TOKEN and TOKEN_EXPIRY and time.time() < TOKEN_EXPIRY:
        return ACCESS_TOKEN

    url = "https://accounts.zoho.in/oauth/v2/token"

    params = {
        "refresh_token": REFRESH_TOKEN,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "grant_type": "refresh_token"
    }

    response = requests.post(url, params=params)
    data = response.json()
    print("TOKEN RESPONSE:", data)

    if "access_token" not in data:
        return None

    ACCESS_TOKEN = data["access_token"]
    TOKEN_EXPIRY = time.time() + data.get("expires_in", 3600) - 60

    return ACCESS_TOKEN


# 🔍 Search record
def search_record(code, access_token):
    url = f"https://www.zohoapis.in/crm/v2/{MODULE}/search"

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}"
    }

    params = {
        "criteria": f"(Invite_Code:equals:{code})"
    }

    res = requests.get(url, headers=headers, params=params)
    try:
        return res.json()
    except Exception:
        return {"error": res.text}


# ✏️ Update record
def update_record(record_id, access_token):
    url = f"https://www.zohoapis.in/crm/v2/{MODULE}"

    headers = {
        "Authorization": f"Zoho-oauthtoken {access_token}",
        "Content-Type": "application/json"
    }

    data = {
        "data": [{
            "id": record_id,
            "Check_In_Status": "Checked",
            "Checkin_time": datetime.now().strftime("%Y-%m-%dT%H:%M:%S+05:30")
        }]
    }

    response = requests.put(url, headers=headers, json=data)
    print("UPDATE RESPONSE:", response.text)
    return response


from fastapi import Query
# 🚀 Main check-in endpoint
@app.get("/checkin", response_class=HTMLResponse)
def checkin(code: str, pin: str = None):

    STAFF_PIN = "1234"

    access_token = get_access_token()

    if not access_token:
        return """
<html><body style='background-color:red;color:white;text-align:center;margin-top:20%;font-size:40px;'>
❌ Token Error
</body></html>
"""

    from fastapi import Request

    result = search_record(code, access_token)

    # ❌ Code not found
    if "data" not in result or not result.get("data"):
        return f"""
<html><body style='background-color:red;color:white;text-align:center;margin-top:20%;font-size:40px;'>
❌ Code Not Found<br>{code}
</body></html>
"""

    record = result["data"][0]

    # 🔐 PIN check (before any action)
    if not pin:
        return f"""
<html><body style='background-color:#111;color:white;text-align:center;margin-top:15%;font-size:30px;'>
Enter Staff PIN<br><br>
<form method='get'>
<input type='hidden' name='code' value='{code}' />
<input type='password' name='pin' placeholder='Enter PIN' style='font-size:20px;padding:10px'/><br><br>
<button type='submit' style='font-size:20px;padding:10px'>Confirm Check-In</button>
</form>
</body></html>
"""

    if pin != STAFF_PIN:
        return """
<html><body style='background-color:red;color:white;text-align:center;margin-top:20%;font-size:40px;'>
❌ Wrong PIN
</body></html>
"""

    status = record.get("Check_In_Status", "").strip().lower()

    # ⚠️ Duplicate (only if actually checked)
    if status == "checked":
        return """
<html><body style='background-color:orange;color:black;text-align:center;margin-top:20%;font-size:40px;'>
⚠️ Already Checked-In
</body></html>
"""

    # ✅ Success → update
    update_record(record["id"], access_token)

    return f"""
<html><body style='background-color:green;color:white;text-align:center;margin-top:20%;font-size:40px;'>
✅ Welcome!<br>Code: {code}
</body></html>
"""
