"""AWS Lambda handler using Mangum to adapt FastAPI to Lambda (ASGI)."""
from mangum import Mangum

from app.api.routes import get_app


app = get_app()
handler = Mangum(app)
