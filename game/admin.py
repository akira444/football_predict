from django.contrib import admin
from .models import PlayerStatus, AvailableLeague, Game

# Register models
admin.site.register(PlayerStatus)
admin.site.register(AvailableLeague)
admin.site.register(Game)
