# ERPNext - web based ERP (http://erpnext.com)
# Copyright (C) 2012 Web Notes Technologies Pvt Ltd
# 
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import unicode_literals
import webnotes
from webnotes.utils import flt, getdate
from webnotes.model.bean import getlist

class DocType:
	def __init__(self,d,dl):
		self.doc, self.doclist = d,dl

	def validate(self):
		"""Validate invoice that c-form is applicable 
			and no other c-form is received for that"""

		for d in getlist(self.doclist, 'invoice_details'):
			if d.invoice_no:
				inv = webnotes.conn.sql("""select c_form_applicable, c_form_no from
					`tabSales Invoice` where name = %s and docstatus = 1""", d.invoice_no)
				
				if not inv:
					webnotes.msgprint("""Invoice: %s is not exists in the system or 
						is not submitted, please check.""" % d.invoice_no, raise_exception=1)
					
				elif inv[0][0] != 'Yes':
					webnotes.msgprint("C-form is not applicable for Invoice: %s" % 
						d.invoice_no, raise_exception=1)
					
				elif inv[0][1] and inv[0][1] != self.doc.name:
					webnotes.msgprint("""Invoice %s is tagged in another C-form: %s.
						If you want to change C-form no for this invoice,
						please remove invoice no from the previous c-form and then try again""" % 
						(d.invoice_no, inv[0][1]), raise_exception=1)

	def on_update(self):
		"""	Update C-Form No on invoices"""
		self.set_total_invoiced_amount()
	
	def on_submit(self):
		self.set_cform_in_sales_invoices()
		
	def before_cancel(self):
		# remove cform reference
		webnotes.conn.sql("""update `tabSales Invoice` set c_form_no=null
			where c_form_no=%s""", self.doc.name)
		
	def set_cform_in_sales_invoices(self):
		inv = [d.invoice_no for d in getlist(self.doclist, 'invoice_details')]
		if inv:
			webnotes.conn.sql("""update `tabSales Invoice` set c_form_no=%s, modified=%s 
				where name in (%s)""" % ('%s', '%s', ', '.join(['%s'] * len(inv))), 
				tuple([self.doc.name, self.doc.modified] + inv))
				
			webnotes.conn.sql("""update `tabSales Invoice` set c_form_no = null, modified = %s 
				where name not in (%s) and ifnull(c_form_no, '') = %s""" % 
				('%s', ', '.join(['%s']*len(inv)), '%s'),
				tuple([self.doc.modified] + inv + [self.doc.name]))
		else:
			webnotes.msgprint("Please enter atleast 1 invoice in the table", raise_exception=1)

	def set_total_invoiced_amount(self):
		total = sum([flt(d.grand_total) for d in getlist(self.doclist, 'invoice_details')])
		webnotes.conn.set(self.doc, 'total_invoiced_amount', total)

	def get_invoice_details(self, invoice_no):
		"""	Pull details from invoices for referrence """

		inv = webnotes.conn.sql("""select posting_date, territory, net_total, grand_total 
			from `tabSales Invoice` where name = %s""", invoice_no)	
		return {
			'invoice_date' : inv and getdate(inv[0][0]).strftime('%Y-%m-%d') or '',
			'territory'    : inv and inv[0][1] or '',
			'net_total'    : inv and flt(inv[0][2]) or '',
			'grand_total'  : inv and flt(inv[0][3]) or ''
		}

def get_invoice_nos(doctype, txt, searchfield, start, page_len, filters):
	from utilities import build_filter_conditions
	conditions, filter_values = build_filter_conditions(filters)
	
	return webnotes.conn.sql("""select name from `tabSales Invoice` where docstatus = 1 
		and c_form_applicable = 'Yes' and ifnull(c_form_no, '') = '' %s 
		and %s like %s order by name limit %s, %s""" % 
		(conditions, searchfield, "%s", "%s", "%s"), 
		tuple(filter_values + ["%%%s%%" % txt, start, page_len]))