from django.db import models


# Create your models here.
class Setting(models.Model):
    """Model for settings of Smart Home (target temperatures)"""
    controller_name = models.CharField(max_length=40, unique=True)
    label = models.CharField(max_length=100)  # The same as controller_name
    value = models.IntegerField(default=20)
