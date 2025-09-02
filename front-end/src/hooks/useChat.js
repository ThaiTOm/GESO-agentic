import { useState, useRef, useEffect } from 'react';
import { sendMessageToServer } from '../services/chatService';

export const useChat = () => {
    const [messages, setMessages] = useState([
        { id: 1, content: 'Xin chào! Tôi là trợ lý ảo, tôi có thể giúp gì cho bạn?', sender: 'bot' },
    ]);
    const [input, setInput] = useState('');
    const [isLoading, setIsLoading] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSendMessage = async (e) => {
        e.preventDefault();
        if (input.trim() === '' || isLoading) return;

        const userMessage = { id: Date.now(), content: input, sender: 'user' };
        const updatedMessages = [...messages, userMessage]; // Get the most recent message list
        setMessages(updatedMessages);

        const currentInput = input;
        setInput('');
        setIsLoading(true);

        // *** THIS IS THE ONLY LINE THAT CHANGES ***
        // We now pass the current input AND the updated message history to the server.
        const botReplyData = await sendMessageToServer(currentInput, updatedMessages);

        const botMessage = { id: Date.now() + 1, content: botReplyData, sender: 'bot' };
        setMessages(prev => [...prev, botMessage]);
        setIsLoading(false);
    };

    return { messages, input, isLoading, messagesEndRef, setInput, handleSendMessage };
}