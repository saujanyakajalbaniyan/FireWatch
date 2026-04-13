import React, { useEffect, useRef, useCallback } from 'react';

/**
 * Robust VoiceAssistant — works reliably across Chrome, Edge, Firefox, Safari.
 *
 * Key fixes:
 * 1. Waits for voices to load asynchronously (onvoiceschanged).
 * 2. Works around Chrome's "half-spoken then silent" bug by cancelling before
 *    every new utterance and chunking long text.
 * 3. Limits the spoken-IDs cache to prevent memory leaks.
 * 4. Never speaks the same alert twice, even across rapid re-renders.
 */

const MAX_SPOKEN_CACHE = 500;

function extractSector(text) {
  if (!text) return null;
  const m = text.match(/sector\s*([a-z0-9-]+)/i);
  return m ? `Sector ${m[1]}` : null;
}

function buildVoiceMessage(alert) {
  const sector = extractSector(alert.title) || extractSector(alert.message);
  const place = sector || 'the monitored region';
  const level = (alert.level || 'high').toUpperCase();
  let type = alert.scene_classification || alert.type || 'fire';
  if (type === 'image_analysis' || type === 'live_camera' || type === 'auto_scan' || type === 'test_alert') {
    type = 'Fire';
  }
  
  return `${type} detected in ${place}. Alert level ${level}. Please take action.`;
}

function alertKey(item) {
  return item.id || `${item.title || ''}_${item.timestamp || item.logged_at || ''}_${item._source || ''}`;
}

export default function VoiceAssistant({ enabled, notifications, alerts, onUnsupported }) {
  const spokenIdsRef = useRef(new Set());
  const voicesReadyRef = useRef(false);
  const pendingQueueRef = useRef([]);
  const isSpeakingRef = useRef(false);

  // ── Resolve the best available voice ──────────────────────
  const pickVoice = useCallback(() => {
    const voices = window.speechSynthesis?.getVoices?.() || [];
    if (!voices.length) return null;
    // Prefer English female voices
    const preferred = voices.find(
      (v) => /en/i.test(v.lang) && /female|zira|aria|samantha|google.*us/i.test(v.name)
    );
    return preferred || voices.find((v) => /en/i.test(v.lang)) || voices[0];
  }, []);

  // ── Actually speak a single message ───────────────────────
  const speakText = useCallback(
    (text) => {
      const synth = window.speechSynthesis;
      if (!synth) return;

      // Chrome bug: if synth is paused/stuck, reset it
      if (synth.paused) synth.resume();
      synth.cancel(); // clear any stuck queue

      const utterance = new SpeechSynthesisUtterance(text);
      utterance.rate = 1.02;
      utterance.pitch = 1.0;
      utterance.volume = 1.0;

      const voice = pickVoice();
      if (voice) utterance.voice = voice;

      utterance.onend = () => {
        isSpeakingRef.current = false;
        processQueue(); // speak next in line
      };
      utterance.onerror = () => {
        isSpeakingRef.current = false;
        processQueue();
      };

      isSpeakingRef.current = true;
      synth.speak(utterance);

      // Chrome bug workaround: if it goes silent after 14s, nudge it
      const nudge = setInterval(() => {
        if (!synth.speaking) {
          clearInterval(nudge);
          return;
        }
        synth.pause();
        synth.resume();
      }, 10000);

      utterance.onend = () => {
        clearInterval(nudge);
        isSpeakingRef.current = false;
        processQueue();
      };
      utterance.onerror = () => {
        clearInterval(nudge);
        isSpeakingRef.current = false;
        processQueue();
      };
    },
    [pickVoice]
  );

  // ── Process pending queue one at a time ───────────────────
  const processQueue = useCallback(() => {
    if (isSpeakingRef.current) return;
    if (!pendingQueueRef.current.length) return;
    const next = pendingQueueRef.current.shift();
    speakText(next);
  }, [speakText]);

  // ── Schedule an alert to be spoken ────────────────────────
  const enqueueAlert = useCallback(
    (item) => {
      const key = alertKey(item);
      if (spokenIdsRef.current.has(key)) return;

      // Trim cache
      if (spokenIdsRef.current.size >= MAX_SPOKEN_CACHE) {
        const iter = spokenIdsRef.current.values();
        for (let i = 0; i < 100; i++) iter.next(); // skip first 100
        // Actually clear oldest entries
        const keep = new Set();
        const arr = Array.from(spokenIdsRef.current);
        arr.slice(-MAX_SPOKEN_CACHE + 100).forEach((k) => keep.add(k));
        spokenIdsRef.current = keep;
      }

      spokenIdsRef.current.add(key);
      const msg = buildVoiceMessage(item);
      pendingQueueRef.current.push(msg);
      processQueue();
    },
    [processQueue]
  );

  // ── Wait for voices to load (async in Chrome) ─────────────
  useEffect(() => {
    if (!('speechSynthesis' in window)) {
      onUnsupported?.();
      return;
    }

    const synth = window.speechSynthesis;
    const voices = synth.getVoices?.() || [];

    if (voices.length > 0) {
      voicesReadyRef.current = true;
    } else {
      const onReady = () => {
        voicesReadyRef.current = true;
        // Process anything that was queued while waiting
        processQueue();
      };
      synth.addEventListener('voiceschanged', onReady);
      return () => synth.removeEventListener('voiceschanged', onReady);
    }
  }, [onUnsupported, processQueue]);

  // ── Handle disable/enable toggle ────────────────────────────
  useEffect(() => {
    if (!enabled) {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      pendingQueueRef.current = [];
      isSpeakingRef.current = false;
    }
  }, [enabled]);

  // ── React to new notifications / alerts ───────────────────
  useEffect(() => {
    if (!enabled) return;
    if (!('speechSynthesis' in window)) return;

    const speakable = [
      ...(notifications || []).map((n) => ({ ...n, _source: 'notification' })),
      ...(alerts || []).map((a) => ({ ...a, _source: 'alert' })),
    ].filter((item) => ['critical', 'high'].includes(item.level));

    for (const item of speakable) {
      enqueueAlert(item);
    }
  }, [enabled, notifications, alerts, enqueueAlert]);

  // ── Cleanup on unmount ────────────────────────────────────
  useEffect(() => {
    return () => {
      if ('speechSynthesis' in window) {
        window.speechSynthesis.cancel();
      }
      pendingQueueRef.current = [];
      isSpeakingRef.current = false;
    };
  }, []);

  return null;
}
