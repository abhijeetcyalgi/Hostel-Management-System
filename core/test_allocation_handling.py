from datetime import date

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Allocation, Hostel, Room, Student, UserAccount


class AllocationHandlingTests(TestCase):
    def setUp(self):
        self.hostel = Hostel.objects.create(name="North Hostel", code="NH")
        self.warden_user = get_user_model().objects.create_user(username="warden", password="test-pass")
        self.warden = UserAccount.objects.create(user=self.warden_user, role=UserAccount.ROLE_WARDEN, hostel=self.hostel)
        self.student_user = get_user_model().objects.create_user(username="student", password="test-pass")
        self.student_account = UserAccount.objects.create(user=self.student_user, hostel=self.hostel)
        self.student = Student.objects.create(user_account=self.student_account, hostel=self.hostel, roll_no="S001", full_name="Test Student")
        self.room = Room.objects.create(hostel=self.hostel, room_no="B-204", block="B", capacity=1)
        self.client.force_login(self.warden_user)

    def test_full_room_rejected_and_list_refreshed(self):
        other_user = get_user_model().objects.create_user(username="other", password="test-pass")
        other_account = UserAccount.objects.create(user=other_user, hostel=self.hostel)
        other_student = Student.objects.create(user_account=other_account, hostel=self.hostel, roll_no="S002", full_name="Other Student")
        Allocation.objects.create(student=other_student, room=self.room, allocated_on=date.today())
        response = self.client.post(reverse("allocation:manage"), {"student": self.student.pk, "room": self.room.pk}, follow=True)
        self.assertContains(response, "Room unavailable")
        self.assertContains(response, "Room unavailable")
        self.assertFalse(Allocation.objects.filter(student=self.student, status=Allocation.STATUS_ACTIVE).exists())

    def test_no_vacant_rooms_message(self):
        other_user = get_user_model().objects.create_user(username="other", password="test-pass")
        other_account = UserAccount.objects.create(user=other_user, hostel=self.hostel)
        other_student = Student.objects.create(user_account=other_account, hostel=self.hostel, roll_no="S002", full_name="Other Student")
        Allocation.objects.create(student=other_student, room=self.room, allocated_on=date.today())
        response = self.client.get(reverse("allocation:manage"))
        self.assertContains(response, "No vacant rooms available")
        self.assertEqual(response.status_code, 200)

    def test_vacancy_list_updates_after_successful_allocation(self):
        response = self.client.post(reverse("allocation:manage"), {"student": self.student.pk, "room": self.room.pk}, follow=True)
        self.assertContains(response, "Room allocated successfully.")
        self.assertContains(response, "No vacant rooms available")
        self.assertEqual(Allocation.objects.filter(student=self.student, status=Allocation.STATUS_ACTIVE).count(), 1)
