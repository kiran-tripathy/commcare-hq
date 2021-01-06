import json
from datetime import datetime

from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django.utils.translation import ugettext_lazy
from django.views.decorators.http import require_http_methods, require_POST
from django.views.generic.edit import BaseCreateView, BaseUpdateView

from corehq import toggles
from corehq.apps.domain.decorators import login_and_domain_required
from corehq.apps.domain.views.settings import BaseProjectSettingsView
from corehq.apps.hqwebapp.views import CRUDPaginatedViewMixin
from corehq.apps.users.decorators import require_permission
from corehq.apps.users.models import Permissions

from .const import SEND_FREQUENCY_CHOICES
from .dhis2_config import Dhis2EntityConfig, Dhis2FormConfig
from .forms import (
    DataSetMapForm,
    DataValueMapCreateForm,
    DataValueMapUpdateForm,
    Dhis2ConfigForm,
    Dhis2EntityConfigForm,
)
from .models import SQLDataSetMap, SQLDataValueMap
from .repeaters import Dhis2EntityRepeater, Dhis2Repeater
from .tasks import send_dataset


@method_decorator(require_permission(Permissions.edit_motech), name='dispatch')
@method_decorator(toggles.DHIS2_INTEGRATION.required_decorator(), name='dispatch')
class DataSetMapListView(BaseProjectSettingsView, CRUDPaginatedViewMixin):
    urlname = 'dataset_map_list_view'
    page_title = ugettext_lazy("DHIS2 DataSet Maps")
    template_name = 'dhis2/dataset_map_list.html'

    limit_text = _('DataSet Maps per page')
    empty_notification = _('There are no DataSet Maps')
    loading_message = _('Loading DataSet Maps')

    @property
    def total(self):
        return self.base_query.count()

    @property
    def base_query(self):
        return SQLDataSetMap.objects.filter(domain=self.domain)

    @property
    def page_context(self):
        return self.pagination_context

    @property
    def paginated_list(self):
        for dataset_map in self.base_query.all():
            yield {
                "itemData": self._get_item_data(dataset_map),
                "template": "dataset-map-template",
            }

    @property
    def column_names(self):
        return [
            _('Description'),
            _('Connection Settings'),
            _('Frequency'),
            _('UCR'),

            _('Action')
        ]

    def _get_item_data(self, dataset_map):
        frequency_names = dict(SEND_FREQUENCY_CHOICES)
        return {
            'id': dataset_map.id,
            'description': dataset_map.description,
            'connectionSettings': str(dataset_map.connection_settings),
            'frequency': frequency_names[dataset_map.frequency],
            'ucr': dataset_map.ucr.title,

            'editUrl': reverse(
                DataSetMapUpdateView.urlname,
                kwargs={'domain': self.domain, 'pk': dataset_map.id}
            ),
        }

    def get_deleted_item_data(self, item_id):
        dataset_map = SQLDataSetMap.objects.get(domain=self.domain, pk=item_id)
        dataset_map.delete()
        return {
            'itemData': self._get_item_data(dataset_map),
            'template': 'dataset-map-deleted-template',
        }

    def post(self, *args, **kwargs):
        return self.paginate_crud_response


@method_decorator(require_permission(Permissions.edit_motech), name='dispatch')
@method_decorator(toggles.DHIS2_INTEGRATION.required_decorator(), name='dispatch')
class DataSetMapCreateView(BaseCreateView, BaseProjectSettingsView):
    urlname = 'dataset_map_create_view'
    page_title = _('DataSet Map')
    template_name = 'dhis2/dataset_map_create.html'
    model = SQLDataSetMap
    form_class = DataSetMapForm

    def get_queryset(self):
        return super().get_queryset().filter(domain=self.domain)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['domain'] = self.domain
        return kwargs

    def get_success_url(self):
        return reverse(
            DataSetMapListView.urlname,
            kwargs={'domain': self.domain},
        )


