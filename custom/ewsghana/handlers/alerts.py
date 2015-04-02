from custom.ilsgateway.tanzania.handlers.keyword import KeywordHandler
from custom.ewsghana.alerts.alerts import report_completion_check, stock_alerts
from corehq.apps.sms.api import send_sms_to_verified_number
from corehq.apps.commtrack.sms import *


class AlertsHandler(KeywordHandler):

    def handle(self):
        verified_contact = self.verified_contact
        user = verified_contact.owner
        domain = Domain.get_by_name(verified_contact.domain)
        splitted_text = self.msg.text.split()
        if splitted_text[0].lower() == 'soh':
            text = ' '.join(self.msg.text.split()[1:])
        else:
            text = self.msg.text

        if not domain.commtrack_enabled:
            return False
        try:
            data = StockAndReceiptParser(domain, verified_contact).parse(text)
            if not data:
                return False
        except NotAUserClassError:
            return False
        except Exception, e:  # todo: should we only trap SMSErrors?
            if settings.UNIT_TESTING or settings.DEBUG:
                raise
            send_sms_to_verified_number(verified_contact, 'problem with stock report: %s' % str(e))
            return True
        process(domain.name, data)
        transactions = data['transactions']
        stock_alerts(transactions, user)
        return True
