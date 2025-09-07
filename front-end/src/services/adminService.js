// src/services/adminService.js
import axios from 'axios';

// !!! QUAN TRỌNG: Thay thế bằng URL backend FastAPI của bạn
const API_BASE_URL = 'http://ai.tvssolutions.vn:2111/api/v1';

// --- Quản lý Chatbot ---
export const getAllChatbots = async () => {
    const response = await axios.get(`${API_BASE_URL}/typesense/chatbot/all`);
    return response.data.chatbots;
};

export const createChatbot = async (name, description = '') => {
    const response = await axios.post(`${API_BASE_URL}/typesense/chatbot/create`, { name, description });
    return response.data.chatbot;
};

export const deleteChatbot = async (chatbotName) => {
    const response = await axios.delete(`${API_BASE_URL}/typesense/chatbot/delete/${chatbotName}`);
    return response.data;
};

// --- Quản lý Tài liệu ---
export const getDocumentsByChatbot = async (chatbotName) => {
    const response = await axios.get(`${API_BASE_URL}/typesense/document/${chatbotName}`);
    return response.data.documents; // Trả về mảng các chunks
};

export const uploadDocument = async (chatbotName, file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await axios.post(
        `${API_BASE_URL}/typesense/document/upload/${chatbotName}`,
        formData,
        { headers: { 'Content-Type': 'multipart/form-data' } }
    );
    return response.data;
};

export const deleteDocument = async (chatbotName, documentTitle) => {
    const response = await axios.delete(
        `${API_BASE_URL}/typesense/document/delete/${chatbotName}/${documentTitle}`
    );
    return response.data;
};