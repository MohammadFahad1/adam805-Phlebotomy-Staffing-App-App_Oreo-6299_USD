from django.contrib import admin
from django.contrib.auth.models import Group
from authentication.models import User, Phlebotomist, Phlebotomist_skill, Phlebotomist_document, PhlebotomistAvailability

admin.site.unregister(Group)
admin.site.register(User)
admin.site.register(Phlebotomist)
admin.site.register(Phlebotomist_skill)
admin.site.register(Phlebotomist_document)
admin.site.register(PhlebotomistAvailability)
