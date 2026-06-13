import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from database.manager import DatabaseManager
from database.models import Student, Course
from analytics.risk_engine import RiskEngine
from ui.dashboard import CanvasRiskApp
import logging

app = typer.Typer()
console = Console()
db_manager = DatabaseManager()

@app.command()
def draft_feedback(student_name: str, assignment_name: str = None):
    """Generate a feedback draft for a specific submission."""
    from utils.feedback_generator import FeedbackGenerator
    from database.models import Submission, Assignment
    
    session = db_manager.get_session()
    query = session.query(Submission).join(Student).join(Assignment).filter(Student.name.ilike(f"%{student_name}%"))
    
    if assignment_name:
        query = query.filter(Assignment.name.ilike(f"%{assignment_name}%"))
    
    submission = query.order_by(Submission.submitted_at.desc()).first()
    
    if not submission:
        console.print("[bold red]Submission not found.[/bold red]")
        return
        
    draft = FeedbackGenerator.generate_draft(submission)
    console.print(Panel(draft, title=f"Feedback Draft for {submission.student.name} - {submission.assignment.name}", expand=False))
    session.close()

@app.command()
def assignment_insights():
    """Show detailed insights about course assignments."""
    from analytics.assignment_insights import AssignmentInsights
    session = db_manager.get_session()
    
    # Toughest
    toughest = AssignmentInsights.get_toughest_assignments(session)
    t_table = Table(title="Toughest Assignments (Lowest Avg %)")
    t_table.add_column("Assignment", style="magenta")
    t_table.add_column("Avg %", justify="right")
    t_table.add_column("Submissions", justify="right")
    for name, avg_pct, count in toughest:
        t_table.add_row(name, f"{avg_pct*100:.1f}%", str(count))
    console.print(t_table)
    
    # Bottlenecks
    bottlenecks = AssignmentInsights.get_bottleneck_assignments(session)
    b_table = Table(title="Bottleneck Assignments (High Late/Missing)")
    b_table.add_column("Assignment", style="yellow")
    b_table.add_column("Late Rate", justify="right")
    b_table.add_column("Missing Rate", justify="right")
    for b in bottlenecks:
        b_table.add_row(b['name'], f"{b['late_rate']*100:.1f}%", f"{b['missing_rate']*100:.1f}%")
    console.print(b_table)
    
    # Backlog
    backlog = AssignmentInsights.get_grading_backlog(session)
    bl_table = Table(title="Grading Backlog")
    bl_table.add_column("Assignment", style="cyan")
    bl_table.add_column("Ungraded Count", justify="right")
    for name, count in backlog:
        bl_table.add_row(name, str(count))
    console.print(bl_table)
    
    session.close()

@app.command()
def sync():
    """Sync data from Canvas API to local database."""
    with console.status("[bold green]Syncing with Canvas..."):
        try:
            db_manager.sync_from_canvas()
            console.print("[bold green]Successfully synced data from Canvas![/bold green]")
        except Exception as e:
            console.print(f"[bold red]Error syncing data: {e}[/bold red]")
            logging.error(f"Sync error: {e}")

@app.command()
def risk_report():
    """Display a report of at-risk students."""
    session = db_manager.get_session()
    report = RiskEngine.get_at_risk_students(session)
    
    table = Table(title="Student Failure Risk Report")
    table.add_column("Student", style="cyan")
    table.add_column("Current Grade", justify="right")
    table.add_column("Missing", justify="center")
    table.add_column("Fail Prob %", justify="center")
    table.add_column("Trend", justify="center")
    
    for item in report:
        s = item['student']
        rd = item['risk_data']
        
        prob = rd['failure_probability']
        risk_color = "green"
        if prob > 70: risk_color = "red"
        elif prob > 40: risk_color = "yellow"
        
        trend = "↑" if rd['trend_score'] < 20 else "↓"
        grade = f"{s.current_score}% ({rd['letter_grade']})" if s.current_score is not None else "N/A"
        
        table.add_row(
            s.name,
            grade,
            str(rd['missing_count']),
            f"[{risk_color}]{prob:.1f}%[/{risk_color}]",
            trend
        )
    
    console.print(table)
    session.close()

@app.command()
def ungraded():
    """Show assignments that need grading."""
    session = db_manager.get_session()
    ungraded_work = RiskEngine.get_ungraded_work(session)
    
    if not ungraded_work:
        console.print("[bold green]No ungraded work found![/bold green]")
        return

    table = Table(title="Ungraded Submissions")
    table.add_column("Student", style="cyan")
    table.add_column("Assignment", style="magenta")
    table.add_column("Submitted At", style="yellow")
    
    for sub in ungraded_work:
        table.add_row(
            sub.student.name,
            sub.assignment.name,
            sub.submitted_at.strftime("%Y-%m-%d %H:%M") if sub.submitted_at else "Unknown"
        )
    
    console.print(table)
    session.close()

