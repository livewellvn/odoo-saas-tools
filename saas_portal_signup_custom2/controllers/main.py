# -*- coding: utf-8 -*-

import werkzeug
from odoo import http
import re
from odoo.http import request
import logging
from datetime import datetime

from openerp.tools import DEFAULT_SERVER_DATE_FORMAT as DF
import odoo
from odoo import SUPERUSER_ID
from odoo.tools.translate import _
from odoo.addons import auth_signup
from odoo.addons.saas_portal.controllers.main import SaasPortal
from odoo.addons.website_payment.controllers.main import WebsitePayment
from odoo.addons.auth_signup.models.res_users import SignupError

_logger = logging.getLogger(__name__)

class AuthSignupHome(auth_signup.controllers.main.AuthSignupHome):

    @http.route()
    def web_auth_signup(self, *args, **kw):

        qcontext = self.get_auth_signup_qcontext()

        country_id = kw.get('country_id')
        if country_id:
            qcontext['prev_sel_country'] = request.env['res.country'].sudo().browse(int(country_id))

        sector_id = kw.get('sector_id')
        if sector_id:
            qcontext['prev_sel_sector'] = request.env['res.partner.sector'].sudo().browse(int(sector_id))

        product_id = kw.get('product_id')
        if product_id:
            qcontext['prev_sel_product'] = request.env['product.product'].sudo().browse(int(product_id))

        state_id = kw.get('state_id')
        if state_id:
            qcontext['prev_sel_state'] = request.env['res.country.state'].sudo().browse(int(state_id))

        currency_id = kw.get('account_currency_id')
        if currency_id:
            qcontext['prev_sel_currency'] = request.env['res.currency'].sudo().browse(int(currency_id))

        company_size = kw.get('company_size')
        if company_size:
            #sizes_dict = dict(request.env['res.partner']._get_company_sizes())
            sizes_dict = dict(request.env['res.partner']._fields["company_size"].selection)
            qcontext['prev_sel_company_size'] = (company_size, sizes_dict[company_size])

        gender = kw.get('gender')
        if gender:
            #genders_dict = dict(request.env['res.partner']._get_genders())
            genders_dict = dict(request.env['res.partner']._fields["gender"].selection)
            qcontext['prev_sel_gender'] = (gender, genders_dict[gender])

        if kw.has_key('g-recaptcha-response') and not request.website.recaptcha_siteverify(kw.get('g-recaptcha-response')):
            qcontext['error'] = _("Please confirm you are human")
            return request.render('auth_signup.signup', qcontext)

        if kw.get('dbname', False) and kw.get('product_id', False):
            redirect = '/saas_portal/add_new_client'
            kw['redirect'] = '%s?dbname=%s&product_id=%s&password=%s&trial_or_working=%s' % (
                redirect, kw['dbname'], kw['product_id'], kw['password'], kw['trial_or_working'])

        # return super(AuthSignupHome, self).web_auth_signup(*args, **kw)
# imp parent code: instead of showing ``Could not create a new account`` show assertion error text (e.g. if the passwords don't match)
        # qcontext = self.get_auth_signup_qcontext()

        if not qcontext.get('token') and not qcontext.get('signup_enabled'):
            raise werkzeug.exceptions.NotFound()

        if 'error' not in qcontext and request.httprequest.method == 'POST':
            try:
                self.do_signup(qcontext)
                return super(AuthSignupHome, self).web_login(*args, **kw)
            except (SignupError, AssertionError), e:
                if request.env["res.users"].sudo().search([("login", "=", qcontext.get("login"))]):
                    qcontext["error"] = _("Another user is already registered using this email address.")
                else:
                    _logger.error(e.message)
                    qcontext['error'] = e.message

        return request.render('auth_signup.signup', qcontext)
# end parent code

    def get_auth_signup_qcontext(self):
        qcontext = super(AuthSignupHome, self).get_auth_signup_qcontext()
        if not qcontext.get('countries', False):
            qcontext['countries'] = request.env['res.country'].search([])
        if not qcontext.get('base_saas_domain', False):
            qcontext['base_saas_domain'] = self.get_saas_domain()
        if not qcontext.get('products', False):
            qcontext['products'] = request.env['product.product'].sudo().search([('saas_plan_id', '!=', False)])
        if not qcontext.get('states', False):
            qcontext['states'] = request.env['res.country.state'].sudo().search([])
        if not qcontext.get('sectors', False):
            qcontext['sectors'] = request.env['res.partner.sector'].sudo().search([])
        if not qcontext.get('company_sizes', False):
            #qcontext['company_sizes'] = request.env['res.partner']._get_company_sizes()
            qcontext['company_sizes'] = request.env['res.partner']._fields["company_size"].selection

            #test1 = request.env['res.partner']
#            qcontext['company_sizes'] = dict(request.env['res.partner']._columns['company_sizes'].selection).get(
#            request.env['res.partner'].company_sizes)
        if not qcontext.get('genders', False):
            #qcontext['genders'] = request.env['res.partner']._get_genders()
            qcontext['genders'] = request.env['res.partner']._fields["gender"].selection
