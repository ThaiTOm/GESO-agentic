import React from 'react';
import { useChat } from '../../hooks/useChat'; // Your main logic hook

// Import the child components
import ChatHeader from './ChatHeader';
import ChatMessage from './ChatMessage';
import ChatInput from './ChatInput';

// Import the CSS module for styling this component's layout
import styles from './ChatInterface.module.css';

const ChatInterface = () => {
    // Call the useChat hook to get all the state and functions we need.
    // We are destructuring the new `selectedApiKey` and its setter.
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
    } = useChat();

    return (
        <div className={styles.chatContainer}>
            {/*
              The header component is responsible for displaying the dropdown.
              We pass it the list of bots, the currently selected key, the function
              to update the key, and the loading state.
            */}
            <ChatHeader
                chatbotList={chatbotList}
                selectedApiKey={selectedApiKey}
                setSelectedApiKey={setSelectedApiKey}
                isLoading={isLoading}
            />

            {/*
              The main area for displaying messages.
              It scrolls automatically thanks to the messagesEndRef.
            */}
            <main className={styles.messagesArea}>
                {messages.map((msg) => (
                    <ChatMessage key={msg.id} message={msg} />
                ))}

                {/* Show a typing indicator when the bot is "thinking" */}
                {isLoading && (
                    <div className={styles.messageWrapperBot}>
                         <div className={styles.typingIndicator}>
                            <span></span><span></span><span></span>
                        </div>
                    </div>
                )}

                {/* This empty div is the target for our auto-scrolling ref */}
                <div ref={messagesEndRef} />
            </main>

            {/*
              The footer contains the input form.
              We pass it all the necessary props to function, including the
              selectedApiKey to know whether it should be enabled or not.
            */}
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