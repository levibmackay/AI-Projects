from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, Static, Label, TabbedContent, TabPane, Input, Button, Markdown
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from database.manager import DatabaseManager
from analytics.risk_engine import RiskEngine
from api.canvas_client import CanvasClient
from database.models import CommunicationLog, Student, Course
from datetime import datetime

class StudentDetail(Static):
    def update_student(self, student_data, velocity=0.0, recent_comms=None):
        s = student_data['student']
        rd = student_data['risk_data']
        
        velocity_icon = "📈" if velocity > 5 else "📉" if velocity < -5 else "➡️"
        velocity_text = f"{velocity:+.1f}%" if abs(velocity) > 0.1 else "Stable"
        
        comm_history = ""
        if recent_comms:
            comm_history = "\n### Recent Communications:\n"
            for log in recent_comms:
                comm_history += f"- **{log.timestamp.strftime('%Y-%m-%d')}** ({log.type}): {log.message[:50]}...\n"
        
        content = f"""
# {s.name}
### {s.profile_tag or 'Uncategorized'}
---
**Grade:** {s.current_score}% ({rd['letter_grade']})
**Risk Score:** [b]{rd['failure_probability']:.1f}%[/b] ({velocity_icon} {velocity_text} risk velocity)

### Risk Breakdown:
- **Missing Assignments:** {rd['missing_count']}
- **Late Submissions:** {rd['late_count']}
- **Grade Trend:** {rd['trend_score']:.1f}
- **Peer Comparison:** {rd['peer_comparison_score']:.1f}
- **Inactivity Score:** {rd['inactivity_score']:.1f}

### Recommended Action:
"""
        if rd['failure_probability'] > 70:
            content += "[red]URGENT: Schedule 1-on-1 meeting. Send intervention message.[/red]"
        elif rd['failure_probability'] > 40:
            content += "[yellow]NUDGE: Send check-in message about missing work.[/yellow]"
        else:
            content += "[green]MONITOR: Keep an eye on recent trends.[/green]"
            
        content += comm_history
        
        self.update(content)

class CanvasRiskApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    #main-container {
        height: 1fr;
    }
    .risk-high { color: red; text-style: bold; }
    .risk-medium { color: yellow; }
    .risk-low { color: green; }
    
    #student-list {
        width: 60%;
    }
    #detail-panel {
        width: 40%;
        border-left: solid $accent;
        padding: 1;
    }
    #simulator-controls, #message-controls {
        background: $boost;
        padding: 1;
        border-top: solid $accent;
        height: auto;
    }
    .sim-input, .msg-input {
        margin-bottom: 1;
    }
    #sim-result, #msg-result {
        color: $accent;
        text-style: bold;
        margin-top: 1;
    }
    #message-body {
        height: 5;
    }
    """

    BINDINGS = [
        ("d", "toggle_dark", "Toggle dark mode"),
        ("q", "quit", "Quit"),
        ("s", "sync", "Sync Data"),
        ("r", "refresh", "Refresh UI"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Risk Dashboard"):
                with Horizontal(id="main-container"):
                    with Vertical(id="student-list"):
                        yield Input(placeholder="Search students...", id="search-input")
                        yield DataTable(id="risk-table")
                    with Vertical(id="detail-panel"):
                        yield StudentDetail(id="student-detail")
                        with Vertical(id="simulator-controls"):
                            yield Label("[b]What-If Simulator[/b]")
                            yield Label("Simulate submitting missing work:")
                            yield Input(placeholder="Number of assignments...", id="sim-missing", classes="sim-input")
                            yield Label("Simulate hypothetical grade %:")
                            yield Input(placeholder="Target grade (e.g. 85)...", id="sim-grade", classes="sim-input")
                            yield Label("", id="sim-result")
                        with Vertical(id="message-controls"):
                            yield Label("[b]Send Canvas Message[/b]")
                            yield Input(placeholder="Subject...", id="message-subject", classes="msg-input")
                            yield Input(placeholder="Body...", id="message-body", classes="msg-input")
                            yield Button("Send Message", id="send-btn", variant="primary")
                            yield Label("", id="msg-result")
            with TabPane("Ungraded Work"):
                with Horizontal():
                    yield DataTable(id="ungraded-table")
                    with Vertical(id="ungraded-detail", classes="hidden"):
                        yield Static(id="ungraded-info")
                        yield Label("[b]Feedback Draft[/b]")
                        yield Static(id="feedback-draft")
                        yield Button("Copy to Clipboard", id="copy-feedback-btn") # Note: textual clipboard support might be limited
            with TabPane("Course Analytics"):
                yield ScrollableContainer(Static("Loading course stats...", id="course-stats"))
        yield Footer()

    def on_mount(self) -> None:
        self.db = DatabaseManager()
        self.client = CanvasClient()
        self.refresh_data()
        self.current_student_id = None

    def refresh_data(self):
        session = self.db.get_session()
        self.report = RiskEngine.get_at_risk_students(session)
        
        # Risk Table
        table = self.query_one("#risk-table", DataTable)
        table.clear(columns=True)
        table.add_columns("Student", "Grade", "Fail %", "Profile")
        
        for item in self.report:
            s = item['student']
            rd = item['risk_data']
            table.add_row(
                s.name,
                f"{s.current_score}%",
                f"{rd['failure_probability']:.1f}%",
                s.profile_tag or "N/A",
                key=str(s.id)
            )

        # Ungraded Table
        ungraded = RiskEngine.get_ungraded_work(session)
        u_table = self.query_one("#ungraded-table", DataTable)
        u_table.clear(columns=True)
        u_table.add_columns("Student", "Assignment", "Submitted At")
        for sub in ungraded:
            u_table.add_row(
                sub.student.name,
                sub.assignment.name,
                sub.submitted_at.strftime("%Y-%m-%d") if sub.submitted_at else "N/A",
                key=str(sub.id)
            )
        
        # Course Analytics
        from analytics.assignment_insights import AssignmentInsights
        analytics = RiskEngine.get_course_analytics(session)
        toughest = AssignmentInsights.get_toughest_assignments(session)
        bottlenecks = AssignmentInsights.get_bottleneck_assignments(session)
        backlog = AssignmentInsights.get_grading_backlog(session)
        
        dist = analytics['grade_distribution']
        dist_text = " | ".join([f"{k}: {v}" for k, v in dist.items()])
        
        toughest_text = "\n".join([f"- {name}: {avg_pct*100:.1f}% avg ({count} subs)" for name, avg_pct, count in toughest])
        bottleneck_text = "\n".join([f"- {b['name']}: {b['late_rate']*100:.1f}% late, {b['missing_rate']*100:.1f}% missing" for b in bottlenecks])
        backlog_text = "\n".join([f"- {name}: {count} pending" for name, count in backlog])
        
        content = f"""
# Course Analytics
---
**Total Students:** {analytics['total_students']}
**Recent Submissions (7d):** {analytics['recent_submission_count']}

### Grade Distribution:
{dist_text}

### Toughest Assignments:
{toughest_text}

### Bottleneck Assignments:
{bottleneck_text}

