# Generated manually for Pro-only tier and AI assist counters

from django.db import migrations, models


def merge_legacy_tiers(apps, schema_editor):
    UserProfile = apps.get_model('profiles', 'UserProfile')
    UserProfile.objects.filter(
        pro_tier__in=['gold', 'platinum', 'diamond'],
    ).update(pro_tier='pro')


class Migration(migrations.Migration):
    dependencies = [
        ('profiles', '0004_userprofile_pro_started_at_userprofile_pro_tier_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='ai_assist_date',
            field=models.DateField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='ai_assist_count',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.RunPython(merge_legacy_tiers, migrations.RunPython.noop),
        migrations.AlterField(
            model_name='userprofile',
            name='pro_tier',
            field=models.CharField(
                blank=True,
                choices=[('', 'Free'), ('pro', 'Pro')],
                default='',
                max_length=16,
            ),
        ),
    ]
