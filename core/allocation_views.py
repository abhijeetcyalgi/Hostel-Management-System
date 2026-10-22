"""Views for warden/admin room allocation."""
from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .allocation_services import (
    RoomUnavailableError, allocate_student_to_room, get_vacant_rooms,
)
from .models import Allocation, Room, Student, UserAccount
from .roles import get_account, role_required


@role_required(UserAccount.ROLE_WARDEN, UserAccount.ROLE_ADMIN)
@require_http_methods(["GET", "POST"])
def manage_allocations(request):
    account = get_account(request.user)
    hostel = account.hostel if account and account.role == UserAccount.ROLE_WARDEN else None
    vacant_rooms = get_vacant_rooms(hostel=hostel)
    active_students = Student.objects.filter(is_active=True)
    if hostel is not None:
        active_students = active_students.filter(hostel=hostel)

    if request.method == "POST":
        student_id = request.POST.get("student")
        room_id = request.POST.get("room")
        student = active_students.filter(pk=student_id).first()
        if student is None:
            messages.error(request, "Select a valid active student.")
        else:
            # Wardens must not allocate students into another hostel by tampering
            # with the submitted room ID.
            room_is_in_scope = hostel is None or Room.objects.filter(pk=room_id, hostel=hostel).exists()
            if not room_is_in_scope:
                messages.error(request, "Room unavailable")
            else:
                try:
                    allocate_student_to_room(
                        student=student, room_id=room_id,
                        allocated_by=account,
                    )
                except RoomUnavailableError:
                    messages.error(request, "Room unavailable")
                except Exception as exc:
                    # Validation errors are user-facing; unexpected errors should not be hidden.
                    from django.core.exceptions import ValidationError
                    if isinstance(exc, ValidationError):
                        messages.error(request, "; ".join(exc.messages))
                    else:
                        raise
                else:
                    messages.success(request, "Room allocated successfully.")
                    return redirect("allocation:manage")

        # Recompute after every POST so the displayed vacancy list is current.
        vacant_rooms = get_vacant_rooms(hostel=hostel)

    allocations = Allocation.objects.filter(status=Allocation.STATUS_ACTIVE).select_related(
        "student", "room", "room__hostel"
    ).order_by("room__hostel__name", "room__room_no")
    if hostel is not None:
        allocations = allocations.filter(room__hostel=hostel)
    return render(request, "core/allocation_manage.html", {
        "vacant_rooms": vacant_rooms,
        "students": active_students.order_by("full_name"),
        "allocations": allocations,
    })


@role_required(UserAccount.ROLE_STUDENT)
def my_room(request):
    account = get_account(request.user)
    allocation = Allocation.objects.filter(
        student__user_account=account, status=Allocation.STATUS_ACTIVE
    ).select_related("room", "room__hostel").first()
    return render(request, "core/my_room.html", {"allocation": allocation})
