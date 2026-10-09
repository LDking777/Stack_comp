let audioCtx = null;
let soundEnabled = true;

const initAudioContext = () => {
  try {
    if (!audioCtx) {
      const AudioContext = window.AudioContext || window.webkitAudioContext;
      if (AudioContext) {
        audioCtx = new AudioContext();
      }
    }
    if (audioCtx && audioCtx.state === 'suspended') {
      audioCtx.resume().catch(() => {});
    }
  } catch (e) {
    console.warn("AudioContext init failed", e);
  }
};

export const toggleSound = () => {
  soundEnabled = !soundEnabled;
  return soundEnabled;
};

export const toggleSoundEnabled = toggleSound;

export const isSoundEnabled = () => soundEnabled;

export const playTone = (type = 'default') => {
  if (!soundEnabled) return;
  initAudioContext();
  
  if (!audioCtx) return;

  try {
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    
    const now = audioCtx.currentTime;
    let freq = 440; // default
    
    switch(type) {
      case 'high':
        freq = 880;
        break;
      case 'low':
        freq = 220;
        break;
      case 'warning':
        freq = 150;
        break;
      case 'default':
      default:
        freq = 440;
        break;
    }
    
    oscillator.type = type === 'warning' ? 'square' : 'sine';
    oscillator.frequency.setValueAtTime(freq, now);
    
    // Envelope
    gainNode.gain.setValueAtTime(0, now);
    gainNode.gain.linearRampToValueAtTime(0.1, now + 0.05);
    gainNode.gain.exponentialRampToValueAtTime(0.001, now + 0.3);
    
    oscillator.start(now);
    oscillator.stop(now + 0.3);
  } catch (e) {
    // Fail silently
  }
};
