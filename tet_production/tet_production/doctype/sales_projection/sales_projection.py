# Copyright (c) 2025, Geetab Technologies Limited and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class SalesProjection(Document):
	def before_save(self):
		if not self.items:
			frappe.throw(_("Please add items before proceeding"),title=_("Items Required"))
		items = get_x_items(self)
		self.add_items(items)

	def on_update(self):
		check_active(self)
		for row in self.items:
			query = f"""UPDATE `tabItem` SET custom_sales_projection_quantity='{row.projected_sales}' WHERE name='{row.item}' """
			frappe.db.sql(query)
		
      
	@frappe.whitelist()
	def get_finished_goods_items(self):
		
		if not self.item_group:
			frappe.throw(_("Please select the item group"),title=_("Item Group Required"))

		""" Pull sales invoices based on criteria selected"""
		items = get_items(self)
		if items:
			self.add_items(items)
			frappe.msgprint(_("Fetching of items is complete"),title=_("Success!"))
		else:
			frappe.msgprint(_("Items from the item group are not found."))

	# Add items
	def add_items(self, items):
		self.set('items', [])
		for data in items:			
			self.append('items', {
				'item': data.item_code,
				'projected_sales': data.custom_sales_projection_quantity,
				'bom': data.default_bom,
			})
		
def get_items(self):
    filter = ""
    if self.item_group:
        filter += " WHERE item_group = %(item_group)s"
    items = frappe.db.sql("""
        SELECT item_code, item_name, custom_sales_projection_quantity, default_bom
        FROM `tabItem`
        {0}
        """.format(filter), {
        "item_group": self.item_group
    }, as_dict=1)
    return items

	
def get_x_items(self):
    data = [row.item for row in self.items]
    items = frappe.db.sql("""
        SELECT item_code, item_name, custom_sales_projection_quantity, default_bom
        FROM `tabItem`
        WHERE name IN %(data)s
        """, {
        "data": data
    }, as_dict=1)
    return items


def check_active(self):        
	x_active = frappe.db.get_value('Sales Projection', {'is_active': 1, 'name': ['!=', self.name]}, ['name'], as_dict=1)
	if x_active and self.is_active == 1:
		frappe.set_value("Sales Projection", x_active, "is_active", 0)
		

@frappe.whitelist()
def make_material_request(**args):
	doc = frappe.get_doc("Sales Projection", args.get('name'))
	if not doc.items:
		frappe.throw(_("Please add items before proceeding"),title=_("Items Required"))

	combined_items = {}

	for row in doc.items:
		if row.bom:
			bom = frappe.get_doc("BOM", row.bom)

			for bi in bom.items:
				item_code = bi.item_code
				qty = (bi.qty * row.projected_sales) / bom.quantity

				if item_code in combined_items:
					combined_items[item_code] += qty
				else:
					combined_items[item_code] = qty

	if not combined_items:
		frappe.throw(_("No raw materials found from the BOMs."))

	mr = frappe.new_doc("Material Request")
	mr.material_request_type = "Purchase"

	for item_code, qty in combined_items.items():
		mr.append("items", {
			"item_code": item_code,
			"qty": qty,
			"schedule_date": frappe.utils.nowdate(),
		})

	mr.insert(ignore_permissions=True)
	return mr
