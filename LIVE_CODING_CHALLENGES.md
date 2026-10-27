# Live Coding Challenges

## Overview

Live Coding Challenges is a new feature that enables learners to practice coding skills directly within the study workspace. Each phase can have multiple challenges with auto-grading, test cases, and a leaderboard.

## Features

### Challenge Types
- **Easy**: Beginner-level problems (10 points)
- **Medium**: Intermediate problems (15 points)
- **Hard**: Advanced problems (20+ points)

### Supported Languages
- Python
- JavaScript
- Java
- C++
- C#
- SQL
- Go
- Rust

### Challenge Components
1. **Problem Description** - Clear problem statement
2. **Starter Code** - Template code to get started
3. **Test Cases** - Multiple test cases for validation
4. **Auto-Grading** - Automatic test execution and scoring
5. **Leaderboard** - Track top performers in each phase

## Architecture

### Backend Models

#### CodeChallenge
```python
- path_id: str (links to learning path)
- phase_idx: int (phase number)
- title: str (challenge title)
- description: str (problem statement)
- difficulty: str (easy/medium/hard)
- language: str (programming language)
- starter_code: str (template code)
- solution_code: str (reference solution)
- test_cases: list (test case objects)
- points: int (points awarded)
```

#### CodeSubmission
```python
- user: FK (learner)
- challenge: FK (code challenge)
- code: str (submitted code)
- status: str (draft/submitted/passed/failed)
- test_results: list (test execution results)
- passed_tests: int (number of passing tests)
- total_tests: int (total test count)
- score: int (points earned)
- submitted_at: datetime (submission timestamp)
```

### API Endpoints

#### List Challenges
```
GET /api/paths/{doc_id}/phases/{phase_idx}/challenges
```
Returns all challenges for a phase with user's submission status.

#### Get Challenge Details
```
GET /api/challenges/{challenge_id}
```
Returns challenge details and user's current submission (if any).

#### Run Tests (Draft)
```
POST /api/challenges/{challenge_id}/run
Body: { "code": "..." }
```
Executes code against test cases without submitting. Returns test results.

#### Submit Challenge
```
POST /api/challenges/{challenge_id}/submit
```
Finalizes submission. If all tests pass, marks as "passed" and awards points.

#### Get Leaderboard
```
GET /api/paths/{doc_id}/phases/{phase_idx}/leaderboard
```
Returns top 100 performers for a phase.

## Frontend Components

### CodeChallengePanel
Main component for the code challenge interface.

**Props:**
- `pathId`: str (learning path ID)
- `phaseIdx`: int (phase index)
- `phaseTitle`: str (phase name)

**Features:**
- Challenge list with difficulty badges
- Code editor with syntax highlighting
- Run/Submit buttons
- Test results display
- Leaderboard view

## Usage

### For Learners

1. **View Challenges**
   - Navigate to Study workspace
   - Select a phase
   - Scroll to "Code Challenges" section
   - See all available challenges

2. **Solve a Challenge**
   - Click on a challenge to open it
   - Read the problem description
   - Write code in the editor
   - Click "Run Tests" to check your solution
   - Fix any failing tests
   - Click "Submit" when all tests pass

3. **Track Progress**
   - Green checkmark indicates passed challenges
   - Points are awarded for each passed challenge
   - View leaderboard to see how you rank

### For Instructors

1. **Create Challenges**
   ```python
   from api.models import CodeChallenge
   
   challenge = CodeChallenge.objects.create(
       path_id="my_path_123",
       phase_idx=0,
       title="Sum Two Numbers",
       description="Write a function that adds two numbers",
       difficulty="easy",
       language="python",
       starter_code="def add(a, b):\n    pass",
       solution_code="def add(a, b):\n    return a + b",
       test_cases=[
           {"input": "2\n3", "output": "5"},
           {"input": "10\n20", "output": "30"},
       ],
       points=10,
   )
   ```

2. **Seed Sample Challenges**
   ```bash
   python manage.py seed_code_challenges
   ```

## Execution Engine

### Judge0 Integration

The system uses Judge0 API for code execution:
- Supports 90+ programming languages
- Sandboxed execution environment
- Configurable time/memory limits
- Real-time compilation and execution

### Configuration

Set in `.env`:
```
JUDGE0_API_KEY=your_rapidapi_key
JUDGE0_API_URL=https://judge0-ce.p.rapidapi.com
```

Get API key from: https://rapidapi.com/judge0-official/api/judge0-ce

### Execution Flow

1. User submits code
2. System sends to Judge0 API
3. Judge0 compiles and runs code
4. Results returned (stdout, stderr, execution time)
5. System compares output with expected output
6. Test marked as passed/failed

## Scoring

### Points Calculation
- **Easy**: 10 points per challenge
- **Medium**: 15 points per challenge
- **Hard**: 20+ points per challenge

### Partial Credit
- If some tests pass: `(passed_tests / total_tests) * points * 0.5`
- If all tests pass: full points awarded

### Leaderboard Ranking
- Ranked by total points in phase
- Ties broken by submission time (earlier is better)

## Security

### Code Execution Safety
- Sandboxed execution environment (Judge0)
- Time limits (default 5 seconds)
- Memory limits (default 256MB)
- No access to file system or network

### Input Validation
- Code size limit: 50KB
- Test case limit: 20 per challenge
- Language validation
- Challenge ownership verification

## Performance

### Optimization
- Test results cached in database
- Leaderboard limited to top 100
- Lazy loading of challenge details
- Async execution via Judge0

### Limits
- Max 20 test cases per challenge
- Max 5 second execution time
- Max 256MB memory usage
- Max 50KB code submission

## Future Enhancements

1. **Collaborative Coding**
   - Pair programming mode
   - Real-time code sharing
   - Peer code review

2. **Advanced Features**
   - Custom test case creation
   - Code templates by language
   - Syntax highlighting
   - Code formatting

3. **Analytics**
   - Time spent per challenge
   - Attempt history
   - Common mistakes
   - Performance trends

4. **Gamification**
   - Achievement badges
   - Streak tracking
   - Challenge difficulty progression
   - Seasonal competitions

## Troubleshooting

### Judge0 API Issues
- Verify API key is set in `.env`
- Check RapidAPI account has active subscription
- Ensure rate limits not exceeded

### Code Execution Errors
- Check code syntax
- Verify input/output format
- Review test case expectations
- Check time/memory limits

### Submission Issues
- Ensure all tests pass before submitting
- Check challenge hasn't been deleted
- Verify user is authenticated

## Examples

### Python Challenge
```python
# Challenge: Sum of Two Numbers
# Description: Write a function that returns the sum of two numbers

def sum_numbers(a, b):
    return a + b

# Test Cases:
# Input: 2, 3 → Output: 5
# Input: 10, 20 → Output: 30
# Input: -5, 5 → Output: 0
```

### JavaScript Challenge
```javascript
// Challenge: Reverse a String
// Description: Write a function that reverses a string

function reverseString(s) {
    return s.split('').reverse().join('');
}

// Test Cases:
// Input: "hello" → Output: "olleh"
// Input: "python" → Output: "nohtyp"
```

## References

- Judge0 API: https://judge0.com/
- RapidAPI: https://rapidapi.com/
- Supported Languages: https://judge0.com/languages

---

**Status**: Production Ready ✅
**Last Updated**: 2024
**Version**: 1.0
