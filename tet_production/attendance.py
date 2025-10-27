import frappe
from frappe import _
import requests
import json
from datetime import datetime, timedelta
import itertools
from frappe.utils import cint, create_batch, get_datetime, get_time, getdate
from hrms.hr.doctype.employee_checkin.employee_checkin import (
	calculate_working_hours,
	mark_attendance_and_link_log,
)
EMPLOYEE_CHUNK_SIZE = 50

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
    
def schedule_attendance():
    try:
        # Get the settings
        settings = frappe.get_doc('Biometric Integration Settings', 'Biometric Integration Settings')
        decrypted_password = settings.get_password('password')
        if decrypted_password:
            
            # Set the time range for today
            today = datetime.now().date()
            start_time = datetime.combine(today, datetime.strptime("00:00:00", "%H:%M:%S").time())
            end_time = datetime.combine(today, datetime.strptime("23:59:59", "%H:%M:%S").time())
            
            # Update the settings with today's date range
            settings.start_date_and_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            settings.end_date_and_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
            settings.save()
            
            # Call the sync function
            frappe.enqueue(
                'biometric_integration.biometric_integration.doctype.biometric_integration_settings.biometric_integration_settings.sync_attendance',
                queue='long',
                timeout=1500
            )
            
            frappe.logger().info("Scheduled attendance sync started successfully")
        
    except Exception as e:
        frappe.logger().error(f"Scheduled attendance sync failed: {str(e)}")
        frappe.log_error(f"Scheduled attendance sync failed: {str(e)}", "Daily Attendance Sync Error")
        
@frappe.whitelist(allow_guest=True)
def process_attendance():
    shift_list = frappe.get_all("Shift Type", filters={"enable_auto_attendance": "1"}, pluck="name")
    for shift in shift_list:
        doc = frappe.get_cached_doc("Shift Type", shift)
        logs = get_employee_checkins(doc)
        if logs:
            for key, group in itertools.groupby(logs, key=lambda x: (x["employee"], x["shift_start"])):
                single_shift_logs = list(group)
                attendance_date = key[1].date()
                employee = key[0]

                if not doc.should_mark_attendance(employee, attendance_date):
                    continue

                (
                    attendance_status,
                    working_hours,
                    late_entry,
                    early_exit,
                    in_time,
                    out_time,
                ) = doc.get_attendance(single_shift_logs)
                
                mark_attendance_and_link_log(
                    single_shift_logs,
                    attendance_status,
                    attendance_date,
                    working_hours,
                    late_entry,
                    early_exit,
                    in_time,
                    out_time,
                    doc.name,
                )

            # commit after processing checkin logs to avoid losing progress
            frappe.db.commit()  # nosemgrep

            assigned_employees = doc.get_assigned_employees(doc.process_attendance_after, True)

            # mark absent in batches & commit to avoid losing progress since this tries to process remaining attendance
            # right from "Process Attendance After" to "Last Sync of Checkin"
            # ...........................
            
            for batch in create_batch(assigned_employees, EMPLOYEE_CHUNK_SIZE):
                for employee in batch:
                    doc.mark_absent_for_dates_with_no_attendance(employee)

                frappe.db.commit()  # nosemgrep

def get_employee_checkins(doc) -> list[dict]:
		return frappe.get_all(
			"Employee Checkin",
			fields=[
				"name",
				"employee",
				"log_type",
				"time",
				"shift",
				"shift_start",
				"shift_end",
				"shift_actual_start",
				"shift_actual_end",
				"device_id",
			],
			filters={
				"skip_auto_attendance": 0,
				"attendance": ("is", "not set"),
				"time": (">=", doc.process_attendance_after),
				"shift": doc.name,
			},
			order_by="employee,time",
		)