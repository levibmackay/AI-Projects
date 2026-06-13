from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean
from sqlalchemy.orm import relationship, declarative_base
from datetime import datetime

Base = declarative_base()

class Student(Base):
    __tablename__ = 'students'
    id = Column(Integer, primary_key=True)
    canvas_id = Column(Integer, unique=True)
    name = Column(String)
    email = Column(String)
    current_score = Column(Float)
    last_sync = Column(DateTime, default=datetime.utcnow)
    profile_tag = Column(String) # e.g., 'The Ghost', 'The Struggler'
    
    submissions = relationship("Submission", back_populates="student")
    risk_history = relationship("RiskRecord", back_populates="student")
    comm_logs = relationship("CommunicationLog", back_populates="student")

class CommunicationLog(Base):
    __tablename__ = 'communication_logs'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    type = Column(String) # 'nudge', 'check-in', 'urgent'
    message = Column(String)
    
    student = relationship("Student", back_populates="comm_logs")

class RiskRecord(Base):
    __tablename__ = 'risk_history'
    id = Column(Integer, primary_key=True)
    student_id = Column(Integer, ForeignKey('students.id'))
    timestamp = Column(DateTime, default=datetime.utcnow)
    failure_probability = Column(Float)
    grade = Column(Float)
    missing_count = Column(Integer)
    
    student = relationship("Student", back_populates="risk_history")

class Course(Base):
    __tablename__ = 'courses'
    id = Column(Integer, primary_key=True)
    canvas_id = Column(Integer, unique=True)
    name = Column(String)
    course_code = Column(String)
    term = Column(String)

class AssignmentGroup(Base):
    __tablename__ = 'assignment_groups'
    id = Column(Integer, primary_key=True)
    canvas_id = Column(Integer, unique=True)
    name = Column(String)
    group_weight = Column(Float) # Percentage (e.g., 20.0 for 20%)

class Assignment(Base):
    __tablename__ = 'assignments'
    id = Column(Integer, primary_key=True)
    canvas_id = Column(Integer, unique=True)
    name = Column(String)
    points_possible = Column(Float)
    due_at = Column(DateTime)
    assignment_group_id = Column(Integer, ForeignKey('assignment_groups.id'))
    
    group = relationship("AssignmentGroup")
    submissions = relationship("Submission", back_populates="assignment")

class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(Integer, primary_key=True)
    canvas_id = Column(Integer, unique=True)
    assignment_id = Column(Integer, ForeignKey('assignments.id'))
    student_id = Column(Integer, ForeignKey('students.id'))
    grade = Column(String)
    score = Column(Float)
    submitted_at = Column(DateTime)
    late = Column(Boolean, default=False)
    missing = Column(Boolean, default=False)
    excused = Column(Boolean, default=False)
    graded_at = Column(DateTime)
    workflow_state = Column(String) # 'submitted', 'graded', 'unsubmitted'

    student = relationship("Student", back_populates="submissions")
    assignment = relationship("Assignment", back_populates="submissions")
