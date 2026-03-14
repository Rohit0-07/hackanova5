import axios from 'axios';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const pipelineApi = {
  analyze: (query, options = {}) => api.post('/pipeline/analyze', { query, ...options }),
  getStatus: (sessionId) => api.get(`/pipeline/status/${sessionId}`),
  getResults: (sessionId) => api.get(`/pipeline/results/${sessionId}`),
  listSessions: () => api.get('/pipeline/sessions'),
  streamUpdates: (sessionId, onMessage, onError) => {
    const eventSource = new EventSource(`${API_BASE_URL}/pipeline/stream/${sessionId}`);
    
    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      onMessage(data);
      if (data.status === 'completed' || data.status === 'failed') {
        eventSource.close();
      }
    };
    
    eventSource.onerror = (err) => {
      onError(err);
      eventSource.close();
    };
    
    return () => eventSource.close();
  }
};

export const chatApi = {
  sendMessage: (sessionId, message) => api.post(`/chat/${sessionId}/chat`, { message }),
};
