import { FiSend } from 'react-icons/fi';
import styles from './ChatInput.module.css';

const ChatInput = ({ input, setInput, handleSendMessage, isLoading }) => {
    return (
        <form onSubmit={handleSendMessage} className={styles.chatForm}>
            <input
                type="text"
                className={styles.textInput}
                placeholder={isLoading ? "..." : "Nhập tin nhắn của bạn..."}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                disabled={isLoading}
            />
            <button type="submit" className={styles.sendButton} disabled={isLoading}>
                <FiSend />
            </button>
        </form>
    );
};
export default ChatInput;