from django.db import migrations


def set_instructor_code(apps, schema_editor):
    TestCase = apps.get_model("editor", "TestCase")
    for testcase in TestCase.objects.all():
        if testcase.instructor_code is None:
            testcase.instructor_code = ""
            testcase.save()


class Migration(migrations.Migration):
    dependencies = [
        ('editor', '0008_alter_testcase_instructor_code_and_more'),  # replace with the actual previous migration name
    ]

    operations = [
        migrations.RunPython(set_instructor_code),
    ]
