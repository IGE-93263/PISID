<?php
session_start();
if (!isset($_SESSION['utilizador'])) {
    header('Location: login.php');
    exit;
}

$host  = 'mysql';
$conn  = new mysqli($host, 'root', 'root', 'labirinto');
$equipa = $_SESSION['equipa'];
$id_sim = intval($_GET['id'] ?? 0);

if (!$id_sim) {
    header('Location: simulacoes.php');
    exit;
}

// Buscar simulação
$stmt = $conn->prepare("SELECT * FROM simulacao WHERE IDSimulacao = ? AND IDEquipa = ?");
$stmt->bind_param("ii", $id_sim, $equipa);
$stmt->execute();
$sim = $stmt->get_result()->fetch_assoc();
$stmt->close();

if (!$sim) {
    header('Location: simulacoes.php');
    exit;
}

$output   = '';
$iniciado = false;
$erro     = '';

// Botão Iniciar — lança o mqtt_to_mongo.py em background
if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['acao'])) {
    $acao = $_POST['acao'];

    if ($acao === 'iniciar') {
        // Caminho para o Python — ajusta conforme a tua máquina
        // Em Docker o PHP corre dentro do contentor, por isso usamos
        // exec() para lançar o script na máquina host via shell
        $grupo  = intval($equipa);
        $cmd    = "python /var/www/html/../Python/mqtt_to_mongo.py $grupo > /tmp/mqtt_to_mongo.log 2>&1 &";
        exec($cmd, $out, $code);

        if ($code === 0 || $code === 1) {
            $iniciado = true;
            $output   = "mqtt_to_mongo.py iniciado para o grupo $grupo.\nLog em: /tmp/mqtt_to_mongo.log";
        } else {
            $erro = "Erro ao iniciar o script (código $code).";
        }
    }

    if ($acao === 'status') {
        // Verifica se o processo está a correr
        exec("pgrep -f 'mqtt_to_mongo.py $equipa'", $pids);
        if (!empty($pids)) {
            $output = "Processo ativo. PID(s): " . implode(', ', $pids);
        } else {
            $output = "Nenhum processo mqtt_to_mongo.py ativo para o grupo $equipa.";
        }
    }

    if ($acao === 'parar') {
        exec("pkill -f 'mqtt_to_mongo.py $equipa'", $out, $code);
        $output = $code === 0 ? "Processo terminado." : "Nenhum processo encontrado para terminar.";
    }
}
?>
<!DOCTYPE html>
<html lang="pt">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Labirinto — Iniciar Simulação</title>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@400;600;800&family=DM+Mono:wght@300;400&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #0a0a0f; --surface: #12121a; --border: #2a2a3a;
    --accent: #7c6af7; --accent2: #4ecdc4; --text: #e8e8f0;
    --muted: #6a6a8a; --green: #4ade80; --red: #f87171; --yellow: #fbbf24;
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
  .main { max-width: 640px; margin: 0 auto; padding: 2rem; }
  h1 { font-family: 'Syne', sans-serif; font-weight: 700; font-size: 1.5rem; margin-bottom: 0.3rem; }
  .page-sub { color: var(--muted); font-size: 0.8rem; margin-bottom: 2rem; }
  .card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.2rem; }
  .card h2 { font-family: 'Syne', sans-serif; font-size: 0.95rem; font-weight: 600; color: var(--accent2); margin-bottom: 1rem; }
  .info-row { display: flex; justify-content: space-between; font-size: 0.82rem; padding: 0.5rem 0;
    border-bottom: 1px solid rgba(42,42,58,0.5); }
  .info-row:last-child { border-bottom: none; }
  .info-label { color: var(--muted); }
  .btn-group { display: flex; gap: 0.75rem; flex-wrap: wrap; margin-top: 1rem; }
  .btn {
    border: none; border-radius: 8px; padding: 0.75rem 1.4rem;
    font-family: 'Syne', sans-serif; font-weight: 600; font-size: 0.9rem;
    cursor: pointer; transition: opacity 0.2s; text-decoration: none; display: inline-block;
  }
  .btn-green  { background: var(--green);  color: #0a0a0f; }
  .btn-yellow { background: var(--yellow); color: #0a0a0f; }
  .btn-red    { background: var(--red);    color: #fff; }
  .btn:hover  { opacity: 0.85; }
  .console {
    background: #060608; border: 1px solid var(--border); border-radius: 8px;
    padding: 1rem; font-size: 0.8rem; color: var(--accent2);
    white-space: pre-wrap; min-height: 60px; margin-top: 1rem;
    line-height: 1.6;
  }
  .msg { border-radius: 8px; padding: 0.7rem 1rem; font-size: 0.83rem; margin-bottom: 1rem; }
  .msg-err { background: rgba(248,113,113,0.1); border: 1px solid rgba(248,113,113,0.3); color: var(--red); }
  .pulse { display: inline-block; width: 8px; height: 8px; border-radius: 50%;
    background: var(--green); margin-right: 0.5rem;
    animation: pulse 1.5s ease-in-out infinite; }
  @keyframes pulse { 0%,100%{opacity:1;transform:scale(1)} 50%{opacity:0.5;transform:scale(0.8)} }
</style>
</head>
<body>

<nav>
  <div class="nav-logo">Labirinto</div>
  <a class="nav-back" href="simulacoes.php">← Voltar às simulações</a>
</nav>

<div class="main">
  <h1>Iniciar Simulação</h1>
  <div class="page-sub">Lança os scripts Python para começar a recolha de dados</div>

  <?php if ($erro): ?>
    <div class="msg msg-err"><?= htmlspecialchars($erro) ?></div>
  <?php endif; ?>

  <!-- Info da simulação -->
  <div class="card">
    <h2>Detalhes</h2>
    <div class="info-row"><span class="info-label">ID</span><span>#<?= $sim['IDSimulacao'] ?></span></div>
    <div class="info-row"><span class="info-label">Descrição</span><span><?= htmlspecialchars($sim['Descricao']) ?></span></div>
    <div class="info-row"><span class="info-label">Equipa</span><span><?= $sim['IDEquipa'] ?></span></div>
    <div class="info-row"><span class="info-label">Início</span><span><?= $sim['DataHoraInicio'] ?></span></div>
  </div>

  <!-- Controlo -->
  <div class="card">
    <h2><?php if ($iniciado): ?><span class="pulse"></span><?php endif; ?>Controlo do Jogador</h2>
    <p style="font-size:0.82rem; color:var(--muted); margin-bottom:1rem;">
      O botão <strong style="color:var(--green)">Iniciar</strong> lança o <code>mqtt_to_mongo.py</code>
      em background — começa a receber dados MQTT e a guardar no MongoDB com deteção de gatilhos odd/even.
    </p>

    <div class="btn-group">
      <form method="POST" style="display:inline">
        <input type="hidden" name="acao" value="iniciar">
        <button type="submit" class="btn btn-green">▶ Iniciar</button>
      </form>
      <form method="POST" style="display:inline">
        <input type="hidden" name="acao" value="status">
        <button type="submit" class="btn btn-yellow">● Status</button>
      </form>
      <form method="POST" style="display:inline">
        <input type="hidden" name="acao" value="parar">
        <button type="submit" class="btn btn-red">■ Parar</button>
      </form>
    </div>

    <?php if ($output): ?>
      <div class="console"><?= htmlspecialchars($output) ?></div>
    <?php endif; ?>
  </div>

  <!-- Instrução manual -->
  <div class="card">
    <h2>Alternativa Manual</h2>
    <p style="font-size:0.82rem; color:var(--muted); margin-bottom:0.75rem;">
      Se o botão acima não funcionar (depende das permissões do Docker),
      corre manualmente no terminal do PC1:
    </p>
    <div class="console">python mqtt_to_mongo.py <?= $equipa ?></div>
  </div>
</div>

</body>
</html>
<?php $conn->close(); ?>
