from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_externalprofilesnapshot'),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name='reviewqueueitem',
            name='review_queue_items_item_type_valid',
        ),
        migrations.AddConstraint(
            model_name='reviewqueueitem',
            constraint=models.CheckConstraint(
                condition=models.Q(
                    item_type__in=[
                        'duplicate_contact',
                        'unknown_tier',
                        'conflicting_membership',
                        'missing_email',
                        'multiple_stripe_customers',
                        'price_anomaly',
                        'sync_error',
                        'unknown_whatsapp_identity',
                        'alias_conflict',
                        'profile_link_review',
                    ]
                ),
                name='review_queue_items_item_type_valid',
            ),
        ),
    ]
