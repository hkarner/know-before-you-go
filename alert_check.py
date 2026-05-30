import os
from supabase import create_client
from grades import calculate_grade, GRADE_ORDER
import sendgrid
from sendgrid.helpers.mail import Mail

FROM_EMAIL = "you@yourdomain.com"  # your verified SendGrid sender
APP_URL = "https://your-app.streamlit.app"  # your deployed URL

def grade_change(old, new):
    return GRADE_ORDER[new] - GRADE_ORDER[old]  # negative = drop

def should_notify(sub, old_grade, new_grade):
    change = grade_change(old_grade, new_grade)
    if change == 0:
        return False
    if sub["floor_grade"] and GRADE_ORDER[new_grade] <= GRADE_ORDER[sub["floor_grade"]]:
        return True
    if change < 0 and sub["notify_on_drop"] and abs(change) >= sub["min_grade_change"]:
        return True
    if change > 0 and sub["notify_on_improvement"] and abs(change) >= sub["min_grade_change"]:
        return True
    return False

def send_alert(email, beach_name, old_grade, new_grade):
    change = grade_change(old_grade, new_grade)
    direction = "dropped" if change < 0 else "improved"
    subject = f"Water quality {direction}: {beach_name} ({old_grade} to {new_grade})"
    body = f"""{beach_name} water quality has changed:
  Previous: {old_grade}  Current: {new_grade}

View details: {APP_URL}
Manage alerts: {APP_URL}?alerts=1
Unsubscribe: {APP_URL}?unsubscribe={email}

-- Know Before You Go, powered by EPA BEACON + USGS data"""
    sg = sendgrid.SendGridAPIClient(api_key=os.environ["SENDGRID_API_KEY"])
    sg.send(Mail(from_email=FROM_EMAIL, to_emails=email, subject=subject, plain_text_content=body))

if __name__ == "__main__":
    client = create_client(os.environ["SUPABASE_URL"], os.environ["SUPABASE_KEY"])
    subs = client.table("alert_subscriptions").select("*").eq("active", 1).execute().data

    for sub in subs:
        current = calculate_grade(sub["beach_id"])
        # TODO: fetch previous grade from grade_history, then:
        # if should_notify(sub, previous_grade, current["grade"]):
        #     send_alert(sub["email"], beach_name, previous_grade, current["grade"])
        pass