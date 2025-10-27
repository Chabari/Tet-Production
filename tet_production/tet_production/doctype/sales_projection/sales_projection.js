// Copyright (c) 2025, Geetab Technologies Limited and contributors
// For license information, please see license.txt

frappe.ui.form.on("Sales Projection", {
	refresh(frm) {
        if (frm.doc.is_active == 1) {
            frm.add_custom_button(__("Material Request"), () => {
                frm.trigger("make_material_request");
            });
        }

        var total_projection = 0;
        frm.doc.items.forEach(function(row){			
            total_projection += row.projected_sales;
        });
		
		if(total_projection > 0){
			frm.get_field("total_quantity").wrapper.innerHTML = '<p class="text-muted small">Total Projected Quantities: </p><b> ' + total_projection.toLocaleString() +  '<br><br></b>'; 
		}
	},
    posting_date: function (frm) {
        if (frm.doc.posting_date) {
            let date = new Date(frm.doc.posting_date);
            let month = date.toLocaleString('en-US', { month: 'long' });
            frm.set_value("month", month);
        }
    },

    fetch_items: function (frm) {
		frappe.call({
			method: "get_finished_goods_items",
			doc: frm.doc,
			callback: function (r) {
				refresh_field('items');
			}
		});
	},

    make_material_request: function (frm) {
        frappe.call({
				"method": "tet_production.tet_production.doctype.sales_projection.sales_projection.make_material_request",
				"args": {
					'name': frm.doc.name
				},
				"freeze": true,
				"freeze_message": "Generating Material Request...",
				"callback": function (data) {
					console.log(data);
					frappe.set_route('Form', data.message.doctype, data.message.name);
				}
			});
	},
    
});
