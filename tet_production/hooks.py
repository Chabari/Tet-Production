app_name = "tet_production"
app_title = "Tet Production"
app_publisher = "Geetab Technologies Limited"
app_description = "Tet Production Customizations"
app_email = "geetabtechnologiesltd@gmail.com"
app_license = "mit"
# required_apps = []

# Includes in <head>
# ------------------
jinja = {
	"methods": [
		"tet_production.tet_production.doctype.work_order_creator.work_order_creator.work_order_body"
	],
}

doc_events = {
    "Biometric Attendance Log": {
        "on_update": "tet_production.attendance.handle_new_log",
    }
}

fixtures = [
    {
        "doctype": "Custom Field",
        "filters": [
            [
                "name",
                "in",
                (
                    "Work Order-custom_work_order_id",
                    "Biometric Attendance Punch Table-custom_employee_checkin"
                    
                ),
            ]
        ],
    },
    
]

scheduler_events = {
    "cron": {
        "*/30 * * * *": [
            "tet_production.attendance.schedule_attendance"
        ]
    }
}
