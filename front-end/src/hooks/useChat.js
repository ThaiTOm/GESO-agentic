import { useState, useRef, useEffect, useCallback } from 'react';
import { sendMessageToServer } from '../services/chatService';
import { getAllChatbots } from '../services/adminService';

export const useChat = () => {
    // --- STATE MANAGEMENT ---
    const [userId, setUserId] = useState('duythai');
    const [userRole, setUserRole] = useState('duythai');
    const [messages, setMessages] = useState([
        { id: 'initial', content: 'Xin chào! Bạn cần tôi giúp gì?', sender: 'bot' }
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const [chatbotList, setChatbotList] = useState([]);
    const [selectedApiKey, setSelectedApiKey] = useState('');
    const messagesEndRef = useRef(null);
    const conversationSummary = useRef('');

    // ================== THIS IS THE RESTORED LOGIC ==================
    // Effect to fetch the chatbot list on initial load
    useEffect(() => {
        const fetchBots = async () => {
            console.log("Attempting to fetch chatbot list...");
            try {
                const bots = await getAllChatbots();
                if (Array.isArray(bots)) {
                    console.log("Successfully fetched chatbots:", bots);
                    setChatbotList(bots);
                } else {
                    console.error("Failed to fetch bots: API did not return an array.", bots);
                    setMessages(prev => [...prev, {
                        id: 'error_fetch_bots_format',
                        content: 'Lỗi: Dữ liệu chatbot nhận được không hợp lệ.',
                        sender: 'bot', isError: true
                    }]);
                }
            } catch (error) {
                console.error("CRITICAL ERROR while fetching chatbot list:", error);
                setMessages(prev => [...prev, {
                    id: 'error_fetch_bots_network',
                    content: 'Lỗi: Không thể tải danh sách chatbots. Vui lòng kiểm tra kết nối và thử lại.',
                    sender: 'bot', isError: true
                }]);
            }
        };

        fetchBots();
    }, []); // Empty dependency array ensures this runs only once on mount
    // ==================================================================

    // --- EFFECT FOR AUTO-SCROLLING ---
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    }, [messages]);

    // --- MAIN FUNCTION TO SEND A MESSAGE (Integrates ServerResponse) ---
    const handleSendMessage = useCallback(async (e) => {
        if (e) e.preventDefault();
        if (!input.trim() || isLoading || !selectedApiKey) return;

        const userMessage = { id: Date.now(), content: input, sender: 'user' };
        setMessages(prev => [...prev, userMessage]);
        const currentInput = input;
        setInput('');
        setIsLoading(true);

        try {
            const response = await sendMessageToServer(
                currentInput, messages, conversationSummary.current,
                selectedApiKey, userId, userRole
            );

            if (response && response.conversation_summary) {
                conversationSummary.current = response.conversation_summary;
            }

            const botContent = typeof response === 'string'
                ? response // Handle simple error strings
                : response.response; // Store the full object for ServerResponse

            const botResponse = {
                id: Date.now() + 1,
                content: botContent, // Content can be an OBJECT or a string
                sender: 'bot',
                isError: typeof response === 'string',
            };
            setMessages(prev => [...prev, botResponse]);
        } catch (error) {
            console.error("Error in handleSendMessage:", error);
            const errorMsg = { id: Date.now() + 1, content: 'Đã có lỗi không mong muốn xảy ra.', sender: 'bot', isError: true };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setIsLoading(false);
        }
    }, [input, isLoading, selectedApiKey, messages, userId, userRole]);

    return {
        messages, input, isLoading, chatbotList, selectedApiKey,
        setSelectedApiKey, messagesEndRef, setInput, handleSendMessage,
        userId, setUserId, userRole, setUserRole,
    };
};