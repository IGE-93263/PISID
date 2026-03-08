<?php
session_start();
if (!isset($_SESSION['utilizador'])) {
    header('Location: login.php');
    exit;
}

$host  = 'mysql';
$conn  = new mysqli($host, 'root', 'root', 'labirinto');
$erro  = '';
$sucesso = '';

$id_utilizador = $_SESSION['utilizador'];
$equipa        = $_SESSION['equipa'];

// Criar nova simulação
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['acao']) && $_POST['acao'] === 'criar') {
    $descricao = trim($_POST['descricao'] ?? '');
    if (empty($descricao)) {
        $erro = 'A descrição é obrigatória.';
    } else {
        $stmt = $conn->prepare("INSERT INTO simulacao (IDEquipa, IDUtilizador, Descricao, DataHoraInicio) VALUES (?, ?, ?, NOW())");
        $stmt->bind_param("iis", $equipa, $id_utilizador, $descricao);
        if ($stmt->execute()) {
            $sucesso = 'Simulação criada com sucesso!';
        } else {
            $erro = 'Erro ao criar simulação: ' . $conn->error;
        }
        $stmt->close();
    }
}

// Listar simulações da equipa
$simulacoes = [];
$result = $conn->query("SELECT s.IDSimulacao, s.Descricao, s.DataHoraInicio, u.Nome 
                         FROM simulacao s 
                         JOIN utilizador u ON s.IDUtilizador = u.IDUtilizador 
                         WHERE s.IDEquipa = $equipa 
                         ORDER BY s.IDSimulacao DESC");
if ($result) {
    while ($row = $result->fetch_assoc()) {
        $simulacoes[] = $row;
    }
}
?>
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Labirinto — Simulações</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f;
    --surface: #12121a;
    --surface2: #1a1a26;
    --border: #2a2a3a;
    --accent: #7c6af7;
    --accent2: #4ecdc4;
    --text: #e8e8f0;
    --muted: #6a6a8a;
    --green: #4ade80;
    --red: #f87171;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'DM Mono', monospace;
    min-height: 100vh;
    background-image: radial-gradient(ellipse at 10% 30%, rgba(124,106,247,0.07) 0%, transparent 55%);
  }
  nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 1.2rem 2rem;
    border-bottom: 1px solid var(--border);
    background: var(--surface);
  }
  .nav-logo {
    font-family: 'Syne', sans-serif;
    font-weight: 800;
    font-size: 1.2rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
  }
  .nav-user {
    display: flex;
    align-items: center;
    gap: 1rem;
    font-size: 0.8rem;
    color: var(--muted);
  }
  .nav-user a { color: var(--red); text-decoration: none; font-size: 0.75rem; }
  .nav-user a:hover { text-decoration: underline; }
  .main { max-width: 900px; margin: 0 auto; padding: 2rem; }
  h1 {
    font-family: 'Syne', sans-serif;
    font-weight: 700;
    font-size: 1.6rem;
    margin-bottom: 0.3rem;
  }
  .page-sub { color: var(--muted); font-size: 0.8rem; margin-bottom: 2rem; }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.5rem;
  }
  .card h2 {
    font-family: 'Syne', sans-serif;
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 1rem;
    color: var(--accent2);
  }
  .form-row { display: flex; gap: 1rem; align-items: flex-end; }
  input[type=text] {
    flex: 1;
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 8px;
    padding: 0.7rem 1rem;
    color: var(--text);
    font-family: 'DM Mono', monospace;
    font-size: 0.85rem;
    outline: none;
    transition: border-color 0.2s;
  }
  input[type=text]:focus { border-color: var(--accent); }
  .btn {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: 8px;
    padding: 0.7rem 1.4rem;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    font-size: 0.85rem;
    cursor: pointer;
    white-space: nowrap;
    transition: opacity 0.2s;
  }
  .btn:hover { opacity: 0.85; }
  .btn-sm {
    padding: 0.4rem 0.9rem;
    font-size: 0.78rem;
    border-radius: 6px;
  }
  .btn-green { background: var(--green); color: #0a0a0f; }
  .btn-outline {
    background: transparent;
    border: 1px solid var(--border);
    color: var(--text);
  }
  .btn-outline:hover { border-color: var(--accent); color: var(--accent); }
  table { width: 100%; border-collapse: collapse; font-size: 0.82rem; }
  th {
    text-align: left;
    padding: 0.6rem 0.8rem;
    color: var(--muted);
    font-size: 0.72rem;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    border-bottom: 1px solid var(--border);
  }
  td { padding: 0.8rem; border-bottom: 1px solid rgba(42,42,58,0.5); vertical-align: middle; }
  tr:last-child td { border-bottom: none; }
  tr:hover td { background: var(--surface2); }
  .id-badge {
    background: rgba(124,106,247,0.15);
    color: var(--accent);
    border-radius: 4px;
    padding: 0.2rem 0.5rem;
    font-size: 0.75rem;
  }
  .actions { display: flex; gap: 0.5rem; }
  .msg {
    border-radius: 8px;
    padding: 0.7rem 1rem;
    font-size: 0.83rem;
    margin-bottom: 1rem;
  }
  .msg-ok  { background: rgba(74,222,128,0.1); border: 1px solid rgba(74,222,128,0.3); color: var(--green); }
  .msg-err { background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.3); color: var(--red); }
  .empty { color: var(--muted); font-size: 0.83rem; text-align: center; padding: 2rem; }
