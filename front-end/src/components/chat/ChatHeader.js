import React from 'react';
import styles from './ChatHeader.module.css';

// --- CHANGED: Props are now `selectedApiKey` and `setSelectedApiKey` ---
const ChatHeader = ({ chatbotList, selectedApiKey, setSelectedApiKey, isLoading }) => {

    const handleChatbotChange = (e) => {
        setSelectedApiKey(e.target.value);
    };

    return (
        <header className={styles.chatHeader}>
            <div className={styles.selectorContainer}>
                <label htmlFor="chatbot-select">Chọn Chatbot:</label>
                <select
                    id="chatbot-select"
                    // --- CHANGED: The value of the select is the API key ---
                    value={selectedApiKey}
                    onChange={handleChatbotChange}
                    disabled={isLoading || chatbotList.length === 0}
                    className={styles.chatbotSelect}
                >
                    <option value="" disabled>-- Vui lòng chọn --</option>
                    {chatbotList.map((bot) => (
                        // --- CRITICAL CHANGE ---
                        // The value is the bot's api_key
                        // The text shown to the user is the bot's name
                        <option key={bot.api_key} value={bot.chatbot_api_key}>
                            {bot.name}
                        </option>
                    ))}
                </select>
            </div>
        </header>
    );
};

export default ChatHeader;