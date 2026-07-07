from rest_framework import serializers

from users.models import User


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'email', 'name', 'role', 'created_at', 'updated_at')
        read_only_fields = fields


class UserRegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True,
        min_length=8,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = ('email', 'name', 'password', 'role')

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)
