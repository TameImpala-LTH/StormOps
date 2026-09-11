/**
 * Frontend speech API service for sending audio recordings to FastAPI /api/speech/transcribe.
 */

import axios from 'axios';

export interface TranscriptionResponse {
  text: string;
  language?: string;
}

export const transcribeAudioBlob = async (
  audioBlob: Blob,
  language?: string
): Promise<TranscriptionResponse> => {
  const formData = new FormData();
  // Determine appropriate filename extension based on blob mime type
  const mimeType = audioBlob.type || 'audio/webm';
  let filename = 'audio.webm';
  if (mimeType.includes('ogg')) {
    filename = 'audio.ogg';
  } else if (mimeType.includes('wav')) {
    filename = 'audio.wav';
  } else if (mimeType.includes('mp4')) {
    filename = 'audio.mp4';
  }

  formData.append('file', audioBlob, filename);
  if (language && language !== 'auto') {
    formData.append('language', language);
  }

  try {
    const response = await axios.post<TranscriptionResponse>('/api/speech/transcribe', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
      timeout: 25000,
    });
    return response.data;
  } catch (error) {
    if (axios.isAxiosError(error) && error.response) {
      throw new Error(error.response.data?.detail || 'Voice transcription failed. Please try again.');
    }
    throw new Error('Network error during voice transcription.');
  }
};
