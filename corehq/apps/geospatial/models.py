from django.db import models
from django.utils.translation import gettext as _

from corehq.apps.geospatial.const import GPS_POINT_CASE_PROPERTY, ALGO_AES
from corehq.apps.geospatial.routing_solvers import pulp
from corehq.motech.utils import b64_aes_encrypt, b64_aes_decrypt


class GeoPolygon(models.Model):
    """
    A GeoJSON file representing a polygon shape
    """

    name = models.CharField(max_length=256)
    geo_json = models.JSONField(default=dict)
    domain = models.CharField(max_length=256, db_index=True)


class GeoConfig(models.Model):

    CUSTOM_USER_PROPERTY = 'custom_user_property'
    ASSIGNED_LOCATION = 'assigned_location'
    RADIAL_ALGORITHM = 'radial_algorithm'
    ROAD_NETWORK_ALGORITHM = 'road_network_algorithm'
    MIN_MAX_GROUPING = 'min_max_grouping'
    TARGET_SIZE_GROUPING = 'target_size_grouping'

    VALID_DISBURSEMENT_ALGORITHM_CLASSES = {
        RADIAL_ALGORITHM: pulp.RadialDistanceSolver,
        ROAD_NETWORK_ALGORITHM: pulp.RoadNetworkSolver,
    }

    VALID_LOCATION_SOURCES = [
        CUSTOM_USER_PROPERTY,
        ASSIGNED_LOCATION,
    ]
    VALID_DISBURSEMENT_ALGORITHMS = [
        (RADIAL_ALGORITHM, _('Radial Algorithm')),
        (ROAD_NETWORK_ALGORITHM, _('Road Network Algorithm')),
    ]
    VALID_GROUPING_METHODS = [
        (MIN_MAX_GROUPING, _('Min/Max Grouping')),
        (TARGET_SIZE_GROUPING, _('Target Size Grouping')),
    ]

    domain = models.CharField(max_length=256, db_index=True, primary_key=True)
    location_data_source = models.CharField(max_length=126, default=CUSTOM_USER_PROPERTY)
    user_location_property_name = models.CharField(max_length=256, default=GPS_POINT_CASE_PROPERTY)
    case_location_property_name = models.CharField(max_length=256, default=GPS_POINT_CASE_PROPERTY)

    selected_grouping_method = models.CharField(
        choices=VALID_GROUPING_METHODS,
        default=MIN_MAX_GROUPING,
        max_length=50
    )
    max_cases_per_group = models.IntegerField(null=True)
    min_cases_per_group = models.IntegerField(null=True)
    target_group_count = models.IntegerField(null=True)

    selected_disbursement_algorithm = models.CharField(
        choices=VALID_DISBURSEMENT_ALGORITHMS,
        default=RADIAL_ALGORITHM,
        max_length=50
    )
    _api_token = models.CharField(max_length=255, blank=True, null=True, db_column="api_token")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._clear_caches()

    def delete(self, *args, **kwargs):
        self._clear_caches()
        return super().delete(*args, **kwargs)

    def _clear_caches(self):
        from .utils import get_geo_case_property, get_geo_user_property

        get_geo_case_property.clear(self.domain)
        get_geo_user_property.clear(self.domain)

    @property
    def disbursement_solver(self):
        return self.VALID_DISBURSEMENT_ALGORITHM_CLASSES[
            self.selected_disbursement_algorithm
        ]

    @property
    def api_token(self):
        if self._api_token and self._api_token.startswith(f'${ALGO_AES}$'):
            ciphertext = self._api_token.split('$', 2)[2]
            return b64_aes_decrypt(ciphertext)
        return self._api_token

    @api_token.setter
    def api_token(self, value):
        if value and not value.startswith(f'${ALGO_AES}$'):
            ciphertext = b64_aes_encrypt(value)
            self._api_token = f'${ALGO_AES}${ciphertext}'
        else:
            self._api_token = None
