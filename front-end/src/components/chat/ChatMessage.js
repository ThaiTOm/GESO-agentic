import React from 'react';
import styles from './ChatMessage.module.css';
import ServerResponse from '../api/ServerResponse';

const ChatMessage = ({ message }) => {
    const isUser = message.sender === 'user';
    const wrapperClass = isUser ? styles.messageWrapperUser : styles.messageWrapperBot;
    const messageClass = isUser ? styles.userMessage : styles.botMessage;

    const renderContent = () => {
        // For user messages (which are already styled correctly by .userMessage)
        if (isUser) {
            return message.content;
        }

        // For simple string bot messages (like errors or "Hello")
        if (typeof message.content === 'string') {
            // THE FIX: Wrap simple text in a div with the new .textContent class
            return <div className={styles.textContent}>{message.content}</div>;
        }

        // For complex bot responses (which are objects)
        if (typeof message.content === 'object' && message.content !== null) {
            // ServerResponse will now correctly fill the padding-less .botMessage bubble
            return <ServerResponse response={message.content} />;
        }

        // Fallback for any unexpected content type
        return <div className={styles.textContent}>Unsupported message format.</div>;
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