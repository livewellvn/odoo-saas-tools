# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
from openerp import SUPERUSER_ID, exceptions
from openerp.addons.saas_portal_start.controllers.main import SaasPortalStart



import werkzeug
import logging
import simplejson

_logger = logging.getLogger(__name__)

PAGE_PLAN_SELECT = "page_plan_select"
PAGE_PLAN_CONFIRM = "page_plan_confirm"
PAGE_TERMS_CONDS = "page_terms_conds"
PAGE_ADDONS_SELECT = "page_addons_select"
PAGE_SUMMARY = "page_summary"

WIZARD_FLOW = {
    PAGE_PLAN_SELECT: {
        "prev": None,
        "next": PAGE_TERMS_CONDS,
    },
    PAGE_TERMS_CONDS: {
        "prev": PAGE_PLAN_SELECT,
        "next": PAGE_PLAN_CONFIRM,
    },
    PAGE_PLAN_CONFIRM: {
        "prev": PAGE_TERMS_CONDS,
        "next": PAGE_ADDONS_SELECT,
    },
    PAGE_ADDONS_SELECT: {
        "prev": PAGE_PLAN_CONFIRM,
        "next": PAGE_SUMMARY,
    },
    PAGE_SUMMARY: {
        "prev": PAGE_ADDONS_SELECT,
        "next": None,
    },
}

class SaasPortalStartWizard(SaasPortalStart):

    @http.route(['/page/website.start', '/page/start'], type='http',
                auth="user", website=True)
    def start(self, **post):
        return super(SaasPortalStartWizard, self).start(**post)

    def __get_plans(self):
        # Get available plans
        plan_model = request.registry['saas_portal.plan']
        domain = [('state', '=', 'confirmed')]
        ids = plan_model.search(request.cr, SUPERUSER_ID, domain)
        plans = plan_model.browse(request.cr, SUPERUSER_ID, ids)

        return {"plans": plans}

    def __get_legal(self):
        cr, uid, context, registry = request.cr, request.uid, request.context, request.registry

        orm_user = registry.get('res.users')
        orm_country = registry.get('res.country')
        state_orm = registry.get('res.country.state')

        country_ids = orm_country.search(cr, SUPERUSER_ID, [], context=context)
        countries = orm_country.browse(cr, SUPERUSER_ID, country_ids, context)
        states_ids = state_orm.search(cr, SUPERUSER_ID, [], context=context)
        states = state_orm.browse(cr, SUPERUSER_ID, states_ids, context)
        partner = orm_user.browse(cr, SUPERUSER_ID, request.uid,
                                  context).partner_id

        values = {
            'name': partner.name or '',
            'phone': partner.phone or getattr(partner.parent_id, "phone", ''),
            'company': getattr(partner.parent_id, "name", ''),
            'vat': getattr(partner.parent_id, "vat", ''),
            'city': partner.city or getattr(partner.parent_id, "city", ''),
            'zip_': partner.zip or getattr(partner.parent_id, "zip", ''),
            'country_id': getattr(
                partner.country_id or getattr(partner.parent_id, "country_id",
                                              False), "id"),
            'state_id': getattr(
                partner.state_id or getattr(partner.parent_id, "state_id",
                                            False), "id"),
            'countries': countries,
            'states': states,
        }
        return values

    def __get_terms(self):
        company = request.registry['ir.model.data'].xmlid_to_object(
            request.cr,
            SUPERUSER_ID,
            "base.main_company")

        return {"terms": company.terms_n_conds or False}

    @http.route(['/page/start/wizard'], type='http', auth="user", website=True)
    def start_wizard(self, **post):
        _logger.info("\n\nWIZARD START with :: %s\n", post)
        state = {"upstream": post.items()}
        state["upstream"].append(("plan_id", None))

        state.update(self.__get_plans())
        state.update({"wizard_page": PAGE_PLAN_SELECT})

        #
        # addon_model = request.registry['ir.module.module']
        # domain = [('application', '=', True)]
        # ids = addon_model.search(request.cr, SUPERUSER_ID, domain)
        # addons = addon_model.browse(request.cr, SUPERUSER_ID, ids)
        #
        # addon_data = []
        # for addon in addons:
        #     data = {
        #         "name": addon.shortdesc,
        #         "summ": addon.summary,
        #         "id": addon.name,
        #         "logo": addon.icon,
        #     }
        #     addon_data.append(data)
        # state.update({"addons": addon_data})

        return request.website.render("saas_portal_start_wizard.wizard_tpl",
                                      state)

    @http.route(['/page/start/wizard/submit'], type='http', auth="user",
                website=True)
    def wizard_submit(self, **post):
        _logger.info("\n\nWIZARD SUBMIT with :: %s\n", post)

        current_page = post.pop("wizard_page")
        action = "next" if post.pop("page_next", False) == '' else "prev"
        post.pop("page_prev", False)

        next_page = WIZARD_FLOW[current_page][action]

        if (not next_page) and (action == "prev"):
            return werkzeug.utils.redirect('/page/start/')

        if (not next_page) and (action == "next"):
            return werkzeug.utils.redirect(
                '/saas_portal/add_new_client?{}'.format(
                    werkzeug.url_encode(post)
                )
            )

        state = {"upstream": post.items()}

        data = {
            PAGE_PLAN_SELECT: self.__get_plans,
            PAGE_TERMS_CONDS: self.__get_terms,
            PAGE_PLAN_CONFIRM: self.__get_legal,
        }[next_page]()

        _logger.info("\n\nData for next page: %s\n", data)

        state.update(data)
        state.update({"wizard_page": next_page})

        return request.website.render("saas_portal_start_wizard.wizard_tpl",
                                      state)

    @http.route(['/saas_portal/add_new_client'], type='http', auth='user',
                website=True)
    def add_new_client(self, **post):
        if not post.get("plan_id", False):
            return werkzeug.utils.redirect(
                '/page/start/wizard?{}'.format(werkzeug.url_encode(post)))

        post.update({"plan_id": int(post["plan_id"])})

        dbname = self.get_full_dbname(post.get('dbname'))
        plan = self.get_plan(post.get('plan_id'))
        url = plan.create_new_database(dbname)[0]

        base, params = url.split("?")
        params = werkzeug.url_decode(params)
        state = simplejson.loads(params['state'])

        addons = []
        if post.get('addons', False):
            addons = post['addons'].split(",")
        state.update({'addons': addons})

        company_data = {
            "name": post.get("company"),
            "vat": post.get("vat"),
            "phone": post.get("phone"),
            "city": post.get("city"),
            "state": post.get("state"),
            "country": post.get("country"),
            "zip": post.get("zip"),
        }

        state.update({"company_data": company_data})
        params['state'] = simplejson.dumps(state)

        url = "{base}?{params}".format(base=base, params=werkzeug.url_encode(params))
        _logger.info("\n\nFinal URL: %s\n", url)

        return werkzeug.utils.redirect(url)

