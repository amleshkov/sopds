from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('opds_catalog', '0005_auto_20161204_2138'),
    ]

    operations = [
        migrations.RenameModel(old_name='bauthor', new_name='BookAuthor'),
        migrations.RenameModel(old_name='bgenre', new_name='BookGenre'),
        migrations.RenameModel(old_name='bseries', new_name='BookSeries'),
    ]
