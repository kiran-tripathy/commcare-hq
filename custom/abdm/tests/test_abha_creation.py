from unittest.mock import patch

from rest_framework import status
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from custom.abdm.models import ABDMUser


class TestABHACreation(APITestCase):

    def setUp(self):
        self.user, _ = ABDMUser.objects.get_or_create(username="abdm_test", domain="abdm_test")
        token = self.user.access_token
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + token)
        self.invalid_req_msg = "Unable to process the current request due to incorrect data entered."

    @staticmethod
    def _mock_abdm_http_post(url, payload):
        abdm_txn_id_mock = {"txnId": "1234"}
        return {
            "v1/registration/aadhaar/generateOtp": abdm_txn_id_mock,
            "v1/registration/aadhaar/verifyMobileOTP": abdm_txn_id_mock,
            "v1/registration/aadhaar/verifyOTP": abdm_txn_id_mock,
            "v1/registration/aadhaar/generateMobileOTP": abdm_txn_id_mock,
            "v1/registration/aadhaar/createHealthIdWithPreVerified": {"token": "1122", "refreshToken": "1133",
                                                                      "health_id": "123-456", "txnId": "1234"},
        }.get(url)

    def test_aadhaar_otp_generation_success(self):
        abdm_txn_id_mock = {"txnId": "1234"}
        with patch('custom.abdm.milestone_one.views.abha_creation_views.abdm_util.get_response_http_post',
                   side_effect=TestABHACreation._mock_abdm_http_post):
            response = self.client.post(reverse("generate_aadhaar_otp"), {"aadhaar": "123456"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), abdm_txn_id_mock)

    def test_aadhaar_otp_generation_failure(self):
        response = self.client.post(reverse("generate_aadhaar_otp"), {"pan": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.invalid_req_msg, response.json().get("message"))

    def test_mobile_otp_generation_success(self):
        abdm_txn_id_mock = {"txnId": "1234"}
        with patch('custom.abdm.milestone_one.views.abha_creation_views.abdm_util.get_response_http_post',
                   side_effect=TestABHACreation._mock_abdm_http_post):
            response = self.client.post(reverse("generate_mobile_otp"),
                                        {"txn_id": "1234", "mobile_number": "9999988888"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), abdm_txn_id_mock)

    def test_mobile_otp_generation_failure(self):
        response = self.client.post(reverse("generate_mobile_otp"), {"pan": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.invalid_req_msg, response.json().get("message"))

    def test_aadhaar_otp_verification_success(self):
        abdm_txn_id_mock = {"txnId": "1234"}
        with patch('custom.abdm.milestone_one.views.abha_creation_views.abdm_util.get_response_http_post',
                   side_effect=TestABHACreation._mock_abdm_http_post):
            response = self.client.post(reverse("verify_aadhaar_otp"),
                                        {"txn_id": "1234", "otp": "1111"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), abdm_txn_id_mock)

    def test_aadhaar_otp_verification_failure(self):
        response = self.client.post(reverse("verify_aadhaar_otp"), {"pan": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.invalid_req_msg, response.json().get("message"))

    def test_mobile_otp_verification_success(self):
        with patch('custom.abdm.milestone_one.views.abha_creation_views.abdm_util.get_response_http_post',
                   side_effect=TestABHACreation._mock_abdm_http_post):
            response = self.client.post(reverse("verify_mobile_otp"),
                                        {"txn_id": "1234", "otp": "1111"})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json(), {"health_id": "123-456", "txnId": "1234"})

    def test_mobile_otp_verification_failure(self):
        response = self.client.post(reverse("verify_mobile_otp"), {"pan": "123456"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(self.invalid_req_msg, response.json().get("message"))

    def tearDown(self) -> None:
        ABDMUser.objects.all().delete()
