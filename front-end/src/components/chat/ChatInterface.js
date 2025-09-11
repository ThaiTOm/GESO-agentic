import React from 'react';
import { useChat } from '../../hooks/useChat';

import ChatHeader from './ChatHeader';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';
import styles from './ChatInterface.module.css';

const ChatInterface = () => {
    // --- MODIFIED: Destructure all the new state and setters from useChat ---
    const {
        messages,
        input,
        isLoading,
        chatbotList,
        selectedApiKey,
        setSelectedApiKey,
        messagesEndRef,
        setInput,
        handleSendMessage,
        userId,
        setUserId,
        userRole,
        setUserRole,
    } = useChat();

    return (
        <div className={styles.chatContainer}>
            {/* --- MODIFIED: Pass the new props down to the ChatHeader --- */}
            <ChatHeader
                chatbotList={chatbotList}
                selectedApiKey={selectedApiKey}
                setSelectedApiKey={setSelectedApiKey}
                isLoading={isLoading}
                userId={userId}
                setUserId={setUserId}
                userRole={userRole}
                setUserRole={setUserRole}
            />

            {/* --- NO CHANGES to the rest of the component --- */}
            <main className={styles.messagesArea}>
                {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                ))}

                {isLoading && (
                    <div className={styles.messageWrapperBot}>
                         <div className={styles.typingIndicator}>
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </main>

            <footer className={styles.inputArea}>
                <ChatInput
                    input={input}
                    setInput={setInput}
                    handleSendMessage={handleSendMessage}
                    isLoading={isLoading}
                    selectedApiKey={selectedApiKey}
                />
            </footer>
        </div>
    );
};

export default ChatInterface;