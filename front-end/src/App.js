// src/App.js
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
import ChatPage from './pages/ChatPage';
import AdminPage from './pages/AdminPage';
import ChatbotDetailPage from './pages/ChatbotDetailPage'; // Import trang mới
import AppLayout from './layouts/AppLayout';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route element={<AppLayout />}>
                    <Route path="/chat" element={<ChatPage />} />
                    <Route path="/admin" element={<AdminPage />} />
                    {/* Route mới cho trang chi tiết chatbot */}
                    <Route path="/admin/:chatbotName" element={<ChatbotDetailPage />} />
                </Route>
            </Routes>
        </Router>
    );
}

export default App;