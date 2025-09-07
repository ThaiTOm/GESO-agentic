import { useState, useRef, useEffect } from 'react';
import { sendMessageToServer } from '../services/chatService';
import { getAllChatbots } from '../services/adminService';

export const useChat = () => {
    const [messages, setMessages] = useState([
        { id: 1, content: 'Xin chào! Vui lòng chọn một chatbot để bắt đầu.', sender: 'bot' },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    // --- CHANGED: State management is now based on API keys ---
    const [chatbotList, setChatbotList] = useState([]);
    // This state will now store the API KEY of the selected chatbot
    const [selectedApiKey, setSelectedApiKey] = useState('');

    useEffect(() => {
        const fetchChatbots = async () => {
            try {
                const bots = await getAllChatbots();
                console.log(bots)
                setChatbotList(bots);
                // --- CHANGED: Set the API KEY of the first bot as the default ---
                if (bots && bots.length > 0) {
                    setSelectedApiKey(bots[0].chatbot_api_key); // Assuming the property is named 'api_key'
                }
            } catch (error) {
                console.error("Failed to fetch chatbots:", error);
                const errorMessage = {
                    id: Date.now(),
                    content: 'Lỗi: Không thể tải danh sách chatbots.',
                    sender: 'bot'
                };
                setMessages(prev => [...prev, errorMessage]);
            }
        };

        fetchChatbots();
    }, []);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        // --- CHANGED: Check for a selected API key ---
        if (input.trim() === '' || isLoading || !selectedApiKey) {
            if (!selectedApiKey) {
                alert('Vui lòng chọn một chatbot trước khi gửi tin nhắn!');
            }
            return;
        }

        const userMessage = { id: Date.now(), content: input, sender: 'user' };
        const updatedMessages = [...messages, userMessage];
        setMessages(updatedMessages);

        const currentInput = input;
        setInput('');
        setIsLoading(true);

        // --- CHANGED: Pass the selected API KEY to the server function ---
        const botReplyData = await sendMessageToServer(currentInput, updatedMessages, selectedApiKey);

        const botMessage = { id: Date.now() + 1, content: botReplyData, sender: 'bot' };
        setMessages(prev => [...prev, botMessage]);
        setIsLoading(false);
    };

    // --- CHANGED: Return the new state variables and their setters ---
    return {
        messages,
        input,
        isLoading,
        chatbotList,
        selectedApiKey,      // Return the key
        setSelectedApiKey,   // Return the setter for the key
        messagesEndRef,
        setInput,
        handleSendMessage
    };
}