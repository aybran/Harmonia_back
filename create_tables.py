from core.database import Base, engine

print("Criando tabelas... ✅")
Base.metadata.create_all(bind=engine)
print("Finalizado ✅")