@method_decorator(require_permission(Permissions.edit_motech), name='dispatch')
@method_decorator(toggles.DHIS2_INTEGRATION.required_decorator(), name='dispatch')
class DataSetMapUpdateView(BaseUpdateView, BaseProjectSettingsView,
                           CRUDPaginatedViewMixin):
    urlname = 'dataset_map_update_view'
    page_title = _('DataSet Map')
    template_name = 'dhis2/dataset_map_update.html'
    model = SQLDataSetMap
    form_class = DataSetMapForm

    limit_text = _('DataValue Maps per page')
    empty_notification = _('This DataSet Map has no DataValue Maps')
    loading_message = _('Loading DataValue Maps')

    def get_queryset(self):
        return super().get_queryset().filter(domain=self.domain)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['domain'] = self.domain
        return kwargs

    def get_success_url(self):
        return reverse(
            DataSetMapListView.urlname,
            kwargs={'domain': self.domain},
        )

    @property
    def page_url(self):
        return reverse(self.urlname, args=[self.domain, self.kwargs['pk']])

    def post(self, request, *args, **kwargs):
        super().post(request, *args, **kwargs)
        return self.paginate_crud_response

    @property
    def total(self):
        return self.base_query.count()

    @property
    def base_query(self):
        return self.object.datavalue_maps

    @property
    def page_context(self):
        return {
            'dataset_map_id': self.kwargs['pk'],
            **self.pagination_context,
        }

    @property
    def paginated_list(self):
        for datavalue_map in self.base_query.all():
            yield {
                "itemData": self._get_item_data(datavalue_map),
                "template": "datavalue-map-template",
            }

    def get_create_item_data(self, create_form):
        datavalue_map = create_form.save()
        return {
            'itemData': self._get_item_data(datavalue_map),
            'template': 'new-datavalue-map-template',
        }

    def get_updated_item_data(self, update_form):
        datavalue_map = update_form.save()
        return {
            "itemData": self._get_item_data(datavalue_map),
            "template": "datavalue-map-template",
        }

    def get_deleted_item_data(self, item_id):
        datavalue_map = SQLDataValueMap.objects.get(pk=item_id,
                                                    dataset_map=self.object)
        datavalue_map.delete()
        return {
            'itemData': self._get_item_data(datavalue_map),
            'template': 'deleted-datavalue-map-template',
        }

    @property
    def column_names(self):
        return [
            _('Column'),
            _('DataElementID'),
            _('CategoryOptionComboID'),
            _('Comment'),

            _('Action'),
        ]

    def _get_item_data(self, datavalue_map):
        return {
            'id': datavalue_map.id,
            'column': datavalue_map.column,
            'dataElementId': datavalue_map.data_element_id,
            'categoryOptionComboId': datavalue_map.category_option_combo_id,
            'comment': datavalue_map.comment,

            'updateForm': self.get_update_form_response(
                self.get_update_form(datavalue_map)
            ),
        }

    def get_create_form(self, is_blank=False):
        if self.request.method == 'POST' and not is_blank:
            return DataValueMapCreateForm(self.object, self.request.POST)
        return DataValueMapCreateForm(self.object)

    def get_update_form(self, instance=None):
        if instance is None:
            instance = SQLDataValueMap.objects.get(
                id=self.request.POST.get("id"),
                dataset_map=self.object,
            )
        if self.request.method == 'POST' and self.action == 'update':
            return DataValueMapUpdateForm(self.object, self.request.POST,
                                          instance=instance)
        return DataValueMapUpdateForm(self.object, instance=instance)


@require_POST
@require_permission(Permissions.edit_motech)
def send_dataset_now(request, domain, pk):
    dataset_map = SQLDataSetMap.objects.get(domain=domain, pk=pk)
    send_date = datetime.utcnow().date()
    result = send_dataset(dataset_map, send_date)
    return JsonResponse(result, status=result['status_code'] or 500)


@login_and_domain_required
@require_http_methods(["GET", "POST"])
def config_dhis2_repeater(request, domain, repeater_id):
    repeater = Dhis2Repeater.get(repeater_id)
    assert repeater.domain == domain, f'"{repeater.domain}" != "{domain}"'

    if request.method == 'POST':
        form = Dhis2ConfigForm(data=request.POST)
        if form.is_valid():
            data = form.cleaned_data
            repeater.dhis2_config.form_configs = list(map(Dhis2FormConfig.wrap, data['form_configs']))
            repeater.save()

    else:
        form_configs = json.dumps([
            form_config.to_json() for form_config in repeater.dhis2_config.form_configs
        ])
        form = Dhis2ConfigForm(
            data={
                'form_configs': form_configs,
            }
        )
    return render(request, 'dhis2/edit_config.html', {
        'domain': domain,
        'repeater_id': repeater_id,
        'form': form
    })


@login_and_domain_required
@require_http_methods(["GET", "POST"])
def config_dhis2_entity_repeater(request, domain, repeater_id):
    repeater = Dhis2EntityRepeater.get(repeater_id)
    assert repeater.domain == domain
    if request.method == 'POST':
        errors = []
        case_configs = []
        case_types = set()
        post_data = json.loads(request.POST["case_configs"])
        for case_config in post_data:
            form = Dhis2EntityConfigForm(data={"case_config": json.dumps(case_config)})
            if form.is_valid():
                case_configs.append(form.cleaned_data["case_config"])
                case_types.add(form.cleaned_data["case_config"]["case_type"])
            else:
                # form.errors is a dictionary where values are lists.
                errors.extend([err for errlist in form.errors.values() for err in errlist])
        if len(case_types) < len(case_configs):
            errors.append(_('You cannot have more than one case config for the same case type.'))
        if errors:
            return JsonResponse({'errors': errors}, status=400)
        else:
            repeater.dhis2_entity_config = Dhis2EntityConfig.wrap({
                "case_configs": case_configs
            })
            repeater.save()
            return JsonResponse({'success': _('DHIS2 Tracked Entity configuration saved')})

    else:
        case_configs = [
            case_config.to_json()
            for case_config in repeater.dhis2_entity_config.case_configs
        ]
    return render(request, 'dhis2/dhis2_entity_config.html', {
        'domain': domain,
        'repeater_id': repeater_id,
        'case_configs': case_configs,
    })
