from django.core.management.base import BaseCommand
from api.models import CodeChallenge


class Command(BaseCommand):
    help = 'Seed code challenges for a specific path'

    def add_arguments(self, parser):
        parser.add_argument('path_id', type=str, help='Path ID to seed challenges for')

    def handle(self, *args, **options):
        path_id = options['path_id']
        
        challenges = [
            {
                'path_id': path_id,
                'phase_idx': 0,
                'phase_title': 'Basics',
                'title': 'Sum of Two Numbers',
                'description': 'Write a function that takes two numbers and returns their sum.',
                'difficulty': 'easy',
                'language': 'python',
                'starter_code': 'def sum_numbers(a, b):\n    # Your code here\n    pass',
                'solution_code': 'def sum_numbers(a, b):\n    return a + b',
                'test_cases': [
                    {'input': '2\n3', 'output': '5'},
                    {'input': '10\n20', 'output': '30'},
                    {'input': '-5\n5', 'output': '0'},
                ],
                'points': 10,
            },
            {
                'path_id': path_id,
                'phase_idx': 0,
                'phase_title': 'Basics',
                'title': 'Reverse a String',
                'description': 'Write a function that reverses a string.',
                'difficulty': 'easy',
                'language': 'python',
                'starter_code': 'def reverse_string(s):\n    # Your code here\n    pass',
                'solution_code': 'def reverse_string(s):\n    return s[::-1]',
                'test_cases': [
                    {'input': 'hello', 'output': 'olleh'},
                    {'input': 'python', 'output': 'nohtyp'},
                    {'input': 'a', 'output': 'a'},
                ],
                'points': 10,
            },
        ]

        created = 0
        for challenge_data in challenges:
            try:
                challenge, created_flag = CodeChallenge.objects.get_or_create(
                    path_id=challenge_data['path_id'],
                    phase_idx=challenge_data['phase_idx'],
                    title=challenge_data['title'],
                    defaults=challenge_data,
                )
                if created_flag:
                    created += 1
                    self.stdout.write(
                        self.style.SUCCESS(f'Created challenge: {challenge.title}')
                    )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'Challenge already exists: {challenge.title}')
                    )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Error creating challenge: {str(e)}')
                )

        self.stdout.write(
            self.style.SUCCESS(f'\nSuccessfully created {created} code challenges for path: {path_id}')
        )
