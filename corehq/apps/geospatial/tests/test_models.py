from contextlib import contextmanager

from django.test import TestCase

from ..const import GPS_POINT_CASE_PROPERTY, ALGO_AES
from ..models import GeoConfig
from ..utils import get_geo_case_property


class TestGeoConfig(TestCase):

    domain = 'test-geo-config'
    geo_property = 'gps_location'

    def test_geo_config(self):
        case_property = get_geo_case_property(self.domain)
        self.assertEqual(case_property, GPS_POINT_CASE_PROPERTY)
        with self.get_geo_config():
            case_property = get_geo_case_property(self.domain)
            self.assertEqual(case_property, self.geo_property)
        case_property = get_geo_case_property(self.domain)
        self.assertEqual(case_property, GPS_POINT_CASE_PROPERTY)

    def test_geo_config_api_token(self):
        with self.get_geo_config() as config:
            config.api_token = '1234'
            self.assertEqual(config.api_token, '1234')
            self.assertTrue(config._api_token.startswith(f"${ALGO_AES}$"))

            config.api_token = None
            self.assertEqual(config.api_token, None)
            self.assertEqual(config._api_token, None)

    @contextmanager
    def get_geo_config(self):
        conf = GeoConfig(
            domain=self.domain,
            case_location_property_name=self.geo_property,
        )
        conf.save()
        try:
            yield conf
        finally:
            conf.delete()
