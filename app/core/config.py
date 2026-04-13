import os
from dotenv import load_dotenv

load_dotenv()

BASE_URL = "https://apigee.googleapis.com/v1"
SA_KEY_ENV = os.environ.get("APIGEE_SA_KEY")
SA_KEY_PATH = os.environ.get("APIGEE_SA_KEY_PATH", "service-account.json")
