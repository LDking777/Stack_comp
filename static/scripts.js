document.addEventListener('DOMContentLoaded', () => {
    // --- ELEMENTOS DEL DOM ---
    const chatToggle = document.getElementById('ai-chat-toggle');
    const chatClose = document.getElementById('ai-chat-close');
    const chatWindow = document.getElementById('ai-chat-window');
    const chatInput = document.getElementById('ai-chat-input');
    const chatSendBtn = document.getElementById('ai-chat-send');
    const chatMessages = document.getElementById('ai-chat-messages');
    
    // Botones de control
    const micBtn = document.getElementById('ai-chat-mic');
    const micIcon = document.getElementById('mic-icon');
    const speakerBtn = document.getElementById('ai-toggle-speaker');
    const speakerIcon = document.getElementById('speaker-icon');

    // --- VARIABLES DE ESTADO ---
    let mediaRecorder;
    let audioChunks = [];
    let isRecording = false;
    let isSpeakerEnabled = false; // Muteado por defecto

    // --- 1. LÓGICA DE APERTURA/CIERRE ---
    const toggleChat = () => chatWindow.classList.toggle('hidden');
    chatToggle.addEventListener('click', toggleChat);
    chatClose.addEventListener('click', toggleChat);

    // --- 2. LÓGICA DE BOCINA (LECTURA DE RESPUESTA) ---
    speakerBtn.addEventListener('click', () => {
        isSpeakerEnabled = !isSpeakerEnabled;
        if (isSpeakerEnabled) {
            speakerIcon.className = "fa-solid fa-volume-high";
            speakerBtn.classList.remove('muted');
        } else {
            speakerIcon.className = "fa-solid fa-volume-xmark";
            speakerBtn.classList.add('muted');
            window.speechSynthesis.cancel(); // Detener lectura si se apaga
        }
    });

    const leerEnVozAlta = (texto) => {
        if (!isSpeakerEnabled) return;
        // Limpiamos Markdown para que la voz no lea asteriscos o hashtags
        const textoLimpio = texto.replace(/[#*`_]/g, '');
        const utterance = new SpeechSynthesisUtterance(textoLimpio);
        utterance.lang = 'es-MX'; // Español
        window.speechSynthesis.speak(utterance);
    };

    // --- 3. FUNCIÓN PARA AGREGAR MENSAJES A LA UI ---
    
    // 🛡️ SEGURIDAD CORREGIDA: Función para neutralizar código malicioso (Evita ataques XSS)
    const escapeHTML = (str) => {
        if (!str) return "";
        return str.toString().replace(/[&<>'"]/g, 
            tag => ({
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                "'": '&#39;',
                '"': '&quot;'
            }[tag] || tag));
    };

    // 💡 AÑADIMOS EL PARÁMETRO "isHTML=false" PARA EXCEPCIONES SEGURAS COMO LA ANIMACIÓN
    const appendMessage = (text, sender, source = null, timeTaken = null, isHTML = false) => {
        const msgDiv = document.createElement('div');
        msgDiv.classList.add('ai-msg', sender);
        
        const avatar = sender === 'bot' ? '🤖' : '👤';
        
        let content;
        if (sender === 'bot' && typeof marked !== 'undefined') {
            content = marked.parse(text); // Confiamos en el bot, procesamos su Markdown
        } else if (isHTML) {
            content = text; // 💡 Si le decimos explícitamente que es HTML seguro (nuestra animación), lo deja pasar.
        } else {
            // 🛡️ Si es un texto normal del usuario, lo blindamos.
            content = escapeHTML(text); 
        }
        
        const infoHtml = source ? `<div style="font-size: 0.75em; color: #888; margin-top: 4px;">⚡ ${source} en ${timeTaken}s</div>` : '';
        
        msgDiv.innerHTML = `
            <div class="ai-msg-avatar">${avatar}</div>
            <div class="ai-msg-content">
                <div class="ai-msg-bubble">${content}</div>
                ${infoHtml}
            </div>
        `;
        
        chatMessages.appendChild(msgDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        return msgDiv;
    };

    // --- 4. ENVÍO DE TEXTO AL BACKEND (CARRERA DE IAs) ---
    const sendMessageToServer = async (text) => {
        // Mostramos indicador de que el bot está pensando si no viene de audio
        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: text })
            });

            const data = await response.json();

            if (response.ok) {
                appendMessage(data.response, 'bot', data.source, data.time_taken);
                leerEnVozAlta(data.response);
            } else {
                appendMessage("Lo siento, hubo un error en la carrera de IAs.", "bot");
            }
        } catch (error) {
            console.error("Error:", error);
            appendMessage("Error de conexión con el servidor.", "bot");
        }
    };

    // --- 5. LÓGICA DE GRABACIÓN Y ANIMACIÓN ---
    const startRecording = async () => {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            mediaRecorder = new MediaRecorder(stream);
            audioChunks = [];

            mediaRecorder.ondataavailable = (e) => audioChunks.push(e.data);
            
            mediaRecorder.onstop = async () => {
                const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });

                // Inyectamos la animación de ondas pulsantes
                const waveHtml = `
                    <div class="ai-msg-wave-dots">
                        <span class="ai-msg-wave-dot"></span>
                        <span class="ai-msg-wave-dot"></span>
                        <span class="ai-msg-wave-dot"></span>
                    </div>
                `;
                // 💡 AQUÍ ESTÁ EL TRUCO: Le pasamos "true" al final para que no rompa el HTML.
                const tempMsg = appendMessage(waveHtml, "user", null, null, true);
                tempMsg.querySelector('.ai-msg-bubble').classList.add('loading-bubble');

                const formData = new FormData();
                formData.append('audio', audioBlob);

                try {
                    // Enviamos a Whisper
                    const res = await fetch('/transcribe', { method: 'POST', body: formData });
                    const data = await res.json();
                    
                    tempMsg.remove(); // Quitamos la animación

                    if (data.text) {
                        appendMessage(data.text, 'user'); // Ponemos lo que el usuario dijo (ahora blindado)
                        sendMessageToServer(data.text);   // Se lo mandamos a la IA
                    }
                } catch (err) {
                    tempMsg.remove();
                    appendMessage("❌ Error al procesar audio.", "bot");
                }
            };

            mediaRecorder.start();
            isRecording = true;
            micBtn.classList.replace('muted', 'recording');
            micIcon.className = "fa-solid fa-microphone";
            chatInput.placeholder = "Escuchando...";
        } catch (err) {
            alert("No se pudo acceder al micrófono. Revisa los permisos.");
        }
    };

    const stopRecording = () => {
        if (mediaRecorder) mediaRecorder.stop();
        isRecording = false;
        micBtn.classList.replace('recording', 'muted');
        micIcon.className = "fa-solid fa-microphone-slash";
        chatInput.placeholder = "Escribe algo...";
    };

    // --- 6. EVENTOS DE DISPARO ---
    micBtn.addEventListener('click', () => {
        if (!isRecording) startRecording();
        else stopRecording();
    });

    const handleSend = () => {
        const text = chatInput.value.trim();
        if (!text) return;
        appendMessage(text, 'user');
        chatInput.value = '';
        sendMessageToServer(text);
    };

    chatSendBtn.addEventListener('click', handleSend);

    chatInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    });
});