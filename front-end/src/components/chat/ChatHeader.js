import React from 'react';
import styles from './ChatHeader.module.css';
import { FiUser, FiShield } from 'react-icons/fi'; // Icons for the inputs

// --- MODIFIED: Added props for userId, setUserId, userRole, setUserRole ---
const ChatHeader = ({
    chatbotList,
    selectedApiKey,
    setSelectedApiKey,
    isLoading,
    userId,
    setUserId,
    userRole,
    setUserRole,
}) => {

    const handleChatbotChange = (e) => {
        setSelectedApiKey(e.target.value);
    };

    return (
        <header className={styles.chatHeader}>
            {/* Chatbot Selector - No changes here */}
            <div className={styles.selectorContainer}>
                <label htmlFor="chatbot-select">Chọn Chatbot:</label>
                <select
                    id="chatbot-select"
                    value={selectedApiKey}
                    onChange={handleChatbotChange}
                    disabled={isLoading || !chatbotList || chatbotList.length === 0}
                    className={styles.chatbotSelect}
                >
                    <option value="" disabled>-- Vui lòng chọn --</option>
                    {chatbotList && chatbotList.map((bot) => (
                        <option key={bot.chatbot_api_key} value={bot.chatbot_api_key}>
                            {bot.name}
                        </option>
                    ))}
                </select>
            </div>

            {/* --- NEW: Container for User ID and Role inputs --- */}
            <div className={styles.userSettings}>
                {/* User ID Input with Tooltip */}
                <div className={styles.inputWrapper} title="Nhập User ID để lọc dữ liệu dành riêng cho bạn.">
                    <FiUser className={styles.icon} />
                    <input
                        type="text"
                        value={userId}
                        onChange={(e) => setUserId(e.target.value)}
                        placeholder="User ID"
                        className={styles.userInput}
                        disabled={isLoading}
                        aria-label="User ID"
                    />
                </div>
                {/* User Role Input with Tooltip */}
                <div className={styles.inputWrapper} title="Nhập vai trò (role) của bạn để truy cập các tài liệu được phân quyền.">
                    <FiShield className={styles.icon} />
                    <input
                        type="text"
                        value={userRole}
                        onChange={(e) => setUserRole(e.target.value)}
                        placeholder="User Role"
                        className={styles.userInput}
                        disabled={isLoading}
                        aria-label="User Role"
                    />
                </div>
            </div>
        </header>
    );
};

export default ChatHeader;