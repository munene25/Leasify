from django.db import models

class Block(models.TextChoices):
    A = "block A" "Block A"
    B = "block B", "Block B"
    C = "block C", "Block C"
    D = "block D", "Block D"

class Wing(models.TextChoices):
    NORTH = "north", "North wing"
    SOUTH = "south", "South wing"
    EAST = "east", "East wing"
    WEST = "west", "West wing"