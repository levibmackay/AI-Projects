import unittest
from analytics.risk_engine import RiskEngine
from database.models import Base, Student, Submission, Assignment
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

class TestRiskEngine(unittest.TestCase):
    def setUp(self):
        # Use in-memory SQLite for testing DB interactions
        self.engine = create_engine('sqlite:///:memory:')
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.session = self.Session()

    def tearDown(self):
        self.session.close()

    def test_get_letter_grade(self):
        self.assertEqual(RiskEngine.get_letter_grade(95), "A")
        self.assertEqual(RiskEngine.get_letter_grade(85), "B")
        self.assertEqual(RiskEngine.get_letter_grade(75), "C")
        self.assertEqual(RiskEngine.get_letter_grade(65), "D")
        self.assertEqual(RiskEngine.get_letter_grade(55), "F")
        self.assertEqual(RiskEngine.get_letter_grade(None), "N/A")

    def test_categorize_student(self):
        risk_data = {
            'failure_probability': 5,
            'missing_count': 0,
            'inactivity_score': 10,
            'grade_risk': 10,
            'trend_score': 10,
            'late_count': 0
        }
        self.assertEqual(RiskEngine.categorize_student(risk_data), "🌟 High Achiever")
        
        risk_data['failure_probability'] = 80
        self.assertEqual(RiskEngine.categorize_student(risk_data), "⚠️ High Risk")

    def test_get_ungraded_work_logic(self):
        # 1. Setup Student
        student = Student(name="Test Student", canvas_id=1)
        self.session.add(student)
        
        # 2. Setup Assignments
        team_act = Assignment(name="Team Activity 1", points_possible=10, canvas_id=101)
        hw = Assignment(name="Homework", points_possible=10, canvas_id=102)
        self.session.add_all([team_act, hw])
        self.session.commit()

        # 3. Create Submissions
        # Case A: Graded Team Activity (9/10) - Should NOT be in ungraded
        sub_a = Submission(student_id=student.id, assignment_id=team_act.id, score=9.0, workflow_state='graded', canvas_id=201)
        
        # Case B: Graded Homework (0/10) - SHOULD be in ungraded (user wants 0s)
        sub_b = Submission(student_id=student.id, assignment_id=hw.id, score=0.0, workflow_state='graded', canvas_id=202)
        
        # Case C: Unsubmitted - Should NOT be in ungraded
        sub_c = Submission(student_id=student.id, assignment_id=hw.id, score=None, workflow_state='unsubmitted', canvas_id=203)
        
        # Case D: Submitted but no score - SHOULD be in ungraded
        sub_d = Submission(student_id=student.id, assignment_id=hw.id, score=None, workflow_state='submitted', canvas_id=204)

        self.session.add_all([sub_a, sub_b, sub_c, sub_d])
        self.session.commit()

        ungraded = RiskEngine.get_ungraded_work(self.session)
        ids = [s.canvas_id for s in ungraded]
        
        self.assertIn(202, ids, "Graded 0 should be in ungraded list")
        self.assertIn(204, ids, "Submitted without score should be in ungraded list")
        self.assertNotIn(201, ids, "Graded Team Activity (not 100) should NOT be in ungraded list")
        self.assertNotIn(203, ids, "Unsubmitted work should NOT be in ungraded list")

if __name__ == '__main__':
    unittest.main()
