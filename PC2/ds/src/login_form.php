<?php
session_start();

// Se já está autenticado, redireciona
if (isset($_SESSION['utilizador'])) {
    header('Location: simulacoes.php');
    exit;
}

$erro = '';

if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $email = trim($_POST['email'] ?? '');
    $password = trim($_POST['password'] ?? '');

    if (empty($email) || empty($password)) {
        $erro = 'Preencha todos os campos.';
    } else {
        $host   = 'mysql';
        $conn   = new mysqli($host, 'root', 'root', 'labirinto');

        if ($conn->connect_error) {
            $erro = 'Erro de ligação à base de dados.';
        } else {
            $stmt = $conn->prepare("SELECT IDUtilizador, Nome, Equipa FROM utilizador WHERE Email = ? AND Password = ?");
            $stmt->bind_param("ss", $email, $password);
            $stmt->execute();
            $result = $stmt->get_result();
            $user   = $result->fetch_assoc();

            if ($user) {
                $_SESSION['utilizador']   = $user['IDUtilizador'];
                $_SESSION['nome']         = $user['Nome'];
                $_SESSION['equipa']       = $user['Equipa'];
                header('Location: simulacoes.php');
                exit;
            } else {
                $erro = 'Email ou password incorretos.';
            }
            $stmt->close();
            $conn->close();
        }
    }
}
?>
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Labirinto — Login</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --border: #2a2a3a;
    --accent: #7c6af7;
    --accent2: #4ecdc4;
    --text: #e8e8f0;
    --muted: #6a6a8a;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    background-image: radial-gradient(ellipse at 20% 50%, rgba(124,106,247,0.08) 0%, transparent 60%),
                      radial-gradient(ellipse at 80% 20%, rgba(78,205,196,0.06) 0%, transparent 50%);
  }
  .container {
    width: 100%;
    max-width: 420px;
    padding: 2rem;
  }
  .logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 2rem;
    letter-spacing: -0.02em;
    margin-bottom: 0.4rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .subtitle {
    color: var(--muted);
    font-size: 0.8rem;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 2.5rem;
  }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 2rem;
  }
  .field { margin-bottom: 1.2rem; }
  label {
    display: block;
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }
  input {
    width: 100%;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
  }
  input:focus { border-color: var(--accent); }
  .btn {
    width: 100%;
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.85rem;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 0.95rem;
    cursor: pointer;
    margin-top: 0.5rem;
    transition: opacity 0.2s, transform 0.1s;
    letter-spacing: 0.02em;
  }
  .btn:hover { opacity: 0.9; transform: translateY(-1px); }
  .btn:active { transform: translateY(0); }
  .erro {
    background: rgba(255,80,80,0.1);
    border: 1px solid rgba(255,80,80,0.3);
    border-radius: 8px;
    padding: 0.75rem 1rem;
    color: #ff6b6b;
    font-size: 0.85rem;
    margin-bottom: 1.2rem;
  }
</style>
</head>
<body>
<div class="container">
  <div class="logo">Labirinto</div>
  <div class="subtitle">Sistema de Gestão · Grupo 19</div>
  <div class="card">
    <?php if ($erro): ?>
      <div class="erro"><?= htmlspecialchars($erro) ?></div>
    <?php endif; ?>
    <form method="POST">
      <div class="field">
        <label>Email</label>
        <input type="email" name="email" placeholder="grupo19@labirinto.pt" required>
      </div>
      <div class="field">
        <label>Password</label>
        <input type="password" name="password" placeholder="••••••••" required>
      </div>
      <button type="submit" class="btn">Entrar</button>
    </form>
  </div>
</div>
</body>
</html>
