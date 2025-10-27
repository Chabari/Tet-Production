import frappe
from frappe import _
import requests
import json
from datetime import datetime, timedelta

@frappe.whitelist(allow_guest=True)
def send_attendance():
    api_key = "65d16a09004c8a4"
    api_secret = "be4c6641aabc879"
    url = "http://134.209.255.194/api/method/hrms.hr.doctype.employee_checkin.employee_checkin.add_log_based_on_employee_field"
    attendances = frappe.db.sql('''SELECT 
																			
								name, punch_time, parent								
							FROM 
								`tabBiometric Attendance Punch Table`
							
							WHERE
								custom_employee_checkin is null
						''', as_dict=1)
    for att in attendances:
        attendance_log = frappe.get_doc("Biometric Attendance Log", att.parent)
        headers = {
            "Authorization": f"token {api_key}:{api_secret}",
            "Content-Type": "application/json"
        }
        punch_datetime = datetime.strptime(f"{attendance_log.event_date} {att.punch_time}", '%Y-%m-%d %H:%M:%S')
        timestamp_str = punch_datetime.strftime("%Y-%m-%d %H:%M:%S.%f")

        payload = {
            "employee_field_value": attendance_log.employee_no,
            "timestamp": timestamp_str
        }

        try:
            
            response = requests.post(url, json=payload, headers=headers)
            if not response.ok:
                continue
            result = response.json()
            checkin_doc = result.get("message")

            if checkin_doc:
                log = frappe.get_doc('Biometric Attendance Punch Table', att.name)
                log.custom_employee_checkin = checkin_doc.get("name")
                log.save(ignore_permissions=True)
                frappe.db.commit()

                print(f"✅ Synced successfully and saved: {checkin_doc.get('name')}")
            else:
                print("⚠️ No message found in response.")

        except Exception as e:
            frappe.log_error(f"Error syncing checkin:", "Checkin Sync Error")
            print(f"{str(e)}")
            continue

def handle_new_log(doc, method):
    frappe.enqueue(
        'tet_production.attendance.send_attendance'
    )