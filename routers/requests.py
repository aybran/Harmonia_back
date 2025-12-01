# ============================================================
# MÓDULO DE ROTAS: requests.py
# Responsável por gerenciar solicitações de atendimento (Requests)
# ============================================================
 
# Importações principais do FastAPI e SQLAlchemy
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import json
from datetime import datetime
 
# Importa a função que fornece uma sessão do banco de dados
from core.database import get_db
 
# Importa os modelos do banco (tabelas)
from models.models import Request, User, UserType, RequestStatus
 
# Importa os schemas (Pydantic) usados para validação e resposta das rotas
from schemas.schemas import RequestCreate, RequestUpdate, Request as RequestSchema
 
# Importa o serviço de autenticação que retorna o usuário logado via token
from services.auth_service import get_current_user
 
# Cria o roteador de rotas com o prefixo "/requests"
# Todas as rotas aqui terão o caminho base: /requests
router = APIRouter(prefix="/requests", tags=["requests"])
 
 
# ============================================================
# ROTA: GET /requests
# Objetivo: Listar todas as solicitações destinadas ao psicólogo logado
# ============================================================
@router.get("/", response_model=List[RequestSchema])
async def get_requests(
    current_user: User = Depends(get_current_user),  # Obtém o usuário logado via token JWT
    db: Session = Depends(get_db),                   # Conexão ativa com o banco de dados
):
    """
    Retorna todas as solicitações de atendimento recebidas por um psicólogo específico.
    Apenas psicólogos autenticados podem acessar esta rota.
    """
 
    # Verifica se o usuário logado é psicólogo
    if current_user.type != UserType.PSICOLOGO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas psicólogos podem visualizar as solicitações."
        )
 
    # Busca todas as solicitações destinadas ao psicólogo logado
    requests = db.query(Request).filter(
        Request.preferred_psychologist == current_user.id
    ).all()
 
    # Converte os campos preferred_dates e preferred_times de JSON (string) para lista
    for req in requests:
        req.preferred_dates = json.loads(req.preferred_dates) if req.preferred_dates else []
        req.preferred_times = json.loads(req.preferred_times) if req.preferred_times else []
 
    # Retorna a lista de solicitações como resposta
    return requests
 
 
# ============================================================
# ROTA: POST /requests
# Objetivo: Criar uma nova solicitação de atendimento (feita por um paciente)
# ============================================================
@router.post("/", response_model=RequestSchema)
async def create_request(
    request_data: RequestCreate,   # Dados enviados no corpo da requisição
    db: Session = Depends(get_db), # Sessão com o banco de dados
):
    """
    Permite que um paciente crie uma nova solicitação de atendimento para um psicólogo.
    - Verifica se já existe uma solicitação pendente entre o mesmo paciente e psicólogo.
    - Armazena listas de horários e datas preferidas como JSON.
    """
 
    # Verifica se o paciente já possui uma solicitação pendente para o mesmo psicólogo
    existing_request = db.query(Request).filter(
        Request.patient_email == request_data.patient_email,
        Request.preferred_psychologist == request_data.preferred_psychologist,
        Request.status == RequestStatus.PENDENTE
    ).first()
 
    # Se já existir uma solicitação pendente, retorna erro 400
    if existing_request:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Você já possui uma solicitação pendente para este psicólogo"
        )
 
    # Cria o objeto da nova solicitação a partir dos dados recebidos
    db_request = Request(
        patient_name=request_data.patient_name,
        patient_email=request_data.patient_email,
        patient_phone=request_data.patient_phone,
        preferred_psychologist=request_data.preferred_psychologist,
        description=request_data.description,
        urgency=request_data.urgency,
        # Converte listas de preferências para JSON (string) antes de salvar
        preferred_dates=json.dumps(request_data.preferred_dates),
        preferred_times=json.dumps(request_data.preferred_times),
        status=RequestStatus.PENDENTE  # Define o status inicial como "pendente"
    )
 
    # Adiciona e confirma o novo registro no banco de dados
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
 
    # Converte novamente os campos JSON para lista antes de retornar
    db_request.preferred_dates = request_data.preferred_dates
    db_request.preferred_times = request_data.preferred_times
 
    # Retorna o objeto recém-criado
    return db_request
 
 
# ============================================================
# ROTA: PUT /requests/{request_id}
# Objetivo: Atualizar o status ou observações de uma solicitação existente
# ============================================================
@router.put("/{request_id}", response_model=RequestSchema)
async def update_request_status(
    request_id: int,                               # ID da solicitação a ser atualizada
    update_data: RequestUpdate,                    # Dados de atualização (status, notas)
    current_user: User = Depends(get_current_user),  # Usuário autenticado
    db: Session = Depends(get_db),                 # Sessão com o banco
):
    """
    Permite que o psicólogo aceite, rejeite ou atualize uma solicitação.
    Apenas psicólogos autenticados podem realizar essa operação.
    """
 
    # Verifica se o usuário logado é psicólogo
    if current_user.type != UserType.PSICOLOGO:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Apenas psicólogos podem atualizar solicitações"
        )
 
    # Busca a solicitação pelo ID e garante que ela pertence ao psicólogo logado
    request = db.query(Request).filter(
        Request.id == request_id,
        Request.preferred_psychologist == current_user.id
    ).first()
 
    # Se não for encontrada, retorna erro 404
    if not request:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Solicitação não encontrada"
        )
 
    # Atualiza o status e as observações da solicitação
    request.status = update_data.status
    request.notes = update_data.notes or ""  # Se não houver notas, salva string vazia
    request.updated_at = datetime.now()      # Atualiza o timestamp de modificação
 
    # Salva as alterações no banco
    db.commit()
    db.refresh(request)
 
    # Converte novamente campos JSON para lista antes de retornar
    request.preferred_dates = json.loads(request.preferred_dates) if request.preferred_dates else []
    request.preferred_times = json.loads(request.preferred_times) if request.preferred_times else []
 
    # Retorna a solicitação atualizada
    return request
 
 