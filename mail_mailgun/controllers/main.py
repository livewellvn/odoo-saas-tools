# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
import werkzeug


class MailMailgun(http.Controller):

    @http.route('/mail_mailgun', auth='public')
    def incoming_mail(self, **kw):
        print '\n\n\n', 'in incoming_mail ', 'kw ', kw, '\n\n\n\n'
