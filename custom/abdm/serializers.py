from rest_framework import serializers

from custom.abdm.const import TIME_UNITS, DATA_ACCESS_MODES, ConsentPurpose


class GatewayRequestBaseSerializer(serializers.Serializer):
    requestId = serializers.UUIDField()


class GatewayErrorSerializer(serializers.Serializer):
    code = serializers.IntegerField()
    message = serializers.CharField()


class GatewayResponseReferenceSerializer(serializers.Serializer):
    requestId = serializers.UUIDField()


class GatewayIdSerializer(serializers.Serializer):
    id = serializers.CharField()


class GatewayCareContextSerializer(serializers.Serializer):
    patientReference = serializers.CharField()
    careContextReference = serializers.CharField()


class GatewayRequesterSerializer(serializers.Serializer):
    class IdentifierSerializer(serializers.Serializer):
        type = serializers.CharField()
        value = serializers.CharField()
        system = serializers.CharField(required=False, allow_null=True)

    name = serializers.CharField()
    identifier = IdentifierSerializer(required=False)


class GatewayPermissionSerializer(serializers.Serializer):
    class DateRangeSerializer(serializers.Serializer):
        vars()['from'] = serializers.DateTimeField()
        to = serializers.DateTimeField()

    class FrequencySerializer(serializers.Serializer):
        unit = serializers.ChoiceField(choices=TIME_UNITS)
        value = serializers.IntegerField()
        repeats = serializers.IntegerField()

    accessMode = serializers.ChoiceField(choices=DATA_ACCESS_MODES)
    dateRange = DateRangeSerializer()
    dataEraseAt = serializers.DateTimeField()
    frequency = FrequencySerializer()


class GatewayPurposeSerializer(serializers.Serializer):
    code = serializers.ChoiceField(choices=ConsentPurpose.CHOICES)
    text = serializers.CharField()
    refUri = serializers.CharField(required=False, allow_null=True)


class KeyMaterialSerializer(serializers.Serializer):

    class DHPublicKeySerializer(serializers.Serializer):
        expiry = serializers.DateTimeField()
        parameters = serializers.CharField()
        keyValue = serializers.CharField()

    cryptoAlg = serializers.CharField()
    curve = serializers.CharField()
    dhPublicKey = DHPublicKeySerializer()
    nonce = serializers.CharField()
