import axios from 'axios';

// The endpoint for the orchestrator
const ORCHESTRATE_API_URL = 'http://ai.tvssolutions.vn:8001/orchestrate';

// --- Configuration ---
const USER_ID = "duythai";
const USER_ROLE = "duythai";

/**
 * Formats the message history for the API.
 * The API expects a simple { role, content } format with text only.
 * @param {Array<Object>} messages - The message array from the useChat hook.
 * @returns {Array<{role: string, content: string}>}
 */
const formatChatHistory = (messages) => {
    // We filter out the very first "Hello!" message from the bot,
    // as it's not part of the actual conversation history.
    // You might adjust this logic based on your needs.
    const actualConversation = messages.slice(1);

    return actualConversation.map(msg => {
        const role = msg.sender === 'user' ? 'user' : 'assistant';

        let content = '';
        if (typeof msg.content === 'string') {
            content = msg.content;
        } else if (typeof msg.content === 'object' && msg.content !== null) {
            content = msg.content.answer || msg.content.text_summary_for_llm || '[Data was displayed]';
        }

        return { role, content };
    });
};

/**
 * Sends a query and the chat context to the main orchestrator endpoint.
 * @param {string} message - The current user input.
 *  @param {Array<Object>} chatHistory - The entire history of messages from the chat state.
 * @param {string} conversationSummary - The running summary of the conversation. // <-- NEW PARAMETER
 * @param {string} api_key - The API key for the selected chatbot.
 * @param {string} userId - // <-- NEW DYNAMIC PARAMETER
 * @param {string} userRole - // <-- NEW DYNAMIC PARAMETE
 * @returns {Promise<any>} A promise that resolves to the server's FULL response object.
 */
export const sendMessageToServer = async (message, chatHistory, conversationSummary, api_key, userId, userRole) => {
    const formattedHistory = formatChatHistory(chatHistory);

    const payload = {
        query: message,
        // MODIFIED: Use the parameters instead of constants
        user_role: userRole,
        user_id: userId,
        api_key: api_key,
        top_k: 10,
        include_sources: true,
        chat_history: formattedHistory,
        conversation_summary: conversationSummary,
        prompt_from_user: "",
        cloud_call: true,
        voice: false
    };

    console.log("Sending payload to orchestrator:", payload);

    try {
        const response = await axios.post(ORCHESTRATE_API_URL, payload);
        return response.data;
    } catch (error) {
        console.error("Error sending message to orchestrator:", error);
        if (error.response) {
            return `Lỗi từ máy chủ: ${error.response.data.detail || error.message}`;
        } else if (error.request) {
            return "Không thể kết nối tới máy chủ. Vui lòng kiểm tra lại kết nối.";
        } else {
            return "Đã có lỗi xảy ra. Vui lòng thử lại.";
        }
    }
};
