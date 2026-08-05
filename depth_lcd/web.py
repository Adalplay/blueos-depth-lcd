from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from .state import AppState


class TitleRequest(BaseModel):
    title: str


def create_app(state: AppState, worker) -> FastAPI:
    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        worker.start()
        yield
        worker.stop()

    app = FastAPI(title="Depth LCD", version="1.0.0", lifespan=lifespan)

    @app.get("/register_service")
    def register_service() -> dict:
        return {
            "name": "Depth LCD",
            "description": "Profundidade do veículo e estado do LCD I2C",
            "icon": "mdi-waves-arrow-up",
            "company": "Adalplay",
            "version": "1.0.0",
            "webpage": "/",
            "api": "/docs",
            "new_page": False,
            "works_in_relative_paths": True,
        }

    @app.get("/api/status")
    def status() -> dict:
        return state.snapshot()

    @app.post("/api/settings/title")
    def change_title(request: TitleRequest) -> dict:
        title = request.title.strip()
        if not title or len(title) > 16:
            raise HTTPException(400, "O texto deve ter entre 1 e 16 caracteres")
        state.set_title(title)
        return {"ok": True, "title": title}

    @app.post("/api/lcd/test")
    def test_lcd() -> dict:
        state.request_test()
        return {"ok": True}

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return PAGE

    return app


PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Depth LCD</title>
  <style>
    :root { color-scheme: dark; font-family: Arial, sans-serif; }
    body { margin: 0; background: #101820; color: #eef6fa; }
    main { max-width: 720px; margin: auto; padding: 28px 18px; }
    h1 { font-size: 24px; font-weight: 500; }
    .card { background: #172630; border: 1px solid #294451; border-radius: 12px;
            padding: 24px; margin: 16px 0; }
    .label { color: #9db4c0; font-size: 14px; }
    .depth { color: #54d6ff; font-size: clamp(42px, 10vw, 72px); font-weight: 700;
             margin: 12px 0 20px; }
    .grid { display: grid; grid-template-columns: repeat(auto-fit,minmax(180px,1fr)); gap: 12px; }
    .status { background: #0f1c23; border-radius: 8px; padding: 12px; }
    .ok { color: #55df91; } .bad { color: #ff7b72; } .wait { color: #f5c451; }
    input, button { font: inherit; border-radius: 7px; padding: 10px 12px; }
    input { color: white; background: #0f1c23; border: 1px solid #45606d; }
    button { color: #07151c; background: #54d6ff; border: 0; cursor: pointer; font-weight: 600; }
    form { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 10px; }
    #message { min-height: 20px; margin-top: 10px; color: #9db4c0; }
  </style>
</head>
<body><main>
  <h1>Depth LCD</h1>
  <section class="card">
    <div class="label">Profundidade atual</div>
    <div id="depth" class="depth">--.-- metros</div>
    <div class="grid">
      <div class="status">MAVLink<br><strong id="mavlink" class="wait">Aguardando</strong></div>
      <div class="status">LCD<br><strong id="lcd" class="wait">Aguardando</strong></div>
      <div class="status">Fonte<br><strong id="source">--</strong></div>
      <div class="status">Última leitura<br><strong id="age">--</strong></div>
    </div>
    <p id="lcd-error" class="bad"></p>
  </section>
  <section class="card">
    <div class="label">Texto da primeira linha do LCD (máximo 16 caracteres)</div>
    <form id="title-form">
      <input id="title" maxlength="16" required>
      <button type="submit">Salvar texto</button>
      <button type="button" id="test">Testar LCD</button>
    </form>
    <div id="message"></div>
  </section>
<script>
const relative = path => new URL(path, window.location.href.endsWith('/') ? window.location.href : window.location.href + '/');
let titleLoaded = false;
async function refresh() {
  try {
    const response = await fetch(relative('api/status'));
    const data = await response.json();
    document.querySelector('#depth').textContent = data.depth_m == null ? '--.-- metros' : `${data.depth_m.toFixed(2)} metros`;
    setStatus('#mavlink', data.mavlink_connected, 'Conectado', 'Sem dados');
    setStatus('#lcd', data.lcd_connected, 'Conectado', 'Desconectado');
    document.querySelector('#source').textContent = data.source || '--';
    document.querySelector('#age').textContent = data.age_seconds == null ? '--' : `${data.age_seconds.toFixed(1)} s`;
    document.querySelector('#lcd-error').textContent = data.lcd_error || '';
    if (!titleLoaded) { document.querySelector('#title').value = data.title; titleLoaded = true; }
  } catch (_) { setStatus('#mavlink', false, '', 'Página sem comunicação'); }
}
function setStatus(selector, ok, yes, no) {
  const element = document.querySelector(selector);
  element.textContent = ok ? yes : no;
  element.className = ok ? 'ok' : 'bad';
}
document.querySelector('#title-form').addEventListener('submit', async event => {
  event.preventDefault();
  const title = document.querySelector('#title').value;
  const response = await fetch(relative('api/settings/title'), {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({title})});
  const result = await response.json();
  document.querySelector('#message').textContent = response.ok ? 'Texto atualizado.' : (result.detail || 'Erro ao atualizar.');
});
document.querySelector('#test').addEventListener('click', async () => {
  await fetch(relative('api/lcd/test'), {method:'POST'});
  document.querySelector('#message').textContent = 'Teste solicitado.';
});
refresh(); setInterval(refresh, 500);
</script>
</main></body></html>"""

