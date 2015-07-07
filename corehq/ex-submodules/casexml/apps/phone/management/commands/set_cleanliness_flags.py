from optparse import make_option
from django.core.management import BaseCommand
from corehq.apps.domain.models import Domain
from corehq.toggles import OWNERSHIP_CLEANLINESS


class Command(BaseCommand):
    """
    Set cleanliness flags for a domain, or for all domains
    """
    option_list = BaseCommand.option_list + (
        make_option('--force',
                    action='store_true',
                    dest='force',
                    default=False,
                    help="Force rebuild on top of existing flags/hints."),
    )

    def handle(self, *args, **options):
        from casexml.apps.phone.cleanliness import set_cleanliness_flags_for_domain
        force_full = options['force']
        if len(args) == 1:
            domain = args[0]
            set_cleanliness_flags_for_domain(domain, force_full=force_full)
        else:
            assert len(args) == 0
            for domain in Domain.get_all_names():
                if OWNERSHIP_CLEANLINESS.enabled(domain):
                    print 'updating flags for {}'.format(domain)
                    set_cleanliness_flags_for_domain(domain, force_full=force_full)
