// Copyright (c) 2025, Geetab Technologies Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Work Order Creator", {
	refresh(frm) {

		if(frm.doc.work_order_id){
			frm.add_custom_button(__("Print Work Orders"), function () {
				frm.print_doc();
			});
		}

        frm.add_custom_button(__("Generate Work Orders"), () => {
			let my_items = frm.doc.items.map(row => {
				return {
					item: row.item,
					bom: row.bom,
					work_order_quantity: row.work_order_quantity,
					order_quantity: row.work_order_quantity,
					date: null
				};
			});

			const fields = [
				{
					label: "Items",
					fieldtype: "Table",
					fieldname: "items",
					description: __("Select Items and Qty for Manufacturing"),
					fields: [
						{
							fieldtype: "Read Only",
							fieldname: "item",
							label: __("Item Code"),
							in_list_view: 1,
							columns: 4, 
						},
						{
							fieldtype: "Date",
							fieldname: "date",
							label: __("Work Order Date"),
							in_list_view: 1, 
							reqd: 1,
							columns: 3, 
						},
						{
							fieldtype: "Float",
							fieldname: "order_quantity",
							reqd: 1,
							label: __("Qty to Manufacture"),
							in_list_view: 1,
							columns: 3, 
						},
					],
					data: my_items, 
				},
			];

			let d = new frappe.ui.Dialog({
				title: __("Select Items to Manufacture"),
				fields: fields,
				primary_action_label: __("Create Work Orders"),
				primary_action(values) {
					let items = values.items || [];
					for (let row of items) {
						if (!row.order_quantity) {
							frappe.throw(__("Order Quantity is required for all rows"));
						}
						if (!row.date) {
							frappe.throw(__("Work Order Date is required for all rows"));
						}
					}
					frm.call({
						method: "tet_production.tet_production.doctype.work_order_creator.work_order_creator.generate_work_order",
						args: {
							items: items
						},
						freeze: true,
						freeze_message: "Generating Work Orders...",
						callback: function (r) {
							if (r.success == true) {
								frappe.msgprint(
									__(r.message)
								);
							}
							d.hide();
							frm.reload_doc();
						},
					});
				},
			});

			d.show();

        });

		


	},
    onload(frm) { 
        frm.events.fetch_items(frm);
    },

    fetch_items: function (frm) {
		frappe.call({
			method: "fetch_bom_items",
			doc: frm.doc,
			callback: function (r) {
				refresh_field('items');
			}
		});
	},
});
