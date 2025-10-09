import os
from keycove import encrypt, decrypt

secret_key = os.environ.get("TOKEN_SECRET")

def decrypt_api_key(api_key: str):
  return decrypt(api_key,secret_key)

def encrypt_api_key(api_key: str):
  return encrypt(api_key,secret_key)

