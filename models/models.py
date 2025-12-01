from sqlalchemy import Column, Integer, String, DateTime, Date, ForeignKey, Text, Enum, JSON
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime, timezone
import enum

class UserType(str, enum.Enum):
    PSICOLOGO = "psicologo"
    PACIENTE = "paciente"

class AppointmentStatus(str, enum.Enum):
    AGENDADO = "agendado"
    CONCLUIDO = "concluido"
    CANCELADO = "cancelado"
    REAGENDADO = "reagendado"

class RequestStatus(str, enum.Enum):
    PENDENTE = "pendente"
    ACEITO = "aceito"
    REJEITADO = "rejeitado"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)
    type = Column(Enum(UserType), nullable=False)
    name = Column(String, nullable=False)
    specialty = Column(String, nullable=True)
    crp = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patients = relationship("Patient", back_populates="psychologist")


class Patient(Base):
    __tablename__ = "patients"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    phone = Column(String)
    birth_date = Column(Date)
    age = Column(Integer)
    status = Column(String)
    psychologist_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    psychologist = relationship("User", back_populates="patients")


class Appointment(Base):
    __tablename__ = "appointments"

    id = Column(Integer, primary_key=True, index=True)
    patient_id = Column(Integer, ForeignKey("patients.id"))
    psychologist_id = Column(Integer, ForeignKey("users.id"))
    date = Column(Date)
    time = Column(String)
    status = Column(Enum(AppointmentStatus), default=AppointmentStatus.AGENDADO)
    description = Column(String)
    duration = Column(Integer, default=50)
    notes = Column(Text, default="")
    full_report = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    patient = relationship("Patient")
    psychologist = relationship("User")


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True, index=True)
    patient_name = Column(String)
    patient_email = Column(String)
    patient_phone = Column(String)
    preferred_psychologist = Column(Integer, ForeignKey("users.id"))
    description = Column(Text)
    urgency = Column(String)
    preferred_dates = Column(JSON)
    preferred_times = Column(JSON)
    status = Column(Enum(RequestStatus), default=RequestStatus.PENDENTE)
    notes = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=True)

    psychologist = relationship("User")
