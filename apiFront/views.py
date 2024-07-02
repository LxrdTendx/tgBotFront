from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from .models import User, Organization, WorkType, Object, BlockSection, FrontTransfer
from .serializers import UserSerializer, OrganizationSerializer, WorkTypeSerializer, ObjectSerializer, BlockSectionSerializer, FrontTransferSerializer
import logging

logger = logging.getLogger(__name__)

class OrganizationViewSet(viewsets.ViewSet):
    def list(self, request):
        organizations = Organization.objects.filter(is_general_contractor=False)
        serializer = OrganizationSerializer(organizations, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            organization = Organization.objects.get(pk=pk)
            serializer = OrganizationSerializer(organization)
            return Response(serializer.data)
        except Organization.DoesNotExist:
            return Response(status=404)

class UserViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None):
        try:
            user = User.objects.get(chat_id=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(status=404)

    def retrieve_by_id(self, request, pk=None):
        try:
            user = User.objects.get(pk=pk)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        except User.DoesNotExist:
            return Response(status=404)

    def create(self, request):
        logger.info(f"Получены данные для создания пользователя: {request.data}")
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=201)
        logger.error(f"Ошибки валидации: {serializer.errors}")
        return Response(serializer.errors, status=400)

    def update(self, request, pk=None):
        try:
            user = User.objects.get(chat_id=pk)
            serializer = UserSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)
        except User.DoesNotExist:
            return Response(status=404)

    def list(self, request):
        organization = request.query_params.get('organization')
        if organization:
            users = User.objects.filter(organization=organization)
        else:
            users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)

class WorkTypeViewSet(viewsets.ViewSet):
    def list(self, request):
        work_types = WorkType.objects.all()
        serializer = WorkTypeSerializer(work_types, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            work_type = WorkType.objects.get(pk=pk)
            serializer = WorkTypeSerializer(work_type)
            return Response(serializer.data)
        except WorkType.DoesNotExist:
            return Response(status=404)

class ObjectViewSet(viewsets.ViewSet):
    def list(self, request):
        objects = Object.objects.all()
        serializer = ObjectSerializer(objects, many=True)
        return Response(serializer.data)

    def retrieve(self, request, pk=None):
        try:
            obj = Object.objects.get(pk=pk)
            serializer = ObjectSerializer(obj)
            return Response(serializer.data)
        except Object.DoesNotExist:
            return Response(status=404)

    def block_sections(self, request, pk=None):
        try:
            obj = Object.objects.get(pk=pk)
            block_sections = obj.block_sections.all()
            serializer = BlockSectionSerializer(block_sections, many=True)
            return Response(serializer.data)
        except Object.DoesNotExist:
            return Response(status=404)

class BlockSectionViewSet(viewsets.ViewSet):
    def retrieve(self, request, pk=None):
        try:
            block_section = BlockSection.objects.get(pk=pk)
            serializer = BlockSectionSerializer(block_section)
            return Response(serializer.data)
        except BlockSection.DoesNotExist:
            return Response(status=404)

class FrontTransferViewSet(viewsets.ViewSet):
    def create(self, request):
        logger.info(f"Получены данные для создания передачи фронта: {request.data}")
        serializer = FrontTransferSerializer(data=request.data)
        if serializer.is_valid():
            transfer = serializer.save()
            return Response(FrontTransferSerializer(transfer).data, status=201)
        logger.error(f"Ошибки валидации: {serializer.errors}")
        return Response(serializer.errors, status=400)

    def update(self, request, pk=None):
        try:
            transfer = FrontTransfer.objects.get(pk=pk)
            logger.info(f"Получены данные для обновления передачи фронта: {request.data}")
            serializer = FrontTransferSerializer(transfer, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            logger.error(f"Ошибки валидации: {serializer.errors}")
            return Response(serializer.errors, status=400)
        except FrontTransfer.DoesNotExist:
            return Response(status=404)

    def retrieve(self, request, pk=None):
        try:
            transfer = FrontTransfer.objects.get(pk=pk)
            serializer = FrontTransferSerializer(transfer)
            return Response(serializer.data)
        except FrontTransfer.DoesNotExist:
            return Response(status=404)

    def list(self, request):
        status_filter = request.query_params.get('status')
        if status_filter:
            transfers = FrontTransfer.objects.filter(status=status_filter)
        else:
            transfers = FrontTransfer.objects.all()
        serializer = FrontTransferSerializer(transfers, many=True)
        return Response(serializer.data)