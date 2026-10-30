const $ = (id) => document.getElementById(id);
const formatTime = (seconds) => {
  const s = Math.max(0, Number(seconds || 0));
  const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  return h ? `${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}` :
    `${String(m).padStart(2,'0')}:${String(sec).padStart(2,'0')}`;
};
function renderTables(tables) {
  const grid = $("tableGrid");
  if (!tables.length) { grid.innerHTML = '<div class="empty">Aucune table configurée.</div>'; return; }
  grid.innerHTML = tables.map(t => `
    <div class="table-card ${t.occupied ? 'occupied' : ''}">
      <div><div class="table-name">${t.name}</div><small>${t.people_count} personne(s) détectée(s)</small></div>
      <div class="table-right"><div class="table-time">${t.occupied ? formatTime(t.occupied_seconds) : '--:--'}</div>
      <div class="status">${t.occupied ? '● OCCUPÉE' : '● LIBRE'}</div></div>
    </div>`).join('');
}
async function refresh() {
  try {
    const response = await fetch('/api/state', {cache:'no-store'});
    const data = await response.json();
    const s = data.summary, c = data.camera;
    $('occupied').textContent = s.occupied_tables;
    $('free').textContent = s.free_tables;
    $('people').textContent = s.people_detected;
    $('totalTables').textContent = s.total_tables;
    $('avg').textContent = formatTime(s.average_occupancy_seconds);
    $('fps').textContent = `${c.fps} FPS`;
    $('cameraName').textContent = `Caméra ${c.camera_index}`;
    $('modelName').textContent = c.model || 'YOLO';
    const ok = c.camera_ok && c.model_ok;
    $('systemLabel').textContent = ok ? 'Système opérationnel' : 'Initialisation / vérification';
    $('visionState').textContent = ok ? 'Analyse active' : 'En attente';
    $('visionDetail').textContent = c.last_error || (ok ? 'Détection et suivi en cours.' : 'Vérifiez la webcam et le démarrage du modèle.');
    $('videoOverlay').style.display = c.camera_ok ? 'none' : 'block';
    renderTables(data.tables);
  } catch (e) {
    $('systemLabel').textContent = 'Serveur inaccessible';
    $('visionState').textContent = 'Connexion perdue';
    $('visionDetail').textContent = 'Vérifiez que le serveur RESTO-VISION est démarré.';
    $('videoOverlay').style.display = 'block';
  }
}
setInterval(refresh, 1000);
refresh();
