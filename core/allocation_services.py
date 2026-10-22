"""Business rules for room allocation (FR-04.06, FR-04.10)."""
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import Allocation, Room


class RoomUnavailableError(ValidationError):
    """Raised when a room is inactive or has no remaining capacity."""


class NoVacantRoomsError(ValidationError):
    """Raised when no active room has remaining capacity."""


def get_vacant_rooms(*, hostel=None, room_type=None):
    """Return active rooms with capacity, optionally filtered by hostel/type."""
    rooms = Room.objects.filter(is_active=True).select_related("hostel")
    if hostel is not None:
        rooms = rooms.filter(hostel=hostel)
    if room_type:
        rooms = rooms.filter(room_type=room_type)
    return [room for room in rooms.order_by("hostel__name", "block", "room_no")
            if room.vacancies > 0]


@transaction.atomic
def allocate_student_to_room(*, student, room_id, allocated_by=None, allocated_on=None):
    """Allocate a student only when both the student and room are eligible."""
    room = Room.objects.select_for_update().select_related("hostel").filter(pk=room_id).first()
    if room is None or not room.is_active or room.vacancies <= 0:
        raise RoomUnavailableError("Room unavailable")

    if not student.is_active:
        raise ValidationError("Inactive students cannot be allocated a room")
    if Allocation.objects.filter(student=student, status=Allocation.STATUS_ACTIVE).exists():
        raise ValidationError("Student already has an active room allocation")

    try:
        return Allocation.objects.create(
            student=student,
            room=room,
            allocated_by=allocated_by,
            allocated_on=allocated_on or timezone.localdate(),
            status=Allocation.STATUS_ACTIVE,
        )
    except IntegrityError as exc:
        # The database constraint remains the final guard against duplicate active allocations.
        raise RoomUnavailableError("Room unavailable or student already allocated") from exc
