const BACKEND = "https://manabia-backend.onrender.com";

// ==================== CHAT ====================
function abrirChat() {
  document.getElementById("chat-panel").classList.add("abierto");
  document.getElementById("chat-overlay").classList.add("abierto");
  document.getElementById("chat-input").focus();
}

function cerrarChat() {
  document.getElementById("chat-panel").classList.remove("abierto");
  document.getElementById("chat-overlay").classList.remove("abierto");
}

function preguntar(texto) {
  document.getElementById("chat-input").value = texto;
  enviarMensaje();
}

async function enviarMensaje() {
  const input = document.getElementById("chat-input");
  const texto = input.value.trim();
  if (!texto) return;

  agregarMensajeUsuario(texto);
  input.value = "";

  const typing = agregarTyping();

  try {
    const res = await fetch(`${BACKEND}/mana/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ texto })
    });
    const data = await res.json();
    typing.remove();
    agregarMensajeMana(data.respuesta || "Lo siento, no pude procesar tu consulta.");
  } catch (e) {
    typing.remove();
    agregarMensajeMana("Ups, parece que hay un problema de conexión. Intenta de nuevo en un momento.");
  }
}

function agregarMensajeUsuario(texto) {
  const div = document.createElement("div");
  div.className = "mensaje-usuario";
  div.textContent = texto;
  document.getElementById("chat-mensajes").appendChild(div);
  scrollChat();
}

function agregarMensajeMana(texto) {
  const div = document.createElement("div");
  div.className = "mensaje-mana";
  div.innerHTML = texto
    .replace(/\*([^*]+)\*/g, "<strong>$1</strong>")
    .replace(/\n/g, "<br>");
  document.getElementById("chat-mensajes").appendChild(div);
  scrollChat();
}

function agregarTyping() {
  const div = document.createElement("div");
  div.className = "typing";
  div.innerHTML = "<span></span><span></span><span></span>";
  document.getElementById("chat-mensajes").appendChild(div);
  scrollChat();
  return div;
}

function scrollChat() {
  const mensajes = document.getElementById("chat-mensajes");
  mensajes.scrollTop = mensajes.scrollHeight;
}

// ==================== BÚSQUEDA ====================
async function buscar() {
  const consulta = document.getElementById("buscador").value.trim();
  const canton = document.getElementById("filtro-canton").value;
  const categoria = document.getElementById("filtro-categoria").value;

  if (!consulta && !canton && !categoria) return;

  const params = new URLSearchParams();
  if (consulta) params.append("consulta", consulta);
  if (canton) params.append("canton", canton);
  if (categoria) params.append("categoria", categoria);

  try {
    const res = await fetch(`${BACKEND}/lugares?${params}`);
    const data = await res.json();
    mostrarResultados(data.lugares || []);
  } catch (e) {
    console.error("Error buscando:", e);
  }
}

function mostrarResultados(lugares) {
  const section = document.getElementById("resultados-section");
  const grid = document.getElementById("resultados-grid");

  grid.innerHTML = "";

  if (lugares.length === 0) {
    grid.innerHTML = `<p style="color:#666; grid-column:1/-1;">No encontramos resultados. Intenta con otros términos.</p>`;
  } else {
    lugares.forEach(lugar => {
      const card = document.createElement("div");
      card.className = "card-lugar";
      card.innerHTML = `
        <span class="tag">${lugar.Categoría || lugar.Subcategoría || "Lugar"}</span>
        <h3>${lugar.Nombre || ""}</h3>
        <p>${lugar.Descripción || ""}</p>
        <div class="info">
          📍 ${lugar.Parroquia || ""}, ${lugar.Cantón || ""}
          ${lugar.Horario ? `<br>🕐 ${lugar.Horario}` : ""}
          ${lugar.Teléfono ? `<br>📞 ${lugar.Teléfono}` : ""}
          ${lugar.Precio ? `<br>💰 ${lugar.Precio}` : ""}
        </div>
      `;
      grid.appendChild(card);
    });
  }

  section.style.display = "block";
  section.scrollIntoView({ behavior: "smooth" });
}

function filtrarCanton(canton) {
  document.getElementById("filtro-canton").value = canton;
  document.getElementById("buscador").value = "";
  buscar();
  document.getElementById("resultados-section").scrollIntoView({ behavior: "smooth" });
}

// ==================== VOZ ====================
let reconocimiento = null;
let escuchando = false;

function toggleVoz() {
  if (!("webkitSpeechRecognition" in window) && !("SpeechRecognition" in window)) {
    alert("Tu navegador no soporta reconocimiento de voz. Usa Chrome.");
    return;
  }

  if (escuchando) {
    reconocimiento.stop();
    return;
  }

  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  reconocimiento = new SR();
  reconocimiento.lang = "es-EC";
  reconocimiento.continuous = false;
  reconocimiento.interimResults = false;

  reconocimiento.onstart = () => {
    escuchando = true;
    document.getElementById("btn-voz").classList.add("escuchando");
  };

  reconocimiento.onresult = (e) => {
    const texto = e.results[0][0].transcript;
    document.getElementById("chat-input").value = texto;
    enviarMensaje();
  };

  reconocimiento.onend = () => {
    escuchando = false;
    document.getElementById("btn-voz").classList.remove("escuchando");
  };

  reconocimiento.onerror = () => {
    escuchando = false;
    document.getElementById("btn-voz").classList.remove("escuchando");
  };

  reconocimiento.start();
}

// Buscar con Enter en el buscador principal
document.getElementById("buscador").addEventListener("keypress", (e) => {
  if (e.key === "Enter") buscar();
});
