import { useState, useEffect, useRef, useCallback } from 'react';
import { LanguageCode } from '../types/weather';

interface SpeechRecognitionOptions {
  onResult?: (transcript: string) => void;
  onEnd?: () => void;
}

interface IWindow extends Window {
  SpeechRecognition?: any;
  webkitSpeechRecognition?: any;
}

export function useSpeechRecognition(options?: SpeechRecognitionOptions) {
  const [isListening, setIsListening] = useState<boolean>(false);
  const [isCapturingSpeech, setIsCapturingSpeech] = useState<boolean>(false);
  const [transcript, setTranscript] = useState<string>('');
  const [error, setError] = useState<string | null>(null);

  const recognitionRef = useRef<any>(null);
  const optionsRef = useRef<SpeechRecognitionOptions | undefined>(options);
  optionsRef.current = options;

  const isSupported =
    typeof window !== 'undefined' &&
    Boolean((window as IWindow).SpeechRecognition || (window as IWindow).webkitSpeechRecognition);

  const getLocaleForLanguage = (lang: LanguageCode): string => {
    switch (lang) {
      case 'hi':
        return 'hi-IN';
      case 'bn':
        return 'bn-IN';
      case 'ta':
        return 'ta-IN';
      case 'te':
        return 'te-IN';
      case 'mr':
        return 'mr-IN';
      case 'en':
      case 'auto':
      default:
        return 'en-IN';
    }
  };

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore
        }
      }
    }
    setIsListening(false);
    setIsCapturingSpeech(false);
  }, []);

  const startListening = useCallback(
    (lang: LanguageCode = 'en') => {
      if (!isSupported) {
        setError("Voice input isn't supported in this browser.");
        return;
      }

      // Stop any lingering instance before creating a new one
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore
        }
        recognitionRef.current = null;
      }

      const SpeechRecognitionClass =
        (window as IWindow).SpeechRecognition || (window as IWindow).webkitSpeechRecognition;

      let recognition: any;
      try {
        recognition = new SpeechRecognitionClass();
      } catch {
        setError('Could not initialize speech recognition.');
        return;
      }

      recognitionRef.current = recognition;

      // Configuration
      recognition.continuous = false;
      recognition.interimResults = true;
      recognition.maxAlternatives = 1;
      recognition.lang = getLocaleForLanguage(lang);

      setError(null);

      // Event handlers
      recognition.onstart = () => {
        setIsListening(true);
        setIsCapturingSpeech(false);
        setError(null);
      };

      recognition.onspeechstart = () => {
        setIsCapturingSpeech(true);
      };

      recognition.onspeechend = () => {
        setIsCapturingSpeech(false);
      };

      recognition.onresult = (event: any) => {
        let finalChunk = '';
        let interimChunk = '';

        for (let i = 0; i < event.results.length; ++i) {
          const res = event.results[i];
          if (res.isFinal) {
            finalChunk += res[0].transcript;
          } else {
            interimChunk += res[0].transcript;
          }
        }

        const fullText = (finalChunk + interimChunk).trim();

        if (fullText) {
          setTranscript(fullText);
          if (optionsRef.current?.onResult) {
            optionsRef.current.onResult(fullText);
          }
        }
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        setIsCapturingSpeech(false);

        let errMsg: string | null = null;
        switch (event.error) {
          case 'not-allowed':
          case 'service-not-allowed':
            errMsg = 'Microphone permission is required.';
            break;
          case 'no-speech':
            errMsg = "Couldn't hear anything. Try again.";
            break;
          case 'audio-capture':
            errMsg = 'Microphone unavailable.';
            break;
          case 'network':
            errMsg = 'Network error during voice recognition.';
            break;
          case 'aborted':
            // Aborted intentionally by user stop or instance reset; do not display error
            errMsg = null;
            break;
          default:
            errMsg = "Couldn't capture voice input. Try again.";
            break;
        }

        if (errMsg) {
          setError(errMsg);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
        setIsCapturingSpeech(false);
        if (optionsRef.current?.onEnd) {
          optionsRef.current.onEnd();
        }
      };

      try {
        recognition.start();
      } catch (err: any) {
        setIsListening(false);
        setIsCapturingSpeech(false);
        setError('Microphone unavailable.');
      }
    },
    [isSupported]
  );

  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch {
          // Ignore
        }
        recognitionRef.current = null;
      }
    };
  }, []);

  return {
    isSupported,
    isListening,
    isCapturingSpeech,
    transcript,
    error,
    startListening,
    stopListening,
    clearError: () => setError(null),
  };
}
