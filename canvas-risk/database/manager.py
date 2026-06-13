from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from config.settings import settings
from database.models import Base, Student, Assignment, Submission
from api.canvas_client import CanvasClient
from datetime import datetime
from analytics.risk_engine import RiskEngine
import logging

class DatabaseManager:
    def __init__(self):
        self.engine = create_engine(settings.DATABASE_URL)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_session(self):
        return self.Session()

    def sync_from_canvas(self):
        client = CanvasClient()
        session = self.get_session()

        # 0. Sync Course
        c_data = client.get_course()
        from database.models import Course, AssignmentGroup # Import here if needed, but they are already in models.py
        course = session.query(Course).filter_by(canvas_id=c_data['id']).first()
        if not course:
            course = Course(canvas_id=c_data['id'])
            session.add(course)
        course.name = c_data.get('name')
        course.course_code = c_data.get('course_code')
        # term is often nested or separate, skipping for now or adding if available
        session.commit()

        # 1. Sync Assignment Groups
        groups_data = client.get_assignment_groups()
        for g_data in groups_data:
            group = session.query(AssignmentGroup).filter_by(canvas_id=g_data['id']).first()
            if not group:
                group = AssignmentGroup(canvas_id=g_data['id'])
                session.add(group)
            group.name = g_data.get('name')
            group.group_weight = g_data.get('group_weight')
        session.commit()

        # 2. Sync Students
        students_data = client.get_students()
        for s_data in students_data:
            student = session.query(Student).filter_by(canvas_id=s_data['id']).first()
            if not student:
                student = Student(canvas_id=s_data['id'])
                session.add(student)
            
            student.name = s_data.get('name')
            student.email = s_data.get('email')
            enrollments = s_data.get('enrollments', [])
            if enrollments:
                grades_data = enrollments[0].get('grades', {})
                student.current_score = grades_data.get('current_score')
            student.last_sync = datetime.utcnow()
        session.commit()

        # 3. Sync Assignments
        assignments_data = client.get_assignments()
        for a_data in assignments_data:
            assignment = session.query(Assignment).filter_by(canvas_id=a_data['id']).first()
            if not assignment:
                assignment = Assignment(canvas_id=a_data['id'])
                session.add(assignment)
            
            assignment.name = a_data.get('name')
            assignment.points_possible = a_data.get('points_possible')
            due_at_str = a_data.get('due_at')
            if due_at_str:
                assignment.due_at = datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))
            
            group_canvas_id = a_data.get('assignment_group_id')
            if group_canvas_id:
                group = session.query(AssignmentGroup).filter_by(canvas_id=group_canvas_id).first()
                if group:
                    assignment.assignment_group_id = group.id
        session.commit()

        # 4. Sync All Submissions (Optimized Batch Sync)
        all_subs_data = client.get_all_submissions()
        for sub_data in all_subs_data:
            sub = session.query(Submission).filter_by(canvas_id=sub_data['id']).first()
            if not sub:
                sub = Submission(canvas_id=sub_data['id'])
                session.add(sub)
            
            student = session.query(Student).filter_by(canvas_id=sub_data['user_id']).first()
            assignment = session.query(Assignment).filter_by(canvas_id=sub_data['assignment_id']).first()
            
            if student and assignment:
                sub.student_id = student.id
                sub.assignment_id = assignment.id
                
                sub.grade = sub_data.get('grade')
                sub.score = sub_data.get('score')
                sub.workflow_state = sub_data.get('workflow_state')
                sub.late = bool(sub_data.get('late', False))
                sub.missing = bool(sub_data.get('missing', False))
                sub.excused = bool(sub_data.get('excused', False))
                
                sub_at_str = sub_data.get('submitted_at')
                if sub_at_str:
                    sub.submitted_at = datetime.fromisoformat(sub_at_str.replace('Z', '+00:00'))
                
                graded_at_str = sub_data.get('graded_at')
                if graded_at_str:
                    sub.graded_at = datetime.fromisoformat(graded_at_str.replace('Z', '+00:00'))

        session.commit()
        
        # Record analytics snapshot after sync
        try:
            RiskEngine.record_risk_snapshot(session)
        except Exception as e:
            logging.error(f"Error recording risk snapshot: {e}")
            
        session.close()
