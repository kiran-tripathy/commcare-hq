from django.template.loader import render_to_string

import settings 

from xformmanager.models import FormDefModel, Metadata

def domain_summary(request, domain=None):
    '''Domain Admin Summary Data'''
    if not domain:
        domain = request.extuser.domain
    summary = DomainSummary(domain)
    return render_to_string("custom/all/domain_summary.html", 
                            {"MEDIA_URL": settings.MEDIA_URL, # we pretty sneakly have to explicitly pass this
                             "domain": domain,
                             "summary": summary})

class DomainSummary(object):
    
    def __init__(self, domain):
        self.form_data = []
        self.chw_data = []
        self.domain = domain
        domain_meta = Metadata.objects.filter(formdefmodel__domain=domain)
        self.full_count = domain_meta.count()
        chws = domain_meta.values_list('username', flat=True).distinct()
        forms = FormDefModel.objects.filter(domain=domain)
        blacklist = domain.get_blacklist()
        for form in forms:
            form_metas = domain_meta.filter(formdefmodel=form)
            self.form_data.append({"form": form,
                                   "count": form_metas.count(),
                                   "first": _get_first_object(form_metas, "timeend", True),
                                   "last": _get_first_object(form_metas, "timeend", False)
                                  })
        self.blacklist_count = 0
        self.chw_blacklist_count = 0
        self.chw_count = 0
        for chw in chws:
            chw_forms = domain_meta.filter(username=chw)
            in_blacklist = chw in blacklist
            self.chw_data.append({"name": chw,
                                  "count": chw_forms.count(),
                                  "in_blacklist": in_blacklist,
                                  "first": _get_first_object(chw_forms, "timeend", True),
                                  "last": _get_first_object(chw_forms, "timeend", False)
                                  })
            if in_blacklist:
                self.chw_blacklist_count += 1
                self.blacklist_count += chw_forms.count()
            else:
                self.chw_count += 1
        self.count = self.full_count - self.blacklist_count
        
    def chws(self):
        """Flat list of CHW's found in this domain"""
        return self.chw_counts.keys()
    
    def form_count(self):
        """Number of unique formss (types) found in this domain."""
        return len(self.form_data)
    
def _get_first_object(queryset, column_name, first):
    sort_str = "" if first else "-"
    sorted_qs = queryset.order_by("%s%s" % (sort_str, column_name))
    if sorted_qs.count() > 0:
        return sorted_qs[0]