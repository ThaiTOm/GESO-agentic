import React from 'react';
import ServerResponse from '../api/ServerResponse'; // Import the new component
import styles from './ChatMessage.module.css';

const ChatMessage = ({ message }) => {
    // Determine if the message is from the user or the bot
    const isUser = message.sender === 'user';

    return (
        <div className={`${styles.messageWrapper} ${isUser ? styles.user : styles.bot}`}>
            <div className={styles.messageContent}>
                {isUser ? (
                    // User messages are always simple text from 'message.content'
                    <p>{message.content}</p>
                ) : (
                    // Bot messages are passed to ServerResponse,
                    // which handles whether it's text, analysis, or RAG
                    <ServerResponse response={message.content} />
                )}
            </div>
        </div>
    );
};

export default ChatMessage;