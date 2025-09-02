import { useChat } from '../hooks/useChat';
import ChatMessage from '../components/chat/ChatMessage';
import ChatInput from '../components/chat/ChatInput';
import styles from './ChatPage.module.css';

const ChatPage = () => {
    const { messages, input, isLoading, messagesEndRef, setInput, handleSendMessage } = useChat();

    return (
        // Thay đổi class ở đây
        <div className={styles.chatPage}>
            <header className={styles.chatHeader}>
                <h1>Tư vấn viên AI</h1>
            </header>
            <div className={styles.messageList}>
                {messages.map((msg) => <ChatMessage key={msg.id} message={msg} />)}
                {isLoading && <div className={styles.typingIndicator}>Bot đang trả lời...</div>}
                <div ref={messagesEndRef} />
            </div>
            <div className={styles.inputArea}>
                <ChatInput input={input} setInput={setInput} handleSendMessage={handleSendMessage} isLoading={isLoading} />
            </div>
        </div>
    );
};
export default ChatPage;