# -*- coding: utf-8 -*-
# Copyright (c) 2015, EOSSF and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import add_days, add_years, nowdate, getdate
from frappe import _
import foundation

class Membership(Document):
	def validate(self):
		member_name = frappe.get_value('Member', dict(email=frappe.session.user))

		if not member_name:
			user = frappe.get_doc('User', frappe.session.user)
			member = frappe.get_doc(dict(
				doctype='Member',
				email=frappe.session.user,
				member_name=user.get_fullname()
			)).insert(ignore_permissions=True)
			member_name = member.name

		if self.get("__islocal"):
			self.member = member_name

		# get last membership (if active)
		last_membership = foundation.get_last_membership()

		if last_membership:
			# if last membership does not expire in 30 days, then do not allow to renew
			if getdate(add_days(last_membership.to_date, -30)) > getdate(nowdate()):
				frappe.throw(_('You can only renew if your membership expires within 30 days'))

			self.from_date = add_days(last_membership.to_date, 1)
		else:
			self.from_date = nowdate()

		self.to_date = add_years(self.from_date, 1)

	def on_payment_authorized(self, status_changed_to=None):
		if status_changed_to in ("Completed", "Authorized"):
			self.load_from_db()
			self.db_set('paid', 1)

			self.link_member_with_service_provider()

	def link_member_with_service_provider(self):
		service_provider = frappe.db.get_value("Service Provider", dict(owner=frappe.session.user))

		if service_provider:
			frappe.db.set_value("Service Provider", service_provider, "member", frappe.session.user,
				update_modified=False)
		else:
			# create new service provider for the member
			doc = frappe.get_doc({
				"doctype": "Service Provider",
				"email": frappe.session.user,
				"title": frappe.db.get_value("Member", self.member, "member_name"),
				"member": self.member,
				"show_in_website": 1
			}).insert(ignore_mandatory=True, ignore_permissions = True)