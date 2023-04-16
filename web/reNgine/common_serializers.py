from rest_framework import serializers
from targetApp.models import *


class HistoricalIPSerializer(serializers.ModelSerializer):
    class Meta:
        model = HistoricalIP
        fields = ['ip', 'location', 'owner', 'last_seen']


class RelatedDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = RelatedDomain
        fields = '__all__'


class NameServersSerializer(serializers.ModelSerializer):
    class Meta:
        model = NameServer
        fields = ['name']


class DomainRegistrarSerializer(serializers.ModelSerializer):
    class Meta:
        model = Registrar
        fields = ['name', 'phone', 'email', 'url']


class DomainRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainRegistration
        fields = [
            'name',
            'organization',
            'address',
            'city',
            'state',
            'zip_code',
            'country',
            'email',
            'phone',
            'fax'
        ]

class DomainWhoisStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = WhoisStatus
        fields = ['name']


class DomainDNSRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DNSRecord
        fields = ['name', 'type']
