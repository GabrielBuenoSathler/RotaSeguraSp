import os
import asyncio
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


async def test_connection():
    if not DATABASE_URL:
        print("❌ DATABASE_URL não encontrada")
        return

    print("🔌 Tentando conectar ao PostgreSQL...")

    try:
        conn = await asyncpg.connect(DATABASE_URL)

        result = await conn.fetchval("SELECT version();")

        print("✅ Conexão realizada com sucesso!")
        print(f"PostgreSQL: {result}")

        await conn.close()
        print("🔌 Conexão encerrada.")

    except Exception as e:
        print("❌ Erro ao conectar:")
        print(e)


if __name__ == "__main__":
    asyncio.run(test_connection())
