from rest_framework import serializers
from .models import User, Organization, WorkType, Object, BlockSection, FrontTransfer

class OrganizationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Organization
        fields = ['id', 'organization', 'is_general_contractor']

class UserSerializer(serializers.ModelSerializer):
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False, allow_null=True)

    class Meta:
        model = User
        fields = ['id', 'chat_id', 'full_name', 'is_authorized', 'organization']

    def update(self, instance, validated_data):
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.is_authorized = validated_data.get('is_authorized', instance.is_authorized)
        organization_data = validated_data.get('organization')
        if organization_data:
            instance.organization = organization_data
        instance.save()
        return instance

class WorkTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkType
        fields = ['id', 'name']

class ObjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Object
        fields = ['id', 'name']

class BlockSectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = BlockSection
        fields = ['id', 'object', 'name', 'number_of_floors']

class FrontTransferSerializer(serializers.ModelSerializer):

    photo_ids = serializers.JSONField(required=False)

    sender = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    sender_chat_id = serializers.CharField(max_length=100)  # Новое поле

    receiver = serializers.PrimaryKeyRelatedField(queryset=User.objects.all(), required=False, allow_null=True)
    object = serializers.PrimaryKeyRelatedField(queryset=Object.objects.all())
    work_type = serializers.PrimaryKeyRelatedField(queryset=WorkType.objects.all())
    block_section = serializers.PrimaryKeyRelatedField(queryset=BlockSection.objects.all())
    next_work_type = serializers.PrimaryKeyRelatedField(queryset=WorkType.objects.all(), required=False, allow_null=True)
    photo1 = serializers.ImageField(required=False, allow_null=True)
    photo2 = serializers.ImageField(required=False, allow_null=True)
    photo3 = serializers.ImageField(required=False, allow_null=True)
    photo4 = serializers.ImageField(required=False, allow_null=True)
    photo5 = serializers.ImageField(required=False, allow_null=True)

    object_name = serializers.SerializerMethodField()
    work_type_name = serializers.SerializerMethodField()
    block_section_name = serializers.SerializerMethodField()
    next_work_type_name = serializers.SerializerMethodField()

    created_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M:%S', read_only=False)
    approval_at = serializers.DateTimeField(format='%d-%m-%Y %H:%M:%S', read_only=False, allow_null=True)

    class Meta:
        model = FrontTransfer
        fields = ['id', 'sender', 'sender_chat_id', 'object', 'work_type', 'block_section', 'floor', 'status',
                  'photo1', 'photo2', 'photo3', 'photo4', 'photo5', 'receiver', 'remarks', 'next_work_type',
                  'created_at', 'object_name', 'work_type_name', 'block_section_name', 'next_work_type_name',
                  'boss', 'photo_ids', 'approval_at']

    def get_object_name(self, obj):
        return obj.object.name

    def get_work_type_name(self, obj):
        return obj.work_type.name

    def get_block_section_name(self, obj):
        return obj.block_section.name

    def get_next_work_type_name(self, obj):
        return obj.next_work_type.name if obj.next_work_type else None


