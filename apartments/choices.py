from django.db import models

class Block(models.TextChoices):
    A = "A" "Block A"
    B = "B", "Block B"
    C = "C", "Block C"
    D = "D", "Block D"

class Wing(models.TextChoices):
    NORTH = "north", "North wing"
    SOUTH = "south", "South wing"
    EAST = "east", "East wing"
    WEST = "west", "West wing"