</style>
</head>
<body>

<nav>
  <div class="nav-logo">Labirinto</div>
  <div class="nav-user">
    <span><?= htmlspecialchars($_SESSION['nome']) ?> · Equipa <?= $equipa ?></span>
    <a href="logout.php">Sair</a>
  </div>
</nav>

<div class="main">
  <h1>Simulações</h1>
  <div class="page-sub">Gere as simulações da tua equipa</div>

  <?php if ($sucesso): ?>
    <div class="msg msg-ok"><?= htmlspecialchars($sucesso) ?></div>
  <?php endif; ?>
  <?php if ($erro): ?>
    <div class="msg msg-err"><?= htmlspecialchars($erro) ?></div>
  <?php endif; ?>

  <!-- Criar simulação -->
  <div class="card">
    <h2>Nova Simulação</h2>
    <form method="POST">
      <input type="hidden" name="acao" value="criar">
      <div class="form-row">
        <input type="text" name="descricao" placeholder="Descrição da simulação..." required>
        <button type="submit" class="btn">Criar</button>
      </div>
    </form>
  </div>

  <!-- Lista de simulações -->
  <div class="card">
    <h2>As Minhas Simulações</h2>
    <?php if (empty($simulacoes)): ?>
      <div class="empty">Nenhuma simulação criada ainda.</div>
    <?php else: ?>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>Descrição</th>
            <th>Criado por</th>
            <th>Data Início</th>
            <th>Ações</th>
          </tr>
        </thead>
        <tbody>
          <?php foreach ($simulacoes as $s): ?>
          <tr>
            <td><span class="id-badge">#<?= $s['IDSimulacao'] ?></span></td>
            <td><?= htmlspecialchars($s['Descricao']) ?></td>
            <td><?= htmlspecialchars($s['Nome']) ?></td>
            <td><?= $s['DataHoraInicio'] ?></td>
            <td>
              <div class="actions">
                <a href="editar_simulacao.php?id=<?= $s['IDSimulacao'] ?>">
                  <button class="btn btn-sm btn-outline">Editar</button>
                </a>
                <a href="iniciar_simulacao.php?id=<?= $s['IDSimulacao'] ?>">
                  <button class="btn btn-sm btn-green">▶ Iniciar</button>
                </a>
              </div>
            </td>
          </tr>
          <?php endforeach; ?>
        </tbody>
      </table>
    <?php endif; ?>
  </div>
</div>

</body>
</html>
<?php $conn->close(); ?>
