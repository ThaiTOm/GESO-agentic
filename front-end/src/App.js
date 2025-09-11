import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import HomePage from './pages/HomePage';
// Make sure you have this layout component
import AppLayout from './layouts/AppLayout';
// Make sure you're importing the right chat component
import ChatInterface from './components/chat/ChatInterface';
import AdminPage from './pages/AdminPage';
import ChatbotDetailPage from './pages/ChatbotDetailPage';

function App() {
    return (
        <Router>
            <Routes>
                <Route path="/" element={<HomePage />} />
                <Route element={<AppLayout />}>
                    <Route path="/chat" element={<ChatInterface />} />
                    <Route path="/admin" element={<AdminPage />} />
                    <Route path="/admin/:chatbotName" element={<ChatbotDetailPage />} />
                </Route>
            </Routes>
        </Router>
    );
}

export default App;