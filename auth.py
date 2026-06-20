import hashlib

# Sal fixo para aumentar a entropia do hash
SALT = "antigravity_flower_salt_2026"

# Credenciais simuladas (mock) para validação
MOCK_CREDENTIALS = {
    "admin": "password123",
    "client1": "flower_power_2026",
    "client2": "secure_node_99"
}

def generate_sha256_hash(username: str, password: str) -> str:
    """
    Gera um hash SHA-256 combinando username, password e o sal correspondente.
    """
    hash_input = f"{username}:{password}:{SALT}"
    return hashlib.sha256(hash_input.encode('utf-8')).hexdigest()

def verify_credentials(username: str, client_hash: str) -> bool:
    """
    Valida as credenciais. Compara o hash enviado pelo cliente
    com o hash gerado a partir do banco de dados mockado.
    """
    username_norm = username.lower().replace("cliente", "client")
    if username_norm not in MOCK_CREDENTIALS:
        return False
    
    expected_password = MOCK_CREDENTIALS[username_norm]
    expected_hash = generate_sha256_hash(username, expected_password)
    
    return client_hash == expected_hash
