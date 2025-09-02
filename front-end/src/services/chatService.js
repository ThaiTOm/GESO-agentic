import axios from 'axios';

// Khi có server thật, hãy thay thế URL này
const API_URL = 'http://your-real-api.com/chat';

const mockSendMessage = (message) => {
  console.log(`Sending to MOCK server: "${message}"`);
  return new Promise(resolve => {
    setTimeout(() => {
      const replies = [
        `Tôi đã nhận được tin nhắn: "${message}".`,
        "Cảm ơn bạn. Tôi đang xử lý yêu cầu của bạn...",
        "Đây là một câu trả lời tự động. Tôi sẽ liên hệ lại sau.",
      ];
      const reply = replies[Math.floor(Math.random() * replies.length)];
      resolve({ data: { reply } });
    }, 1500);
  });
};

export const sendMessageToServer = async (message) => {
  try {
    // Tạm thời dùng mock server để test
    const response = await mockSendMessage(message);
    return response.data.reply;
    
    // Khi có server thật, bỏ comment dòng dưới và xóa dòng trên
    // const response = await axios.post(API_URL, { message });
    // return response.data.reply;
  } catch (error) {
    console.error("Error sending message to server:", error);
    return "Rất tiếc, đã có lỗi kết nối. Vui lòng thử lại sau.";
  }
};