#            qcontext['genders'] = dict(request.env['res.partner']._columns['genders'].selection).get(
#            request.env['res.partner'].genders)
        if not qcontext.get('currencies', False):
            qcontext['currencies'] = request.env['res.currency'].search([])
        return qcontext

    def get_saas_domain(self):
        config = request.env['ir.config_parameter']
        full_param = 'saas_portal.base_saas_domain'
        base_saas_domain = config.get_param(full_param)
        return base_saas_domain

    def do_signup(self, qcontext):
        values = dict((key, qcontext.get(key)) for key in ('login', 'name', 'password'))

        parent_values = {}
        parent_values['is_company'] = True
        parent_values['name'] = qcontext.get('company_name', None)
        establishment_date = datetime(int(qcontext.get('establishment_year')), 1, 1)
        parent_values['establishment_year'] = establishment_date.strftime(DF)
        parent_values['previous_year_turnover'] = qcontext.get('previous_year_turnover', None)
        parent_values['company_size'] = qcontext.get('company_size', None)
        parent_values['website'] = qcontext.get('company_website', None)
        parent_values['phone'] = qcontext.get('tel', None)
        parent_values['fax'] = qcontext.get('fax', None)
        parent_values['city'] = qcontext.get('city', None)
        parent_values['street'] = qcontext.get('address', None)
        parent_values['vat'] = qcontext.get('tax_code', None)
        parent_values['zip'] = qcontext.get('postal_code', None)
        parent_values['business_reg_no'] = qcontext.get('business_reg_no', None)
        parent_values['tax_code'] = qcontext.get('tax_code', None)
        parent_values['dnb_number'] = qcontext.get('dnb_number', None)
        parent_values['email'] = qcontext['login']

        birthdate_date = qcontext.get('birthdate_date') and \
                datetime.strptime(qcontext['birthdate_date'], "%m/%d/%Y")
        if qcontext.get('full_name'):
            parent_values['child_ids'] = [(0, 0, {
                'name': qcontext['full_name'],
                'gender': qcontext.get('gender'),
                'birthdate_date': birthdate_date.strftime(DF),
                'function': 'Director',
                })]

        if qcontext.get('sector_id', False):
            parent_values['sector_id'] = qcontext['sector_id']
        if qcontext.get('country_id', False):
            parent_values['country_id'] = qcontext['country_id']
        if qcontext.get('account_currency_id', False):
            parent_values['account_currency_id'] = qcontext['account_currency_id']
        if qcontext.get('state_id', False):
            parent_values['state_id'] = qcontext['state_id']

        parent_id = request.env['res.partner'].sudo().create(parent_values)

        values['parent_id'] = parent_id.id
        values['company_name'] = qcontext.get('company_name', None)
        values['email'] = qcontext['login']
        # values['name'] = qcontext.get('company_name', None)
        values['is_company'] = False

        if qcontext.get('dbname', False):
            f_dbname = '%s.%s' % (qcontext['dbname'], self.get_saas_domain())
            full_dbname = f_dbname.replace('www.', '')
            db_exists = odoo.service.db.exp_db_exist(full_dbname)
            assert re.match('[a-zA-Z0-9_.-]+$', qcontext.get('dbname')), _("Only letters or numbers are allowed in domain.")
            assert db_exists == False, _("Web address exists, please choose another web address")

        assert re.match("^.+\\@(\\[?)[a-zA-Z0-9\\-\\.]+\\.([a-zA-Z]{2,3}|[0-9]{1,3})(\\]?)$", values['email']), _("Please enter a valid email address.")
        assert any([k for k in values.values()]), _("The form was not properly filled in.")
        assert values.get('password') == qcontext.get('confirm_password'), _("Passwords do not match; please retype them.")
        supported_langs = [lang['code'] for lang in request.env['res.lang'].sudo().search_read([], ['code'])]
        if request.lang in supported_langs:
            values['lang'] = request.lang
        self._signup_with_values(qcontext.get('token'), values)
        request.cr.commit()


class AuthSaasPortal(SaasPortal):

    @http.route()
    def add_new_client(self, **post):

        product = request.env['product.product'].sudo().browse(int(post.get('product_id')))
        res = None
        if product:
            plan = product.saas_plan_id
            kw = post.copy()
            kw['dbname'] = post.get('dbname')
            kw['plan_id'] = plan.id
            kw['trial'] = kw['trial_or_working'] == 'trial'
            kw['product_id'] = product.id
            res = super(AuthSaasPortal, self).add_new_client(**kw)

        return res


class SaaSWebsitePayment(WebsitePayment):

    @http.route()
    def pay(self, reference='', amount=False, currency_id=None, acquirer_id=None, **kw):
        return super(SaaSWebsitePayment, self).pay(reference=reference,
                                                   amount=amount,
                                                   currency_id=currency_id,
                                                   acquirer_id=acquirer_id, **kw)

    @http.route(['/saas_payment/pay'], type='http', auth='public', website=True)
    def saas_pay(self, **kw):
        contract_id = kw.get('contract_id')
        if contract_id:
            contract = request.env['account.analytic.account'].browse(contract_id)
            saas_portal_client = request.env['saas_portal.client'].sudo().search([('contract_id', '=', int(contract_id))], limit=1)
            if saas_portal_client.trial:
                if kw.get('convert_or_new') == 'convert':
                    saas_portal_client.trial = False
                elif kw.get('convert_or_new') == 'new':
                    name = saas_portal_client.name
                    plan = saas_portal_client.plan_id
                    partner_id = saas_portal_client.partner_id.id
                    user_id = request.session.uid
                    contract_id = saas_portal_client.contract_id

                    saas_portal_client.delete_database_server()

                    res = plan._create_new_database(dbname=name,
                                                    partner_id=partner_id,
                                                    user_id=user_id)
                    saas_portal_client = request.env['saas_portal.client'].sudo().browse(res['id'])
                    saas_portal_client.contract_id = contract_id
                else:
                    return request.render('saas_portal_signup_custom2.saas_trial_pay')

        url = '/website_payment/pay?%s' % werkzeug.url_encode(kw)
        return request.redirect(url)
