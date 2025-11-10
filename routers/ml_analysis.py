from sqlalchemy.orm import Session
from models.models import Patient, Appointment, AppointmentStatus
from datetime import datetime, timedelta
from typing import List, Dict


class RiskLevel:
    BAIXO = "Baixo"
    MODERADO = "Moderado"
    ALTO = "Alto"


def calculate_patient_risk(db: Session, psychologist_id: int) -> List[Dict]:
    """
    Calcula risco dos pacientes baseado em padrões de frequência
    """
    patients = db.query(Patient).filter(Patient.psychologist_id == psychologist_id).all()
    risk_analysis = []

    for patient in patients:
        appointments = (
            db.query(Appointment)
            .filter(
                Appointment.patient_id == patient.id,
                Appointment.psychologist_id == psychologist_id,
            )
            .order_by(Appointment.date.desc())
            .all()
        )

        if not appointments:
            continue

        # Métricas para análise
        metrics = _extract_patient_metrics(appointments)

        # Calcula score de risco (0–100)
        risk_score = _calculate_risk_score(metrics)

        # Determina nível de risco
        risk_level = _determine_risk_level(risk_score)

        # Identifica razão principal do risco
        risk_reason = _identify_risk_reason(metrics)

        risk_analysis.append({
            "id": patient.id,
            "patient": patient.name,
            "risk": risk_level,
            "risk_score": risk_score,
            "reason": risk_reason,
            "last_appointment": appointments[0].date.isoformat() if appointments else None,
            "metrics": metrics,
        })

    # Ordena por score de risco (maior risco primeiro)
    return sorted(risk_analysis, key=lambda x: x["risk_score"], reverse=True)


def _extract_patient_metrics(appointments: List[Appointment]) -> Dict:
    """Extrai métricas relevantes dos agendamentos"""
    now = datetime.now().date()

    # Separar por status
    completed = [apt for apt in appointments if apt.status == AppointmentStatus.CONCLUIDO]
    canceled = [apt for apt in appointments if apt.status == AppointmentStatus.CANCELADO]
    scheduled = [apt for apt in appointments if apt.status == AppointmentStatus.AGENDADO]

    # Últimos 30, 60 e 90 dias
    last_30_days = [apt for apt in appointments if (now - apt.date).days <= 30]
    last_60_days = [apt for apt in appointments if (now - apt.date).days <= 60]
    last_90_days = [apt for apt in appointments if (now - apt.date).days <= 90]

    # Dias desde última consulta
    days_since_last = (now - appointments[0].date).days if appointments else 999

    # Taxa de cancelamento
    total_appointments = len(appointments)
    cancellation_rate = len(canceled) / total_appointments if total_appointments > 0 else 0

    # Frequência (consultas por mês)
    if appointments:
        first_appointment = min(apt.date for apt in appointments)
        months_active = max(1, (now - first_appointment).days / 30)
        frequency_per_month = len(completed) / months_active
    else:
        frequency_per_month = 0

    # Tendência recente (comparar últimos 30 vs 30-60 dias)
    recent_completed = len([apt for apt in completed if (now - apt.date).days <= 30])
    previous_completed = len([apt for apt in completed if 30 < (now - apt.date).days <= 60])

    return {
        "total_appointments": total_appointments,
        "completed_appointments": len(completed),
        "canceled_appointments": len(canceled),
        "cancellation_rate": cancellation_rate,
        "days_since_last": days_since_last,
        "frequency_per_month": frequency_per_month,
        "appointments_last_30": len(last_30_days),
        "appointments_last_60": len(last_60_days),
        "appointments_last_90": len(last_90_days),
        "recent_trend": recent_completed - previous_completed,
        "has_future_appointments": len(scheduled) > 0
    }
