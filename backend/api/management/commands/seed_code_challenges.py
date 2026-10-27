from django.core.management.base import BaseCommand
from api.models import CodeChallenge


class Command(BaseCommand):
    help = 'Seed sample code challenges for testing'

    def handle(self, *args, **options):
        challenges = [
            {
                'path_id': 'sample_path_1',
                'phase_idx': 0,
                'phase_title': 'Python Basics',
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
                'path_id': 'sample_path_1',
                'phase_idx': 0,
                'phase_title': 'Python Basics',
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
            {
                'path_id': 'sample_path_1',
                'phase_idx': 1,
                'phase_title': 'Data Structures',
                'title': 'Find Maximum in Array',
                'description': 'Write a function that finds the maximum value in an array.',
                'difficulty': 'medium',
                'language': 'python',
                'starter_code': 'def find_max(arr):\n    # Your code here\n    pass',
                'solution_code': 'def find_max(arr):\n    return max(arr) if arr else None',
                'test_cases': [
                    {'input': '[1, 5, 3, 9, 2]', 'output': '9'},
                    {'input': '[10]', 'output': '10'},
                    {'input': '[-5, -1, -10]', 'output': '-1'},
                ],
                'points': 15,
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
            self.style.SUCCESS(f'\nSuccessfully created {created} code challenges')
        )
