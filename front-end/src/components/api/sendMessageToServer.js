import axios from 'axios';

// Define the base URL for your APIs
const API_BASE_URL = "http://localhost:8000/api/v1";

/**
 * A more robust function to send messages to the server.
 * It now handles different endpoints based on the message content.
 *
 * @param {string} message The user's message.
 * @returns {Promise<any>} The response data from the server.
 */
export const sendMessageToServer = async (message) => {
    try {
        let response;
        // Simple logic to decide which endpoint to call.
        // You can make this more sophisticated (e.g., using keywords).
        if (message.toLowerCase().includes("analyze") || message.toLowerCase().includes("trend")) {
            console.log("Calling data analysis endpoint...");
            response = await axios.get(`${API_BASE_URL}/analysis`, {
                params: { aggregation_level: 'quarterly' } // Or 'monthly'
            });
            // The analysis endpoint directly returns the object we need
            return response.data;
        } else {
            console.log("Calling RAG endpoint...");
            // Replace with your actual RAG endpoint and payload structure
            response = await axios.post(`${API_BASE_URL}/rag-endpoint`, { query: message });
            // Assuming the RAG response is nested under a "response" key
            return response.data.response;
        }
    } catch (error) {
        console.error("Error sending message to server:", error);
        if (error.response) {
            // The request was made and the server responded with a status code
            // that falls out of the range of 2xx
            return `Error: ${error.response.data.detail || error.message}`;
        } else if (error.request) {
            // The request was made but no response was received
            return "Could not connect to the server. Please check your connection and try again.";
        } else {
            // Something happened in setting up the request that triggered an Error
            return "An unexpected error occurred. Please try again later.";
        }
    }
};