export const Card = ({ children, className = '' }) => (
  <div className={`bg-white dark:bg-slate-800 rounded-lg shadow-md p-6 ${className}`}>{children}</div>
);
