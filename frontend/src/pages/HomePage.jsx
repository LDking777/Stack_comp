import { Activity, MessageCircle, ShieldCheck } from "lucide-react";

export default function HomePage({ children, onOpenWhatsApp }) {
  return (
    <main className="home-page">
      <div className="home-grid-glow" aria-hidden="true" />
      <section className="home-stage">
        <div className="home-agent">
          <div className="home-eyebrow">
            <span className="home-status-dot" />
            AGENTE VOCAL COGNITIVO · NEXO IA
          </div>

          <div className="home-avatar-frame">
            <img
              className="home-avatar"
              src="/avatar.jpg"
              alt="Avatar de Nexo IA"
              fetchPriority="high"
            />
            <div className="home-avatar-label">
              <div className="home-avatar-status">
                <span className="home-status-dot" />
                LISTA PARA CONVERSAR
              </div>
              <p>Nexo IA <span>· Analista de IPS</span></p>
            </div>
          </div>

          <div className="home-copy">
            <p className="home-kicker">INTELIGENCIA PARA EL SISTEMA DE SALUD</p>
            <h1>Tu analista de IPS, <span>lista para escucharte.</span></h1>
            <p className="home-description">
              Pregunta por cobertura y capacidad instalada en Colombia, o carga
              documentos del sector salud para consultarlos en esta conversación.
            </p>
          </div>

          <div className="home-assurances">
            <div>
              <ShieldCheck size={17} />
              <span>Cifras verificadas con datos.gov.co</span>
            </div>
            <div>
              <Activity size={17} />
              <span>Especializada en IPS de Colombia</span>
            </div>
            {onOpenWhatsApp && (
              <button
                type="button"
                className="home-assurance-action"
                onClick={onOpenWhatsApp}
              >
                <MessageCircle size={17} />
                <span>Disponible en WhatsApp</span>
              </button>
            )}
          </div>
        </div>

        <div className="home-chat-shell">
          <div className="home-chat-heading">
            <span>CONVERSACIÓN</span>
            <span className="home-chat-source"><span className="home-status-dot" /> DATOS PÚBLICOS · REPS</span>
          </div>
          {children}
        </div>
      </section>

      <footer className="home-footer">
        <span>FUENTE DE DATOS · MIN SALUD / REPS</span>
        <span>Dataset público con corte a noviembre de 2022</span>
      </footer>
    </main>
  );
}
