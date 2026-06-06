/* =========================================
   BINGO SOCKET JS - Motor de Tiempo Real
   ========================================= */

// Usamos window.BINGO_CONFIG para evitar el error de "already declared"
const BINGO_VAR = typeof window.BINGO_CONFIG !== 'undefined' ? window.BINGO_CONFIG : (typeof BINGO_CONFIG !== 'undefined' ? BINGO_CONFIG : null);

if (BINGO_VAR) {
    const protocolo = window.location.protocol === 'https:' ? 'wss://' : 'ws://';
    const wsUrl = protocolo + window.location.host + '/ws/juego/' + BINGO_VAR.id_partida + '/';
    
    console.log("Intentando conectar al servidor de juego en:", wsUrl);

    window.bingoSocket = new WebSocket(wsUrl);

    bingoSocket.onopen = function(e) {
        console.log("🟢 Conectado al sistema de eventos en tiempo real.");
    };

    bingoSocket.onmessage = function(e) {
        const payload = JSON.parse(e.data);
        console.log("📩 Evento recibido:", payload);

        if (payload.canal === 'partida') {
            // 1. EL MEGÁFONO: Avisamos a cualquier pantalla HTML que esté abierta
            document.dispatchEvent(new CustomEvent('evento_partida', { detail: payload.datos }));
            
            // 2. Colorear la matriz del Administrador (Si el admin está viendo su tablero)
            if (payload.datos.evento === 'nueva_bola') {
                const bolaMaestra = document.getElementById(`bola-maestra-${payload.datos.numero}`);
                if (bolaMaestra) {
                    bolaMaestra.classList.remove('ball-pending');
                    bolaMaestra.classList.add('ball-called');
                    const colorClass = bolaMaestra.getAttribute('data-color');
                    if(colorClass) bolaMaestra.classList.add(colorClass);
                }
            }
            // 3. NUEVO: ALERTA GLOBAL DEL ADMINISTRADOR (TIPO TOAST EMERGENTE)
            // 3. NUEVO: ALERTA GLOBAL DEL ADMINISTRADOR (TIPO TOAST EMERGENTE)
            else if (payload.datos.evento === 'alerta_admin') {
                
                // DETECTOR: Si existe el input del admin en la pantalla, significa que SOY el admin.
                const soyAdmin = document.getElementById('admin-mensaje-input') !== null;
                
                // Solo dibujamos la alerta si somos un jugador normal
                if (!soyAdmin) {
                    const toastContainer = document.getElementById('admin-toast-container') || (() => {
                        const tc = document.createElement('div');
                        tc.id = 'admin-toast-container';
                        tc.className = 'toast-container position-fixed top-0 start-50 translate-middle-x p-3 mt-2';
                        tc.style.zIndex = '10500';
                        document.body.appendChild(tc);
                        return tc;
                    })();

                    const toastId = 'toast-' + Date.now();
                    const toastHtml = `
                        <div id="${toastId}" class="toast align-items-center text-bg-danger border-0 shadow-lg animate__animated animate__bounceInDown" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="6000">
                            <div class="d-flex">
                                <div class="toast-body fs-6 fw-bold text-center w-100 p-3">
                                    <i class="fas fa-bullhorn fs-4 d-block mb-2 text-warning"></i> 
                                    ${payload.datos.mensaje}
                                </div>
                                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast" aria-label="Close"></button>
                            </div>
                        </div>
                    `;
                    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
                    const toastElement = document.getElementById(toastId);
                    const toast = new bootstrap.Toast(toastElement);
                    toast.show();
                    
                    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
                }
            }
            // 4. NUEVO: ALERTA DE RECLAMO DE BINGO (FASE 2)
            else if (payload.datos.evento === 'alerta_reclamo') {
                const aliasGanador = payload.datos.alias;
                const codigoCarton = payload.datos.codigo;
                
                const esAdmin = document.querySelector('.master-board') !== null;
                
                if (esAdmin) {
                    // A) Ponemos la medallita y borde rojo intermitente en el radar lateral
                    const lista = document.getElementById('lista-jugadores-conectados');
                    if (lista) {
                        let items = Array.from(lista.getElementsByTagName('li'));
                        let liGanador = items.find(li => li.innerText.includes(aliasGanador));
                        if (liGanador) {
                            liGanador.classList.remove('border-light');
                            liGanador.classList.add('border-danger', 'border-2', 'bg-danger-subtle', 'animate__animated', 'animate__flash');
                            
                            const viejaMedalla = liGanador.querySelector('.medalla-bingo');
                            if(viejaMedalla) viejaMedalla.remove();
                            
                            liGanador.innerHTML += `<span class="medalla-bingo badge bg-danger ms-auto animate__animated animate__tada animate__infinite shadow"><i class="fas fa-trophy"></i> BINGO</span>`;
                        }
                    }
                    
                    // B) Tiramos un Toast gigante en el centro de la pantalla del administrador
                    const toastContainer = document.getElementById('admin-toast-container') || (() => {
                        const tc = document.createElement('div');
                        tc.id = 'admin-toast-container';
                        tc.className = 'toast-container position-fixed top-50 start-50 translate-middle p-3';
                        tc.style.zIndex = '10500';
                        document.body.appendChild(tc);
                        return tc;
                    })();

                    const toastId = 'toast-bingo-' + Date.now();
                    const toastHtml = `
                        <div id="${toastId}" class="toast align-items-center text-bg-warning border-0 shadow-lg animate__animated animate__tada" role="alert" aria-live="assertive" aria-atomic="true" data-bs-delay="15000">
                            <div class="d-flex flex-column">
                                <div class="toast-body fs-5 text-center p-4 text-dark">
                                    <i class="fas fa-trophy fs-1 d-block mb-3 text-danger animate__animated animate__pulse animate__infinite"></i> 
                                    <h3 class="fw-black text-danger mb-3">¡RECLAMO DE BINGO!</h3>
                                    El jugador <b>${aliasGanador}</b> afirma haber ganado con el cartón <br><span class="badge bg-dark mt-2 fs-6">${codigoCarton}</span>.<br>
                                </div>
                                <button type="button" class="btn btn-dark w-100 rounded-0 rounded-bottom py-2 fw-bold" data-bs-dismiss="toast">ENTENDIDO</button>
                            </div>
                        </div>
                    `;
                    toastContainer.insertAdjacentHTML('beforeend', toastHtml);
                    const toastElement = document.getElementById(toastId);
                    const toast = new bootstrap.Toast(toastElement);
                    toast.show();
                    toastElement.addEventListener('hidden.bs.toast', () => toastElement.remove());
                }
            }
        } 
        else if (payload.canal === 'chat') {
            const cajaChat = document.getElementById('chat-mensajes');
            if (cajaChat) {
                // Comprobamos si el mensaje lo enviaste TÚ
                const esMiMensaje = (payload.usuario === (BINGO_VAR && BINGO_VAR.mi_alias));
                
                const nuevoMensaje = document.createElement('div');
                
                // Alineación: Derecha si es tuyo, Izquierda si es de un rival
                nuevoMensaje.className = `mb-3 d-flex flex-column ${esMiMensaje ? 'align-items-end' : 'align-items-start'} animate__animated animate__fadeInUp animate__faster`;
                
                // Colores tipo WhatsApp
                const colorFondo = esMiMensaje ? 'bg-primary text-white shadow-sm' : 'bg-light text-dark border shadow-sm';
                const colorNombre = esMiMensaje ? 'text-primary' : 'text-secondary';
                const nombreAlias = esMiMensaje ? 'Tú' : payload.usuario;
                
                nuevoMensaje.innerHTML = `
                    <span class="small fw-bold ${colorNombre} mb-1 px-1" style="font-size: 0.70rem; letter-spacing: 0.5px;">${nombreAlias}</span>
                    <div class="px-3 py-2 rounded-4 ${colorFondo}" style="max-width: 90%; word-break: break-word; font-size: 0.9rem; line-height: 1.4;">
                        ${payload.mensaje}
                    </div>
                `;
                
                cajaChat.appendChild(nuevoMensaje);
                // Auto-scroll hacia abajo
                cajaChat.scrollTop = cajaChat.scrollHeight;
            }
        }
        // ==========================================
        // LA ZONA BLINDADA: FRANCOTIRADOR DATA-ALIAS Y MATEMÁTICAS REALES
        // ==========================================
        else if (payload.canal === 'presencia') {
            const listas = document.querySelectorAll('.lista-jugadores-dinamica');
            const contadores = document.querySelectorAll('.contador-dinamico');
            const alias = payload.alias.trim();

            if (payload.accion === 'entrar') {
                listas.forEach(lista => {
                    // Francotirador: Buscamos exactamente el elemento por su data-alias invisible
                    let itemExistente = lista.querySelector(`li[data-alias="${alias}"]`);

                    if (itemExistente) {
                        // Si era un fantasma a punto de borrarse, lo rescatamos
                        if (itemExistente.classList.contains('saliendo-fantasma')) {
                            itemExistente.classList.remove('saliendo-fantasma', 'animate__fadeOutRight');
                            itemExistente.classList.add('animate__fadeInLeft');
                        }
                    } else {
                        const vacio = lista.querySelector('.fa-ghost, .fa-user-clock');
                        if (vacio) vacio.closest('li').remove();

                        const li = document.createElement('li');
                        li.setAttribute('data-alias', alias); // Le pegamos el rastreador al nuevo nodo
                        
                        // Diferenciamos el diseño si es el panel lateral o la tarjeta principal
                        const esPanel = lista.closest('#panelSocial') !== null;
                        li.className = esPanel 
                            ? 'list-group-item bg-transparent text-body d-flex align-items-center py-3 animate__animated animate__fadeInLeft'
                            : 'list-group-item d-flex align-items-center py-3 animate__animated animate__fadeInLeft';

                        li.innerHTML = `
                            <div class="text-white rounded-circle d-flex justify-content-center align-items-center me-3 flex-shrink-0" 
                                 style="width: 35px; height: 35px; font-weight: bold; background-color: #4F46E5;">
                                ${alias.charAt(0).toUpperCase()}
                            </div>
                            <span class="fw-bold ${esPanel ? '' : 'text-secondary'} text-truncate">${alias}</span>
                        `;
                        lista.appendChild(li);
                    }
                });

                // MATEMÁTICAS REALES: En vez de "+1", contamos los nodos HTML que existen. Cero errores (NaN).
                if (listas.length > 0) {
                    const totalReales = listas[0].querySelectorAll('li[data-alias]:not(.saliendo-fantasma)').length;
                    contadores.forEach(c => c.textContent = totalReales);
                }

            } else if (payload.accion === 'salir') {
                listas.forEach(lista => {
                    let itemExistente = lista.querySelector(`li[data-alias="${alias}"]`);

                    if (itemExistente && !itemExistente.classList.contains('saliendo-fantasma')) {
                        itemExistente.classList.add('saliendo-fantasma', 'animate__fadeOutRight');
                        itemExistente.classList.remove('animate__fadeInLeft');
                        
                        setTimeout(() => {
                            if (itemExistente.classList.contains('saliendo-fantasma')) {
                                itemExistente.remove();
                                
                                // Volvemos a contar la realidad del HTML
                                const totalReales = lista.querySelectorAll('li[data-alias]:not(.saliendo-fantasma)').length;
                                contadores.forEach(c => c.textContent = totalReales);
                                
                                // Si no queda nadie, ponemos el mensaje de vacío correspondiente
                                if (totalReales === 0 && !lista.querySelector('.fa-ghost, .fa-user-clock')) {
                                    const esPanel = lista.closest('#panelSocial') !== null;
                                    lista.innerHTML = esPanel
                                        ? `<li class="list-group-item bg-transparent border-0 text-center text-body-secondary py-5">
                                            <i class="fas fa-ghost fs-1 mb-3 text-muted"></i><br>
                                            No hay rivales en la sala aún.
                                           </li>`
                                        : `<li class="list-group-item text-center text-muted py-4">
                                            <i class="fas fa-user-clock mb-2 fs-3 animate__animated animate__fadeInDown"></i><br>
                                            Eres el primero en llegar.
                                           </li>`;
                                }
                            }
                        }, 1000); // 1 segundo de gracia
                    }
                });
            }
        }
        
    };

    // Chat Logic
    document.addEventListener('DOMContentLoaded', () => {
        const chatInput = document.getElementById('chat-input');
        const chatBtn = document.getElementById('chat-btn-enviar');
        if (chatInput && chatBtn) {
            function enviarMensajeChat() {
                if (chatInput.value.trim() !== '') {
                    window.bingoSocket.send(JSON.stringify({ 'tipo': 'chat', 'mensaje': chatInput.value.trim() }));
                    chatInput.value = ''; 
                }
            }
            chatBtn.addEventListener('click', enviarMensajeChat);
            chatInput.addEventListener('keyup', (e) => { if (e.key === 'Enter') enviarMensajeChat(); });
        }
    });
}