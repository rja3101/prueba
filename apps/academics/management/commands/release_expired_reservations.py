from django.core.management.base import BaseCommand
from django.utils import timezone
from apps.academics.models import CapReservation, CartItem

class Command(BaseCommand):
    help = "Libera reservas y items de carrito expirados"

    def handle(self, *args, **options):
        now = timezone.now()
        res_del = CapReservation.objects.filter(reserved_until__lte=now).delete()[0]
        items_del = CartItem.objects.filter(reserved_until__lte=now).delete()[0]
        self.stdout.write(self.style.SUCCESS(
            f"Reservas liberadas={res_del}, items removidos={items_del}"
        ))
