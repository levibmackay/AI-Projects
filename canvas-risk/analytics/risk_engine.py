from datetime import datetime, timedelta
from sqlalchemy import func
from database.models import Student, Submission, Assignment, AssignmentGroup, RiskRecord

class RiskEngine:
    WEIGHTS = {
        'grade': 0.40,
        'missing': 0.30,
        'trend': 0.10,
        'inactivity': 0.10,
        'peer_comparison': 0.10
    }

    @staticmethod
    def categorize_student(risk_data):
        """Assign a profile tag based on risk metrics."""
        prob = risk_data['failure_probability']
        missing = risk_data['missing_count']
        inactivity = risk_data['inactivity_score']
        grade = risk_data['grade_risk']

        if prob < 10: return "🌟 High Achiever"
        if inactivity > 80 and missing > 3: return "👻 The Ghost"
        if grade > 70 and inactivity < 30: return "💪 The Struggler"
        if risk_data['trend_score'] > 50: return "📉 Slipping"
        if risk_data['late_count'] > 3: return "⏰ Chronic Latecomer"
        if prob > 60: return "⚠️ High Risk"
        return "✅ On Track"

    @staticmethod
    def record_risk_snapshot(session):
        """Save current risk state for all students to history."""
        students = session.query(Student).all()
        stats = RiskEngine.get_assignment_stats(session)
        for student in students:
            rd = RiskEngine.calculate_student_risk(student, session, stats)
            record = RiskRecord(
                student_id=student.id,
                failure_probability=rd['failure_probability'],
                grade=student.current_score,
                missing_count=rd['missing_count']
            )
            session.add(record)
            student.profile_tag = RiskEngine.categorize_student(rd)
        session.commit()

    @staticmethod
    def get_risk_velocity(student, session):
        """Calculate if risk is increasing or decreasing over time."""
        history = session.query(RiskRecord).filter_by(student_id=student.id).order_by(RiskRecord.timestamp.desc()).limit(5).all()
        if len(history) < 2:
            return 0.0
        
        latest = history[0].failure_probability
        oldest = history[-1].failure_probability
        return latest - oldest

    @staticmethod
    def simulate_student_outcome(student, session, missing_to_submit=0, hypothetical_grade=None):
        """Simulate a student's risk if they submit work or get a certain grade."""
        stats = RiskEngine.get_assignment_stats(session)
        rd = RiskEngine.calculate_student_risk(student, session, stats)
        
        # Adjust metrics hypothetically
        simulated_prob = rd['failure_probability']
        
        # 1. Reduce missing count impact
        if missing_to_submit > 0:
            reduction = min(missing_to_submit * 20 * RiskEngine.WEIGHTS['missing'], simulated_prob)
            simulated_prob -= reduction
            
        # 2. Adjust grade impact
        if hypothetical_grade is not None:
            # Re-calculate grade risk component
            old_grade_risk = rd['grade_risk'] * RiskEngine.WEIGHTS['grade']
            
            new_grade_risk = 0
            if hypothetical_grade < 60: new_grade_risk = 100
            elif hypothetical_grade < 70: new_grade_risk = 80
            elif hypothetical_grade < 80: new_grade_risk = 50
            elif hypothetical_grade < 85: new_grade_risk = 20
            
            new_weighted_risk = new_grade_risk * RiskEngine.WEIGHTS['grade']
            simulated_prob = (simulated_prob - old_grade_risk) + new_weighted_risk

        return max(0, min(100, simulated_prob))

    @staticmethod
    def get_assignment_stats(session):
        """Calculate averages for all assignments."""
        stats = session.query(
            Assignment.id,
            func.avg(Submission.score).label('avg_score'),
            func.count(Submission.id).label('submission_count')
        ).join(Submission).filter(Submission.score != None).group_by(Assignment.id).all()
        return {s.id: {'avg': s.avg_score, 'count': s.submission_count} for s in stats}

    @staticmethod
    def get_letter_grade(percentage):
        if percentage is None:
            return "N/A"
        if percentage >= 93: return "A"
        if percentage >= 90: return "A-"
        if percentage >= 87: return "B+"
        if percentage >= 83: return "B"
        if percentage >= 80: return "B-"
        if percentage >= 77: return "C+"
        if percentage >= 73: return "C"
        if percentage >= 70: return "C-"
        if percentage >= 67: return "D+"
        if percentage >= 63: return "D"
        if percentage >= 60: return "D-"
        return "F"

    @staticmethod
    def calculate_student_risk(student, session, assignment_stats=None):
        if assignment_stats is None:
            assignment_stats = RiskEngine.get_assignment_stats(session)

        # 1. Missing Assignments Score (0-100)
        now = datetime.utcnow()
        missing_subs = session.query(Submission).join(Assignment).filter(
            Submission.student_id == student.id,
            Assignment.points_possible > 0,
            Submission.excused == False,
            (
                (Submission.missing == True) |
                ((Submission.workflow_state == 'unsubmitted') & (Assignment.due_at < now)) |
                ((Submission.workflow_state == 'graded') & (Submission.score == 0)) |
                (Submission.grade.ilike('incomplete'))
            )
        ).all()
        
        # Weighted missing score: missing a final is worse than a quiz
        weighted_missing_impact = 0
        for sub in missing_subs:
            weight = 1.0
            if sub.assignment.group and sub.assignment.group.group_weight:
                weight = sub.assignment.group.group_weight / 10.0 # scale factor
            weighted_missing_impact += weight
        
        missing_score = min(weighted_missing_impact * 20, 100)

        # 2. Late Submissions Score (0-100)
        late_count = session.query(Submission).filter_by(student_id=student.id, late=True).count()
        late_score = min(late_count * 20, 100)

        # 3. Grade Trend Score (0-100)
        submissions = session.query(Submission).join(Assignment).filter(
            Submission.student_id == student.id,
            Submission.score != None
        ).order_by(Assignment.due_at.desc()).limit(5).all()
        
        trend_score = 0
        peer_comparison_score = 0
        
        if submissions:
            # Peer Comparison: How many assignments are below average?
            below_avg_count = 0
            for sub in submissions:
                stats = assignment_stats.get(sub.assignment_id)
                if stats and sub.score < stats['avg']:
                    below_avg_count += 1
            peer_comparison_score = (below_avg_count / len(submissions)) * 100

            if len(submissions) >= 2:
                recent_score = submissions[0].score / submissions[0].assignment.points_possible if submissions[0].assignment.points_possible else 0
                prev_scores = [s.score / s.assignment.points_possible for s in submissions[1:] if s.assignment.points_possible]
                if prev_scores:
                    avg_prev = sum(prev_scores) / len(prev_scores)
                    if recent_score < avg_prev:
                        trend_score = min((avg_prev - recent_score) * 200, 100)

        # 4. Inactivity Score (0-100)
        last_submission = session.query(Submission).filter_by(student_id=student.id).order_by(Submission.submitted_at.desc()).first()
        inactivity_score = 0
        if last_submission and last_submission.submitted_at:
            days_since = (datetime.utcnow() - last_submission.submitted_at).days
            inactivity_score = min(days_since * 7, 100)
        else:
            inactivity_score = 100

        # 5. Grade Risk (0-100)
        grade_risk = 0
        if student.current_score is not None:
            if student.current_score < 60: grade_risk = 100
            elif student.current_score < 70: grade_risk = 80
            elif student.current_score < 80: grade_risk = 50
            elif student.current_score < 85: grade_risk = 20
        else:
            grade_risk = 50

        # Failure Probability Calculation
        failure_prob = (
            grade_risk * RiskEngine.WEIGHTS['grade'] +
            missing_score * RiskEngine.WEIGHTS['missing'] +
            trend_score * RiskEngine.WEIGHTS['trend'] +
            inactivity_score * RiskEngine.WEIGHTS['inactivity'] +
            peer_comparison_score * RiskEngine.WEIGHTS['peer_comparison']
        )

        return {
            'failure_probability': failure_prob,
            'missing_count': len(missing_subs),
            'late_count': late_count,
            'trend_score': trend_score,
            'peer_comparison_score': peer_comparison_score,
            'inactivity_score': inactivity_score,
            'grade_risk': grade_risk,
            'last_activity': last_submission.submitted_at if last_submission else None,
            'letter_grade': RiskEngine.get_letter_grade(student.current_score)
        }

    @staticmethod
    def get_at_risk_students(session):
        students = session.query(Student).all()
        assignment_stats = RiskEngine.get_assignment_stats(session)
        report = []
        for student in students:
            risk_data = RiskEngine.calculate_student_risk(student, session, assignment_stats)
            report.append({
                'student': student,
                'risk_data': risk_data
            })
        
        report.sort(key=lambda x: x['risk_data']['failure_probability'], reverse=True)
        return report

    @staticmethod
    def get_recent_communications(student, session):
        """Get the most recent communications for a student."""
        from database.models import CommunicationLog
        return session.query(CommunicationLog).filter_by(student_id=student.id).order_by(CommunicationLog.timestamp.desc()).limit(5).all()

    @staticmethod
    def get_course_analytics(session):
        """Get high-level course statistics."""
        students = session.query(Student).all()
        
        # 1. Grade Distribution
        dist = {"A": 0, "B": 0, "C": 0, "D": 0, "F": 0, "N/A": 0}
        for s in students:
            lg = RiskEngine.get_letter_grade(s.current_score)
            if lg.startswith("A"): dist["A"] += 1
            elif lg.startswith("B"): dist["B"] += 1
            elif lg.startswith("C"): dist["C"] += 1
            elif lg.startswith("D"): dist["D"] += 1
            elif lg == "F": dist["F"] += 1
            else: dist["N/A"] += 1
            
        # 2. Hardest Assignments (Lowest Average)
        stats = RiskEngine.get_assignment_stats(session)
        assignments = session.query(Assignment).all()
        
        hardest = []
        for a in assignments:
            if a.id in stats and stats[a.id]['count'] > 5: # Only if enough data
                avg_pct = (stats[a.id]['avg'] / a.points_possible) * 100 if a.points_possible else 0
                hardest.append({
                    "name": a.name,
                    "avg_pct": avg_pct,
                    "missing": session.query(Submission).filter_by(assignment_id=a.id, missing=True).count()
                })
        
        hardest.sort(key=lambda x: x['avg_pct'])
        
        # 3. Recent Activity (Last 7 days)
        seven_days_ago = datetime.utcnow() - timedelta(days=7)
        recent_subs = session.query(Submission).filter(Submission.submitted_at >= seven_days_ago).count()
        
        return {
            "grade_distribution": dist,
            "hardest_assignments": hardest[:5],
            "recent_submission_count": recent_subs,
            "total_students": len(students)
        }

    @staticmethod
    def get_ungraded_work(session):
        # Work that needs attention:
        # 1. Any submission in 'submitted' or 'pending_review' state (truly ungraded)
        # 2. Any submission that has a score of 0 (even if 'graded')
        # 3. Any submission where the score is missing
        
        ungraded = session.query(Submission).join(Assignment).filter(
            (Submission.workflow_state != 'unsubmitted'),
            (
                (Submission.workflow_state.in_(['submitted', 'pending_review'])) |
                (Submission.score == 0) |
                (Submission.score == None)
            )
        ).all()
        
        return ungraded
