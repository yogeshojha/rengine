from rest_framework import serializers
from targetApp.models import *


class AssociatedDomainSerializer(serializers.ModelSerializer):
    class Meta:
        model = AssociatedDomain
        fields = '__all__'


class NameServersSerializer(serializers.ModelSerializer):
    class Meta:
        model = NameServers
        fields = ['name']


class DomainRegistrarSerializer(serializers.ModelSerializer):
    class Meta:
        model = DomainRegistrar
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
        model = DomainWhoisStatus
        fields = ['status']
