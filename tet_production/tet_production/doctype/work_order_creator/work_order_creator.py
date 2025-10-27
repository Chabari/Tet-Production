# Copyright (c) 2025, Geetab Technologies Limited and contributors
# For license information, please see license.txt

import frappe, json
from frappe.model.document import Document
from frappe import _
from frappe.utils import (
	flt,
 	now_datetime
)

class WorkOrderCreator(Document):
    
	@frappe.whitelist()
	def fetch_bom_items(self):
		
		items = get_items()
		if items:
			self.add_items(items)
		else:
			frappe.msgprint(_("Items not found."))
   
	def add_items(self, items):
		self.set('items', [])
		for data in items:		
			item = frappe.get_doc("Item", data.item)
			pending_orders = get_pending_order(data.item)
			stock_balance = get_stock_availability(data.item)
			work_order_quantity = (float(item.safety_stock) + float(pending_orders)) - float(stock_balance)
			self.append('items', {
				'item': data.item,
				'safety_stock': item.safety_stock,
				'bom': data.name,
				'pending_orders': pending_orders,
				'stock_balance': stock_balance,
				'work_order_quantity': work_order_quantity
			})


def get_pending_order(item):
    total_pending = frappe.db.sql("""
		SELECT SUM(soi.qty - soi.delivered_qty) AS total_pending_qty
		FROM `tabSales Order Item` soi
		INNER JOIN `tabSales Order` so ON so.name = soi.parent
		WHERE soi.docstatus = 1
		AND soi.item_code = %(item)s
		AND so.status NOT IN ('Closed', 'Completed')
		AND soi.delivered_qty < soi.qty
	""", {"item": item}, as_dict=True)[0].total_pending_qty or 0
    return total_pending

def get_stock_availability(item_code):
    total_qty = frappe.db.sql("""
        SELECT SUM(actual_qty) 
        FROM `tabBin` 
        WHERE item_code = %s
    """, (item_code,), as_dict=False)[0][0] or 0.0

    return total_qty
    
def get_items():
    items = frappe.db.sql("""
        SELECT item, quantity, name
        FROM `tabBOM`
        WHERE is_active = 1 AND is_default = 1
        """, as_dict=1)
    return items

@frappe.whitelist()
def generate_work_order(items):
	job_id = frappe.generate_hash(length=10)
	items = json.loads(items)
	if not items:
		frappe.throw("Failed. Enter items to manufacture.")

	work_oders = []
	for itm in items:
		wo_doc = make_work_order(itm.get('bom'), itm.get('item'), itm.get('order_quantity'), itm.get('date'), job_id)
		work_oders.append(wo_doc.name)
  
	woc = frappe.get_doc("Work Order Creator")
	woc.work_order_id = job_id
	woc.save(ignore_permissions=True)

	frappe.response.success = True
	frappe.response.message = "Success. The following work orders have been generated successfully as drafts. {0}".format(", ".join(work_oders))
	return


@frappe.whitelist()
def make_work_order(bom_no, item, qty, planned_start_date, job_id, project=None, variant_items=None):
	from erpnext.manufacturing.doctype.work_order.work_order import get_item_details, add_variant_item
	if not frappe.has_permission("Work Order", "write"):
		frappe.throw(_("Not permitted"), frappe.PermissionError)

	item_details = get_item_details(item, project)

	wo_doc = frappe.new_doc("Work Order")
	wo_doc.production_item = item
	wo_doc.update(item_details)
	wo_doc.custom_work_order_id = job_id
	wo_doc.planned_start_date = planned_start_date
	wo_doc.bom_no = bom_no
	wo_doc.set_default_warehouse()

	if flt(qty) > 0:
		wo_doc.qty = flt(qty)
		wo_doc.get_items_and_operations_from_bom()

	if variant_items:
		add_variant_item(variant_items, wo_doc, bom_no, "required_items")
  
	wo_doc.insert(ignore_permissions=True)
	return wo_doc

@frappe.whitelist(allow_guest=True)
def work_order_body(job_id):
    items = frappe.db.sql(f"""
        SELECT name, bom_no, planned_start_date, production_item, qty
        FROM `tabWork Order`
        WHERE custom_work_order_id = '{job_id}'
        """, as_dict=1)
    return items
