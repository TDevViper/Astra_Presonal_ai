export default function ChatMessage({ message, isUser }) {
  const getEmotionEmoji = (emotion) => {
    const emojis = {
      joy: '😊',
      sad: '😢',
      angry: '😠',
      anxious: '😰',
      tired: '😴',
      surprised: '😲',
      neutral: '😐'
    };
    return emojis[emotion] || '🤖';
  };

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4`}>
      <div
        className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
          isUser
            ? 'bg-blue-500 text-white'
            : message.isSystem
            ? 'bg-yellow-100 text-yellow-800 text-sm italic'
            : 'bg-gray-200 text-gray-800'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.text}</p>
        
        {/* Metadata footer for AI messages */}
        {!isUser && !message.isSystem && (
          <div className="flex items-center gap-2 mt-2 pt-2 border-t border-gray-300 text-xs opacity-75">
            {message.emotion && (
              <span title={`Detected emotion: ${message.emotion}`}>
                {getEmotionEmoji(message.emotion)}
              </span>
            )}
            {message.agent && (
              <span className="text-xs">
                via {message.agent}
              </span>
            )}
          </div>
        )}
      </div>
    </div>
  );
}