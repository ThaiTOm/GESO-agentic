import { FiSend } from 'react-icons/fi';
import styles from './ChatInput.module.css';

// --- CHANGED: Prop renamed to `selectedApiKey` for consistency ---
const ChatInput = ({ input, setInput, handleSendMessage, isLoading, selectedApiKey }) => {

    // The logic remains the same, it just checks for a truthy value
    const isDisabled = isLoading || !selectedApiKey;

    return (
        <form onSubmit={handleSendMessage} className={styles.chatForm}>
            <input
                type="text"
                className={styles.textInput}
                placeholder={!selectedApiKey ? "Vui lòng chọn một chatbot để bắt đầu" : (isLoading ? "..." : "Nhập tin nhắn của bạn...")}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isDisabled}
            />
            <button type="submit" className={styles.sendButton} disabled={isDisabled}>
                <FiSend />
            </button>
        </form>
    );
};
export default ChatInput;