from datetime import datetime, timedelta, time
from app import db
from app.models.radiology_models import Patient, Appointment

MAX_PATIENTS_PER_DAY = 25
START_HOUR = 8
END_HOUR = 15
SLOT_MINUTES = 15


def generate_patient_number():
    year = datetime.now().year
    count = Patient.query.count() + 1
    return f"RAD-{year}-{count:05d}"


def is_weekend(date_obj):
    return date_obj.weekday() >= 5  # 5=samedi, 6=dimanche


def get_next_working_day(date_obj):
    next_day = date_obj
    while is_weekend(next_day):
        next_day += timedelta(days=1)
    return next_day


def generate_daily_slots(target_date):
    slots = []
    current = datetime.combine(target_date, time(START_HOUR, 0))
    end_time = datetime.combine(target_date, time(END_HOUR, 0))

    while current < end_time and len(slots) < MAX_PATIENTS_PER_DAY:
        slots.append(current)
        current += timedelta(minutes=SLOT_MINUTES)

    return slots


def get_next_available_appointment():
    current_date = datetime.now().date()

    while True:
        current_date = get_next_working_day(current_date)

        existing = Appointment.query.filter(
            db.func.date(Appointment.appointment_datetime) == current_date
        ).count()

        if existing < MAX_PATIENTS_PER_DAY:
            booked_slots = {
                appt.appointment_datetime
                for appt in Appointment.query.filter(
                    db.func.date(Appointment.appointment_datetime) == current_date
                ).all()
            }

            for slot in generate_daily_slots(current_date):
                if slot not in booked_slots:
                    return slot

        current_date += timedelta(days=1)