### Grading Backlog:
{backlog_text}
"""
        self.query_one("#course-stats", Static).update(content)
        session.close()

    def on_data_table_row_selected(self, event: DataTable.RowSelected):
        if event.data_table.id == "risk-table":
            self.current_student_id = int(event.row_key.value)
            self.update_detail_panel()
        elif event.data_table.id == "ungraded-table":
            self.current_submission_id = int(event.row_key.value)
            self.update_ungraded_panel()

    def update_ungraded_panel(self):
        if hasattr(self, 'current_submission_id'):
            from utils.feedback_generator import FeedbackGenerator
            from database.models import Submission
            session = self.db.get_session()
            sub = session.query(Submission).get(self.current_submission_id)
            if sub:
                info = f"# {sub.assignment.name}\n**Student:** {sub.student.name}\n**Submitted:** {sub.submitted_at.strftime('%Y-%m-%d %H:%M') if sub.submitted_at else 'N/A'}"
                self.query_one("#ungraded-info").update(info)
                
                draft = FeedbackGenerator.generate_draft(sub)
                self.query_one("#feedback-draft").update(draft)
                # self.query_one("#ungraded-detail").remove_class("hidden")
            session.close()

    def update_detail_panel(self):
        if self.current_student_id:
            session = self.db.get_session()
            student_data = next((i for i in self.report if i['student'].id == self.current_student_id), None)
            if student_data:
                velocity = RiskEngine.get_risk_velocity(student_data['student'], session)
                recent_comms = RiskEngine.get_recent_communications(student_data['student'], session)
                self.query_one("#student-detail", StudentDetail).update_student(student_data, velocity, recent_comms)
                self.run_simulation()
                
                # Pre-fill nudge template if high risk
                if student_data['risk_data']['failure_probability'] > 40:
                    course = session.query(Course).first()
                    course_name = course.name if course else "the course"
                    self.query_one("#message-subject").value = f"Checking in: {course_name}"
                    self.query_one("#message-body").value = f"Hi {student_data['student'].name.split()[0]}, I'm reaching out to check in on your progress..."
            session.close()

    def on_button_pressed(self, event: Button.Pressed):
        if event.button.id == "send-btn":
            self.send_canvas_message()

    def send_canvas_message(self):
        if not self.current_student_id:
            self.query_one("#msg-result").update("[red]No student selected[/red]")
            return
            
        subject = self.query_one("#message-subject").value
        body = self.query_one("#message-body").value
        
        if not body:
            self.query_one("#msg-result").update("[red]Message body is empty[/red]")
            return
            
        session = self.db.get_session()
        student = session.query(Student).get(self.current_student_id)
        
        try:
            self.client.send_message(student.canvas_id, body, subject)
            
            # Log it
            log = CommunicationLog(
                student_id=student.id,
                type='manual',
                message=body
            )
            session.add(log)
            session.commit()
            
            self.query_one("#msg-result").update("[green]Message Sent![/green]")
            self.query_one("#message-body").value = ""
            self.update_detail_panel()
        except Exception as e:
            self.query_one("#msg-result").update(f"[red]Error: {e}[/red]")
        finally:
            session.close()

    def on_input_changed(self, event: Input.Changed):
        if event.input.id == "search-input":
            search_term = event.value.lower()
            table = self.query_one("#risk-table", DataTable)
            table.clear()
            for item in self.report:
                if search_term in item['student'].name.lower():
                    s = item['student']
                    rd = item['risk_data']
                    table.add_row(
                        s.name,
                        f"{s.current_score}%",
                        f"{rd['failure_probability']:.1f}%",
                        s.profile_tag or "N/A",
                        key=str(s.id)
                    )
        elif event.input.id in ["sim-missing", "sim-grade"]:
            self.run_simulation()

    def run_simulation(self):
        if not self.current_student_id:
            return
            
        try:
            missing = int(self.query_one("#sim-missing").value or 0)
            grade_val = self.query_one("#sim-grade").value
            grade = float(grade_val) if grade_val else None
            
            session = self.db.get_session()
            student_data = next((i for i in self.report if i['student'].id == self.current_student_id), None)
            if student_data:
                sim_prob = RiskEngine.simulate_student_outcome(student_data['student'], session, missing, grade)
                diff = sim_prob - student_data['risk_data']['failure_probability']
                
                result_text = f"Simulated Risk: {sim_prob:.1f}% ({diff:+.1f}%)"
                self.query_one("#sim-result").update(result_text)
            session.close()
        except ValueError:
            self.query_one("#sim-result").update("[red]Invalid simulation input[/red]")

    def action_sync(self):
        self.db.sync_from_canvas()
        self.refresh_data()

    def action_refresh(self):
        self.refresh_data()

if __name__ == "__main__":
    app = CanvasRiskApp()
    app.run()
