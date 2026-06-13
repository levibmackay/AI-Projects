import unittest
from utils.feedback_generator import FeedbackGenerator
from unittest.mock import MagicMock

class TestFeedbackGenerator(unittest.TestCase):
    def test_generate_draft_high_score(self):
        submission = MagicMock()
        submission.student.name = "John Doe"
        submission.assignment.name = "Project 1"
        submission.assignment.points_possible = 100
        submission.score = 95
        submission.late = False
        
        draft = FeedbackGenerator.generate_draft(submission)
        self.assertIn("Excellent work", draft)
        self.assertIn("John", draft)

    def test_generate_draft_low_score_late(self):
        submission = MagicMock()
        submission.student.name = "Jane Smith"
        submission.assignment.name = "Quiz 1"
        submission.assignment.points_possible = 10
        submission.score = 5
        submission.late = True
        
        draft = FeedbackGenerator.generate_draft(submission)
        self.assertIn("marked late", draft)
        self.assertIn("struggling with some of the core concepts", draft)

if __name__ == '__main__':
    unittest.main()
