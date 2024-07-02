from django.contrib import admin
from .models import User, Organization, WorkType, Object, BlockSection, FrontTransfer

class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'chat_id', 'full_name', 'is_authorized', 'organization')

class OrganizationsAdmin(admin.ModelAdmin):
    list_display = ('id', 'organization', 'is_general_contractor')

class FrontTransferAdmin(admin.ModelAdmin):
    list_display = ('id', 'sender', 'object', 'created_at', 'work_type')
class SectionAdmin(admin.ModelAdmin):
    list_display = ('object', 'name', 'number_of_floors')

admin.site.register(Organization, OrganizationsAdmin)
admin.site.register(User, UserAdmin)
admin.site.register(WorkType)
admin.site.register(Object)
admin.site.register(FrontTransfer, FrontTransferAdmin)
admin.site.register(BlockSection, SectionAdmin)