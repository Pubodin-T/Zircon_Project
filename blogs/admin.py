from django.contrib import admin
from .models import Drop_sim
from .models import Launch_site
# Register your models here.

# admin ID
# username = zircon
# password = admin
admin.site.register(Drop_sim)
admin.site.register(Launch_site)