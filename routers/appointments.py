# Importações principais do FastAPI e SQLAlchemy
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

# Importa o gerenciador de sessão com o banco de dados
from app.core.database import get_db

# Importa os modelos do banco
from app.models import Appointment, User, Patient, AppointmentStatus, UserType

# Importa os schemas (Pydantic) para validação de entrada e saída de dados
from app.schemas.appointment import AppointmentCreate, AppointmentUpdate, Appointment as AppointmentSchema

# Importa a função que valida o token e retorna o usuário autenticado
from app.services.auth_service import get_current_user

# Cria o roteador para as rotas de agendamentos
router = APIRouter(prefix="/appointments", tags=["appointments"])


# ----------------------------
# ROTA: LISTAR AGENDAMENTOS
# ----------------------------
@router.get("/", response_model=List[AppointmentSchema])
async def get_appointments(
    current_user: User = Depends(get_current_user),  # Obtém o usuário logado (via token JWT)
    db: Session = Depends(get_db)                    # Conexão com o banco
):
    """
    Retorna todos os agendamentos do usuário logado.
    - Se for psicólogo, lista os agendamentos como profissional.
    - Se for paciente, lista os agendamentos como paciente.
    """

    # Se o usuário for psicólogo, busca agendamentos onde ele é o responsável
    if current_user.user_type == UserType.PSICOLOGO:
        appointments = (
            db.query(Appointment)
            .filter(Appointment.psychologist_id == current_user.id)
            .all()
        )
    else:
        # Primeiro busca o paciente pelo e-mail
        patient = (
            db.query(Patient)
            .filter(Patient.email == current_user.email)
            .first()
        )

        # Se não encontrar o paciente, retorna lista vazia
        if not patient:
            return []

        # Busca todos os agendamentos desse paciente
        appointments = (
            db.query(Appointment)
            .filter(Appointment.patient_id == patient.id)
            .all()
        )

    return appointments


# ----------------------------------
# ROTA: CRIAR AGENDAMENTO
# ----------------------------------
@router.post("/", response_model=AppointmentSchema)
async def create_appointment(
    appointment_data: AppointmentCreate,                # Dados recebidos no corpo da requisição
    current_user: User = Depends(get_current_user),     # Usuário logado
    db: Session = Depends(get_db)                       # Sessão com o banco
):
    """
    Cria um novo agendamento.
    - Verifica se o horário solicitado está disponível.
    - Caso esteja, cria um novo registro no banco.
    """

    # Verifica se já existe um agendamento no mesmo horário com o mesmo psicólogo
    existing_appointment = (
        db.query(Appointment)
        .filter(
            Appointment.psychologist_id == appointment_data.psychologist_id,
            Appointment.date == appointment_data.date,
            Appointment.status == AppointmentStatus.AGENDADO
        )
        .first()
    )

    # Se já houver agendamento nesse horário, retorna erro
    if existing_appointment:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Horário não disponível"
        )

    # Cria o novo objeto de agendamento
    db_appointment = Appointment(
        **appointment_data.dict(),
        status=AppointmentStatus.AGENDADO
    )

    # Salva no banco
    db.add(db_appointment)
    db.commit()
    db.refresh(db_appointment)

    return db_appointment


# --------------------------------------------
# ROTA: ATUALIZAR AGENDAMENTO
# --------------------------------------------
@router.put("/{appointment_id}", response_model=AppointmentSchema)
async def update_appointment(
    appointment_id: int,                                # ID do agendamento que será atualizado
    update_data: AppointmentUpdate,                     # Dados parciais para atualização
    current_user: User = Depends(get_current_user),     # Usuário logado
    db: Session = Depends(get_db)                       # Sessão do banco
):
    """
    Atualiza um agendamento existente.
    Permite modificar a data, horário ou status.
    Verifica se o usuário tem permissão para fazer a alteração.
    """

    # Busca o agendamento pelo ID
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento não encontrado"
        )

    # Verifica se o psicólogo logado é o dono do agendamento
    if current_user.user_type == UserType.PSICOLOGO and appointment.psychologist_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sem permissão para alterar este agendamento"
        )

    # Atualiza apenas os campos enviados
    for field, value in update_data.dict(exclude_unset=True).items():
        setattr(appointment, field, value)

    db.commit()
    db.refresh(appointment)

    return appointment


# --------------------------------------------
# ROTA: CANCELAR AGENDAMENTO
# --------------------------------------------
@router.delete("/{appointment_id}")
async def cancel_appointment(
    appointment_id: int,                               # ID do agendamento a cancelar
    current_user: User = Depends(get_current_user),    # Usuário autenticado
    db: Session = Depends(get_db)                      # Sessão com o banco
):
    """
    Cancela um agendamento alterando seu status para 'CANCELADO'.
    """

    # Busca o agendamento pelo ID
    appointment = db.query(Appointment).filter(Appointment.id == appointment_id).first()
    if not appointment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agendamento não encontrado"
        )

    # Atualiza o status
    appointment.status = AppointmentStatus.CANCELADO
    db.commit()

    return {"message": "Agendamento cancelado com sucesso"}


# -------------------------
# ROTA: VER HORÁRIOS DISPONÍVEIS
# -------------------------
@router.get("/available-slots")
async def get_available_slots(
    date: str,                      # Data solicitada (ex: "2025-10-30")
    psychologist_id: int,           # ID do psicólogo
    db: Session = Depends(get_db)
):
    """
    Retorna os horários disponíveis para um determinado psicólogo em uma data específica.
    - Filtra os horários já ocupados.
    - Retorna apenas os horários livres.
    """

    # Lista fixa de horários possíveis no dia
    all_slots = ['09:00', '10:00', '11:00', '14:00', '15:00', '16:00', '17:00']

    # Busca os horários já ocupados para o psicólogo e a data informada
    occupied_slots = db.query(Appointment.time).filter(
        Appointment.date == date,
        Appointment.psychologist_id == psychologist_id,
        Appointment.status == AppointmentStatus.AGENDADO
    ).all()

    # Extrai apenas os horários da consulta (coluna time)
    occupied_times = [slot[0] for slot in occupied_slots]

    # Filtra horários disponíveis
    available_slots = [slot for slot in all_slots if slot not in occupied_times]

    return available_slots
