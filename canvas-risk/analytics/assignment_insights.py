from sqlalchemy import func
from database.models import Assignment, Submission, Student
from datetime import datetime, timedelta

class AssignmentInsights:
    @staticmethod
    def get_toughest_assignments(session, limit=5):
        """Identify assignments with the lowest average scores."""
        results = session.query(
            Assignment.name,
            func.avg(Submission.score / Assignment.points_possible).label('avg_pct'),
            func.count(Submission.id).label('submission_count')
        ).join(Submission).filter(
            Assignment.points_possible > 0,
            Submission.score != None
        ).group_by(Assignment.id).having(
            func.count(Submission.id) > 0
        ).order_by('avg_pct').limit(limit).all()
        
        return results

    @staticmethod
    def get_bottleneck_assignments(session):
        """Identify assignments with the highest late submission or missing rates."""
        assignments = session.query(Assignment).all()
        bottlenecks = []
        
        for a in assignments:
            total = session.query(Submission).filter_by(assignment_id=a.id).count()
            if total == 0: continue
            
            late = session.query(Submission).filter_by(assignment_id=a.id, late=True).count()
            missing = session.query(Submission).filter_by(assignment_id=a.id, missing=True).count()
            
            late_rate = late / total
            missing_rate = missing / total
            
            if late_rate > 0.3 or missing_rate > 0.2:
                bottlenecks.append({
                    "name": a.name,
                    "late_rate": late_rate,
                    "missing_rate": missing_rate,
                    "total": total
                })
        
        bottlenecks.sort(key=lambda x: x['late_rate'] + x['missing_rate'], reverse=True)
        return bottlenecks

    @staticmethod
    def get_grading_backlog(session):
        """Identify assignments that need the most grading attention."""
        results = session.query(
            Assignment.name,
            func.count(Submission.id).label('ungraded_count')
        ).join(Submission).filter(
            Submission.workflow_state.in_(['submitted', 'pending_review'])
        ).group_by(Assignment.id).order_by(func.count(Submission.id).desc()).all()
        
        return results
