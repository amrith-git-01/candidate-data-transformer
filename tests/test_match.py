from src.match.identity import group_records
from src.models import FieldValue, RawRecord


def _rec(source, name, email=None, phone=None):
    fields = {"full_name": FieldValue(value=name, method="direct")}
    if email:
        fields["email"] = FieldValue(value=email, method="direct")
    if phone:
        fields["phone"] = FieldValue(value=phone, method="direct")
    return RawRecord(source=source, fields=fields)


def test_group_by_email():
    records = [
        _rec("csv", "Linus Torvalds", "linus.torvalds@example.com"),
        _rec("ats", "Linus Torvalds", "linus.torvalds@example.com"),
    ]
    groups = group_records(records)
    assert len(groups) == 1
    assert groups[0].matched_by == "email"


def test_group_by_phone_when_shared_phone():
    records = [
        _rec("csv", "Sindre Sorhus", phone="+1-650-555-0103"),
        _rec("ats", "Sindre Sorhus", phone="+1-650-555-0103"),
    ]
    groups = group_records(records)
    assert len(groups) == 1
    assert groups[0].matched_by == "phone"


def test_disjoint_email_and_phone_stay_separate_groups():
    """CSV email-only and ATS phone-only are not joined without a shared email/phone."""
    records = [
        _rec("csv", "Sindre Sorhus", "sindre@example.com"),
        _rec("ats", "Sindre Sorhus", phone="+1-650-555-0103"),
    ]
    groups = group_records(records)
    assert len(groups) == 2
    assert all(len(g.records) == 1 for g in groups)


def test_email_typo_stays_separate_groups():
    records = [
        _rec("csv", "Ryan Carniato", "ryan.carniato@example.com"),
        _rec("ats", "Ryan Carniato", "ryan.carniatto@example.com"),
    ]
    groups = group_records(records)
    assert len(groups) == 2


def test_singleton_stays_own_group():
    records = [_rec("csv", "Addy Osmani", "addy.osmani@example.com")]
    groups = group_records(records)
    assert len(groups) == 1
    assert len(groups[0].records) == 1


def test_two_people_stay_separate():
    records = [
        _rec("csv", "Linus Torvalds", "linus.torvalds@example.com"),
        _rec("csv", "Dan Abramov", "dan.abramov@example.com"),
    ]
    groups = group_records(records)
    assert len(groups) == 2
