# Generated migration for CodeChallenge and CodeSubmission models

from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0009_portfolio_cohort'),
    ]

    operations = [
        migrations.CreateModel(
            name='CodeChallenge',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('path_id', models.CharField(db_index=True, max_length=100)),
                ('phase_idx', models.IntegerField(default=0)),
                ('phase_title', models.CharField(blank=True, default='', max_length=255)),
                ('title', models.CharField(max_length=255)),
                ('description', models.TextField()),
                ('difficulty', models.CharField(choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')], default='medium', max_length=16)),
                ('language', models.CharField(choices=[('python', 'Python'), ('javascript', 'JavaScript'), ('java', 'Java'), ('cpp', 'C++'), ('csharp', 'C#'), ('sql', 'SQL'), ('go', 'Go'), ('rust', 'Rust')], default='python', max_length=16)),
                ('starter_code', models.TextField()),
                ('solution_code', models.TextField()),
                ('test_cases', models.JSONField(default=list)),
                ('time_limit_seconds', models.IntegerField(default=5)),
                ('memory_limit_mb', models.IntegerField(default=256)),
                ('points', models.IntegerField(default=10)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'unique_together': {('path_id', 'phase_idx', 'title')},
                'indexes': [models.Index(fields=['path_id', 'phase_idx'], name='api_codecha_path_id_phase_idx_idx')],
            },
        ),
        migrations.CreateModel(
            name='CodeSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.TextField()),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('submitted', 'Submitted'), ('passed', 'Passed'), ('failed', 'Failed')], default='draft', max_length=16)),
                ('test_results', models.JSONField(blank=True, default=list)),
                ('passed_tests', models.IntegerField(default=0)),
                ('total_tests', models.IntegerField(default=0)),
                ('score', models.IntegerField(default=0)),
                ('execution_time_ms', models.IntegerField(blank=True, null=True)),
                ('error_message', models.TextField(blank=True, default='')),
                ('submitted_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('challenge', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='submissions', to='api.codechallenge')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='code_submissions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'unique_together': {('user', 'challenge')},
                'indexes': [models.Index(fields=['user', 'status'], name='api_codesub_user_id_status_idx'), models.Index(fields=['challenge', 'status'], name='api_codesub_challenge_id_status_idx')],
            },
        ),
    ]
