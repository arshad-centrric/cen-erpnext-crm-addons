import frappe
from frappe.tests import IntegrationTestCase

from cen_branch_management.tests import utils
from cen_crm_addons.mobile_api.general import get_mobile_user_profile


class TestMobileProfileBranchAccess(IntegrationTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        companies = utils.get_companies()
        cls.company = companies[0]
        cls.other_company = companies[1] if len(companies) > 1 else None
        cls.parent = utils.make_warehouse(cls.company, is_group=1)
        cls.a = utils.make_warehouse(cls.company, parent=cls.parent)
        cls.b = utils.make_warehouse(cls.company, parent=cls.parent)

    def tearDown(self):
        frappe.set_user("Administrator")

    def mobile_user(self):
        user = utils.make_user()
        frappe.get_doc({"doctype": "Mobile User Profile", "user": user}).insert(ignore_permissions=True)
        return user

    def branch(self, users, company=None, restrictions=()):
        company = company or self.company
        fields = {}
        if company == self.company:
            fields = {
                "custom_cen_warehouse_parent": self.parent,
                "custom_cen_user_warehouses": [{"user": u, "warehouse": w} for u, w in restrictions],
            }
        return utils.make_branch(company, users=users, **fields)

    def profile(self, user):
        frappe.set_user(user)
        out = get_mobile_user_profile()
        frappe.set_user("Administrator")
        return out

    def warehouses(self, profile, branch):
        for company in profile["companies"]:
            for row in company["branches"]:
                if row["branch_name"] == branch.name:
                    return sorted(row["warehouses"])
        return None

    def test_unrestricted_user_sees_all_branch_warehouses(self):
        user = self.mobile_user()
        branch = self.branch([user])

        self.assertEqual(self.warehouses(self.profile(user), branch), sorted([self.a, self.b]))

    def test_restricted_user_sees_only_their_warehouse(self):
        # A permission on a single, non-group warehouse used to come back empty.
        user = self.mobile_user()
        branch = self.branch([user], restrictions=[(user, self.b)])

        self.assertEqual(self.warehouses(self.profile(user), branch), [self.b])

    def test_active_branch_is_the_default_branch_with_its_company(self):
        if not self.other_company:
            self.skipTest("Needs a second company on the site")

        user = self.mobile_user()
        self.branch([user])
        pinned = self.branch([user], company=self.other_company)
        frappe.db.set_value("User", user, "custom_cen_default_branch", pinned.name)

        profile = self.profile(user)

        self.assertEqual(profile["active_branch"], pinned.name)
        self.assertEqual(profile["active_company"], self.other_company)

    def test_without_a_default_branch_the_first_branch_in_the_list_is_active(self):
        user = self.mobile_user()
        self.branch([user])
        self.branch([user])

        profile = self.profile(user)
        first = profile["companies"][0]

        self.assertEqual(profile["active_branch"], first["branches"][0]["branch_name"])
        self.assertEqual(profile["active_company"], first["company_name"])
        self.assertEqual(
            profile["active_company"],
            frappe.db.get_value("Branch", profile["active_branch"], "custom_cen_default_company"),
        )

    def test_a_default_branch_the_user_left_is_ignored(self):
        user = self.mobile_user()
        kept = self.branch([user])
        left = self.branch([])
        frappe.db.set_value("User", user, "custom_cen_default_branch", left.name)

        self.assertEqual(self.profile(user)["active_branch"], kept.name)
