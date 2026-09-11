import { useState, useRef, useCallback, useEffect } from 'react';
import { LanguageCode } from '../types/weather';
import { transcribeAudioBlob } from '../services/speech';

interface VoiceRecordingOptions {
  onTranscript?: (text: string, language?: string) => void;
  onError?: (errorMessage: string) => void;
}

export function useVoiceRecording(options?: VoiceRecordingOptions) {
  const [isRecording, setIsRecording] = useState<boolean>(false);
  const [isTranscribing, setIsTranscribing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const optionsRef = useRef<VoiceRecordingOptions | undefined>(options);
  optionsRef.current = options;

  // Language ref to hold target language when recording finishes
  const targetLanguageRef = useRef<LanguageCode>('auto');

  // Check MediaRecorder & mediaDevices support
  const isSupported =
    typeof window !== 'undefined' &&
    typeof navigator !== 'undefined' &&
    'mediaDevices' in navigator &&
    'getUserMedia' in navigator.mediaDevices &&
    'MediaRecorder' in window;

  // Pick best supported MIME type
  const getSupportedMimeType = (): string => {
    if (typeof MediaRecorder === 'undefined') return '';
    const preferredTypes = [
      'audio/webm;codecs=opus',
      'audio/webm',
      'audio/ogg;codecs=opus',
      'audio/ogg',
      'audio/mp4',
      'audio/wav',
    ];
    for (const type of preferredTypes) {
      if (MediaRecorder.isTypeSupported(type)) {
        return type;
      }
    }
    return '';
  };

  const cleanupStream = useCallback(() => {
    if (streamRef.current) {
      try {
        streamRef.current.getTracks().forEach((track) => track.stop());
      } catch {
        // Ignore
      }
      streamRef.current = null;
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      try {
        mediaRecorderRef.current.stop();
      } catch {
        // Ignore
      }
    }
    setIsRecording(false);
  }, []);

  const startRecording = useCallback(
    async (language: LanguageCode = 'auto') => {
      setError(null);
      targetLanguageRef.current = language;

      if (!isSupported) {
        const msg = "Voice recording isn't supported in this browser.";
        setError(msg);
        optionsRef.current?.onError?.(msg);
        return;
      }

      // Cleanup any dangling stream/recorder
      cleanupStream();
      audioChunksRef.current = [];

      let stream: MediaStream;
      try {
        stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        streamRef.current = stream;
      } catch (err: any) {
        let msg = 'Microphone unavailable.';
        if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
          msg = 'Microphone permission is required.';
        } else if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
          msg = 'No microphone found on your device.';
        } else if (err?.name === 'NotReadableError' || err?.name === 'TrackStartError') {
          msg = 'Microphone is already in use by another application.';
        }
        setError(msg);
        optionsRef.current?.onError?.(msg);
        setIsRecording(false);
        return;
      }

      const mimeType = getSupportedMimeType();
      let recorder: MediaRecorder;
      try {
        recorder = mimeType
          ? new MediaRecorder(stream, { mimeType })
          : new MediaRecorder(stream);
      } catch {
        cleanupStream();
        const msg = 'Could not initialize audio recorder.';
        setError(msg);
        optionsRef.current?.onError?.(msg);
        return;
      }

      mediaRecorderRef.current = recorder;
      audioChunksRef.current = [];

      recorder.ondataavailable = (event: BlobEvent) => {
        if (event.data && event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      recorder.onerror = () => {
        setIsRecording(false);
        cleanupStream();
        const msg = "Couldn't capture voice input. Try again.";
        setError(msg);
        optionsRef.current?.onError?.(msg);
      };

      recorder.onstop = async () => {
        setIsRecording(false);
        cleanupStream();

        const chunks = audioChunksRef.current;
        const totalSize = chunks.reduce((acc, c) => acc + c.size, 0);

        if (chunks.length === 0 || totalSize < 100) {
          const msg = "Couldn't hear anything. Try again.";
          setError(msg);
          optionsRef.current?.onError?.(msg);
          return;
        }

        const effectiveMime = recorder.mimeType || mimeType || 'audio/webm';
        const audioBlob = new Blob(chunks, { type: effectiveMime });
        audioChunksRef.current = [];

        // Begin transcription
        setIsTranscribing(true);
        setError(null);

        try {
          const result = await transcribeAudioBlob(
            audioBlob,
            targetLanguageRef.current !== 'auto' ? targetLanguageRef.current : undefined
          );
          setIsTranscribing(false);
          if (result.text && result.text.trim()) {
            optionsRef.current?.onTranscript?.(result.text.trim(), result.language);
          } else {
            const msg = "Couldn't hear anything. Try again.";
            setError(msg);
            optionsRef.current?.onError?.(msg);
          }
        } catch (transcribeErr: any) {
          setIsTranscribing(false);
          const msg =
            transcribeErr instanceof Error
              ? transcribeErr.message
              : 'Voice transcription failed. Please try again.';
          setError(msg);
          optionsRef.current?.onError?.(msg);
        }
      };

      try {
        recorder.start(250); // Collect chunk every 250ms
        setIsRecording(true);
      } catch {
        cleanupStream();
        setIsRecording(false);
        const msg = 'Microphone unavailable.';
        setError(msg);
        optionsRef.current?.onError?.(msg);
      }
    },
    [isSupported, cleanupStream]
  );

  useEffect(() => {
    return () => {
      stopRecording();
      cleanupStream();
    };
  }, [stopRecording, cleanupStream]);

  return {
    isSupported,
    isRecording,
    isTranscribing,
    error,
    startRecording,
    stopRecording,
    clearError: () => setError(null),
  };
}
