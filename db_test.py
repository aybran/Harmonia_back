from core.database import engine, Base

print("✅ DB importado")
Base.metadata.create_all(bind=engine)
print("✅ create_all OK")
