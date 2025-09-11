import React from 'react';
import styles from './ChatMessage.module.css';
import ServerResponse from '../api/ServerResponse'; // Make sure this path is correct

const ChatMessage = ({ message }) => {
    const isUser = message.sender === 'user';
    const wrapperClass = isUser ? styles.messageWrapperUser : styles.messageWrapperBot;
    const messageClass = isUser ? styles.userMessage : styles.botMessage;

    const renderContent = () => {
        // For user messages or simple string bot messages (like errors or "Hello")
        if (isUser || typeof message.content === 'string') {
            return <div className={styles.text_content}>{message.content}</div>;
        }

        // For complex bot responses (which are objects), use ServerResponse
        if (typeof message.content === 'object' && message.content !== null) {
            return <ServerResponse response={message.content} />;
        }

        // Fallback for any unexpected content type
        return <div className={styles.text_content}>Unsupported message format.</div>;
    };

    return (
        <div className={wrapperClass}>
            <div className={messageClass}>
                {renderContent()}
            </div>
        </div>
    );
};

export default ChatMessage;