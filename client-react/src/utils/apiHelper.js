import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000';


export async function apiCallWithRetry(
    axiosCall,
    maxRetries = 3,
    initialDelay = 2000
  ) {
    let lastError;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        const response = await axiosCall();
        return response;
      } catch (error) {
        lastError = error;
        
        if (error.response?.status === 429) {
          throw new Error('Rate limit exceeded. Please try again later.');
        }
        
        const isColdStart = 
          error.code === 'ERR_NETWORK' || 
          error.response?.status >= 500 ||
          error.message?.includes('Network Error');
        
        if (isColdStart && attempt < maxRetries) {
          const delay = initialDelay * Math.pow(2, attempt);
          console.log(`API call failed (attempt ${attempt + 1}/${maxRetries + 1}), retrying in ${delay}ms...`);
          await new Promise(resolve => setTimeout(resolve, delay));
          continue;
        }
        
        throw error;
      }
    }
    
    throw lastError;
  }

export async function apiGet(endpoint, config = {}) {
  return apiCallWithRetry(() => 
    axios.get(`${API_URL}${endpoint}`, config)
  );
}

export async function apiPost(endpoint, data, config = {}) {
  return apiCallWithRetry(() => 
    axios.post(`${API_URL}${endpoint}`, data, config)
  );
}