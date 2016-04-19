# -*- coding: utf-8 -*-
from openerp.addons.web import http
from openerp.addons.web.http import request
import werkzeug
import email


class MailMailgun(http.Controller):

    @http.route('/mail_mailgun', auth='public', csrf=False)
    def incoming_mail(self, **kw):
        print '\n\n\n', 'in incoming_mail ', 'kw ', kw, '\n\n\n\n'

    @http.route('/mail_mailgun_mime', auth='public', csrf=False)
    def incoming_mail_mime(self, **kw):
        print '\n\n\n', 'in incoming_mail_mime ', 'kw ', kw, '\n\n\n\n'
        body_mime = kw.get('body-mime')
        mail_thread = request.env['mail.thread']
        # mail_thread_obj = request.env['res.partner'].sudo()
        # msg_dict = mail_thread_obj.message_parse(body_mime)
        # print '\n\n\n', 'msg_dict ', msg_dict, '\n\n\n'
        # msg_id = msg_dict.get('message_id')
        # print '\n\n\n', 'msg_id ', msg_id, '\n\n\n'
        # mail_thread_obj.message_new(msg_dict)
        res_id = mail_thread.message_process('res.partner', mody_mime)
        print '\n\n\n', 'res_id ', res_id, '\n\n\n'




