from mangum import Mangum
from main import app

# Vercel serverless entrypoint handler for FastAPI
handler = Mangum(app)
