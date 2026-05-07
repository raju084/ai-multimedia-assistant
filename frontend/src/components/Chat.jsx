import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Send, File as FileIcon, Play } from 'lucide-react';

const Chat = ({ onJumpToTime, activeMedia }) => {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');

  const fetchMessages = async () => {
    if (!activeMedia) {
      setMessages([]);
      return;
    }
    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://ai-multimedia-backend.onrender.com';
      const res = await axios.get(`${apiUrl}/api/chat/?document_id=${activeMedia.id}`);
      setMessages(res.data);
    } catch (error) {
      console.error('Failed to fetch messages');
    }
  };

  useEffect(() => {
    fetchMessages();
  }, [activeMedia]);

  const sendMessage = async () => {
    if (!input.trim() || !activeMedia) return;
    
    const newMsg = { 
      role: 'user', 
      content: input,
      referenced_document: activeMedia.id 
    };
    
    // Optimistic update
    setMessages(prev => [...prev, newMsg]);
    setInput('');

    try {
      const apiUrl = import.meta.env.VITE_API_URL || 'https://ai-multimedia-backend.onrender.com';
      await axios.post(`${apiUrl}/api/chat/`, newMsg);
      fetchMessages(); 
    } catch (error) {
      console.error('Failed to send message');
    }
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>AI Chat</h2>
        {activeMedia && (
          <div className="active-doc-badge">
            <FileIcon size={12} /> {activeMedia.title}
          </div>
        )}
      </div>
      <div className="chat-history">
        {messages.map((msg, idx) => (
          <div key={idx} className={`message ${msg.role}`}>
            <p>{msg.content}</p>
            {msg.referenced_timestamp !== null && msg.referenced_timestamp !== undefined && (
              <button 
                className="jump-btn" 
                onClick={() => onJumpToTime(msg.referenced_timestamp)}
              >
                <Play size={14} fill="currentColor" /> Play at {Math.floor(msg.referenced_timestamp / 60)}:{(msg.referenced_timestamp % 60).toFixed(0).padStart(2, '0')}
              </button>
            )}
          </div>
        ))}
      </div>
      <div className="chat-input">
        <input 
          value={input} 
          onChange={(e) => setInput(e.target.value)} 
          onKeyDown={(e) => e.key === 'Enter' && sendMessage()}
          placeholder={activeMedia ? "Ask a question about your files..." : "Please select a file to start chatting"}
          disabled={!activeMedia}
        />
        <button onClick={sendMessage} disabled={!activeMedia}><Send size={18} /></button>
      </div>
    </div>
  );
};

export default Chat;
