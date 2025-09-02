import styles from './ChatMessage.module.css';

const ChatMessage = ({ message }) => {
    const { text, sender } = message;
    const isBot = sender === 'bot';
    const messageClass = isBot ? styles.bot : styles.user;

    return (
        <div className={`${styles.messageRow} ${messageClass}`}>
            <div className={styles.messageBubble}>{text}</div>
        </div>
    );
};
export default ChatMessage;