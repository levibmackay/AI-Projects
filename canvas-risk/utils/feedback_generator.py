class FeedbackGenerator:
    @staticmethod
    def generate_draft(submission):
        """Generate a feedback draft based on submission metrics."""
        student_name = submission.student.name.split()[0]
        assignment_name = submission.assignment.name
        score_pct = (submission.score / submission.assignment.points_possible) * 100 if submission.assignment.points_possible else 0
        
        feedback = f"Hi {student_name},\n\n"
        
        if score_pct >= 90:
            feedback += f"Excellent work on {assignment_name}! Your submission shows a strong understanding of the concepts. Keep up the great work."
        elif score_pct >= 80:
            feedback += f"Good job on {assignment_name}. You've mastered most of the material, though there's a bit of room for improvement in some areas."
        elif score_pct >= 70:
            feedback += f"Solid effort on {assignment_name}. I noticed a few areas where you might want to review the course materials to strengthen your understanding."
        elif score_pct > 0:
            feedback += f"Thank you for submitting {assignment_name}. It looks like you're struggling with some of the core concepts here. I'd recommend reviewing the lectures or coming to office hours for some extra help."
        else:
            feedback += f"I noticed you haven't received a passing grade on {assignment_name}. Please let me know if you're having trouble with the material or the submission process."
            
        if submission.late:
            feedback += "\n\nNote: This submission was marked late. Please try to stay on top of future deadlines to avoid point deductions."
            
        feedback += "\n\nBest,\nYour TA"
        return feedback
