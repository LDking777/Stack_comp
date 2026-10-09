import { useState, useEffect } from 'react';

const easeOutExpo = (t) => {
  return t === 1 ? 1 : 1 - Math.pow(2, -10 * t);
};

/**
 * Hook para animar números de 0 al valor final suavemente.
 * 
 * @param {number} end - El valor final objetivo.
 * @param {number} duration - Duración de la animación en milisegundos.
 * @param {boolean} isFloat - Si es true, el valor se trata como flotante.
 * @param {number} decimals - Cantidad de decimales si isFloat es true.
 * @returns {number} El valor actual del contador.
 */
export const useCountUp = (end, duration = 2000, isFloat = false, decimals = 2) => {
  const [count, setCount] = useState(0);

  useEffect(() => {
    let startTime = null;
    let animationFrameId;

    // Si no es un número válido, no hacer nada y devolver el target directamente
    if (end === null || end === undefined || isNaN(end)) {
        setCount(end);
        return;
    }

    const animate = (currentTime) => {
      if (!startTime) startTime = currentTime;
      const progress = currentTime - startTime;
      const t = Math.min(progress / duration, 1);
      
      // Aplicar función de ease
      const easedProgress = easeOutExpo(t);
      const currentCount = easedProgress * end;

      if (isFloat) {
        setCount(parseFloat(currentCount.toFixed(decimals)));
      } else {
        setCount(Math.round(currentCount));
      }

      if (t < 1) {
        animationFrameId = requestAnimationFrame(animate);
      } else {
        // Asegurar que termine exactamente en el valor objetivo
        setCount(end); 
      }
    };

    animationFrameId = requestAnimationFrame(animate);

    return () => {
      if (animationFrameId) cancelAnimationFrame(animationFrameId);
    };
  }, [end, duration, isFloat, decimals]);

  return count;
};