import csv
import json
from pathlib import Path

@app.command()
def export_report(
    type: str = typer.Option("risk", "--type", "-t", help="Type of report (risk, assignments)"),
    format: str = typer.Option("csv", "--format", "-f", help="Output format (csv, json)"),
    output: str = typer.Option(None, "--output", "-o", help="Output filename without extension")
):
    """Export reports to a file."""
    session = db_manager.get_session()
    
    if type == "risk":
        report = RiskEngine.get_at_risk_students(session)
        data = []
        for item in report:
            s = item['student']
            rd = item['risk_data']
            data.append({
                "name": s.name,
                "email": s.email,
                "current_score": s.current_score,
                "letter_grade": rd['letter_grade'],
                "failure_probability": round(rd['failure_probability'], 2),
                "missing_count": rd['missing_count'],
                "late_count": rd['late_count'],
                "trend_score": round(rd['trend_score'], 2),
                "peer_comparison_score": round(rd['peer_comparison_score'], 2),
                "inactivity_score": rd['inactivity_score']
            })
        default_output = "risk_report"
    elif type == "assignments":
        from analytics.assignment_insights import AssignmentInsights
        toughest = AssignmentInsights.get_toughest_assignments(session, limit=100)
        data = [{"name": name, "avg_pct": round(avg_pct*100, 2), "submissions": count} for name, avg_pct, count in toughest]
        default_output = "assignment_insights"
    else:
        console.print(f"[bold red]Unknown report type: {type}[/bold red]")
        session.close()
        return

    output_filename = f"{output or default_output}.{format}"
    
    if format == "csv" and data:
        with open(output_filename, 'w', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=data[0].keys())
            writer.writeheader()
            writer.writerows(data)
    elif format == "json":
        with open(output_filename, 'w') as f:
            json.dump(data, f, indent=4)
    
    console.print(f"[bold green]Report exported to {output_filename}[/bold green]")
    session.close()

@app.command()
def course_stats():
    """Display high-level course analytics."""
    session = db_manager.get_session()
    analytics = RiskEngine.get_course_analytics(session)
    
    console.print(Panel(f"[bold]Course Analytics[/bold]\nTotal Students: {analytics['total_students']}\nRecent Submissions: {analytics['recent_submission_count']}", expand=False))
    
    # Distribution Table
    dist_table = Table(title="Grade Distribution")
    dist_table.add_column("Grade", style="cyan")
    dist_table.add_column("Count", justify="right")
    for k, v in analytics['grade_distribution'].items():
        dist_table.add_row(k, str(v))
    console.print(dist_table)
    
    # Hardest Assignments
    hard_table = Table(title="Toughest Assignments")
    hard_table.add_column("Assignment", style="magenta")
    hard_table.add_column("Avg %", justify="right")
    hard_table.add_column("Missing", justify="right")
    for a in analytics['hardest_assignments']:
        hard_table.add_row(a['name'], f"{a['avg_pct']:.1f}%", str(a['missing']))
    console.print(hard_table)
    
    session.close()

@app.command()
def nudge(
    student_name: str, 
    send: bool = typer.Option(False, "--send", help="Actually send the message via Canvas")
):
    """Generate or send a nudge email template for a student."""
    session = db_manager.get_session()
    student = session.query(Student).filter(Student.name.ilike(f"%{student_name}%")).first()
    
    if not student:
        console.print(f"[bold red]Student '{student_name}' not found.[/bold red]")
        return
        
    risk_data = RiskEngine.calculate_student_risk(student, session)
    
    course = session.query(Course).first()
    course_name = course.name if course else "this course"
    
    subject = f"Checking in: Your progress in {course_name}"
    
    body = f"Hi {student.name.split()[0]},\n\nI'm reaching out to check in on how you're doing in the course. I noticed that you currently have {risk_data['missing_count']} missing assignments, and your current grade is {student.current_score}% ({risk_data['letter_grade']}).\n"
    
    if risk_data['missing_count'] > 0:
        body += "\nI'm concerned about the missing work and wanted to see if there's anything I can do to help you get back on track. "
    
    body += "\n\nPlease let me know if you'd like to schedule a time to chat or if you have any questions about the material.\n\nBest regards,\nYour TA"
    
    if send:
        from api.canvas_client import CanvasClient
        client = CanvasClient()
        try:
            client.send_message(student.canvas_id, body, subject)
            
            # Log the communication
            from database.models import CommunicationLog
            log = CommunicationLog(
                student_id=student.id,
                type='nudge',
                message=body
            )
            session.add(log)
            session.commit()
            
            console.print(f"[bold green]Message successfully sent to {student.name}![/bold green]")
        except Exception as e:
            console.print(f"[bold red]Failed to send message: {e}[/bold red]")
    else:
        console.print(Panel(f"Subject: {subject}\n\n{body}", title=f"Nudge Template for {student.name}", expand=False))
        console.print("\n[dim]Run with --send to actually send this message.[/dim]")
    
    session.close()

