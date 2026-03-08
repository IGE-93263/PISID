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
$id_sim        = intval($_GET['id'] ?? 0);

if (!$id_sim) {
    header('Location: simulacoes.php');
    exit;
}

// Buscar simulação — só pode editar quem criou
$stmt = $conn->prepare("SELECT * FROM simulacao WHERE IDSimulacao = ? AND IDUtilizador = ?");
$stmt->bind_param("ii", $id_sim, $id_utilizador);
$stmt->execute();
$sim = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$sim) {
    header('Location: simulacoes.php');
    exit;
}

// Guardar alterações
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $descricao = trim($_POST['descricao'] ?? '');
    if (empty($descricao)) {
        $erro = 'A descrição não pode estar vazia.';
    } else {
        // Não permite alterar FKs (IDEquipa, IDUtilizador) conforme enunciado
        $stmt = $conn->prepare("UPDATE simulacao SET Descricao = ? WHERE IDSimulacao = ? AND IDUtilizador = ?");
        $stmt->bind_param("sii", $descricao, $id_sim, $id_utilizador);
        if ($stmt->execute()) {
            $sucesso = 'Simulação atualizada com sucesso!';
            $sim['Descricao'] = $descricao;
        } else {
            $erro = 'Erro ao guardar: ' . $conn->error;
        }
        $stmt->close();
    }
}
?>
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Labirinto — Editar Simulação</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f; --surface: #12121a; --border: #2a2a3a;
    --accent: #7c6af7; --accent2: #4ecdc4; --text: #e8e8f0;
    --muted: #6a6a8a; --green: #4ade80; --red: #f87171;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { background: var(--bg); color: var(--text); font-family: 'DM Mono', monospace; min-height: 100vh; }
  nav {
    display: flex; align-items: center; justify-content: space-between;
    padding: 1.2rem 2rem; border-bottom: 1px solid var(--border); background: var(--surface);
  }
  .nav-logo { font-family: 'Syne', sans-serif; font-weight: 800; font-size: 1.2rem;
    background: linear-gradient(135deg, var(--accent), var(--accent2));
    -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  .nav-back { color: var(--muted); text-decoration: none; font-size: 0.8rem; }
  .nav-back:hover { color: var(--text); }
  .main { max-width: 600px; margin: 0 auto; padding: 2rem; }
  h1 { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.5rem; margin-bottom: 0.3rem; }
  .page-sub { color: var(--muted); font-size: 0.8rem; margin-bottom: 2rem; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; }
  .field { margin-bottom: 1.2rem; }
  label { display: block; font-size: 0.72rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--muted); margin-bottom: 0.5rem; }
  input[type=text], input[type=number] {
    width: 100%; background: var(--bg); border: 1px solid var(--border);
    border-radius: 8px; padding: 0.7rem 1rem; color: var(--text);
    font-family: 'DM Mono', monospace; font-size: 0.85rem; outline: none; transition: border-color 0.2s;
  }
  input:focus { border-color: var(--accent); }
  input[disabled] { opacity: 0.4; cursor: not-allowed; }
  .note { color: var(--muted); font-size: 0.72rem; margin-top: 0.3rem; }
  .btn { background: var(--accent); color: #fff; border: none; border-radius: 8px;
    padding: 0.75rem 1.5rem; font-family: 'Syne', sans-serif; font-weight: 600;
    font-size: 0.9rem; cursor: pointer; transition: opacity 0.2s; }
  .btn:hover { opacity: 0.85; }
  .msg { border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.83rem; margin-bottom: 1rem; }
  .msg-ok  { background: rgba(74,222,128,0.1); border: 1px solid rgba(74,222,128,0.3); color: var(--green); }
  .msg-err { background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.3); color: var(--red); }
  .divider { border: none; border-top: 1px solid var(--border); margin: 1.5rem 0; }
  .id-row { display: flex; gap: 1rem; }
  .id-row .field { flex: 1; }
</style>
</head>
<body>

<nav>
  <div class="nav-logo">Labirinto</div>
  <a class="nav-back" href="simulacoes.php">← Voltar às simulações</a>
</nav>

<div class="main">
  <h1>Editar Simulação #<?= $id_sim ?></h1>
  <div class="page-sub">Apenas podes editar simulações que criaste</div>

  <?php if ($sucesso): ?>
    <div class="msg msg-ok"><?= htmlspecialchars($sucesso) ?></div>
  <?php endif; ?>
  <?php if ($erro): ?>
    <div class="msg msg-err"><?= htmlspecialchars($erro) ?></div>
  <?php endif; ?>

  <div class="card">
    <form method="POST">

      <!-- Campos não editáveis (FKs) -->
      <div class="id-row">
        <div class="field">
          <label>ID Simulação</label>
          <input type="number" value="<?= $sim['IDSimulacao'] ?>" disabled>
          <div class="note">Chave primária — não editável</div>
        </div>
        <div class="field">
          <label>ID Equipa</label>
          <input type="number" value="<?= $sim['IDEquipa'] ?>" disabled>
          <div class="note">Chave estrangeira — não editável</div>
        </div>
      </div>

      <hr class="divider">

      <!-- Campo editável -->
      <div class="field">
        <label>Descrição</label>
        <input type="text" name="descricao" value="<?= htmlspecialchars($sim['Descricao']) ?>" required>
      </div>

      <button type="submit" class="btn">Guardar Alterações</button>
    </form>
  </div>
</div>

</body>
</html>
<?php $conn->close(); ?>
