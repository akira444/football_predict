from django.contrib import admin
from .models import PlayerStatus, AvailableLeague

# Register models
admin.site.register(PlayerStatus)
admin.site.register(AvailableLeague)