@app.command()
def bulk_nudge(
    risk_threshold: float = typer.Option(60.0, "--threshold", "-t", help="Failure probability threshold for nudging"),
    dry_run: bool = typer.Option(True, "--dry-run/--no-dry-run", help="Whether to actually send messages or just show who would be nudged")
):
    """Nudge all students above a certain risk threshold."""
    session = db_manager.get_session()
    report = RiskEngine.get_at_risk_students(session)
    at_risk = [item for item in report if item['risk_data']['failure_probability'] >= risk_threshold]
    
    if not at_risk:
        console.print(f"[bold green]No students found above {risk_threshold}% risk threshold.[/bold green]")
        return

    console.print(f"[bold yellow]Found {len(at_risk)} students above {risk_threshold}% risk.[/bold yellow]")
    
    from api.canvas_client import CanvasClient
    client = CanvasClient()
    course = session.query(Course).first()
    course_name = course.name if course else "the course"

    for item in at_risk:
        student = item['student']
        rd = item['risk_data']
        
        subject = f"Urgent: Your progress in {course_name}"
        body = f"Hi {student.name.split()[0]},\n\nI'm reaching out because I'm concerned about your current progress in {course_name}. You currently have a {rd['failure_probability']:.1f}% failure risk based on {rd['missing_count']} missing assignments and your current grade of {student.current_score}%.\n\nPlease contact me as soon as possible to discuss how we can get you back on track.\n\nBest,\nYour TA"
        
        if dry_run:
            console.print(f"[dim]DRY RUN: Would nudge {student.name} (Risk: {rd['failure_probability']:.1f}%)[/dim]")
        else:
            try:
                client.send_message(student.canvas_id, body, subject)
                
                # Log the communication
                from database.models import CommunicationLog
                log = CommunicationLog(
                    student_id=student.id,
                    type='urgent',
                    message=body
                )
                session.add(log)
                
                console.print(f"[bold green]Nudge sent to {student.name}[/bold green]")
            except Exception as e:
                console.print(f"[bold red]Failed to nudge {student.name}: {e}[/bold red]")
                
    if not dry_run:
        session.commit()
        
    if dry_run:
        console.print("\n[bold yellow]This was a dry run. Use --no-dry-run to actually send messages.[/bold yellow]")
    
    session.close()

@app.command()
def simulate(student_name: str, missing: int = 0, grade: float = None):
    """Simulate a student's risk outcome."""
    session = db_manager.get_session()
    student = session.query(Student).filter(Student.name.ilike(f"%{student_name}%")).first()
    
    if not student:
        console.print(f"[bold red]Student '{student_name}' not found.[/bold red]")
        return
        
    stats = RiskEngine.get_assignment_stats(session)
    original_rd = RiskEngine.calculate_student_risk(student, session, stats)
    sim_prob = RiskEngine.simulate_student_outcome(student, session, missing, grade)
    
    table = Table(title=f"Simulation for {student.name}")
    table.add_column("Metric", style="cyan")
    table.add_column("Original", justify="right")
    table.add_column("Simulated", justify="right", style="bold green")
    
    table.add_row("Failure Prob %", f"{original_rd['failure_probability']:.1f}%", f"{sim_prob:.1f}%")
    table.add_row("Missing Count", str(original_rd['missing_count']), str(max(0, original_rd['missing_count'] - missing)))
    if grade:
        table.add_row("Current Grade", f"{student.current_score}%", f"{grade}%")
        
    console.print(table)
    session.close()

@app.command()
def profiles():
    """Show all students grouped by their profile archetype."""
    session = db_manager.get_session()
    students = session.query(Student).all()
    
    profiles = {}
    for s in students:
        p = s.profile_tag or "Unknown"
        if p not in profiles: profiles[p] = []
        profiles[p].append(s.name)
        
    for p, names in profiles.items():
        console.print(Panel(", ".join(names), title=f"[bold]{p}[/bold]", expand=False))
        
    session.close()

@app.command()
def dashboard():
    """Launch the interactive TUI dashboard."""
    tui = CanvasRiskApp()
    tui.run()

if __name__ == "__main__":
    app()
