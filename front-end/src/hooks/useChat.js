import { useState, useRef, useEffect } from 'react';
import { sendMessageToServer } from '../services/chatService';

export const useChat = () => {
  const [messages, setMessages] = useState([
    { id: 1, text: 'Xin chào! Tôi là trợ lý ảo, tôi có thể giúp gì cho bạn?', sender: 'bot' },
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

    const userMessage = { id: Date.now(), text: input, sender: 'user' };
    setMessages(prev => [...prev, userMessage]);
    const currentInput = input;
    setInput('');
    setIsLoading(true);

    const botReplyText = await sendMessageToServer(currentInput);

    const botMessage = { id: Date.now() + 1, text: botReplyText, sender: 'bot' };
    setMessages(prev => [...prev, botMessage]);
    setIsLoading(false);
  };

  return { messages, input, isLoading, messagesEndRef, setInput, handleSendMessage };
}
