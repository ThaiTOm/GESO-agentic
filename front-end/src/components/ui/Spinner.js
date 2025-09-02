import React from 'react';

// Thêm CSS cho Spinner vào file src/index.css
// @keyframes bounce { 0%, 80%, 100% { transform: scale(0); } 40% { transform: scale(1.0); } }
// .dot { animation: bounce 1.4s infinite ease-in-out both; }
// .dot-1 { animation-delay: -0.32s; }
// .dot-2 { animation-delay: -0.16s; }

const Spinner = () => (
  <div className="flex space-x-1.5">
    <div className="w-2 h-2 bg-slate-400 rounded-full dot dot-1"></div>
    <div className="w-2 h-2 bg-slate-400 rounded-full dot dot-2"></div>
    <div className="w-2 h-2 bg-slate-400 rounded-full dot"></div>
  </div>
);
export default Spinner;
