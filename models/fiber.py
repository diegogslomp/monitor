from django.db import models
from .host import Host


class Dio(models.Model):
    """DIO Bastidor Optico"""

    pop = models.ForeignKey(Host, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)

    def __str__(self):
        return self.name


class Fiber(models.Model):
    """Portas/Fibras dos DIO"""

    dio = models.ForeignKey(Dio, on_delete=models.CASCADE)
    number = models.CharField(max_length=20)
    port = models.CharField(max_length=20, blank=True, default="")
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.number
