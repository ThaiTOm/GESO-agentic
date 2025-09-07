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
    const [conversationSummary, setConversationSummary] = useState('');


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
        const botReplyData = await sendMessageToServer(
                    currentInput,
                    updatedMessages,
                    conversationSummary, // Pass the summary from state
                    selectedApiKey
        );
        // Check if the reply is valid before proceeding
        if (botReplyData) {
            // --- MODIFICATION 3: Extract data and update ALL relevant state ---

            // The AI's answer for the UI
            const botMessageContent = botReplyData.response;
            const botMessage = { id: Date.now() + 1, content: botMessageContent, sender: 'bot' };
            setMessages(prev => [...prev, botMessage]);

            // CRITICAL: Update the summary state for the NEXT turn
            setConversationSummary(botReplyData.conversation_summary);

            // Note: We don't need to update `messages` from `botReplyData.chat_history`
            // because we are already managing the UI messages locally. The backend
            // uses the history we send it, which is correct.
        } else {
            // Handle cases where botReplyData is undefined (e.g., from an error)
            const errorMessage = { id: Date.now() + 1, content: "Đã có lỗi xảy ra khi nhận phản hồi.", sender: 'bot' };
            setMessages(prev => [...prev, errorMessage]);
        }

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